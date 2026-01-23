# TTS Article Generator - MVP

最小可行产品（MVP）版本，实现核心功能：文章切割 + 音频生成。

## 已实现功能

✅ **文章切割** - 智能切割长文章为适合TTS的短句
✅ **音频生成** - 使用F5-TTS生成高质量语音
✅ **命令行接口** - 简单易用的CLI
✅ **进度显示** - 实时显示生成进度

## 快速开始

### 1. 准备参考音频

你需要一个WAV格式的参考音频文件（3-10秒），用于定义生成语音的音色。

```bash
# 参考音频应该放在某个位置，例如：
# examples/voices/my_voice.wav
```

### 2. 准备文章

创建一个UTF-8编码的文本文件，例如 `examples/article.txt`（已提供示例）。

### 3. 运行生成

```bash
# 基本用法
python -m tts_article_generator \
  --input examples/article.txt \
  --ref-audio examples/voices/my_voice.wav \
  --output output/

# 带参考文本（提高质量）
python -m tts_article_generator \
  --input examples/article.txt \
  --ref-audio examples/voices/my_voice.wav \
  --ref-text "这是参考音频的文本内容" \
  --output output/

# 自定义参数
python -m tts_article_generator \
  --input examples/article.txt \
  --ref-audio examples/voices/my_voice.wav \
  --max-length 150 \
  --speed 1.2 \
  --output output/
```

## 命令行参数

### 必需参数

- `--input` - 输入文章文件路径（UTF-8编码）
- `--ref-audio` - 参考音频文件路径（WAV格式）

### 可选参数

- `--output` - 输出目录（默认：output）
- `--ref-text` - 参考音频的文本内容（可选，留空则自动转录）
- `--max-length` - 最大句子长度（默认：200字符）
- `--speed` - 语速倍数（默认：1.0）
- `--model` - F5-TTS模型名称（默认：F5-TTS）

## 输出结构

```
output/
└── segments/
    ├── segment_0000.wav
    ├── segment_0001.wav
    ├── segment_0002.wav
    └── ...
```

每个segment文件对应文章中的一个句子片段。

## 示例输出

```
============================================================
🎙️  TTS Article Generator (MVP)
============================================================

📖 Loading article from: examples/article.txt
   Article length: 245 characters

✂️  Splitting article (max length: 200 chars)...
   Created 8 segments

💾 Output directory: output/segments

🎵 Initializing audio generator...
   Model: F5-TTS
   Speed: 1.0x
   Reference audio: examples/voices/my_voice.wav

🔊 Generating audio for 8 segments...
------------------------------------------------------------

[1/8] 这是一个测试文章。
   ✅ Saved: segment_0000.wav (2.34s)

[2/8] 我们将使用F5-TTS来生成语音。
   ✅ Saved: segment_0001.wav (3.12s)

...

============================================================
📊 Generation Summary
============================================================
✅ Successful: 8/8
💾 Output directory: output/segments
============================================================
```

## 技术细节

### 文章切割逻辑

1. 按句号、问号、感叹号等主要标点符号切割
2. 如果句子超过最大长度，在逗号、分号等次要标点处进一步切割
3. 保留原文的标点符号和格式
4. 为每个片段分配连续的序号

### 音频生成

- 使用F5-TTS的Multi-speech功能
- 支持中英文混合文本
- 自动处理参考音频转录（如果未提供ref_text）
- 懒加载模型（首次使用时才加载）

## 未来扩展（完整版本）

MVP版本专注于核心功能。完整版本将包括：

- 🔄 **缓存管理** - 断点续传，避免重复生成
- 📝 **字幕生成** - 自动生成SRT字幕文件
- 🎬 **文件拼接** - 将所有片段拼接成完整音频
- 🎨 **多音色支持** - 使用[voice_name]标记切换音色
- ⚙️ **配置文件** - TOML配置文件支持
- 📊 **进度条** - 更美观的进度显示
- 🧪 **完整测试** - 单元测试和属性测试

## 故障排除

### 问题：找不到F5-TTS模块

```bash
pip install f5-tts
```

### 问题：CUDA内存不足

尝试使用CPU模式或减少batch size（需要修改代码）。

### 问题：音频质量不佳

- 使用更高质量的参考音频（清晰、无噪音）
- 提供准确的ref_text
- 调整speed参数

### 问题：生成速度慢

- 确保使用GPU（CUDA）
- 减少max_length以生成更短的片段
- 使用更快的模型（如果可用）

## 依赖

- Python 3.10+
- f5-tts
- torch
- torchaudio

## 许可

与F5-TTS项目相同的许可证。
