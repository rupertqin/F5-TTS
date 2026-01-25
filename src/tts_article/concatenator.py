from __future__ import annotations

from typing import List
from pydub import AudioSegment
import os

from .subtitle_generator import SubtitleEntry


class FileConcatenator:
    def __init__(self):
        pass

    def concatenate_audio(
        self,
        audio_paths: List[str],
        output_path: str,
        cross_fade_duration: float = 0.15,
    ) -> str:
        if not audio_paths:
            raise ValueError("No audio paths provided for concatenation")
        combined: AudioSegment = AudioSegment.from_file(audio_paths[0])
        for p in audio_paths[1:]:
            next_seg = AudioSegment.from_file(p)
            combined = combined.append(next_seg, crossfade=int(cross_fade_duration * 1000))
        # Ensure WAV output
        combined.export(output_path, format="wav")
        return output_path

    def concatenate_subtitles(
        self, entries: List[SubtitleEntry], output_path: str
    ) -> str:
        # For compatibility, delegate to generating an SRT from entries
        from .subtitle_generator import SubtitleGenerator
        sg = SubtitleGenerator()
        return sg.generate_srt(entries, output_path)
