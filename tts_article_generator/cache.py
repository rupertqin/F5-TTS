from __future__ import annotations

import os
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict

from .config import Config


@dataclass
class CacheEntry:
    segment_index: int
    audio_path: str
    duration: float
    text: str
    voice_name: str
    timestamp: float


class CacheManager:
    def __init__(self, cache_dir: str, task_id: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.task_id = task_id
        self.cache_path = self.cache_dir / f"cache_{task_id}.json"
        self._cache: Dict[int, CacheEntry] = {}

    def load_cache(self) -> Dict[int, CacheEntry]:
        if not self.cache_path.exists():
            self._cache = {}
            return self._cache
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            entries = data.get("entries", {}) or {}
            self._cache = {
                int(k): CacheEntry(**v) for k, v in entries.items()
            }
            return self._cache
        except Exception:
            self._cache = {}
            return self._cache

    def save_cache(self, cache: Dict[int, CacheEntry]):
        data = {
            "task_id": self.task_id,
            "entries": {str(k): asdict(v) for k, v in cache.items()}
        }
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_entry(self, segment_index: int) -> Optional[CacheEntry]:
        return self._cache.get(segment_index)

    def add_entry(self, entry: CacheEntry):
        self._cache[entry.segment_index] = entry

    def validate_entry(self, entry: CacheEntry) -> bool:
        p = Path(entry.audio_path)
        if not p.exists():
            return False
        try:
            if p.stat().st_size <= 0:
                return False
        except Exception:
            return False
        return True

    def clear_cache(self):
        if self.cache_path.exists():
            self.cache_path.unlink()

    def generate_task_id(self, article_path: str, config: Config) -> str:
        article_text = ""
        if os.path.exists(article_path):
            try:
                with open(article_path, 'r', encoding='utf-8') as f:
                    article_text = f.read()
            except Exception:
                article_text = ""
        article_hash = hashlib.md5(article_text.encode('utf-8')).hexdigest()
        config_repr = repr(config)
        config_hash = hashlib.md5(config_repr.encode('utf-8')).hexdigest()
        return hashlib.md5((article_hash + config_hash).encode('utf-8')).hexdigest()
