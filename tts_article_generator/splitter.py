from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Tuple
import re


@dataclass
class SentenceSegment:
    index: int
    text: str
    voice_name: str


class ArticleSplitter:
    def __init__(self, max_length: int = 200):
        self.max_length = max_length

    def _split_by_punctuation(self, text: str) -> List[str]:
        if not text:
            return []
        # Split on common punctuation, keep the punctuation at the end of segments when possible
        parts = re.split(r'(?<=[。！？!.?；;,，])\s*', text)
        segments = [p.strip() for p in parts if p.strip()]
        return segments if segments else [text.strip()]

    def _parse_voice_markers(self, text: str) -> List[Tuple[str, str]]:
        # Extract [voice] markers and associate following text until the next marker
        segments: List[Tuple[str, str]] = []
        current_voice = "main"
        pattern = re.compile(r"\[([^\]]+)\]")
        pos = 0
        for m in pattern.finditer(text):
            before = text[pos:m.start()]
            if before.strip():
                segments.append((current_voice, before))
            current_voice = m.group(1).strip()
            pos = m.end()
        tail = text[pos:]
        if tail.strip():
            segments.append((current_voice, tail))
        if not segments:
            segments.append(("main", text))
        return segments

    def _split_by_json_blocks(self, text: str) -> List[Tuple[str, str]]:
        # Detect blocks like: {"name": "f-a/happy", "seed": -1, "speed": 1} 这段文本
        blocks = []
        pattern = re.compile(r"\{[^}]+\}")
        matches = list(pattern.finditer(text))
        if not matches:
            return []
        for i, m in enumerate(matches):
            json_str = m.group(0)
            try:
                cfg = json.loads(json_str)
            except Exception:
                continue
            voice_name = cfg.get("name", "main")
            start = m.end()
            end = matches[i+1].start() if i + 1 < len(matches) else len(text)
            segment_text = text[start:end].strip()
            if segment_text:
                blocks.append((voice_name, segment_text))
        return blocks

    def split(self, article: str, default_voice: str = "main") -> List[SentenceSegment]:
        # First try JSON-block based segmentation (experimental multi-voice JSON markers)
        blocks = self._split_by_json_blocks(article)
        segments: List[SentenceSegment] = []
        idx = 0
        if blocks:
            for voice, text in blocks:
                text = text.strip()
                if not text:
                    continue
                sentences = self._split_by_punctuation(text)
                for s in sentences:
                    s = s.strip()
                    if not s:
                        continue
                    if len(s) <= self.max_length:
                        segments.append(SentenceSegment(index=idx, text=s, voice_name=voice))
                        idx += 1
                    else:
                        words = s.split()
                        chunk = []
                        cur_len = 0
                        for w in words:
                            if cur_len + len(w) + (1 if chunk else 0) <= self.max_length:
                                chunk.append(w)
                                cur_len += len(w) + (1 if chunk else 0)
                            else:
                                seg_text = " ".join(chunk).strip()
                                if seg_text:
                                    segments.append(SentenceSegment(index=idx, text=seg_text, voice_name=voice))
                                    idx += 1
                                chunk = [w]
                                cur_len = len(w)
                        if chunk:
                            seg_text = " ".join(chunk).strip()
                            if seg_text:
                                segments.append(SentenceSegment(index=idx, text=seg_text, voice_name=voice))
                                idx += 1
            # ensure index order
            for i, seg in enumerate(segments):
                seg.index = i
            return segments

        # Fallback: simple [voice] markers
        pieces = self._parse_voice_markers(article)
        for voice, text in pieces:
            text = text.strip()
            if not text:
                continue
            sentences = self._split_by_punctuation(text)
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                segments.append(SentenceSegment(index=idx, text=s, voice_name=voice or default_voice))
                idx += 1
        # Normalize indices
        for i, seg in enumerate(segments):
            seg.index = i
        return segments
