from __future__ import annotations

import os
from typing import Tuple
from pydub import AudioSegment

# Delay importing the heavy / native-backed F5-TTS package until we have
# validated environment variables (notably PYTHONHASHSEED). Importing it at
# module import time can cause a hard Python crash on some platforms if
# PYTHONHASHSEED is invalid. We'll import inside initialize_model().
F5TTS = None

from .config import VoiceConfig as VoiceConfig, Config as TTSConfig


class AudioGenerator:
    def __init__(self, config: TTSConfig):
        self.config = config
        self._tts = None

    def initialize_model(self):
        if self._tts is None:
            try:
                # Ensure PYTHONHASHSEED is valid; some environments set an invalid
                # value which causes a fatal error inside extension modules when
                # Python attempts to spawn worker processes. If it's invalid,
                # override to 'random'.
                phs = os.environ.get("PYTHONHASHSEED")
                def _valid_phs(v):
                    if v is None:
                        return True
                    if v == "random":
                        return True
                    try:
                        i = int(v)
                        return 0 <= i <= 4294967295
                    except Exception:
                        return False
                if not _valid_phs(phs):
                    print(f"⚠️  Invalid PYTHONHASHSEED='{phs}', setting to 'random' to avoid runtime crash.")
                    os.environ["PYTHONHASHSEED"] = "random"

                # Import the F5-TTS binding now that we've ensured the
                # environment is in a safe state.
                try:
                    from f5_tts.api import F5TTS as _F5TTS  # type: ignore
                except Exception:
                    print("⚠️  F5-TTS is not installed or failed to import in this environment.")
                    self._tts = None
                    return

                print("🔄 Loading F5-TTS model...")
                self._tts = _F5TTS(model=self.config.model_name)
                print("✅ Model loaded!\n")
            except Exception as e:
                import traceback
                print(f"⚠️  Could not load F5-TTS model: {e}")
                traceback.print_exc()
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

        # If model is not available, emit a very short placeholder tone to help
        # debugging. Do NOT silently fall back when ref_audio is missing or on
        # general generation errors — surface the error so caller can handle it.
        if self._tts is None:
            duration = 0.5
            try:
                from pydub.generators import Sine
                tone = Sine(880).to_audio_segment(duration=duration * 1000)
            except Exception:
                tone = AudioSegment.silent(duration=int(duration * 1000))
            tone.export(output_path, format="wav")
            return output_path, duration

        # If model is available but ref_audio is missing, raise an error so the
        # issue is explicit (previously code silently generated beep/silence).
        if not os.path.exists(ref_audio):
            raise FileNotFoundError(f"Reference audio not found: {ref_audio}")

        # Perform the generation; let exceptions bubble up to the caller so the
        # caller can decide how to handle failures.
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

    def get_audio_duration(self, audio_path: str) -> float:
        # Use soundfile to determine duration
        import soundfile as sf
        with sf.SoundFile(audio_path) as f:
            return len(f) / f.samplerate
