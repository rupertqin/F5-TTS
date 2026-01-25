"""
Tests for configuration management.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.tts_article.config import Config, ConfigManager, VoiceConfig


class TestConfigManager:
    """Test suite for ConfigManager class."""

    def test_load_config_valid(self, tmp_path):
        """Test loading a valid TOML configuration file."""
        # Create a temporary voice file
        voice_file = tmp_path / "test_voice.wav"
        voice_file.write_text("dummy wav content")

        # Create a temporary article file
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article content")

        # Create a valid TOML config
        config_file = tmp_path / "config.toml"
        config_content = f"""
input_article = "{article_file}"
output_dir = "output"
max_sentence_length = 150
model_name = "F5-TTS"
nfe_step = 32
cfg_strength = 2.0
speed = 1.0
target_rms = 0.1

[voices.main]
ref_audio = "{voice_file}"
ref_text = "Test reference text"
speed = 1.2

[voices.narrator]
ref_audio = "{voice_file}"
ref_text = ""
"""
        config_file.write_text(config_content)

        # Load config
        config = ConfigManager.load_config(str(config_file))

        # Verify loaded values
        assert config.input_article == str(article_file)
        assert config.output_dir == "output"
        assert config.max_sentence_length == 150
        assert config.model_name == "F5-TTS"
        assert config.nfe_step == 32
        assert config.cfg_strength == 2.0
        assert config.speed == 1.0
        assert config.target_rms == 0.1

        # Verify voices
        assert len(config.voices) == 2
        assert "main" in config.voices
        assert "narrator" in config.voices

        main_voice = config.voices["main"]
        assert main_voice.name == "main"
        assert main_voice.ref_audio == str(voice_file)
        assert main_voice.ref_text == "Test reference text"
        assert main_voice.speed == 1.2

        narrator_voice = config.voices["narrator"]
        assert narrator_voice.name == "narrator"
        assert narrator_voice.ref_audio == str(voice_file)
        assert narrator_voice.ref_text == ""
        assert narrator_voice.speed is None

    def test_load_config_with_defaults(self, tmp_path):
        """Test loading config with default values for optional fields."""
        # Create a temporary voice file
        voice_file = tmp_path / "test_voice.wav"
        voice_file.write_text("dummy wav content")

        # Create a temporary article file
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article content")

        # Create a minimal TOML config (only required fields)
        config_file = tmp_path / "config.toml"
        config_content = f"""
input_article = "{article_file}"
output_dir = "output"

[voices.main]
ref_audio = "{voice_file}"
"""
        config_file.write_text(config_content)

        # Load config
        config = ConfigManager.load_config(str(config_file))

        # Verify default values are used
        assert config.max_sentence_length == 200
        assert config.model_name == "F5-TTS"
        assert config.nfe_step == 32
        assert config.cfg_strength == 2.0
        assert config.speed == 1.0
        assert config.target_rms == 0.1

    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            ConfigManager.load_config("nonexistent_config.toml")

    def test_load_config_invalid_toml(self, tmp_path):
        """Test loading config with invalid TOML syntax."""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text("invalid toml [[[")

        with pytest.raises(ValueError, match="Failed to parse TOML file"):
            ConfigManager.load_config(str(config_file))

    def test_load_config_missing_required_field_input_article(self, tmp_path):
        """Test loading config missing input_article field."""
        config_file = tmp_path / "config.toml"
        config_content = """
output_dir = "output"

[voices.main]
ref_audio = "voice.wav"
"""
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="Missing required field: input_article"):
            ConfigManager.load_config(str(config_file))

    def test_load_config_missing_required_field_output_dir(self, tmp_path):
        """Test loading config missing output_dir field."""
        config_file = tmp_path / "config.toml"
        config_content = """
input_article = "article.txt"

[voices.main]
ref_audio = "voice.wav"
"""
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="Missing required field: output_dir"):
            ConfigManager.load_config(str(config_file))

    def test_load_config_no_voices(self, tmp_path):
        """Test loading config without any voices configured."""
        config_file = tmp_path / "config.toml"
        config_content = """
input_article = "article.txt"
output_dir = "output"
"""
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="At least one voice must be configured"):
            ConfigManager.load_config(str(config_file))

    def test_load_config_invalid_voice_config(self, tmp_path):
        """Test loading config with invalid voice configuration."""
        config_file = tmp_path / "config.toml"
        config_content = """
input_article = "article.txt"
output_dir = "output"

[voices.main]
# Missing ref_audio field
ref_text = "test"
"""
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="Missing 'ref_audio' for voice 'main'"):
            ConfigManager.load_config(str(config_file))

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = ConfigManager.get_default_config()

        # Verify default values
        assert config.input_article == "speech.txt"
        assert config.output_dir == "output"
        assert config.max_sentence_length == 200
        assert config.model_name == "F5-TTS"
        assert config.nfe_step == 32
        assert config.cfg_strength == 2.0
        assert config.speed == 1.0
        assert config.target_rms == 0.1

        # Verify default voice
        assert len(config.voices) == 1
        assert "main" in config.voices
        main_voice = config.voices["main"]
        assert main_voice.name == "main"
        assert main_voice.ref_audio == "voices/main.wav"
        assert main_voice.ref_text == ""
        assert main_voice.speed is None

    def test_validate_config_valid(self, tmp_path):
        """Test validating a valid configuration."""
        # Create necessary files
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article")

        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        # Create valid config
        config = Config(
            input_article=str(article_file),
            output_dir=str(tmp_path / "output"),
            max_sentence_length=200,
            model_name="F5-TTS",
            nfe_step=32,
            cfg_strength=2.0,
            speed=1.0,
            target_rms=0.1,
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=None
                )
            },
        )

        errors = ConfigManager.validate_config(config)
        assert errors == []

    def test_validate_config_input_article_not_found(self, tmp_path):
        """Test validation when input article file doesn't exist."""
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        config = Config(
            input_article="nonexistent_article.txt",
            output_dir="output",
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert len(errors) == 1
        assert "Input article file not found" in errors[0]

    def test_validate_config_input_article_empty(self, tmp_path):
        """Test validation when input article path is empty."""
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        config = Config(
            input_article="",
            output_dir="output",
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert len(errors) == 1
        assert "input_article path is empty" in errors[0]

    def test_validate_config_input_article_is_directory(self, tmp_path):
        """Test validation when input article path is a directory."""
        article_dir = tmp_path / "article_dir"
        article_dir.mkdir()

        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        config = Config(
            input_article=str(article_dir),
            output_dir="output",
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert len(errors) == 1
        assert "Input article path is not a file" in errors[0]

    def test_validate_config_output_dir_empty(self, tmp_path):
        """Test validation when output_dir is empty."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        config = Config(
            input_article=str(article_file),
            output_dir="",
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("output_dir path is empty" in e for e in errors)

    def test_validate_config_invalid_max_sentence_length(self, tmp_path):
        """Test validation with invalid max_sentence_length values."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        # Test negative value
        config = Config(
            input_article=str(article_file),
            output_dir="output",
            max_sentence_length=-10,
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("max_sentence_length must be positive" in e for e in errors)

        # Test too large value
        config.max_sentence_length = 2000
        errors = ConfigManager.validate_config(config)
        assert any("max_sentence_length is too large" in e for e in errors)

    def test_validate_config_invalid_speed(self, tmp_path):
        """Test validation with invalid speed values."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        # Test negative speed
        config = Config(
            input_article=str(article_file),
            output_dir="output",
            speed=-0.5,
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("speed must be positive" in e for e in errors)

        # Test too high speed
        config.speed = 5.0
        errors = ConfigManager.validate_config(config)
        assert any("speed is too high" in e for e in errors)

    def test_validate_config_no_voices(self, tmp_path):
        """Test validation when no voices are configured."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        config = Config(
            input_article=str(article_file),
            output_dir="output",
            voices={}
        )

        errors = ConfigManager.validate_config(config)
        assert any("At least one voice must be configured" in e for e in errors)

    def test_validate_config_voice_ref_audio_not_found(self, tmp_path):
        """Test validation when voice reference audio file doesn't exist."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        config = Config(
            input_article=str(article_file),
            output_dir="output",
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio="nonexistent_voice.wav",
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("Reference audio file not found" in e for e in errors)

    def test_validate_config_voice_ref_audio_not_wav(self, tmp_path):
        """Test validation when voice reference audio is not a WAV file."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        # Create a non-WAV file
        audio_file = tmp_path / "voice.mp3"
        audio_file.write_text("dummy mp3")

        config = Config(
            input_article=str(article_file),
            output_dir="output",
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(audio_file),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("Reference audio must be a WAV file" in e for e in errors)

    def test_validate_config_voice_invalid_speed(self, tmp_path):
        """Test validation with invalid voice-specific speed."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        # Test negative speed
        config = Config(
            input_article=str(article_file),
            output_dir="output",
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=-0.5
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("speed must be positive" in e for e in errors)

        # Test too high speed
        config.voices["main"].speed = 5.0
        errors = ConfigManager.validate_config(config)
        assert any("speed is too high" in e for e in errors)

    def test_validate_config_multiple_errors(self, tmp_path):
        """Test validation with multiple errors."""
        config = Config(
            input_article="nonexistent.txt",
            output_dir="",
            max_sentence_length=-10,
            speed=-1.0,
            voices={}
        )

        errors = ConfigManager.validate_config(config)
        # Should have multiple errors
        assert len(errors) >= 4
        assert any("Input article file not found" in e for e in errors)
        assert any("output_dir path is empty" in e for e in errors)
        assert any("max_sentence_length must be positive" in e for e in errors)
        assert any("At least one voice must be configured" in e for e in errors)

    def test_validate_config_voice_ref_audio_empty(self, tmp_path):
        """Test validation when voice ref_audio is empty."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        config = Config(
            input_article=str(article_file),
            output_dir="output",
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio="",
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("ref_audio path is empty" in e for e in errors)

    def test_validate_config_voice_ref_audio_is_directory(self, tmp_path):
        """Test validation when voice ref_audio is a directory."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        audio_dir = tmp_path / "audio_dir"
        audio_dir.mkdir()

        config = Config(
            input_article=str(article_file),
            output_dir="output",
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(audio_dir),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("Reference audio path is not a file" in e for e in errors)

    def test_load_config_voice_with_all_fields(self, tmp_path):
        """Test loading config with all voice fields specified."""
        voice_file = tmp_path / "test_voice.wav"
        voice_file.write_text("dummy wav content")

        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article content")

        config_file = tmp_path / "config.toml"
        config_content = f"""
input_article = "{article_file}"
output_dir = "output"

[voices.main]
ref_audio = "{voice_file}"
ref_text = "Complete reference text"
speed = 1.5
"""
        config_file.write_text(config_content)

        config = ConfigManager.load_config(str(config_file))

        assert len(config.voices) == 1
        main_voice = config.voices["main"]
        assert main_voice.name == "main"
        assert main_voice.ref_audio == str(voice_file)
        assert main_voice.ref_text == "Complete reference text"
        assert main_voice.speed == 1.5

    def test_load_config_multiple_voices(self, tmp_path):
        """Test loading config with multiple voices."""
        voice_file1 = tmp_path / "voice1.wav"
        voice_file1.write_text("dummy wav 1")
        voice_file2 = tmp_path / "voice2.wav"
        voice_file2.write_text("dummy wav 2")
        voice_file3 = tmp_path / "voice3.wav"
        voice_file3.write_text("dummy wav 3")

        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article content")

        config_file = tmp_path / "config.toml"
        config_content = f"""
input_article = "{article_file}"
output_dir = "output"

[voices.main]
ref_audio = "{voice_file1}"

[voices.narrator]
ref_audio = "{voice_file2}"
ref_text = "Narrator voice"

[voices.character1]
ref_audio = "{voice_file3}"
speed = 1.3
"""
        config_file.write_text(config_content)

        config = ConfigManager.load_config(str(config_file))

        assert len(config.voices) == 3
        assert "main" in config.voices
        assert "narrator" in config.voices
        assert "character1" in config.voices

        assert config.voices["main"].ref_audio == str(voice_file1)
        assert config.voices["narrator"].ref_text == "Narrator voice"
        assert config.voices["character1"].speed == 1.3

    def test_load_config_all_optional_fields(self, tmp_path):
        """Test loading config with all optional fields specified."""
        voice_file = tmp_path / "test_voice.wav"
        voice_file.write_text("dummy wav content")

        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article content")

        config_file = tmp_path / "config.toml"
        config_content = f"""
input_article = "{article_file}"
output_dir = "output"
max_sentence_length = 150
model_name = "F5TTS_Base"
nfe_step = 64
cfg_strength = 3.0
speed = 1.5
target_rms = 0.15

[voices.main]
ref_audio = "{voice_file}"
ref_text = "Test"
"""
        config_file.write_text(config_content)

        config = ConfigManager.load_config(str(config_file))

        assert config.input_article == str(article_file)
        assert config.output_dir == "output"
        assert config.max_sentence_length == 150
        assert config.model_name == "F5TTS_Base"
        assert config.nfe_step == 64
        assert config.cfg_strength == 3.0
        assert config.speed == 1.5
        assert config.target_rms == 0.15

    def test_validate_config_boundary_values(self, tmp_path):
        """Test validation with boundary values for numeric parameters."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        # Test boundary values that should be valid
        config = Config(
            input_article=str(article_file),
            output_dir="output",
            max_sentence_length=1,  # Minimum valid value
            nfe_step=1,  # Minimum valid value
            cfg_strength=0.0,  # Minimum valid value
            speed=0.01,  # Very small but positive
            target_rms=0.05,  # Minimum valid value
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=0.01
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        # These boundary values should be valid
        assert not any("must be positive" in e for e in errors)
        assert not any("must be non-negative" in e for e in errors)

        # Test upper boundary values
        config.max_sentence_length = 1000  # Maximum valid value
        config.speed = 3.0  # Maximum valid value
        config.target_rms = 0.2  # Maximum valid value
        config.voices["main"].speed = 3.0

        errors = ConfigManager.validate_config(config)
        assert not any("too large" in e for e in errors)
        assert not any("too high" in e for e in errors)

    def test_validate_config_zero_values(self, tmp_path):
        """Test validation with zero values for numeric parameters."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        # Test zero values (should be invalid for most parameters)
        config = Config(
            input_article=str(article_file),
            output_dir="output",
            max_sentence_length=0,
            voices={
                "main": VoiceConfig(
                    name="main",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("max_sentence_length must be positive" in e for e in errors)

        # Test zero speed
        config.max_sentence_length = 200
        config.speed = 0.0
        errors = ConfigManager.validate_config(config)
        assert any("speed must be positive" in e for e in errors)

        # Test zero nfe_step
        config.speed = 1.0
        config.nfe_step = 0
        errors = ConfigManager.validate_config(config)
        assert any("nfe_step must be positive" in e for e in errors)

    def test_load_config_with_comments_and_whitespace(self, tmp_path):
        """Test loading config with comments and extra whitespace."""
        voice_file = tmp_path / "test_voice.wav"
        voice_file.write_text("dummy wav content")

        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article content")

        config_file = tmp_path / "config.toml"
        config_content = f"""
# This is a comment
input_article = "{article_file}"  # Inline comment

# Another comment
output_dir = "output"

# Voice configuration
[voices.main]
ref_audio = "{voice_file}"
ref_text = ""  # Empty reference text
"""
        config_file.write_text(config_content)

        # Should load successfully despite comments
        config = ConfigManager.load_config(str(config_file))
        assert config.input_article == str(article_file)
        assert config.output_dir == "output"
        assert "main" in config.voices

    def test_load_config_voice_not_dict(self, tmp_path):
        """Test loading config when voice configuration is not a dictionary."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article content")

        config_file = tmp_path / "config.toml"
        config_content = f"""
input_article = "{article_file}"
output_dir = "output"

[voices]
main = "not_a_dict"
"""
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="Invalid voice configuration for 'main'"):
            ConfigManager.load_config(str(config_file))

    def test_validate_config_empty_voice_name(self, tmp_path):
        """Test validation when voice name is empty."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test")

        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy wav")

        # Create config with empty voice name (using empty string as key)
        config = Config(
            input_article=str(article_file),
            output_dir="output",
            voices={
                "": VoiceConfig(
                    name="",
                    ref_audio=str(voice_file),
                    ref_text="",
                    speed=None
                )
            }
        )

        errors = ConfigManager.validate_config(config)
        assert any("Voice name cannot be empty" in e for e in errors)

    def test_voice_config_all_params(self, tmp_path):
        """Test VoiceConfig with all parameters."""
        voice_file = tmp_path / "test_voice.wav"
        voice_file.write_text("dummy wav content")

        voice = VoiceConfig(
            name="custom",
            ref_audio=str(voice_file),
            ref_text="Reference text",
            speed=1.2,
            nfe_step=48,
            cfg_strength=2.5,
            target_rms=0.15
        )

        assert voice.name == "custom"
        assert voice.ref_audio == str(voice_file)
        assert voice.ref_text == "Reference text"
        assert voice.speed == 1.2
        assert voice.nfe_step == 48
        assert voice.cfg_strength == 2.5
        assert voice.target_rms == 0.15

    def test_voice_config_defaults(self):
        """Test VoiceConfig default values."""
        voice = VoiceConfig(name="test", ref_audio="test.wav")

        assert voice.ref_text == ""
        assert voice.speed is None
        assert voice.nfe_step is None
        assert voice.cfg_strength is None
        assert voice.target_rms is None

    def test_load_config_voice_with_nfe_step_cfg_strength(self, tmp_path):
        """Test loading config with voice-specific nfe_step and cfg_strength."""
        voice_file = tmp_path / "test_voice.wav"
        voice_file.write_text("dummy wav content")

        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article content")

        config_file = tmp_path / "config.toml"
        config_content = f"""
input_article = "{article_file}"
output_dir = "output"
nfe_step = 32
cfg_strength = 2.0

[voices.main]
ref_audio = "{voice_file}"

[voices.character1]
ref_audio = "{voice_file}"
nfe_step = 64
cfg_strength = 3.0

[voices.character2]
ref_audio = "{voice_file}"
nfe_step = 16
cfg_strength = 1.5
"""
        config_file.write_text(config_content)

        config = ConfigManager.load_config(str(config_file))

        # Global values
        assert config.nfe_step == 32
        assert config.cfg_strength == 2.0

        # main voice uses global values
        assert config.voices["main"].nfe_step is None
        assert config.voices["main"].cfg_strength is None

        # character1 uses custom values
        assert config.voices["character1"].nfe_step == 64
        assert config.voices["character1"].cfg_strength == 3.0

        # character2 uses different custom values
        assert config.voices["character2"].nfe_step == 16
        assert config.voices["character2"].cfg_strength == 1.5

    def test_load_config_voice_with_target_rms(self, tmp_path):
        """Test loading config with voice-specific target_rms."""
        voice_file = tmp_path / "test_voice.wav"
        voice_file.write_text("dummy wav content")

        article_file = tmp_path / "article.txt"
        article_file.write_text("Test article content")

        config_file = tmp_path / "config.toml"
        config_content = f"""
input_article = "{article_file}"
output_dir = "output"
target_rms = 0.1

[voices.main]
ref_audio = "{voice_file}"

[voices.loud]
ref_audio = "{voice_file}"
target_rms = 0.18

[voices.quiet]
ref_audio = "{voice_file}"
target_rms = 0.05
"""
        config_file.write_text(config_content)

        config = ConfigManager.load_config(str(config_file))

        # Global value
        assert config.target_rms == 0.1

        # main uses global
        assert config.voices["main"].target_rms is None

        # loud uses custom
        assert config.voices["loud"].target_rms == 0.18

        # quiet uses custom
        assert config.voices["quiet"].target_rms == 0.05
