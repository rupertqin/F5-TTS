# 🚀 快速开始 - TTS Article Generator MVP

## 5分钟上手指南

### 步骤 1: 验证环境 ✅

你的环境已经配置好了：

```bash
✅ Python 3.13.11
✅ f5-tts 1.1.15
✅ torch 2.10.0
✅ conda env: f5-tts
```

### 步骤 2: 测试功能（无需音频）

```bash
# 测试文章切割和音色标记功能
python test_mvp.py
```

你应该看到：

```
✅ Splitting test completed!
✅ Voice markers test completed!
🎉 All tests passed!
```

### 步骤 3: 准备参考音频

你需要一个WAV格式的参考音频文件（3-10秒）：

**选项A: 使用现有的WAV文件**

```bash
# 如果你有WAV文件，直接使用
REF_AUDIO="/path/to/your/voice.wav"
```

**选项B: 从MP3转换**

```bash
# 使用FFmpeg转换
ffmpeg -i your_audio.mp3 -ar 24000 reference.wav
REF_AUDIO="reference.wav"
```

**选项C: 使用F5-TTS自带的示例**

```bash
# 检查是否有示例音频
ls src/f5_tts/infer/examples/basic/*.wav
# 如果有，可以使用：
REF_AUDIO="src/f5_tts/infer/examples/basic/basic_ref_zh.wav"
```

### 步骤 4: 生成语音！

```bash
# 基本用法
python -m tts_article_generator \
  --input examples/article.txt \
  --ref-audio $REF_AUDIO \
  --output output/

# 带参考文本（推荐，质量更好）
python -m tts_article_generator \
  --input examples/article.txt \
  --ref-audio $REF_AUDIO \
  --ref-text "你的参考音频的文本内容" \
  --output output/
```

### 步骤 5: 查看结果

```bash
# 查看生成的音频文件
ls -lh output/segments/

# 播放第一个片段（macOS）
afplay output/segments/segment_0000.wav

# 或使用其他播放器
# vlc output/segments/segment_0000.wav
```

## 完整示例

### 示例 1: 使用中文参考音频

```bash
python -m tts_article_generator \
  --input examples/article.txt \
  --ref-audio my_chinese_voice.wav \
  --ref-text "这是我的声音" \
  --speed 1.0 \
  --max-length 200 \
  --output output_chinese/
```

### 示例 2: 使用英文参考音频

```bash
python -m tts_article_generator \
  --input examples/article.txt \
  --ref-audio my_english_voice.wav \
  --ref-text "This is my voice" \
  --speed 1.1 \
  --max-length 150 \
  --output output_english/
```

### 示例 3: 使用音色标记

创建一个带音色标记的文章 `multi_voice_article.txt`：

```text
这是默认音色的开场白。

[narrator]
现在切换到旁白音色。
这段用于叙述背景。

[character1]
这是角色一的台词。

[main]
切换回主音色。
```

然后生成（注意：MVP版本会忽略音色标记，都使用同一个参考音频）：

```bash
python -m tts_article_generator \
  --input multi_voice_article.txt \
  --ref-audio narrator_voice.wav \
  --output output_multi/
```

## 常用参数

| 参数           | 说明         | 默认值         | 示例             |
| -------------- | ------------ | -------------- | ---------------- |
| `--input`      | 输入文章文件 | 必需           | `article.txt`    |
| `--ref-audio`  | 参考音频文件 | 必需           | `voice.wav`      |
| `--output`     | 输出目录     | `output`       | `my_output/`     |
| `--ref-text`   | 参考文本     | 空（自动转录） | `"这是参考文本"` |
| `--max-length` | 最大句子长度 | 200            | `150`            |
| `--speed`      | 语速倍数     | 1.0            | `1.2`            |
| `--model`      | 模型名称     | `F5-TTS`       | `F5-TTS`         |

## 输出说明

生成的文件结构：

```
output/
└── segments/
    ├── segment_0000.wav  # 第1个句子
    ├── segment_0001.wav  # 第2个句子
    ├── segment_0002.wav  # 第3个句子
    └── ...
```

每个文件对应文章中的一个句子片段。

## 后续处理

### 合并所有音频（可选）

如果你想要一个完整的音频文件：

```bash
# 方法1: 使用FFmpeg
cd output/segments
ls *.wav | sort | sed 's/^/file /' > filelist.txt
ffmpeg -f concat -safe 0 -i filelist.txt -c copy ../final.wav

# 方法2: 使用Python (pydub)
python -c "
from pydub import AudioSegment
import glob

segments = sorted(glob.glob('output/segments/*.wav'))
combined = AudioSegment.empty()
for seg in segments:
    combined += AudioSegment.from_wav(seg)
combined.export('output/final.wav', format='wav')
"
```

## 故障排除

### 问题: 找不到参考音频文件

```
❌ Error: Reference audio file not found
```

**解决**: 检查文件路径是否正确，使用绝对路径或相对路径。

### 问题: CUDA内存不足

```
RuntimeError: CUDA out of memory
```

**解决**:

- 减少 `--max-length` 参数（如改为100）
- 关闭其他占用GPU的程序
- 或等待完整版本支持CPU模式

### 问题: 生成速度很慢

**原因**: F5-TTS模型较大，每个句子需要几秒到十几秒。
**解决**:

- 确保使用GPU
- 减少句子数量（缩短文章）
- 这是正常现象，耐心等待

### 问题: 音质不好

**解决**:

- 使用更高质量的参考音频（清晰、无噪音）
- 提供准确的 `--ref-text`
- 尝试不同的 `--speed` 值
- 使用更长的参考音频（5-10秒）

## 下一步

### 如果MVP满足需求

- 继续使用MVP版本
- 手动合并音频文件
- 根据需要调整参数

### 如果需要更多功能

完整版本将包括：

- 🔄 缓存管理（断点续传）
- 📝 字幕生成（SRT格式）
- 🎬 自动拼接（一键生成完整音频）
- 🎨 多音色支持（真正的音色切换）
- ⚙️ 配置文件（TOML格式）

## 获取帮助

```bash
# 查看所有参数
python -m tts_article_generator --help

# 查看详细文档
cat MVP_README.md

# 查看完成状态
cat MVP_COMPLETE.md
```

## 示例输出

运行成功后，你会看到类似这样的输出：

```
============================================================
🎙️  TTS Article Generator (MVP)
============================================================

📖 Loading article from: examples/article.txt
   Article length: 393 characters

✂️  Splitting article (max length: 200 chars)...
   Created 9 segments

💾 Output directory: output/segments

🎵 Initializing audio generator...
   Model: F5-TTS
   Speed: 1.0x
   Reference audio: voice.wav

🔄 Loading F5-TTS model...
✅ Model loaded successfully!

🔊 Generating audio for 9 segments...
------------------------------------------------------------

[1/9] 这是一个测试文章。
   ✅ Saved: segment_0000.wav (2.34s)

[2/9] 我们将使用F5-TTS来生成语音。
   ✅ Saved: segment_0001.wav (3.12s)

...

============================================================
📊 Generation Summary
============================================================
✅ Successful: 9/9
💾 Output directory: output/segments
============================================================
```

---

**准备好了吗？开始生成你的第一个TTS音频吧！** 🎉
