from __future__ import annotations

import os
import time
import json
from pathlib import Path
from typing import List, Tuple, Dict

from .splitter import ArticleSplitter, SentenceSegment
from .cache import CacheManager, CacheEntry
from .audio_generator import AudioGenerator, VoiceConfig  # type: ignore
from .subtitle_generator import SubtitleGenerator, SubtitleEntry
from .concatenator import FileConcatenator
from .config import Config, VoiceConfig as VoiceCfg
from pydub import AudioSegment


class GenerationPipeline:
    def __init__(self, config: Config):
        self.config = config
        self.splitter = ArticleSplitter(max_length=config.max_sentence_length)
        # Defer AudioGenerator creation until we know which voices are used in
        # the input article. This avoids loading or preparing unused voices.
        self.audio_gen = None
        self.subtitle_gen = SubtitleGenerator()
        self.concater = FileConcatenator()
        self.voices = config.voices  # Dict[str, VoiceCfg]
        # Prepare task id and cache
        self.cache = None  # type: ignore

    def _load_article(self) -> str:
        path = Path(self.config.input_article)
        if not path.exists():
            raise FileNotFoundError(f"Article not found: {self.config.input_article}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _process_segments(self, article_text: str) -> Tuple[List[SentenceSegment], List[SubtitleEntry]]:
        segments = self.splitter.split(article_text)
        # Build placeholder subtitles list; actual times set after durations computed
        entries: List[SubtitleEntry] = []
        current_start = 0.0
        for seg in segments:
            # We'll fill durations later; for now, use 0 as placeholder
            duration = 0.0
            entries.append(SubtitleEntry(index=seg.index+1, start_time=current_start, end_time=current_start+duration, text=seg.text))
            current_start += duration
        return segments, entries

    def run(self) -> Tuple[str, str]:
        article_text = self._load_article()
        segments = self.splitter.split(article_text)
        if not segments:
            raise ValueError("No segments produced from article.")

        # Determine which voices are referenced in the article and build a
        # trimmed voices map to pass to the TTS engine. Default voice is
        # 'f-a/tender' if present; otherwise fall back to config 'main'.
        referenced = set(s.voice_name for s in segments if s.voice_name)
        voices_for_tts = {}
        default_key = "f-a/tender"
        for vkey in referenced:
            if self.voices and vkey in self.voices:
                voices_for_tts[vkey] = self.voices[vkey]

        # Ensure default tender is available in the voices passed to TTS
        if default_key not in voices_for_tts:
            if self.voices and default_key in self.voices:
                voices_for_tts[default_key] = self.voices[default_key]
            elif self.voices and "main" in self.voices:
                # map main to default_key internally so caller code can rely on tender
                voices_for_tts[default_key] = self.voices["main"]

        # Build a lightweight TTS config for AudioGenerator and initialize it
        from .config import Config as TTSConfig
        tts_config = TTSConfig(
            input_article=self.config.input_article,
            output_dir=self.config.output_dir,
            cache_dir=getattr(self.config, "cache_dir", ".cache"),
            max_sentence_length=self.config.max_sentence_length,
            model_name=self.config.model_name,
            nfe_step=self.config.nfe_step,
            cfg_strength=self.config.cfg_strength,
            speed=self.config.speed,
            voices=voices_for_tts,
            enable_cache=getattr(self.config, "enable_cache", True),
        )
        self.audio_gen = AudioGenerator(tts_config)
        # Force model initialization up-front so failures are explicit and we
        # don't silently generate placeholder tones for every segment.
        self.audio_gen.initialize_model()
        if self.audio_gen._tts is None:
            raise RuntimeError("Failed to initialize TTS model; aborting generation.")

        # Initialize cache with a simple task_id
        # We base task_id on article content hash and config
        article_path = str(self.config.input_article)
        from .cache import CacheManager
        # Generate a deterministic task_id by hashing content and config
        try:
            task_mgr = CacheManager(self.config.cache_dir, "tmp-task")
            task_id = task_mgr.generate_task_id(article_path, self.config)
        except Exception:
            task_id = "tmp-task"
        self.cache = CacheManager(self.config.cache_dir, task_id)
        self.cache.load_cache()

        # Output directories
        audio_dir = Path(self.config.output_dir) / "audio"
        srt_dir = Path(self.config.output_dir) / "subs"
        audio_dir.mkdir(parents=True, exist_ok=True)
        srt_dir.mkdir(parents=True, exist_ok=True)

        # Prepare to generate/collect audio files
        generated_audio_paths: List[str] = []
        entries: List[SubtitleEntry] = []
        current_time = 0.0
        # If multiple different voices are referenced, use a multi-speech path:
        unique_voices = sorted({s.voice_name for s in segments if s.voice_name})
        use_multispeech = len(unique_voices) > 1

        if use_multispeech:
            # Build speech type map: voice_name -> (ref_audio, ref_text, speed)
            speech_types: Dict[str, Tuple[str, str, float]] = {}
            for v in unique_voices:
                vc = (self.config.voices or {}).get(v)
                if vc is None:
                    # fallback to default tender or main
                    vc = (self.config.voices or {}).get("f-a/tender") or (self.config.voices or {}).get("main")
                if vc is None:
                    raise RuntimeError(f"No reference audio configured for voice '{v}'")
                ref_text = vc.ref_text
                if not ref_text:
                    txt = os.path.splitext(vc.ref_audio)[0] + ".txt"
                    if os.path.exists(txt):
                        try:
                            ref_text = open(txt, "r", encoding="utf-8").read().strip()
                        except Exception:
                            ref_text = ""
                speech_types[v] = (vc.ref_audio, ref_text or "", vc.speed if vc.speed is not None else self.config.speed)

            # Now generate per segment using the loaded model infer directly
            for seg in segments:
                ref_audio, ref_text, v_speed = speech_types.get(seg.voice_name, speech_types.get("f-a/tender"))
                audio_path = audio_dir / f"segment_{seg.index:04d}.wav"
                # Call model infer directly (model already initialized)
                wav, sr, spec = self.audio_gen._tts.infer(
                    ref_file=ref_audio,
                    ref_text=ref_text,
                    gen_text=seg.text,
                    file_wave=str(audio_path),
                    nfe_step=self.config.nfe_step,
                    cfg_strength=self.config.cfg_strength,
                    speed=v_speed,
                )
                # Some models may produce audio that contains residual frames
                # matching the reference audio (or may be clipped). To reduce
                # audible artifacts at segment boundaries we add a short
                # silence tail and apply a gentle fade-out. This also helps
                # when concatenating segments so words are not swallowed.
                try:
                    seg_audio = AudioSegment.from_wav(str(audio_path))
                    # add 150ms silence tail and 30ms fade out
                    tail_ms = 150
                    fade_ms = 30 if len(seg_audio) > 2 * 30 else 0
                    seg_audio = seg_audio + AudioSegment.silent(duration=tail_ms)
                    if fade_ms:
                        seg_audio = seg_audio.fade_out(fade_ms)
                    seg_audio.export(str(audio_path), format="wav")
                except Exception:
                    # If postprocessing fails, continue with raw wav
                    pass
                duration = len(AudioSegment.from_wav(str(audio_path))) / 1000.0
                generated_audio_paths.append(str(audio_path))
                if self.cache:
                    ce = CacheEntry(segment_index=seg.index, audio_path=str(audio_path), duration=duration, text=seg.text, voice_name=seg.voice_name, timestamp=time.time())
                    self.cache.add_entry(ce)
                ent = SubtitleEntry(index=seg.index+1, start_time=current_time, end_time=current_time+duration, text=seg.text)
                entries.append(ent)
                current_time += duration
        else:
            for seg in segments:
                voice_cfg = voices_for_tts.get(seg.voice_name)
                if voice_cfg is None:
                    # fallback to tender default
                    voice_cfg = voices_for_tts.get("f-a/tender")
                    if voice_cfg is None and self.config.voices:
                        # final fallback to config main entry
                        voice_cfg = self.config.voices.get("main")
                if voice_cfg is None:
                    raise RuntimeError(f"No voice available for segment: {seg.voice_name}")
                audio_path = audio_dir / f"segment_{seg.index:04d}.wav"
                # Check cache
                cache_entry = None
                if self.cache:
                    cache_entry = self.cache.get_entry(seg.index)
                    if cache_entry and self.cache.validate_entry(cache_entry):
                        generated_audio_paths.append(cache_entry.audio_path)
                        duration = cache_entry.duration
                        if duration:
                            ent = SubtitleEntry(index=seg.index+1, start_time=current_time, end_time=current_time+duration, text=seg.text)
                            entries.append(ent)
                            current_time += duration
                        continue
                # Perform generation; let exceptions propagate so we can fail fast
                out_path, duration = self.audio_gen.generate(seg, voice_cfg, str(audio_path))
                # Ensure a short silent tail + fade to avoid last-word artifacts
                try:
                    seg_audio = AudioSegment.from_wav(str(out_path))
                    tail_ms = 150
                    fade_ms = 30 if len(seg_audio) > 2 * 30 else 0
                    seg_audio = seg_audio + AudioSegment.silent(duration=tail_ms)
                    if fade_ms:
                        seg_audio = seg_audio.fade_out(fade_ms)
                    seg_audio.export(str(out_path), format="wav")
                    duration = len(seg_audio) / 1000.0
                except Exception:
                    # keep duration returned by generator if postprocess fails
                    pass
                generated_audio_paths.append(str(out_path))
                # Persist in cache
                if self.cache:
                    ce = CacheEntry(segment_index=seg.index, audio_path=str(out_path), duration=duration, text=seg.text, voice_name=seg.voice_name, timestamp=time.time())
                    self.cache.add_entry(ce)
                ent = SubtitleEntry(index=seg.index+1, start_time=current_time, end_time=current_time+duration, text=seg.text)
                entries.append(ent)
                current_time += duration

        # After processing all segments, save cache
        if self.cache:
            self.cache.save_cache(self.cache._cache if hasattr(self.cache, "_cache") else {})

        # Concatenate audio and subtitles
        final_audio = Path(self.config.output_dir) / "final_audio.wav"
        final_srt = Path(self.config.output_dir) / "final_output.srt"
        if generated_audio_paths:
            self.concater.concatenate_audio(generated_audio_paths, str(final_audio))
        # Write final subtitles with configurable width
        self.subtitle_gen.generate_srt(entries, str(final_srt), max_chars=self.config.subtitle_max_width)
        # Return final artifact paths
        return str(final_audio), str(final_srt)

    # Helpers used by CLI/tests
    # duplicate _load_article removed
