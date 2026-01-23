"""
TTS Article Generator

A text-to-speech article generator based on F5-TTS that intelligently splits
long articles into short sentences, generates high-quality audio using multiple
voices, and automatically creates corresponding subtitle files.

Features:
- Intelligent article splitting with sentence segmentation
- Multi-voice support for different characters or sections
- High-quality audio generation using F5-TTS
- Automatic SRT subtitle generation
- Resume capability with caching mechanism
- Flexible configuration management
"""

__version__ = "0.1.0"
__author__ = "TTS Article Generator Team"

# Package metadata
__all__ = [
    "__version__",
    "__author__",
]
