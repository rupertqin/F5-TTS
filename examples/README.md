# Examples

This directory contains example files for the TTS Article Generator.

## Contents

The following files will be added in later tasks:

- **config.toml** (Task 1.4): Example configuration file with all available options
- **article.txt** (Task 12.1): Sample article demonstrating text formatting and voice markers
- **voices/** (Task 12.2): Directory containing sample voice reference audio files

## Usage

Once the examples are complete, you can run the generator with:

```bash
python -m tts_article_generator --config examples/config.toml
```

## Voice Markers

The article text supports voice markers to switch between different voices:

```
This text uses the default voice.

[narrator]
This text will use the narrator voice.

[character1]
This text will use character1 voice.

[main]
Back to the default voice.
```

## Configuration

See `config.toml` for detailed configuration options including:

- Input article path
- Output directory
- Voice file mappings
- F5-TTS model parameters
- Article splitting parameters
- Cache settings
