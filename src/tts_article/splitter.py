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
        raw_segments = [p.strip() for p in parts if p.strip()]
        # Enforce max_length by further splitting long segments
        segments: List[str] = []
        for seg in raw_segments:
            if len(seg) <= self.max_length:
                segments.append(seg)
            else:
                segments.extend(self._split_long_segment(seg))
        return segments if segments else [text.strip()]

    def _split_long_segment(self, segment: str) -> List[str]:
        """Split a long text segment into smaller pieces no longer than
        self.max_length.

        Strategy:
        - Prefer splitting at Chinese commas/commas '，' and ','
        - Then split at other punctuation boundaries if present
        - Then split at whitespace for English text
        - Fallback: hard-split by characters preserving max_length
        """
        seg = segment.strip()
        if not seg:
            return []

        # Try splitting at Chinese/English commas first
        if '，' in seg or ',' in seg:
            parts = re.split(r'[，,]+\s*', seg)
            parts = [p for p in parts if p]
            out: List[str] = []
            cur = ''
            for p in parts:
                if not cur:
                    cur = p
                elif len(cur) + 1 + len(p) <= self.max_length:
                    cur = cur + '，' + p
                else:
                    out.append(cur)
                    cur = p
            if cur:
                out.append(cur)
            # If any part still too long, recursively split
            result: List[str] = []
            for o in out:
                if len(o) <= self.max_length:
                    result.append(o)
                else:
                    # try splitting by whitespace
                    result.extend(self._split_long_segment_by_whitespace(o))
            return result

        # Try splitting by whitespace (English long text)
        if re.search(r"\s+", seg):
            return self._split_long_segment_by_whitespace(seg)

        # Fallback: hard split by max_length
        return [seg[i : i + self.max_length].strip() for i in range(0, len(seg), self.max_length)]

    def _split_long_segment_by_whitespace(self, seg: str) -> List[str]:
        words = seg.split()
        out: List[str] = []
        cur_words: List[str] = []
        cur_len = 0
        for w in words:
            add_len = len(w) + (1 if cur_words else 0)
            if cur_len + add_len <= self.max_length:
                cur_words.append(w)
                cur_len += add_len
            else:
                out.append(' '.join(cur_words))
                cur_words = [w]
                cur_len = len(w)
        if cur_words:
            out.append(' '.join(cur_words))
        # if any piece still exceeds max_length, hard split those
        final: List[str] = []
        for o in out:
            if len(o) <= self.max_length:
                final.append(o)
            else:
                final.extend([o[i : i + self.max_length].strip() for i in range(0, len(o), self.max_length)])
        return final

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
                # Prefer preserving original line breaks: treat each non-empty
                # input line as a primary sentence. Only split lines further if
                # they exceed max_length.
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                if not lines:
                    # fallback to punctuation-based splitting
                    candidates = self._split_by_punctuation(text)
                else:
                    candidates = []
                    for line in lines:
                        if len(line) <= self.max_length:
                            candidates.append(line)
                        else:
                            # split long lines by punctuation first, then hard split
                            parts = self._split_by_punctuation(line)
                            for p in parts:
                                if len(p) <= self.max_length:
                                    candidates.append(p)
                                else:
                                    candidates.extend(self._split_long_segment(p))

                for s in candidates:
                    s = s.strip()
                    if not s:
                        continue
                    segments.append(SentenceSegment(index=idx, text=s, voice_name=voice))
                    idx += 1
            # normalize indices
            for i, seg in enumerate(segments):
                seg.index = i
            return segments

        # Fallback: simple [voice] markers
        pieces = self._parse_voice_markers(article)
        for voice, text in pieces:
            text = text.strip()
            if not text:
                continue
            # Respect original lines first (one line => one segment). If a
            # line is too long, fall back to punctuation/long-segment splitting.
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if lines:
                for line in lines:
                    if len(line) <= self.max_length:
                        segments.append(SentenceSegment(index=idx, text=line, voice_name=voice or default_voice))
                        idx += 1
                    else:
                        parts = self._split_by_punctuation(line)
                        for p in parts:
                            p = p.strip()
                            if not p:
                                continue
                            if len(p) <= self.max_length:
                                segments.append(SentenceSegment(index=idx, text=p, voice_name=voice or default_voice))
                                idx += 1
                            else:
                                for sub in self._split_long_segment(p):
                                    segments.append(SentenceSegment(index=idx, text=sub, voice_name=voice or default_voice))
                                    idx += 1
            else:
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
