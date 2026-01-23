from __future__ import annotations

import os
from typing import Tuple
from pydub import AudioSegment

try:
    from f5_tts.api import F5TTS  # type: ignore
except Exception:
    F5TTS = None  # Fallback when F5-TTS is not installed

from .config import VoiceConfig as VoiceConfig, Config as TTSConfig


class AudioGenerator:
    def __init__(self, config: TTSConfig):
        self.config = config
        self._tts = None

    def initialize_model(self):
        if self._tts is None:
            try:
                if F5TTS is None:
                    print("⚠️  F5-TTS is not installed in this environment.")
                    self._tts = None
                    return
                print("🔄 Loading F5-TTS model...")
                self._tts = F5TTS(model=self.config.model_name)
                print("✅ Model loaded!\n")
            except Exception as e:
                print(f"⚠️  Could not load F5-TTS model: {e}")
                self._tts = None

    def _ensure_model(self):
        if self._tts is None:
            self.initialize_model()

    def generate(self, segment, voice_config: VoiceConfig, output_path: str) -> Tuple[str, float]:
        """Generate audio for a single sentence segment.
        Returns (output_path, duration_seconds).
        """
        self._ensure_model()
        ref_audio = voice_config.ref_audio
        text = segment.text
        speed = voice_config.speed if voice_config.speed is not None else self.config.speed

        # If voice reference audio is missing or model not loaded, fall back to silent audio (MVP)
        if not os.path.exists(ref_audio) or self._tts is None:
            duration = 1.0
            try:
                from pydub.generators import Sine
                beep = Sine(440).to_audio_segment(duration=duration*1000)
            except Exception:
                beep = AudioSegment.silent(duration=int(duration * 1000))
            beep.export(output_path, format="wav")
            return output_path, duration

        try:
            wav, sr, _ = self._tts.infer(
                ref_file=ref_audio,
                ref_text=voice_config.ref_text,
                gen_text=text,
                file_wave=output_path,
                seed=None,
                speed=speed,
            )
            duration = len(wav) / sr
            return str(output_path), duration
        except Exception:
            # Fallback to silent audio if TTS generation fails
            duration = 1.0
            silence = AudioSegment.silent(duration=int(duration * 1000))
            silence.export(output_path, format="wav")
            return str(output_path), duration

    def get_audio_duration(self, audio_path: str) -> float:
        # Use soundfile to determine duration
        import soundfile as sf
        with sf.SoundFile(audio_path) as f:
            return len(f) / f.samplerate
