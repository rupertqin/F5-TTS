#!/usr/bin/env python
"""
Simple TTS generation script with JSON-style voice markers.

Format: {"name": "f-a/happy", "seed": -1, "speed": 1} Your text here.

The script will:
1. Read from gen/speech.txt
2. Parse voice markers
3. Generate audio for each segment
4. Save to gen/output/
"""

import os
import re
import json
from pathlib import Path
from f5_tts.api import F5TTS


class SimpleGenerator:
    """Simple generator with JSON voice markers."""

    def __init__(self, voices_dir="voices", output_dir="gen/output"):
        self.voices_dir = Path(voices_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tts = None

    def initialize_model(self):
        """Initialize F5-TTS model."""
        if self.tts is None:
            print("🔄 Loading F5-TTS model...")
            self.tts = F5TTS(model_type="F5-TTS", device="auto")
            print("✅ Model loaded!\n")

    def parse_segments(self, text):
        """
        Parse text with JSON voice markers.

        Format: {"name": "f-a/happy", "seed": -1, "speed": 1} Text content.

        Returns:
            List of (voice_config, text) tuples
        """
        # Pattern to match JSON config followed by text
        pattern = r'\{[^}]+\}\s*([^\{]+?)(?=\{|$)'

        segments = []
        last_end = 0

        for match in re.finditer(r'\{[^}]+\}', text):
            json_str = match.group(0)
            start = match.end()

            # Find the text after this JSON config
            next_match = re.search(r'\{[^}]+\}', text[start:])
            if next_match:
                end = start + next_match.start()
            else:
                end = len(text)

            segment_text = text[start:end].strip()

            if segment_text:
                try:
                    config = json.loads(json_str)
                    segments.append((config, segment_text))
                except json.JSONDecodeError as e:
                    print(f"⚠️  Warning: Invalid JSON config: {json_str}")
                    print(f"   Error: {e}")

        return segments

    def generate_segment(self, config, text, index):
        """Generate audio for a single segment."""
        voice_name = config.get("name", "f-a/happy")
        speed = config.get("speed", 1.0)
        seed = config.get("seed", -1)

        # Build reference audio path
        ref_audio = self.voices_dir / f"{voice_name}.wav"

        if not ref_audio.exists():
            print(f"❌ Error: Voice file not found: {ref_audio}")
            return None

        # Output path
        output_path = self.output_dir / f"segment_{index:04d}.wav"

        # Generate
        print(f"[{index}] {voice_name} (speed={speed})")
        print(f"    {text[:60]}{'...' if len(text) > 60 else ''}")

        try:
            wav, sr, spect = self.tts.infer(
                gen_text=text,
                ref_file=str(ref_audio),
                ref_text="",  # Auto-transcribe
                speed=speed,
                seed=seed if seed >= 0 else None
            )

            self.tts.export_wav(str(output_path))
            duration = len(wav) / sr

            print(f"    ✅ Saved: {output_path.name} ({duration:.2f}s)\n")
            return output_path

        except Exception as e:
            print(f"    ❌ Error: {e}\n")
            return None

    def generate_from_file(self, input_file="gen/speech.txt"):
        """Generate audio from input file."""
        print("=" * 60)
        print("🎙️  TTS Generator with Multiple Voices")
        print("=" * 60)

        # Read input
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"❌ Error: Input file not found: {input_file}")
            return

        print(f"\n📖 Reading from: {input_file}")
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # Parse segments
        print("✂️  Parsing voice markers...")
        segments = self.parse_segments(text)

        if not segments:
            print("⚠️  No voice markers found!")
            print("   Format: {\"name\": \"f-a/happy\", \"seed\": -1, \"speed\": 1} Your text.")
            return

        print(f"   Found {len(segments)} segments\n")

        # Initialize model
        self.initialize_model()

        # Generate audio
        print("🔊 Generating audio...")
        print("-" * 60)

        success_count = 0
        for i, (config, text) in enumerate(segments):
            result = self.generate_segment(config, text, i)
            if result:
                success_count += 1

        # Summary
        print("=" * 60)
        print("📊 Summary")
        print("=" * 60)
        print(f"✅ Generated: {success_count}/{len(segments)}")
        print(f"💾 Output: {self.output_dir}/")
        print("=" * 60)


def main():
    """Main entry point."""
    generator = SimpleGenerator(
        voices_dir="voices",
        output_dir="gen/output"
    )

    generator.generate_from_file("gen/speech.txt")


if __name__ == "__main__":
    main()
