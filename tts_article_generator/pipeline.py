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


class GenerationPipeline:
    def __init__(self, config: Config):
        self.config = config
        self.splitter = ArticleSplitter(max_length=config.max_sentence_length)
        # Build a lightweight TTS config for AudioGenerator (no need to pass through full pipeline Config)
        from .config import Config as TTSConfig
        voices_for_tts = config.voices if config.voices is not None else {}
        tts_config = TTSConfig(
            input_article=config.input_article,
            output_dir=config.output_dir,
            cache_dir=getattr(config, "cache_dir", ".cache"),
            max_sentence_length=config.max_sentence_length,
            model_name=config.model_name,
            nfe_step=config.nfe_step,
            cfg_strength=config.cfg_strength,
            speed=config.speed,
            voices=voices_for_tts,
            enable_cache=getattr(config, "enable_cache", True),
        )
        self.audio_gen = AudioGenerator(tts_config)
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
        # Iterate over segments
        for seg in segments:
            voice_cfg = self.voices.get(seg.voice_name)
            if voice_cfg is None:
                main_voice = (self.config.voices or {}).get("main")
                voice_cfg = VoiceCfg(
                    name=seg.voice_name,
                    ref_audio=main_voice.ref_audio if main_voice is not None else "voices/main.wav",
                    ref_text=main_voice.ref_text if main_voice is not None else "",
                    speed=main_voice.speed if main_voice is not None else 1.0,
                )
            audio_path = audio_dir / f"segment_{seg.index:04d}.wav"
            # Check cache
            cache_entry = None
            if self.cache:
                cache_entry = self.cache.get_entry(seg.index)
                if cache_entry and self.cache.validate_entry(cache_entry):
                    generated_audio_paths.append(cache_entry.audio_path)
                    # Update timings later after we know durations; for simplicity we'll recompute durations when concatenating
                    duration = cache_entry.duration
                    if duration:
                        # Update subtitle start/end times
                        ent = SubtitleEntry(index=seg.index+1, start_time=current_time, end_time=current_time+duration, text=seg.text)
                        entries.append(ent)
                        current_time += duration
                    continue
            # Generate new audio if not cached
            try:
                out_path, duration = self.audio_gen.generate(seg, voice_cfg, str(audio_path))
                generated_audio_paths.append(str(out_path))
                # Persist in cache
                if self.cache:
                    ce = CacheEntry(segment_index=seg.index, audio_path=str(out_path), duration=duration, text=seg.text, voice_name=seg.voice_name, timestamp=time.time())
                    self.cache.add_entry(ce)
            except Exception:
                # On failure, skip this segment but keep pipeline running
                duration = 0.0
            # Append subtitle entry even if duration is 0 (for robustness)
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
        # Write final subtitles
        self.subtitle_gen.generate_srt(entries, str(final_srt))
        # Return final artifact paths
        return str(final_audio), str(final_srt)

    # Helpers used by CLI/tests
    # duplicate _load_article removed
