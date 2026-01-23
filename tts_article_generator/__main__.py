import argparse
from pathlib import Path

from .config import ConfigManager
from .pipeline import GenerationPipeline


def parse_arguments():
    parser = argparse.ArgumentParser(description="TTS Article Generator (V2) - Multi-speech pipeline with cache and SRT")
    parser.add_argument("--config", help="Path to TOML config file", default=None)
    parser.add_argument("--input", help="Input article file path", default=None)
    parser.add_argument("--output", help="Output directory", default=None)
    parser.add_argument("--resume", help="Resume from cache if possible", action="store_true")
    parser.add_argument("--verbose", help="Verbose logging", action="store_true")
    return parser.parse_args()


def main():
    args = parse_arguments()
    # Load config
    if args.config:
        config = ConfigManager.load_config(args.config)
    else:
        config = ConfigManager.get_default_config()
    if args.input:
        config.input_article = args.input
    if args.output:
        config.output_dir = args.output
    # Default article source for MVP: use gen/speech.txt if present
    if not args.input:
        if Path("gen/speech.txt").exists():
            config.input_article = "gen/speech.txt"
        elif Path("gen/article.txt").exists():
            config.input_article = "gen/article.txt"
    # Simple resume flag: enable_cache in config toggling could be used, but we honor the flag here by forcing enable_cache
    config.enable_cache = True if args.resume else config.enable_cache
    pipeline = GenerationPipeline(config)
    final_audio, final_srt = pipeline.run()
    print(f"Final audio: {final_audio}")
    print(f"Final subtitles: {final_srt}")


if __name__ == "__main__":
    main()
