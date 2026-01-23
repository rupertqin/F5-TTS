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
    speed: float = 1.0


@dataclass
class Config:
    input_article: str
    output_dir: str
    cache_dir: str
    max_sentence_length: int = 200
    model_name: str = "F5TTS_v1_Base"
    nfe_step: int = 32
    cfg_strength: float = 2.0
    speed: float = 1.0
    voices: Optional[Dict[str, VoiceConfig]] = None
    enable_cache: bool = True

    def __post_init__(self):
        if self.voices is None:
            self.voices = {}


class ConfigManager:
    @staticmethod
    def load_config(config_path: str) -> Config:
        # Try JSON first; if not JSON, attempt to parse TOML if available
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            data = json.loads(content)
        except Exception:
            tomli = None
            try:
                import importlib
                tomli = importlib.import_module("tomli")
            except Exception:
                tomli = None
            if tomli is None:
                raise RuntimeError("Config must be JSON. TOML parsing requires 'tomli' to be installed.")
            data = tomli.loads(content)
        voices_data = data.get("voices", {})
        voices: Dict[str, VoiceConfig] = {}
        for key, v in voices_data.items():
            voice = VoiceConfig(
                name=key,
                ref_audio=v.get("ref_audio", ""),
                ref_text=v.get("ref_text", ""),
                speed=v.get("speed", 1.0),
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
            input_article=data.get("input_article", "gen/article.txt"),
            output_dir=data.get("output_dir", "gen/output"),
            cache_dir=data.get("cache_dir", ".cache"),
            max_sentence_length=data.get("max_sentence_length", 200),
            model_name=data.get("model_name", "F5TTS_v1_Base"),
            nfe_step=data.get("nfe_step", 32),
            cfg_strength=data.get("cfg_strength", 2.0),
            speed=data.get("speed", 1.0),
            voices=voices,
            enable_cache=data.get("enable_cache", True),
        )
        return cfg

    @staticmethod
    def get_default_config() -> Config:
        voices = {
            "main": VoiceConfig(name="main", ref_audio="voices/f-a/tender.wav", ref_text="", speed=1.0),
            # Multivoice presets for multi-speech mode; audio files may be placeholders
            "f-a/happy": VoiceConfig(name="f-a/happy", ref_audio="voices/f-a/happy.wav", ref_text="", speed=1.0),
            "f-a/confused": VoiceConfig(name="f-a/confused", ref_audio="voices/f-a/confused.wav", ref_text="", speed=1.0),
            "f-a/sad": VoiceConfig(name="f-a/sad", ref_audio="voices/f-a/sad.wav", ref_text="", speed=1.0),
            "f-a/friendly": VoiceConfig(name="f-a/friendly", ref_audio="voices/f-a/friendly.wav", ref_text="", speed=1.0),
            "f-b/haoya": VoiceConfig(name="f-b/haoya", ref_audio="voices/f-b/haoya.wav", ref_text="", speed=1.0),
            "f-c/heihei": VoiceConfig(name="f-c/heihei", ref_audio="voices/f-c/heihei.wav", ref_text="", speed=1.1),
            "f-c/xiaoshagua": VoiceConfig(name="f-c/xiaoshagua", ref_audio="voices/f-c/xiaoshagua.wav", ref_text="", speed=0.95),
            "f-a/tender": VoiceConfig(name="f-a/tender", ref_audio="voices/f-a/tender.wav", ref_text="", speed=1.0),
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
            input_article="gen/article.txt",
            output_dir="gen/output",
            cache_dir=".cache",
            max_sentence_length=200,
            model_name="F5TTS_v1_Base",
            nfe_step=32,
            cfg_strength=2.0,
            speed=1.0,
            voices=voices,
            enable_cache=True,
        )

    @staticmethod
    def validate_config(config: Config) -> list[str]:
        errors: list[str] = []
        if not os.path.exists(config.input_article):
            errors.append(f"Input article not found: {config.input_article}")
        # Check voice files exist
        if config.voices:
            for name, v in config.voices.items():
                if not os.path.exists(v.ref_audio):
                    errors.append(f"Voice '{name}' audio not found: {v.ref_audio}")
        return errors
