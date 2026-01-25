from __future__ import annotations

import os
import json
import tempfile
import threading
from pathlib import Path
from typing import List, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def _get_ref_text(ref_audio: str, voice_cfg: VoiceCfg | None = None) -> str:
    """Load ref_text from config or from companion .txt file."""
    ref_text = voice_cfg.ref_text if voice_cfg else ""
    if not ref_text:
        txt = os.path.splitext(ref_audio)[0] + ".txt"
        if os.path.exists(txt):
            try:
                ref_text = open(txt, "r", encoding="utf-8").read().strip()
            except Exception:
                ref_text = ""
    if not ref_text:
        root_speech = Path(__file__).resolve().parents[1] / "speech.txt"
        if root_speech.exists():
            try:
                ref_text = open(root_speech, "r", encoding="utf-8").read().strip()
            except Exception:
                ref_text = ""
    return ref_text or ""


class GenerationPipeline:
    def __init__(self, config: Config, workers: int = 4):
        self.config = config
        self.workers = workers
        self.splitter = ArticleSplitter(max_length=config.max_sentence_length)
        self.audio_gen = None
        self.concater = FileConcatenator()
        self.voices = config.voices
        self._gpu_lock = threading.Lock()  # Protect GPU inference on Metal

    def _load_article(self) -> str:
        path = Path(self.config.input_article)
        if not path.exists():
            raise FileNotFoundError(f"Article not found: {self.config.input_article}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _get_audio_path(self, audio_dir: Path, voice_name: str | None, text: str) -> Path:
        """Generate deterministic path for audio file based on text content."""
        slug = slugify_text(text, max_len=40)
        if not slug:
            slug = hashlib.sha1(text.encode('utf-8')).hexdigest()[:6]
        voice = voice_name or "main"
        return audio_dir / f"{voice}_{slug}.wav"

    def _postprocess_audio(self, audio_path: str) -> float:
        """Add silence tail and fade out to audio file."""
        try:
            seg_audio = AudioSegment.from_wav(audio_path)
            tail_ms = 150
            fade_ms = 30 if len(seg_audio) > 2 * 30 else 0
            seg_audio = seg_audio + AudioSegment.silent(duration=tail_ms)
            if fade_ms:
                seg_audio = seg_audio.fade_out(fade_ms)
            seg_audio.export(audio_path, format="wav")
            return len(seg_audio) / 1000.0
        except Exception:
            return len(AudioSegment.from_wav(audio_path)) / 1000.0

    def _generate_segment(self, seg: SentenceSegment, speech_types: Dict[str, Tuple[str, str, float]], audio_dir: Path) -> Tuple[int, str, float]:
        """Generate audio for a single segment (runs in worker thread)."""
        ref_audio, ref_text, v_speed = speech_types.get(seg.voice_name, speech_types.get("f-a/tender"))
        audio_path = self._get_audio_path(audio_dir, seg.voice_name, seg.text)

        if audio_path.exists():
            duration = self._postprocess_audio(str(audio_path))
            return seg.index, str(audio_path), duration

        # Generate with temporary file to avoid conflicts
        with tempfile.NamedTemporaryFile(suffix=".wav", dir=audio_dir, delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Use lock for GPU inference on Metal (not thread-safe)
            with self._gpu_lock:
                wav, sr, spec = self.audio_gen._tts.infer(
                    ref_file=ref_audio,
                    ref_text=ref_text,
                    gen_text=seg.text,
                    file_wave=tmp_path,
                    nfe_step=self.config.nfe_step,
                    cfg_strength=self.config.cfg_strength,
                    speed=v_speed,
                )
            # Rename to final path
            os.rename(tmp_path, str(audio_path))
            duration = self._postprocess_audio(str(audio_path))
            return seg.index, str(audio_path), duration
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def run(self) -> Tuple[str, str]:
        article_text = self._load_article()
        segments = self.splitter.split(article_text)
        if not segments:
            raise ValueError("No segments produced from article.")

        # Build voices map
        referenced = set(s.voice_name for s in segments if s.voice_name)
        voices_for_tts = {}
        for vkey in referenced:
            if self.voices and vkey in self.voices:
                voices_for_tts[vkey] = self.voices[vkey]
        if not voices_for_tts:
            if self.voices and "main" in self.voices:
                voices_for_tts["main"] = self.voices["main"]

        # Build TTS config and initialize model
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
        self.audio_gen.initialize_model()
        if self.audio_gen._tts is None:
            raise RuntimeError("Failed to initialize TTS model; aborting generation.")

        # Output directories
        audio_dir = Path(self.config.output_dir) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Build speech types map (ref_audio, ref_text, speed per voice)
        unique_voices = sorted({s.voice_name for s in segments if s.voice_name})
        use_multispeech = len(unique_voices) > 1
        speech_types: Dict[str, Tuple[str, str, float]] = {}

        for v in unique_voices:
            vc = (self.config.voices or {}).get(v)
            if vc is None:
                vc = (self.config.voices or {}).get("f-a/tender") or (self.config.voices or {}).get("main")
            if vc is None:
                raise RuntimeError(f"No reference audio configured for voice '{v}'")
            ref_text = _get_ref_text(vc.ref_audio, vc)
            speech_types[v] = (vc.ref_audio, ref_text, vc.speed if vc.speed is not None else self.config.speed)

        # Handle single voice fallback for missing voices
        default_ref = speech_types.get("f-a/tender") or speech_types.get("main")
        if default_ref is None and speech_types:
            default_ref = list(speech_types.values())[0]

        # Generate all segments
        index_to_audio: Dict[int, Tuple[str, float]] = {}

        if use_multispeech and len(segments) > 1:
            # Parallel generation for multi-voice mode
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = {
                    executor.submit(self._generate_segment, seg, speech_types, audio_dir): seg
                    for seg in segments
                }
                for future in as_completed(futures):
                    seg = futures[future]
                    try:
                        idx, path, duration = future.result()
                        index_to_audio[idx] = (path, duration)
                    except Exception as e:
                        print(f"Error generating segment {seg.index}: {e}")
                        raise
        else:
            # Sequential for single voice or single segment
            for seg in segments:
                idx, path, duration = self._generate_segment(seg, speech_types or {"main": default_ref}, audio_dir)
                index_to_audio[idx] = (path, duration)

        # Sort by index to maintain order
        per_segment_audio_paths = [index_to_audio[i][0] for i in sorted(index_to_audio.keys())]

        # Concatenate all audio
        final_audio = Path(self.config.output_dir) / "final_audio.wav"
        if per_segment_audio_paths:
            from pydub import AudioSegment as _AS
            combined = _AS.empty()
            last_path = None
            for p in per_segment_audio_paths:
                if last_path is not None and p == last_path:
                    combined += _AS.silent(duration=200)
                combined += _AS.from_wav(p)
                last_path = p
            combined.export(str(final_audio), format="wav")

        return str(final_audio), ""
