# 🚀 使用指南

## 超简单！只需3步

### 1️⃣ 编辑文本

打开 `gen/speech.txt`，按以下格式编写：

```
{"name": "f-a/happy", "seed": -1, "speed": 1} 你的第一句话。

{"name": "f-b/sad", "seed": -1, "speed": 1} 你的第二句话。
```

### 2️⃣ 运行生成

```bash
python generate.py
```

### 3️⃣ 获取音频

生成的音频在 `gen/output/` 目录！

---

## 📝 格式说明

每段文本前面加一个JSON配置：

```json
{
  "name": "f-a/happy", // 音色（必需）
  "seed": -1, // 随机种子（可选，-1表示随机）
  "speed": 1.0 // 语速（可选，1.0=正常）
}
```

然后直接写文本内容。

---

## 🎭 可用音色

你的 `voices/` 目录下有：

### f-a 系列

- `f-a/angry` - 生气
- `f-a/confused` - 困惑
- `f-a/fear` - 恐惧
- `f-a/happy` - 开心
- `f-a/sad` - 悲伤
- `f-a/tender` - 温柔

### f-b 系列

- `f-b/angry`
- `f-b/confused`
- `f-b/fear`
- `f-b/happy`
- `f-b/sad`
- `f-b/tender`

### f-c 系列

- `f-c/angry`
- `f-c/confused`
- `f-c/fear`
- `f-c/happy`
- `f-c/sad`
- `f-c/tender`

---

## 💡 示例

### 对话示例

```
{"name": "f-a/happy", "seed": -1, "speed": 1} 你好！今天天气真好。

{"name": "f-b/happy", "seed": -1, "speed": 1} 是啊，我们出去走走吧。

{"name": "f-a/confused", "seed": -1, "speed": 1} 去哪里呢？

{"name": "f-b/happy", "seed": -1, "speed": 1} 去公园怎么样？
```

### 情感变化示例

```
{"name": "f-a/happy", "seed": -1, "speed": 1} 我今天收到了一个好消息！

{"name": "f-a/sad", "seed": -1, "speed": 0.9} 但是也有一些不太好的事情发生。

{"name": "f-a/angry", "seed": -1, "speed": 1.1} 有人居然欺骗了我！

{"name": "f-a/tender", "seed": -1, "speed": 0.95} 不过，我选择原谅。
```

### 多角色示例

```
{"name": "f-a/happy", "seed": -1, "speed": 1} 欢迎收听今天的节目。

{"name": "f-b/happy", "seed": -1, "speed": 1} 今天我们邀请到了一位特别嘉宾。

{"name": "f-c/happy", "seed": -1, "speed": 1} 大家好，很高兴来到这里。

{"name": "f-a/confused", "seed": -1, "speed": 1} 请问您是做什么工作的？

{"name": "f-c/happy", "seed": -1, "speed": 1} 我是一名人工智能研究员。
```

---

## ⚙️ 参数说明

### speed（语速）

- `0.8` - 慢速（适合学习）
- `1.0` - 正常速度（推荐）
- `1.2` - 快速（适合新闻）
- `1.5` - 很快

### seed（随机种子）

- `-1` - 每次都不同（推荐）
- `0, 1, 2...` - 固定种子，每次相同

---

## 📂 文件位置

```
gen/
├── speech.txt          ← 编辑这个文件
├── speech_example.txt  ← 参考示例
└── output/             ← 生成的音频在这里
    ├── segment_0000.wav
    ├── segment_0001.wav
    └── ...
```

---

## 🎵 播放音频

### macOS

```bash
afplay gen/output/segment_0000.wav
```

### Linux

```bash
aplay gen/output/segment_0000.wav
# 或
vlc gen/output/segment_0000.wav
```

### Windows

```bash
start gen/output/segment_0000.wav
```

---

## 🔧 合并音频（可选）

如果想要一个完整的音频文件：

```bash
cd gen/output
ls *.wav | sort | sed 's/^/file /' > filelist.txt
ffmpeg -f concat -safe 0 -i filelist.txt -c copy ../final.wav
```

---

## ❓ 常见问题

**Q: 找不到音色文件？**

```
❌ Error: Voice file not found: voices/f-a/happy.wav
```

检查 `voices/` 目录下是否有对应的WAV文件。

**Q: JSON格式错误？**

```
⚠️  Warning: Invalid JSON config
```

确保JSON格式正确，使用双引号，不要有多余的逗号。

**Q: 生成速度慢？**
这是正常的，F5-TTS模型较大，每段需要几秒到十几秒。

**Q: 如何提高音质？**

- 确保参考音频（voices/下的WAV）质量高
- 调整speed参数
- 尝试不同的音色

---

## 🎉 开始使用

1. 编辑 `gen/speech.txt`
2. 运行 `python generate.py`
3. 查看 `gen/output/`

就这么简单！
