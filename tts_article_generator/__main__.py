import os
import argparse
from pathlib import Path

# Ensure PYTHONHASHSEED is valid very early — some native extensions and
# multiprocessing code will abort with a hard crash if this env var is set to
# an invalid value. If it's invalid, force it to 'random' before importing
# other modules or initializing heavy libraries.
def _valid_phs(v: str | None) -> bool:
    if v is None:
        return True
    if v == "random":
        return True
    try:
        i = int(v)
        return 0 <= i <= 4294967295
    except Exception:
        return False

phs = os.environ.get("PYTHONHASHSEED")
if not _valid_phs(phs):
    # If the current interpreter was launched with an invalid PYTHONHASHSEED,
    # re-exec the process after setting a safe value so the new Python process
    # is initialized correctly. We avoid infinite recursion with a marker.
    if os.environ.get("_PHSE_REEXEC") != "1":
        print(f"⚠️  Invalid PYTHONHASHSEED='{phs}', re-execing with 'random' to avoid runtime crash.")
        os.environ["PYTHONHASHSEED"] = "random"
        os.environ["_PHSE_REEXEC"] = "1"
        import sys
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        # Already re-executed once; set to a safe value and continue.
        print(f"⚠️  Invalid PYTHONHASHSEED='{phs}', forcing 'random' and continuing.")
        os.environ["PYTHONHASHSEED"] = "random"

# Limit threaded BLAS/OpenMP usage and force a safe multiprocessing start
# method early. These reduce the chance of native extensions spawning
# worker processes that pick up an invalid interpreter configuration.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
try:
    import multiprocessing
    # Force 'spawn' which is safer on macOS and avoids forking issues with
    # native multi-threaded libraries. Only set if not already set.
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        # start method already set — ignore
        pass
except Exception:
    pass

from .config import ConfigManager
from .pipeline import GenerationPipeline


def parse_arguments():
    parser = argparse.ArgumentParser(description="TTS Article Generator - Multi-speech pipeline")
    parser.add_argument("--config", help="Path to TOML config file", default=None)
    parser.add_argument("--input", help="Input article file path", default=None)
    parser.add_argument("--output", help="Output directory", default=None)
    parser.add_argument("--verbose", help="Verbose logging", action="store_true")
    return parser.parse_args()


def main():
    args = parse_arguments()
    # Load config
    if args.config:
        config = ConfigManager.load_config(args.config)
    else:
        # If a project-level `config.toml` exists, prefer it as the default
        # so users can run the CLI without passing --config each time.
        if Path("config.toml").exists():
            config = ConfigManager.load_config("config.toml")
        else:
            config = ConfigManager.get_default_config()
    if args.input:
        config.input_article = args.input
    if args.output:
        config.output_dir = args.output
    # Default article source: use speech.txt in current directory
    if not args.input and not Path("speech.txt").exists():
        raise FileNotFoundError("speech.txt not found in current directory")
    pipeline = GenerationPipeline(config)
    final_audio, final_srt = pipeline.run()
    print(f"Final audio: {final_audio}")
    print(f"Final subtitles: {final_srt}")


if __name__ == "__main__":
    main()
