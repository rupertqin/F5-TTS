from __future__ import annotations

from dataclasses import dataclass
from typing import List
import re
import unicodedata


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

    def _is_punct(self, ch: str) -> bool:
        try:
            return unicodedata.category(ch).startswith("P")
        except Exception:
            return False

    def _wrap_subtitle_lines(self, text: str, max_chars: int = 15) -> List[str]:
        # Remove voice markers for display purposes
        s = self._strip_voice_markers(text)
        if not s:
            return [""]
        lines: List[str] = []
        cur = ""
        cur_len = 0
        for ch in s:
            if self._is_punct(ch) or ch.isspace():
                # include punctuation/space in current line but don't count towards max_chars
                cur += ch
                continue
            if cur_len + 1 <= max_chars:
                cur += ch
                cur_len += 1
            else:
                if cur.strip():
                    lines.append(cur.strip())
                cur = ch
                cur_len = 1
        if cur.strip():
            lines.append(cur.strip())
        if not lines:
            lines = [s]
        return lines

    def wrap_text_for_subtitles(self, text: str, max_chars: int = 15) -> str:
        parts = self._wrap_subtitle_lines(text, max_chars=max_chars)
        return "\n".join(parts)

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

    def generate_srt(self, entries: List[SubtitleEntry], output_path: str, max_chars: int = 15):
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, e in enumerate(entries, start=1):
                f.write(f"{idx}\n")
                f.write(f"{self.format_time(e.start_time)} --> {self.format_time(e.end_time)}\n")
                # Write wrapped text to keep each line <= max_chars (ignoring punctuation)
                wrapped = self.wrap_text_for_subtitles(e.text, max_chars=max_chars)
                f.write(f"{wrapped}\n\n")
        return output_path
