"""
Article splitter for TTS Article Generator.

This module handles splitting long articles into sentence segments suitable
for speech synthesis, with support for voice markers.

Implementation: Task 2.1 - 2.4
"""

from dataclasses import dataclass


@dataclass
class SentenceSegment:
    """
    Sentence segment data class.

    Represents a single sentence segment from an article, including its
    sequence number, text content, and the voice name to use for synthesis.

    Attributes:
        index: Segment sequence number (0-indexed)
        text: Segment text content
        voice_name: Name of the voice to use for this segment
    """
    index: int
    text: str
    voice_name: str


class ArticleSplitter:
    """
    Article splitter for TTS generation.

    Splits long articles into sentence segments suitable for speech synthesis,
    ensuring each segment does not exceed the maximum length.

    Attributes:
        max_length: Maximum length of each sentence segment in characters
    """

    def __init__(self, max_length: int = 200):
        """
        Initialize the article splitter.

        Args:
            max_length: Maximum sentence length in characters (default: 200)
        """
        self.max_length = max_length

    def _split_by_punctuation(self, text: str) -> list[str]:
        """
        Split text by punctuation marks.

        Splits text at major punctuation marks (period, question mark,
        exclamation mark) and minor punctuation marks (comma, semicolon)
        when needed for length constraints.

        Args:
            text: Text to split

        Returns:
            List of text segments split at punctuation marks
        """
        import re

        # Major punctuation marks that always indicate sentence boundaries
        major_punct = r'[。！？.!?]'

        # Split by major punctuation, keeping the punctuation with the text
        segments = []
        current_pos = 0

        for match in re.finditer(major_punct, text):
            end_pos = match.end()
            segment = text[current_pos:end_pos].strip()
            if segment:
                segments.append(segment)
            current_pos = end_pos

        # Add any remaining text
        if current_pos < len(text):
            remaining = text[current_pos:].strip()
            if remaining:
                segments.append(remaining)

        # If no major punctuation found, return the whole text
        if not segments:
            segments = [text.strip()] if text.strip() else []

        # Check length constraints and split further if needed
        final_segments = []
        for segment in segments:
            if len(segment) <= self.max_length:
                final_segments.append(segment)
            else:
                # Split long segments at minor punctuation (comma, semicolon)
                final_segments.extend(self._split_long_segment(segment))

        return final_segments

    def _split_long_segment(self, segment: str) -> list[str]:
        """
        Split a long segment at minor punctuation marks.

        When a segment exceeds max_length, this method splits it at
        commas, semicolons, or other suitable punctuation marks.

        Args:
            segment: Long segment to split

        Returns:
            List of shorter segments
        """
        import re

        # Minor punctuation marks for secondary splitting
        minor_punct = r'[，,；;、]'

        result = []
        current_pos = 0
        current_segment = ""

        # Find all minor punctuation positions
        matches = list(re.finditer(minor_punct, segment))

        if not matches:
            # No minor punctuation, split by max_length
            for i in range(0, len(segment), self.max_length):
                result.append(segment[i:i + self.max_length])
            return result

        # Split at minor punctuation while respecting max_length
        for match in matches:
            end_pos = match.end()
            potential_segment = segment[current_pos:end_pos].strip()

            if len(current_segment) + len(potential_segment) <= self.max_length:
                current_segment += segment[current_pos:end_pos]
                current_pos = end_pos
            else:
                # Current segment would exceed max_length
                if current_segment:
                    result.append(current_segment.strip())
                current_segment = segment[current_pos:end_pos]
                current_pos = end_pos

        # Add remaining text
        if current_pos < len(segment):
            remaining = segment[current_pos:].strip()
            if len(current_segment) + len(remaining) <= self.max_length:
                current_segment += remaining
            else:
                if current_segment:
                    result.append(current_segment.strip())
                # If remaining is still too long, split by max_length
                if len(remaining) > self.max_length:
                    for i in range(0, len(remaining), self.max_length):
                        result.append(remaining[i:i + self.max_length])
                else:
                    result.append(remaining)

        if current_segment:
            result.append(current_segment.strip())

        return [s for s in result if s]  # Filter out empty strings

    def _parse_voice_markers(self, text: str) -> list[tuple[str, str]]:
        """
        Parse voice markers in text.

        Voice markers have the format [voice_name] and indicate which voice
        should be used for the following text.

        Args:
            text: Text potentially containing voice markers

        Returns:
            List of (voice_name, text) tuples
        """
        import re

        # Pattern to match voice markers like [voice_name]
        voice_pattern = r'\[(\w+)\]'

        result = []
        current_pos = 0
        current_voice = None

        for match in re.finditer(voice_pattern, text):
            # Get text before this marker
            if match.start() > current_pos:
                text_before = text[current_pos:match.start()].strip()
                if text_before:
                    result.append((current_voice, text_before))

            # Update current voice
            current_voice = match.group(1)
            current_pos = match.end()

        # Add remaining text
        if current_pos < len(text):
            remaining = text[current_pos:].strip()
            if remaining:
                result.append((current_voice, remaining))

        # If no markers found, return all text with None voice
        if not result:
            result = [(None, text.strip())] if text.strip() else []

        return result

    def split(self, article: str, default_voice: str = "main") -> list[SentenceSegment]:
        """
        Split article into sentence segments.

        This is the main method that orchestrates the splitting process:
        1. Parse voice markers to identify voice changes
        2. Split text by punctuation
        3. Assign sequential indices
        4. Create SentenceSegment objects

        Args:
            article: Input article text
            default_voice: Default voice name to use (default: "main")

        Returns:
            List of SentenceSegment objects
        """
        # Parse voice markers
        voice_sections = self._parse_voice_markers(article)

        # Split each section by punctuation
        all_segments = []
        segment_index = 0

        for voice_name, text in voice_sections:
            # Use default voice if no voice specified
            voice = voice_name if voice_name else default_voice

            # Split text by punctuation
            text_segments = self._split_by_punctuation(text)

            # Create SentenceSegment objects
            for text_seg in text_segments:
                if text_seg.strip():  # Skip empty segments
                    segment = SentenceSegment(
                        index=segment_index,
                        text=text_seg.strip(),
                        voice_name=voice
                    )
                    all_segments.append(segment)
                    segment_index += 1

        return all_segments
