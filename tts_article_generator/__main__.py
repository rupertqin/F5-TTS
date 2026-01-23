"""
Main entry point for the TTS Article Generator.

This module provides the command-line interface for running the TTS article
generator. It can be invoked using:
    python -m tts_article_generator [options]
"""

import argparse
import sys
from pathlib import Path
from tts_article_generator.splitter import ArticleSplitter
from tts_article_generator.audio_generator import AudioGenerator


def main():
    """
    Main entry point for the TTS Article Generator CLI (MVP).

    This is a minimal viable product implementation that:
    - Loads an article from a text file
    - Splits it into sentence segments
    - Generates audio for each segment using F5-TTS
    """
    parser = argparse.ArgumentParser(
        description="TTS Article Generator - Convert articles to speech (MVP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python -m tts_article_generator --input article.txt --ref-audio voice.wav --output output/

  # With reference text and custom speed
  python -m tts_article_generator --input article.txt --ref-audio voice.wav --ref-text "参考文本" --speed 1.2
        """
    )

    # Required arguments
    parser.add_argument(
        "--input",
        required=True,
        help="Input article text file (UTF-8 encoded)"
    )
    parser.add_argument(
        "--ref-audio",
        required=True,
        help="Reference audio file (WAV format) for voice cloning"
    )

    # Optional arguments
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory for generated audio files (default: output)"
    )
    parser.add_argument(
        "--ref-text",
        default="",
        help="Reference text matching the reference audio (optional, auto-transcribed if empty)"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=200,
        help="Maximum sentence length in characters (default: 200)"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speech speed multiplier (default: 1.0)"
    )
    parser.add_argument(
        "--model",
        default="F5-TTS",
        help="F5-TTS model name (default: F5-TTS)"
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {args.input}")
        return 1

    # Validate reference audio
    ref_audio_path = Path(args.ref_audio)
    if not ref_audio_path.exists():
        print(f"❌ Error: Reference audio file not found: {args.ref_audio}")
        return 1

    print("=" * 60)
    print("🎙️  TTS Article Generator (MVP)")
    print("=" * 60)

    # Load article
    print(f"\n📖 Loading article from: {args.input}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            article = f.read()
        print(f"   Article length: {len(article)} characters")
    except Exception as e:
        print(f"❌ Error reading article: {e}")
        return 1

    # Split article
    print(f"\n✂️  Splitting article (max length: {args.max_length} chars)...")
    splitter = ArticleSplitter(max_length=args.max_length)
    segments = splitter.split(article)
    print(f"   Created {len(segments)} segments")

    # Create output directory
    output_dir = Path(args.output)
    segments_dir = output_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n💾 Output directory: {segments_dir}")

    # Initialize audio generator
    print(f"\n🎵 Initializing audio generator...")
    print(f"   Model: {args.model}")
    print(f"   Speed: {args.speed}x")
    print(f"   Reference audio: {args.ref_audio}")
    generator = AudioGenerator(model_name=args.model, speed=args.speed)

    # Generate audio for each segment
    print(f"\n🔊 Generating audio for {len(segments)} segments...")
    print("-" * 60)

    success_count = 0
    failed_count = 0

    for segment in segments:
        output_path = segments_dir / f"segment_{segment.index:04d}.wav"

        # Show progress
        progress = f"[{segment.index + 1}/{len(segments)}]"
        text_preview = segment.text[:50] + "..." if len(segment.text) > 50 else segment.text
        print(f"\n{progress} {text_preview}")

        try:
            path, duration = generator.generate(
                text=segment.text,
                ref_audio=args.ref_audio,
                ref_text=args.ref_text,
                output_path=str(output_path)
            )
            print(f"   ✅ Saved: {output_path.name} ({duration:.2f}s)")
            success_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("📊 Generation Summary")
    print("=" * 60)
    print(f"✅ Successful: {success_count}/{len(segments)}")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count}/{len(segments)}")
    print(f"💾 Output directory: {segments_dir}")
    print("=" * 60)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
