import os
import tempfile
from src.tts_article.splitter import ArticleSplitter, SentenceSegment
from src.tts_article.config import ConfigManager, VoiceConfig, Config
from src.tts_article.subtitle_generator import SubtitleGenerator, SubtitleEntry
from src.tts_article.concatenator import FileConcatenator


def test_split_and_voice_mapping():
    text = "这是第一句。\n[hero] 这是英雄的台词！[villain] 恶棍回应？"
    splitter = ArticleSplitter(max_length=200)
    segments = splitter.split(text)
    assert all(isinstance(s, SentenceSegment) for s in segments)
    # Expect voices main, hero, villain to appear
    voices = set(s.voice_name for s in segments)
    assert {"main", "hero", "villain"}.issubset(voices)


def test_srt_generation_and_order():
    sg = SubtitleGenerator()
    entries = [
        sg.create_entry(index=0, start_time=0.0, duration=1.2, text="第一句"),
        sg.create_entry(index=1, start_time=1.2, duration=0.8, text="第二句"),
    ]
    tmp = tempfile.mkdtemp()
    srt_path = os.path.join(tmp, "out.srt")
    sg.generate_srt(entries, srt_path)
    assert os.path.exists(srt_path)
    content = open(srt_path, "r", encoding="utf-8").read()
    # Ensure ordering 1 then 2 present
    assert "第一句" in content and "第二句" in content


def test_concatenation_order_and_crossfade():
    tmp = tempfile.mkdtemp()
    # Create two short silent wavs
    p1 = os.path.join(tmp, "a.wav")
    p2 = os.path.join(tmp, "b.wav")
    from pydub import AudioSegment
    AudioSegment.silent(duration=500).export(p1, format="wav")
    AudioSegment.silent(duration=700).export(p2, format="wav")
    out = os.path.join(tmp, "combined.wav")
    fc = FileConcatenator()
    fc.concatenate_audio([p1, p2], out, cross_fade_duration=0.1)
    assert os.path.exists(out)
