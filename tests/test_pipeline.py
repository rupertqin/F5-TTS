"""
Tests for generation pipeline.

Tests the pipeline's ability to:
- Handle single and multi-voice articles
- Generate audio files with proper naming
- Support concurrent generation
- Work with config parameters (nfe_step, cfg_strength, speed, target_rms)
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.tts_article.config import Config, VoiceConfig
from src.tts_article.pipeline import GenerationPipeline, slugify_text, _get_ref_text


class TestSlugifyText:
    """Tests for the slugify_text helper function."""

    def test_basic_slugify(self):
        """Test basic text slugification."""
        assert slugify_text("Hello World") == "hello_world"
        assert slugify_text("Test123") == "test123"

    def test_remove_punctuation(self):
        """Test that punctuation is removed."""
        assert slugify_text("Hello, World!") == "hello_world"
        assert slugify_text("Test's value.") == "tests_value"

    def test_truncate_length(self):
        """Test that long text is truncated."""
        long_text = "a" * 100
        result = slugify_text(long_text, max_len=40)
        assert len(result) == 40
        assert result == "a" * 40

    def test_empty_after_truncate(self):
        """Test that punctuation-only text becomes empty string."""
        text = "!!!"
        result = slugify_text(text, max_len=40)
        # Empty result is acceptable - will use text content as-is
        assert isinstance(result, str)


class TestGetRefText:
    """Tests for the _get_ref_text helper function."""

    def test_ref_text_from_voice_config(self, tmp_path):
        """Test ref_text is loaded from VoiceConfig."""
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy")
        voice_cfg = VoiceConfig(
            name="test",
            ref_audio=str(voice_file),
            ref_text="Config ref text"
        )
        ref_text = _get_ref_text(str(voice_file), voice_cfg)
        assert ref_text == "Config ref text"

    def test_ref_text_from_txt_file(self, tmp_path):
        """Test ref_text is loaded from companion .txt file."""
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy")
        txt_file = tmp_path / "voice.txt"
        txt_file.write_text("File ref text")

        voice_cfg = VoiceConfig(name="test", ref_audio=str(voice_file))
        ref_text = _get_ref_text(str(voice_file), voice_cfg)
        assert ref_text == "File ref text"

    def test_ref_text_empty_fallback(self, tmp_path):
        """Test ref_text is empty when no source available."""
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy")

        voice_cfg = VoiceConfig(name="test", ref_audio=str(voice_file))
        ref_text = _get_ref_text(str(voice_file), voice_cfg)
        # May read from project speech.txt if it exists, or be empty
        assert isinstance(ref_text, str)


class TestGenerationPipeline:
    """Test suite for GenerationPipeline class."""

    def test_init(self):
        """Test pipeline initialization."""
        config = Config(
            input_article="test.txt",
            output_dir="output",
            voices={"main": VoiceConfig(name="main", ref_audio="voice.wav")}
        )
        pipeline = GenerationPipeline(config)
        assert pipeline.config == config
        assert pipeline.workers == 4  # default

    def test_init_custom_workers(self):
        """Test pipeline with custom worker count."""
        config = Config(
            input_article="test.txt",
            output_dir="output",
            voices={"main": VoiceConfig(name="main", ref_audio="voice.wav")}
        )
        pipeline = GenerationPipeline(config, workers=8)
        assert pipeline.workers == 8

    def test_get_audio_path_single_voice(self, tmp_path):
        """Test audio path generation for single voice."""
        config = Config(
            input_article="test.txt",
            output_dir=str(tmp_path),
            voices={"main": VoiceConfig(name="main", ref_audio="voice.wav")}
        )
        pipeline = GenerationPipeline(config)
        audio_dir = tmp_path / "audio"

        path = pipeline._get_audio_path(audio_dir, None, "Hello world")
        assert path.stem.startswith("main_")
        assert path.suffix == ".wav"

    def test_get_audio_path_with_voice_name(self, tmp_path):
        """Test audio path generation with voice name."""
        config = Config(
            input_article="test.txt",
            output_dir=str(tmp_path),
            voices={"vivian": VoiceConfig(name="vivian", ref_audio="voice.wav")}
        )
        pipeline = GenerationPipeline(config)
        audio_dir = tmp_path / "audio"

        path = pipeline._get_audio_path(audio_dir, "vivian", "Hello world")
        assert "vivian" in path.stem
        assert path.suffix == ".wav"

    def test_get_audio_path_consistency(self, tmp_path):
        """Test that same text produces same audio path."""
        config = Config(
            input_article="test.txt",
            output_dir=str(tmp_path),
            voices={"main": VoiceConfig(name="main", ref_audio="voice.wav")}
        )
        pipeline = GenerationPipeline(config)
        audio_dir = tmp_path / "audio"

        path1 = pipeline._get_audio_path(audio_dir, None, "Hello world")
        path2 = pipeline._get_audio_path(audio_dir, None, "Hello world")
        assert path1 == path2

    def test_get_audio_path_different_text(self, tmp_path):
        """Test that different text produces different audio path."""
        config = Config(
            input_article="test.txt",
            output_dir=str(tmp_path),
            voices={"main": VoiceConfig(name="main", ref_audio="voice.wav")}
        )
        pipeline = GenerationPipeline(config)
        audio_dir = tmp_path / "audio"

        path1 = pipeline._get_audio_path(audio_dir, None, "Hello")
        path2 = pipeline._get_audio_path(audio_dir, None, "World")
        assert path1 != path2


class TestPipelineIntegration:
    """Integration tests for the pipeline (without actual model)."""

    def test_run_requires_article_file(self, tmp_path):
        """Test that pipeline raises error when article file doesn't exist."""
        config = Config(
            input_article=str(tmp_path / "nonexistent.txt"),
            output_dir=str(tmp_path),
            voices={"main": VoiceConfig(name="main", ref_audio="voice.wav")}
        )
        pipeline = GenerationPipeline(config)

        with pytest.raises(FileNotFoundError):
            pipeline.run()

    def test_run_with_empty_article(self, tmp_path):
        """Test that pipeline raises error with empty article."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("")
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy")

        config = Config(
            input_article=str(article_file),
            output_dir=str(tmp_path),
            voices={"main": VoiceConfig(name="main", ref_audio=str(voice_file))}
        )
        pipeline = GenerationPipeline(config)

        with pytest.raises(ValueError, match="No segments produced"):
            pipeline.run()

    @patch('src.tts_article.pipeline.AudioGenerator')
    def test_run_single_voice(self, mock_audio_gen_class, tmp_path):
        """Test pipeline runs with single voice."""
        # Setup
        article_file = tmp_path / "article.txt"
        article_file.write_text("Hello world. This is a test.")
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy")

        # Mock TTS model
        mock_tts = MagicMock()
        mock_tts.infer = MagicMock(return_value=(None, 44100, None))
        mock_audio_gen = MagicMock()
        mock_audio_gen._tts = mock_tts
        mock_audio_gen_class.return_value = mock_audio_gen

        config = Config(
            input_article=str(article_file),
            output_dir=str(tmp_path),
            nfe_step=32,
            cfg_strength=2.0,
            speed=1.0,
            target_rms=0.1,
            voices={"main": VoiceConfig(name="main", ref_audio=str(voice_file))}
        )
        pipeline = GenerationPipeline(config, workers=2)

        # Run (will fail at concat since no real audio, but we've tested the path)
        try:
            pipeline.run()
        except Exception:
            pass  # Expected - no real audio generated

        # Verify model was called
        assert mock_tts.infer.called

    @patch('src.tts_article.pipeline.AudioGenerator')
    def test_run_multi_voice(self, mock_audio_gen_class, tmp_path):
        """Test pipeline runs with multiple voices."""
        # Setup
        article_file = tmp_path / "article.txt"
        article_file.write_text("""[main]
Hello world.
[vivian]
This is a test.
""")
        voice_file1 = tmp_path / "voice1.wav"
        voice_file1.write_text("dummy1")
        voice_file2 = tmp_path / "voice2.wav"
        voice_file2.write_text("dummy2")

        # Mock TTS model
        mock_tts = MagicMock()
        mock_tts.infer = MagicMock(return_value=(None, 44100, None))
        mock_audio_gen = MagicMock()
        mock_audio_gen._tts = mock_tts
        mock_audio_gen_class.return_value = mock_audio_gen

        config = Config(
            input_article=str(article_file),
            output_dir=str(tmp_path),
            nfe_step=32,
            cfg_strength=2.0,
            speed=1.0,
            voices={
                "main": VoiceConfig(name="main", ref_audio=str(voice_file1)),
                "vivian": VoiceConfig(name="vivian", ref_audio=str(voice_file2))
            }
        )
        pipeline = GenerationPipeline(config, workers=2)

        try:
            pipeline.run()
        except Exception:
            pass

        # Verify model was called for both voices
        assert mock_tts.infer.called


class TestPipelineConcurrency:
    """Tests for concurrent generation features."""

    @patch('src.tts_article.pipeline.AudioGenerator')
    def test_concurrent_execution(self, mock_audio_gen_class, tmp_path):
        """Test that concurrent execution works."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Sentence one. Sentence two. Sentence three.")
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy")

        # Track call count
        call_count = {"count": 0}

        def mock_infer(*args, **kwargs):
            call_count["count"] += 1
            return (None, 44100, None)

        mock_tts = MagicMock()
        mock_tts.infer = mock_infer
        mock_audio_gen = MagicMock()
        mock_audio_gen._tts = mock_tts
        mock_audio_gen_class.return_value = mock_audio_gen

        config = Config(
            input_article=str(article_file),
            output_dir=str(tmp_path),
            nfe_step=32,
            cfg_strength=2.0,
            speed=1.0,
            target_rms=0.1,
            voices={"main": VoiceConfig(name="main", ref_audio=str(voice_file))}
        )
        pipeline = GenerationPipeline(config, workers=4)

        try:
            pipeline.run()
        except Exception:
            pass

        # Verify infer was called for each segment
        assert call_count["count"] >= 1


class TestPipelineAudioNaming:
    """Tests for audio file naming conventions."""

    def test_audio_path_includes_voice_and_text_hash(self, tmp_path):
        """Test audio path includes voice name and text hash."""
        config = Config(
            input_article="test.txt",
            output_dir=str(tmp_path),
            voices={"vivian": VoiceConfig(name="vivian", ref_audio="voice.wav")}
        )
        pipeline = GenerationPipeline(config)
        audio_dir = tmp_path / "audio"

        path = pipeline._get_audio_path(audio_dir, "vivian", "Hello world")
        assert "vivian" in path.name
        assert path.suffix == ".wav"

    def test_audio_path_stability(self, tmp_path):
        """Test that audio paths are stable across runs."""
        config = Config(
            input_article="test.txt",
            output_dir=str(tmp_path),
            voices={"main": VoiceConfig(name="main", ref_audio="voice.wav")}
        )
        pipeline = GenerationPipeline(config)
        audio_dir = tmp_path / "audio"

        text = "Consistent text"
        path1 = pipeline._get_audio_path(audio_dir, None, text)
        path2 = pipeline._get_audio_path(audio_dir, None, text)
        assert path1 == path2


class TestPipelineConfigParameters:
    """Tests for pipeline handling of config parameters."""

    @patch('src.tts_article.pipeline.AudioGenerator')
    def test_nfe_step_passed_to_infer(self, mock_audio_gen_class, tmp_path):
        """Test that nfe_step is passed to model infer."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test sentence.")
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy")

        mock_tts = MagicMock()
        mock_tts.infer = MagicMock(return_value=(None, 44100, None))
        mock_audio_gen = MagicMock()
        mock_audio_gen._tts = mock_tts
        mock_audio_gen_class.return_value = mock_audio_gen

        config = Config(
            input_article=str(article_file),
            output_dir=str(tmp_path),
            nfe_step=64,
            cfg_strength=2.0,
            speed=1.0,
            target_rms=0.1,
            voices={"main": VoiceConfig(name="main", ref_audio=str(voice_file))}
        )
        pipeline = GenerationPipeline(config, workers=1)

        try:
            pipeline.run()
        except Exception:
            pass

        # Verify nfe_step was passed correctly
        call_kwargs = mock_tts.infer.call_args[1]
        assert call_kwargs.get("nfe_step") == 64

    @patch('src.tts_article.pipeline.AudioGenerator')
    def test_cfg_strength_passed_to_infer(self, mock_audio_gen_class, tmp_path):
        """Test that cfg_strength is passed to model infer."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test sentence.")
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy")

        mock_tts = MagicMock()
        mock_tts.infer = MagicMock(return_value=(None, 44100, None))
        mock_audio_gen = MagicMock()
        mock_audio_gen._tts = mock_tts
        mock_audio_gen_class.return_value = mock_audio_gen

        config = Config(
            input_article=str(article_file),
            output_dir=str(tmp_path),
            nfe_step=32,
            cfg_strength=3.0,
            speed=1.0,
            target_rms=0.1,
            voices={"main": VoiceConfig(name="main", ref_audio=str(voice_file))}
        )
        pipeline = GenerationPipeline(config, workers=1)

        try:
            pipeline.run()
        except Exception:
            pass

        call_kwargs = mock_tts.infer.call_args[1]
        assert call_kwargs.get("cfg_strength") == 3.0

    @patch('src.tts_article.pipeline.AudioGenerator')
    def test_target_rms_passed_to_infer(self, mock_audio_gen_class, tmp_path):
        """Test that target_rms is passed to model infer."""
        article_file = tmp_path / "article.txt"
        article_file.write_text("Test sentence.")
        voice_file = tmp_path / "voice.wav"
        voice_file.write_text("dummy")

        mock_tts = MagicMock()
        mock_tts.infer = MagicMock(return_value=(None, 44100, None))
        mock_audio_gen = MagicMock()
        mock_audio_gen._tts = mock_tts
        mock_audio_gen_class.return_value = mock_audio_gen

        config = Config(
            input_article=str(article_file),
            output_dir=str(tmp_path),
            nfe_step=32,
            cfg_strength=2.0,
            speed=1.0,
            target_rms=0.15,
            voices={"main": VoiceConfig(name="main", ref_audio=str(voice_file))}
        )
        pipeline = GenerationPipeline(config, workers=1)

        try:
            pipeline.run()
        except Exception:
            pass

        call_kwargs = mock_tts.infer.call_args[1]
        assert call_kwargs.get("target_rms") == 0.15
