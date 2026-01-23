"""
Audio generator for TTS Article Generator.

This module handles audio generation using F5-TTS for sentence segments.

Implementation: MVP - Simple audio generation
"""

import os
from pathlib import Path
from typing import Tuple
from f5_tts.api import F5TTS


class AudioGenerator:
    """
    Simple audio generator using F5-TTS.

    This is a minimal MVP implementation that generates audio for text segments.
    """

    def __init__(self, model_name: str = "F5-TTS", speed: float = 1.0):
        """
        Initialize the audio generator.

        Args:
            model_name: F5-TTS model name (default: "F5-TTS")
            speed: Speech speed multiplier (default: 1.0)
        """
        self.model_name = model_name
        self.speed = speed
        self.tts = None

    def initialize_model(self):
        """Initialize F5-TTS model (lazy loading)."""
        if self.tts is None:
            print(f"🔄 Loading {self.model_name} model...")
            self.tts = F5TTS(model_type=self.model_name, device="auto")
            print("✅ Model loaded successfully!")

    def generate(
        self,
        text: str,
        ref_audio: str,
        ref_text: str,
        output_path: str
    ) -> Tuple[str, float]:
        """
        Generate audio for text using F5-TTS.

        Args:
            text: Text to synthesize
            ref_audio: Path to reference audio file
            ref_text: Reference text (can be empty for auto-transcription)
            output_path: Path to save generated audio

        Returns:
            Tuple of (output_path, duration_in_seconds)
        """
        # Initialize model if needed
        self.initialize_model()

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate audio
        wav, sr, spect = self.tts.infer(
            gen_text=text,
            ref_file=ref_audio,
            ref_text=ref_text if ref_text else "",
            speed=self.speed
        )

        # Save audio
        self.tts.export_wav(output_path)

        # Calculate duration
        duration = len(wav) / sr

        return output_path, duration
