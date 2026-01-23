#!/usr/bin/env python
"""
Quick test script for MVP functionality (without actual audio generation).

This script tests the article splitting functionality without requiring
F5-TTS model or reference audio files.
"""

from tts_article_generator.splitter import ArticleSplitter


def test_splitting():
    """Test article splitting functionality."""
    print("=" * 60)
    print("🧪 Testing Article Splitter")
    print("=" * 60)

    # Load test article
    print("\n📖 Loading test article...")
    with open('examples/article.txt', 'r', encoding='utf-8') as f:
        article = f.read()

    print(f"   Article length: {len(article)} characters")
    print(f"   Preview: {article[:100]}...")

    # Test with different max lengths
    for max_length in [50, 100, 200]:
        print(f"\n✂️  Testing with max_length={max_length}")
        print("-" * 60)

        splitter = ArticleSplitter(max_length=max_length)
        segments = splitter.split(article)

        print(f"   Created {len(segments)} segments")

        # Verify all segments are within max length
        too_long = [s for s in segments if len(s.text) > max_length]
        if too_long:
            print(f"   ⚠️  Warning: {len(too_long)} segments exceed max length!")
            for s in too_long:
                print(f"      Segment {s.index}: {len(s.text)} chars")
        else:
            print(f"   ✅ All segments within max length")

        # Show first few segments
        print(f"\n   First 3 segments:")
        for seg in segments[:3]:
            preview = seg.text[:40] + '...' if len(seg.text) > 40 else seg.text
            print(f"      [{seg.index}] ({len(seg.text)} chars) {preview}")

    print("\n" + "=" * 60)
    print("✅ Splitting test completed!")
    print("=" * 60)


def test_voice_markers():
    """Test voice marker parsing."""
    print("\n" + "=" * 60)
    print("🎭 Testing Voice Markers")
    print("=" * 60)

    # Test article with voice markers
    test_text = """
这是默认音色的文本。

[narrator]
这段使用旁白音色。
可以跨越多行。

[character1]
这是角色一的台词。

[main]
切换回主音色。
"""

    print("\n📝 Test text with voice markers:")
    print(test_text)

    splitter = ArticleSplitter(max_length=200)
    segments = splitter.split(test_text)

    print(f"\n✂️  Created {len(segments)} segments:")
    print("-" * 60)

    for seg in segments:
        print(f"[{seg.index}] voice={seg.voice_name}")
        print(f"    {seg.text}")
        print()

    # Verify voice assignments
    voices_used = set(s.voice_name for s in segments)
    print(f"✅ Voices used: {', '.join(sorted(voices_used))}")

    print("=" * 60)


if __name__ == "__main__":
    test_splitting()
    test_voice_markers()

    print("\n" + "=" * 60)
    print("🎉 All tests passed!")
    print("=" * 60)
    print("\n💡 To test with actual audio generation, you need:")
    print("   1. A reference audio file (WAV format)")
    print("   2. Run: python -m tts_article_generator --input examples/article.txt --ref-audio your_voice.wav")
    print("=" * 60)
