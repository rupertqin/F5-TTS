from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Tuple, Dict

from .splitter import ArticleSplitter, SentenceSegment
from .audio_generator import AudioGenerator, VoiceConfig  # type: ignore
from .concatenator import FileConcatenator
from .config import Config, VoiceConfig as VoiceCfg
import re
import hashlib


def _sanitize_for_filename(text: str, max_len: int = 60) -> str:
    # Basic slugify: remove punctuation, lowercase, spaces to underscores
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r"[^A-Za-z0-9\s]", "", text)
    text = text.strip().lower()
    text = re.sub(r"\s+", "_", text)
    if max_len and len(text) > max_len:
        text = text[:max_len]
    return text
def slugify_text(text: str, max_len: int = 60) -> str:
    return _sanitize_for_filename(text, max_len=max_len)
from pydub import AudioSegment


class GenerationPipeline:
    def __init__(self, config: Config):
        self.config = config
        self.splitter = ArticleSplitter(max_length=config.max_sentence_length)
        # Defer AudioGenerator creation until we know which voices are used in
        # the input article. This avoids loading or preparing unused voices.
        self.audio_gen = None
        self.concater = FileConcatenator()
        self.voices = config.voices  # Dict[str, VoiceCfg]

    def _load_article(self) -> str:
        path = Path(self.config.input_article)
        if not path.exists():
            raise FileNotFoundError(f"Article not found: {self.config.input_article}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _process_segments(self, article_text: str) -> Tuple[List[SentenceSegment], List[object]]:
        segments = self.splitter.split(article_text)
        # Placeholder subtitles list removed
        entries: List[object] = []
        current_start = 0.0
        for seg in segments:
            # We'll fill durations later; for now, use 0 as placeholder
            duration = 0.0
            # Subtitle entry creation removed
            current_start += duration
        return segments, entries

    def run(self) -> Tuple[str, str]:
        article_text = self._load_article()
        segments = self.splitter.split(article_text)
        if not segments:
            raise ValueError("No segments produced from article.")

        # Determine which voices are referenced in the article and build a
        # voices map to pass to the TTS engine. If none specified, fall back to main.
        referenced = set(s.voice_name for s in segments if s.voice_name)
        voices_for_tts = {}
        for vkey in referenced:
            if self.voices and vkey in self.voices:
                voices_for_tts[vkey] = self.voices[vkey]
        # Fallback to main voice if nothing specified
        if not voices_for_tts:
            if self.voices and "main" in self.voices:
                voices_for_tts["main"] = self.voices["main"]

        # Build a lightweight TTS config for AudioGenerator and initialize it
        from .config import Config as TTSConfig
        tts_config = TTSConfig(
            input_article=self.config.input_article,
            output_dir=self.config.output_dir,
            max_sentence_length=self.config.max_sentence_length,
            model_name=self.config.model_name,
            nfe_step=self.config.nfe_step,
            cfg_strength=self.config.cfg_strength,
            speed=self.config.speed,
            voices=voices_for_tts,
        )
        self.audio_gen = AudioGenerator(tts_config)
        # Force model initialization up-front so failures are explicit and we
        # don't silently generate placeholder tones for every segment.
        self.audio_gen.initialize_model()
        if self.audio_gen._tts is None:
            raise RuntimeError("Failed to initialize TTS model; aborting generation.")

        # Output directories
        audio_dir = Path(self.config.output_dir) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Prepare to generate/collect audio files
        generated_audio_paths: List[str] = []
        per_segment_audio_paths: List[str] = []
        entries: List[object] = []
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
                    # Fall back to root speech.txt if present
                    if not ref_text:
                        root_speech = Path(__file__).resolve().parents[2] / "speech.txt"
                        if root_speech.exists():
                            try:
                                with open(root_speech, "r", encoding="utf-8") as sf:
                                    content = sf.read().strip()
                                if content:
                                    ref_text = content
                            except Exception:
                                pass
                speech_types[v] = (vc.ref_audio, ref_text or "", vc.speed if vc.speed is not None else self.config.speed)

            # Now generate per segment using the loaded model infer directly
            for seg in segments:
                ref_audio, ref_text, v_speed = speech_types.get(seg.voice_name, speech_types.get("f-a/tender"))
                accent = seg.voice_name or "main"
                slug = slugify_text(seg.text, max_len=40)
                if not slug:
                    # Fallback to a short hash if text becomes empty after slugification
                    slug = hashlib.sha1(seg.text.encode('utf-8')).hexdigest()[:6]
                base_path = audio_dir / f"{accent}_{slug}.wav"
                audio_path = base_path
                # If file already exists, reuse it (slug-based path includes text hash)
                if base_path.exists():
                    audio_path = base_path
                else:
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
                duration = len(AudioSegment.from_wav(str(audio_path))) / 1000.0
                generated_audio_paths.append(str(audio_path))
                per_segment_audio_paths.append(str(audio_path))
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
                current_time += duration
        else:
            # Single voice mode: use slug-based filenames (includes text hash for cache)
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
                ref_text = voice_cfg.ref_text
                if not ref_text:
                    txt = os.path.splitext(voice_cfg.ref_audio)[0] + ".txt"
                    if os.path.exists(txt):
                        try:
                            ref_text = open(txt, "r", encoding="utf-8").read().strip()
                        except Exception:
                            ref_text = ""
                # Use slug-based path (includes text content hash for cache)
                slug = slugify_text(seg.text, max_len=40)
                if not slug:
                    slug = hashlib.sha1(seg.text.encode('utf-8')).hexdigest()[:6]
                base_path = audio_dir / f"main_{slug}.wav"
                audio_path = base_path
                # If file already exists, reuse it
                if base_path.exists():
                    audio_path = base_path
                else:
                    # Perform generation
                    out_path, duration = self.audio_gen.generate(seg, voice_cfg, str(audio_path))
                    audio_path = out_path
                # Ensure a short silent tail + fade to avoid last-word artifacts
                try:
                    seg_audio = AudioSegment.from_wav(str(audio_path))
                    tail_ms = 150
                    fade_ms = 30 if len(seg_audio) > 2 * 30 else 0
                    seg_audio = seg_audio + AudioSegment.silent(duration=tail_ms)
                    if fade_ms:
                        seg_audio = seg_audio.fade_out(fade_ms)
                    seg_audio.export(str(audio_path), format="wav")
                    duration = len(seg_audio) / 1000.0
                except Exception:
                    # keep duration returned by generator if postprocess fails
                    pass
                generated_audio_paths.append(str(audio_path))
                per_segment_audio_paths.append(str(audio_path))
                current_time += duration

        # Concatenate audio per-segment to produce final audio, avoiding duplicate path issues
        final_audio = Path(self.config.output_dir) / "final_audio.wav"
        final_srt = Path(self.config.output_dir) / "final_output.srt"
        if per_segment_audio_paths:
            from pydub import AudioSegment as _AS
            combined = _AS.empty()
            last_path = None
            for p in per_segment_audio_paths:
                if last_path is not None and p == last_path:
                    # Insert a brief silence between identical audio blocks to
                    # avoid abrupt repetition without changing overall duration logic
                    combined += _AS.silent(duration=200)
                combined += _AS.from_wav(p)
                last_path = p
            combined.export(str(final_audio), format="wav")
        # Subtitles generation removed; no SRT output
        final_srt = ""
        # Return final artifact paths (no subtitles)
        return str(final_audio), str(final_srt)

    # Helpers used by CLI/tests
    # duplicate _load_article removed
