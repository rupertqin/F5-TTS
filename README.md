# 🎙️ TTS Article Generator

基于F5-TTS的多音色文本转语音生成器。

## ✨ 特点

- 🎭 **多音色支持** - 在一篇文章中使用多个不同的音色
- 📝 **简单格式** - 使用JSON标记指定音色和参数
- 🚀 **一键生成** - 无需复杂的命令行参数
- 🎵 **高质量** - 基于F5-TTS的先进语音合成技术

## 🚀 快速开始

### 1. 编辑文本

打开 `gen/speech.txt`：

```
{"name": "f-a/happy", "seed": -1, "speed": 1} 你好！今天天气真好。

{"name": "f-b/哇", "seed": -1, "speed": 1} 哇，真的很不错呢！

{"name": "f-c/嘿嘿", "seed": -1, "speed": 1.1} 嘿嘿，我们出去玩吧。
```

### 2. 运行生成

```bash
python generate.py
```

### 3. 获取音频

生成的音频在 `gen/output/` 目录！

## 📋 可用音色

### f-a（情感音色）

- `f-a/angry` - 生气
- `f-a/confused` - 困惑
- `f-a/fear` - 恐惧
- `f-a/happy` - 开心
- `f-a/sad` - 悲伤
- `f-a/tender` - 温柔

### f-b（语气词）

- `f-b/哇` - 惊叹
- `f-b/哼` - 不满
- `f-b/好呀` - 同意

### f-c（口语化）

- `f-c/嘿嘿` - 调皮
- `f-c/小傻瓜` - 亲昵
- `f-c/是呀` - 肯定

## 📝 格式说明

每段文本前添加JSON配置：

```json
{
  "name": "f-a/happy", // 音色路径
  "seed": -1, // 随机种子（-1=随机）
  "speed": 1.0 // 语速（1.0=正常）
}
```

## 📚 文档

- **[START_HERE.md](START_HERE.md)** - 快速开始指南
- **[USAGE.md](USAGE.md)** - 详细使用说明
- **[VOICES.md](VOICES.md)** - 所有音色列表
- **[SIMPLE_VERSION_COMPLETE.md](SIMPLE_VERSION_COMPLETE.md)** - 完整文档

## 💡 示例

### 对话场景

```
{"name": "f-a/happy", "seed": -1, "speed": 1} 你好！今天天气真好。

{"name": "f-b/好呀", "seed": -1, "speed": 1} 是啊，我们出去走走吧。

{"name": "f-a/confused", "seed": -1, "speed": 1} 去哪里呢？

{"name": "f-c/嘿嘿", "seed": -1, "speed": 1.1} 嘿嘿，我知道一个好地方。
```

### 情感变化

```
{"name": "f-a/happy", "seed": -1, "speed": 1} 我今天收到了一个好消息！

{"name": "f-a/sad", "seed": -1, "speed": 0.9} 但是也有一些不太好的事情。

{"name": "f-a/angry", "seed": -1, "speed": 1.1} 有人居然欺骗了我！

{"name": "f-a/tender", "seed": -1, "speed": 0.95} 不过，我选择原谅。
```

## 🔧 参数说明

### speed（语速）

- `0.8` - 慢速（适合学习）
- `1.0` - 正常速度
- `1.2` - 快速（适合新闻）
- `1.5` - 很快

### seed（随机种子）

- `-1` - 每次都不同（推荐）
- `0, 1, 2...` - 固定种子，每次相同

## 📂 项目结构

```
.
├── generate.py              # 主程序
├── gen/
│   ├── speech.txt          # 输入文本（编辑这个）
│   └── output/             # 生成的音频
└── voices/                 # 音色文件
    ├── f-a/
    ├── f-b/
    └── f-c/
```

## 🎵 播放音频

```bash
# macOS
afplay gen/output/segment_0000.wav

# Linux
aplay gen/output/segment_0000.wav

# Windows
start gen/output/segment_0000.wav
```

## 🔧 合并音频（可选）

```bash
cd gen/output
ls *.wav | sort | sed 's/^/file /' > filelist.txt
ffmpeg -f concat -safe 0 -i filelist.txt -c copy ../final.wav
```

## ❓ 常见问题

**Q: 找不到音色文件？**
检查 `voices/` 目录，确保音色文件存在。

**Q: JSON格式错误？**
确保使用双引号，格式正确。

**Q: 生成速度慢？**
正常现象，每段需要几秒。确保使用GPU。

## 📦 依赖

- Python 3.10+
- f5-tts
- torch
- torchaudio

## 📄 许可

与F5-TTS项目相同的许可证。

---

**开始创作你的多音色TTS内容吧！** 🎉

```bash
python generate.py
```
