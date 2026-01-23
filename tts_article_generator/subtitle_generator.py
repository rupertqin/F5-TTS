from __future__ import annotations

from dataclasses import dataclass
from typing import List
import re


@dataclass
class SubtitleEntry:
    index: int
    start_time: float
    end_time: float
    text: str


class SubtitleGenerator:
    def __init__(self):
        pass

    def _strip_voice_markers(self, text: str) -> str:
        return re.sub(r"\[[^\]]+\]", "", text).strip()

    def create_entry(self, index: int, start_time: float, duration: float, text: str) -> SubtitleEntry:
        return SubtitleEntry(index=index, start_time=start_time, end_time=start_time + duration, text=text)

    def format_time(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def generate_srt(self, entries: List[SubtitleEntry], output_path: str):
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, e in enumerate(entries, start=1):
                f.write(f"{idx}\n")
                f.write(f"{self.format_time(e.start_time)} --> {self.format_time(e.end_time)}\n")
                f.write(f"{self._strip_voice_markers(e.text)}\n\n")
        return output_path
