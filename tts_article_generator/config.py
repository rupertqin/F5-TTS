"""
Configuration management for TTS Article Generator.

This module handles loading, validating, and managing system configuration
from TOML files and command-line arguments.

Implementation: Task 1.2 - 1.3
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for older Python versions


@dataclass
class VoiceConfig:
    """
    Configuration for a single voice/audio reference.

    Attributes:
        name: Friendly name for the voice
        ref_audio: Path to the reference audio file (WAV format)
        ref_text: Optional reference text for the audio (if empty, will be auto-transcribed)
        speed: Optional speed multiplier for this voice (overrides global setting)

    Requirements: 7.2
    """
    name: str
    ref_audio: str
    ref_text: str = ""
    speed: Optional[float] = None


@dataclass
class Config:
    """
    Main configuration data class for the TTS Article Generator system.

    This class holds all system configuration including input/output paths,
    model parameters, and voice configurations.

    Attributes:
        input_article: Path to the input article text file
        output_dir: Directory for output files
        cache_dir: Directory for cache files
        max_sentence_length: Maximum length of sentence segments in characters
        model_name: Name of the F5-TTS model to use
        nfe_step: Number of sampling steps for the model
        cfg_strength: CFG (Classifier-Free Guidance) strength parameter
        speed: Global speech speed multiplier
        voices: Dictionary mapping voice names to VoiceConfig objects
        enable_cache: Whether to enable caching for resume functionality

    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """
    input_article: str
    output_dir: str
    cache_dir: str = ".cache"
    max_sentence_length: int = 200
    model_name: str = "F5-TTS"
    nfe_step: int = 32
    cfg_strength: float = 2.0
    speed: float = 1.0
    voices: Dict[str, VoiceConfig] = field(default_factory=dict)
    enable_cache: bool = True


class ConfigManager:
    """
    Manager for loading, validating, and managing system configuration.

    This class provides static methods for configuration management including
    loading from TOML files, providing defaults, and validating configuration.

    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
    """

    @staticmethod
    def load_config(config_path: str) -> Config:
        """
        Load configuration from a TOML file.

        Args:
            config_path: Path to the TOML configuration file

        Returns:
            Config object with loaded configuration

        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If the config file is invalid or missing required fields

        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
        """
        # Check if file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Load TOML file
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse TOML file: {e}")

        # Extract required fields
        if "input_article" not in data:
            raise ValueError("Missing required field: input_article")
        if "output_dir" not in data:
            raise ValueError("Missing required field: output_dir")

        # Parse voices configuration
        voices = {}
        if "voices" in data:
            for voice_name, voice_data in data["voices"].items():
                if not isinstance(voice_data, dict):
                    raise ValueError(f"Invalid voice configuration for '{voice_name}'")
                if "ref_audio" not in voice_data:
                    raise ValueError(f"Missing 'ref_audio' for voice '{voice_name}'")

                voices[voice_name] = VoiceConfig(
                    name=voice_name,
                    ref_audio=voice_data["ref_audio"],
                    ref_text=voice_data.get("ref_text", ""),
                    speed=voice_data.get("speed")
                )

        # Ensure at least one voice is configured
        if not voices:
            raise ValueError("At least one voice must be configured in the 'voices' section")

        # Create Config object with loaded data
        config = Config(
            input_article=data["input_article"],
            output_dir=data["output_dir"],
            cache_dir=data.get("cache_dir", ".cache"),
            max_sentence_length=data.get("max_sentence_length", 200),
            model_name=data.get("model_name", "F5-TTS"),
            nfe_step=data.get("nfe_step", 32),
            cfg_strength=data.get("cfg_strength", 2.0),
            speed=data.get("speed", 1.0),
            voices=voices,
            enable_cache=data.get("enable_cache", True)
        )

        return config

    @staticmethod
    def get_default_config() -> Config:
        """
        Get a default configuration with sensible defaults.

        This is useful for testing or when no config file is provided.
        Note: The default config has placeholder paths that need to be
        updated before use.

        Returns:
            Config object with default values

        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
        """
        default_voice = VoiceConfig(
            name="main",
            ref_audio="voices/main.wav",
            ref_text="",
            speed=None
        )

        return Config(
            input_article="article.txt",
            output_dir="output",
            cache_dir=".cache",
            max_sentence_length=200,
            model_name="F5-TTS",
            nfe_step=32,
            cfg_strength=2.0,
            speed=1.0,
            voices={"main": default_voice},
            enable_cache=True
        )

    @staticmethod
    def validate_config(config: Config) -> List[str]:
        """
        Validate configuration and return a list of error messages.

        Performs validation checks including:
        - File path existence checks
        - Parameter range validation
        - Voice configuration validation

        Args:
            config: Config object to validate

        Returns:
            List of error messages (empty list if valid)

        Requirements: 7.6
        """
        errors = []

        # Validate input article path
        if not config.input_article:
            errors.append("input_article path is empty")
        elif not os.path.exists(config.input_article):
            errors.append(f"Input article file not found: {config.input_article}")
        elif not os.path.isfile(config.input_article):
            errors.append(f"Input article path is not a file: {config.input_article}")

        # Validate output directory
        if not config.output_dir:
            errors.append("output_dir path is empty")
        # Note: We don't check if output_dir exists because it will be created if needed

        # Validate cache directory
        if not config.cache_dir:
            errors.append("cache_dir path is empty")

        # Validate max_sentence_length
        if config.max_sentence_length <= 0:
            errors.append(f"max_sentence_length must be positive, got: {config.max_sentence_length}")
        elif config.max_sentence_length > 1000:
            errors.append(f"max_sentence_length is too large (>1000): {config.max_sentence_length}")

        # Validate model parameters
        if config.nfe_step <= 0:
            errors.append(f"nfe_step must be positive, got: {config.nfe_step}")

        if config.cfg_strength < 0:
            errors.append(f"cfg_strength must be non-negative, got: {config.cfg_strength}")

        if config.speed <= 0:
            errors.append(f"speed must be positive, got: {config.speed}")
        elif config.speed > 3.0:
            errors.append(f"speed is too high (>3.0): {config.speed}")

        # Validate voices
        if not config.voices:
            errors.append("At least one voice must be configured")
        else:
            for voice_name, voice_config in config.voices.items():
                # Validate voice name
                if not voice_name:
                    errors.append("Voice name cannot be empty")

                # Validate ref_audio path
                if not voice_config.ref_audio:
                    errors.append(f"Voice '{voice_name}': ref_audio path is empty")
                elif not os.path.exists(voice_config.ref_audio):
                    errors.append(f"Voice '{voice_name}': Reference audio file not found: {voice_config.ref_audio}")
                elif not os.path.isfile(voice_config.ref_audio):
                    errors.append(f"Voice '{voice_name}': Reference audio path is not a file: {voice_config.ref_audio}")
                else:
                    # Check if it's a WAV file (basic check by extension)
                    if not voice_config.ref_audio.lower().endswith('.wav'):
                        errors.append(f"Voice '{voice_name}': Reference audio must be a WAV file: {voice_config.ref_audio}")

                # Validate voice-specific speed if provided
                if voice_config.speed is not None:
                    if voice_config.speed <= 0:
                        errors.append(f"Voice '{voice_name}': speed must be positive, got: {voice_config.speed}")
                    elif voice_config.speed > 3.0:
                        errors.append(f"Voice '{voice_name}': speed is too high (>3.0): {voice_config.speed}")

        return errors
