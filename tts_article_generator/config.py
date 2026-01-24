from __future__ import annotations

import os
import json
import hashlib
from typing import Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class VoiceConfig:
    name: str
    ref_audio: str
    ref_text: str = ""
    speed: Optional[float] = None


@dataclass
class Config:
    input_article: str
    output_dir: str
    max_sentence_length: int = 200
    model_name: str = "F5TTS_v1_Base"
    nfe_step: int = 32
    cfg_strength: float = 2.0
    speed: float = 1.0
    voices: Optional[Dict[str, VoiceConfig]] = None

    def __post_init__(self):
        if self.voices is None:
            self.voices = {}


class ConfigManager:
    @staticmethod
    def load_config(config_path: str) -> Config:
        # Load file contents; provide a clearer error if missing
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        try:
            data = json.loads(content)
        except Exception:
            # Try stdlib tomllib (Python 3.11+), then tomli third-party
            toml_data = None
            parse_err = None
            try:
                import tomllib as _tomllib  # type: ignore
                toml_data = _tomllib.loads(content)
            except Exception as e:  # pragma: no cover - depends on runtime
                parse_err = e
                try:
                    import importlib
                    tomli = importlib.import_module("tomli")
                    toml_data = tomli.loads(content)
                except Exception as e2:
                    parse_err = e2
                    toml_data = None
            if toml_data is None:
                raise ValueError(f"Failed to parse TOML file: {parse_err}")
            data = toml_data
        # Validate required top-level fields
        if "input_article" not in data:
            raise ValueError("Missing required field: input_article")
        if "output_dir" not in data:
            raise ValueError("Missing required field: output_dir")

        voices_data = data.get("voices")
        if not isinstance(voices_data, dict):
            raise ValueError("At least one voice must be configured")
        voices: Dict[str, VoiceConfig] = {}
        for key, v in voices_data.items():
            if not isinstance(v, dict):
                raise ValueError(f"Invalid voice configuration for '{key}'")
            if "ref_audio" not in v:
                raise ValueError(f"Missing 'ref_audio' for voice '{key}'")
            voice = VoiceConfig(
                name=key,
                ref_audio=v.get("ref_audio", ""),
                ref_text=v.get("ref_text", ""),
                speed=v.get("speed", None),
            )
            # Auto-fill ref_text from a companion .txt file next to the audio if not provided
            if not voice.ref_text and voice.ref_audio:
                base = os.path.splitext(voice.ref_audio)[0]
                txt_path = base + ".txt"
                if os.path.exists(txt_path):
                    try:
                        with open(txt_path, "r", encoding="utf-8") as tf:
                            content = tf.read().strip()
                            if content:
                                voice.ref_text = content
                    except Exception:
                        pass
            voices[key] = voice
        cfg = Config(
            input_article=data.get("input_article", "article.txt"),
            output_dir=data.get("output_dir", "output"),
            max_sentence_length=data.get("max_sentence_length", 200),
            model_name=data.get("model_name", "F5-TTS"),
            nfe_step=data.get("nfe_step", 32),
            cfg_strength=data.get("cfg_strength", 2.0),
            speed=data.get("speed", 1.0),
            voices=voices,
        )
        return cfg

    @staticmethod
    def get_default_config() -> Config:
        voices = {
            "main": VoiceConfig(name="main", ref_audio="voices/main.wav", ref_text="", speed=None),
        }
        # Auto-fill default ref_text from accompanying txt if present
        if voices:
            for key, voice in list(voices.items()):
                if not voice.ref_text and voice.ref_audio:
                    txt_path = os.path.splitext(voice.ref_audio)[0] + ".txt"
                    if os.path.exists(txt_path):
                        try:
                            with open(txt_path, "r", encoding="utf-8") as tf:
                                content = tf.read().strip()
                                if content:
                                    voice.ref_text = content
                        except Exception:
                            pass
        return Config(
            input_article="article.txt",
            output_dir="output",
            max_sentence_length=200,
            model_name="F5-TTS",
            nfe_step=32,
            cfg_strength=2.0,
            speed=1.0,
            voices=voices,
        )

    @staticmethod
    def validate_config(config: Config) -> list[str]:
        errors: list[str] = []
        # input_article checks
        if not config.input_article:
            errors.append("input_article path is empty")
        else:
            if not os.path.exists(config.input_article):
                errors.append(f"Input article file not found: {config.input_article}")
            elif not os.path.isfile(config.input_article):
                errors.append("Input article path is not a file")

        # output_dir
        if not config.output_dir:
            errors.append("output_dir path is empty")

        # numeric validations
        if config.max_sentence_length <= 0:
            errors.append("max_sentence_length must be positive")
        elif config.max_sentence_length > 1000:
            errors.append("max_sentence_length is too large")

        if config.nfe_step <= 0:
            errors.append("nfe_step must be positive")

        if config.cfg_strength < 0:
            errors.append("cfg_strength must be non-negative")

        if config.speed <= 0:
            errors.append("speed must be positive")
        elif config.speed > 3.0:
            errors.append("speed is too high")

        # voices
        if not config.voices:
            errors.append("At least one voice must be configured")
            return errors

        for name, v in config.voices.items():
            if not name:
                errors.append("Voice name cannot be empty")
            if not v.ref_audio:
                errors.append("ref_audio path is empty")
                continue
            if not os.path.exists(v.ref_audio):
                errors.append(f"Reference audio file not found: {v.ref_audio}")
                continue
            if os.path.isdir(v.ref_audio):
                errors.append("Reference audio path is not a file")
                continue
            _, ext = os.path.splitext(v.ref_audio)
            if ext.lower() != ".wav":
                errors.append("Reference audio must be a WAV file")
            # voice speed
            if v.speed is not None:
                if v.speed <= 0:
                    errors.append("speed must be positive")
                elif v.speed > 3.0:
                    errors.append("speed is too high")

        return errors
