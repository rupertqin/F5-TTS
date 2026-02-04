# TTS Article Generator

基于 F5-TTS 的多音色文本转语音生成器，支持在文章中使用多个不同的音色。

## 功能特点

- **多音色支持** - 使用 `[voice_name]` 标记切换不同音色
- **并发生成** - 支持并行生成多个音频片段
- **多音字处理** - 支持配置同音字替换，解决多音字读音问题
- **CLI 命令** - 一键生成 `tts-article`

## 快速开始

### 1. 编辑文本

编辑 `speech.txt`：

```text
[main]
这是主声音的文本。

[vivian]
这是 vivian 的文本。

[man]
这是男性的文本。
```

### 2. 运行生成

```bash
tts-article
```

或者使用 Python：

```bash
python -m tts_article
```

### 3. 获取音频

生成的音频在 `output/` 目录：

- `output/audio/*.wav` - 各个片段
- `output/final_audio.wav` - 合并后的完整音频

## 配置说明

### 配置文件 (config.toml)

```toml
input_article = "speech.txt"      # 输入文本文件
output_dir = "output"             # 输出目录
model_name = "F5TTS_v1_Base"      # 模型名称
max_sentence_length = 200         # 最大句子长度

# 生成参数
nfe_step = 32                     # Flow matching 步数 (16-64)
cfg_strength = 2.0                # 音色相似度 (1.0-4.0)
speed = 1.0                       # 语速 (0.5-2.0)
target_rms = 0.1                  # 音量 (0.05-0.2)

# 多音字处理（使用同音字替换）
polyphone_dict = { "偏好" = "偏浩", "行长" = "航长" }

# 音色配置
[voices.main]
ref_audio = "voices/nice/happy.wav"
speed = 0.9

[voices.vivian]
ref_audio = "voices/vivian/normal.wav"
speed = 1.0
```

### 语音标记格式

在 `speech.txt` 中使用 `[voice_name]`或者 `{"name": "voice_name", "seed": -1, "speed": 0.9} ` 切换音色：

```text
[caixukun]
我跟我闺蜜看电影就特别有画面感。

[man]
由于男性作为权力的"生产者"，他们更信奉力量本身。

[vivian.happy]
她只需要回到一个正确的时间点。
```

## 可用音色

### nice 音色

| 音色     | 路径                     | 语速 |
| -------- | ------------------------ | ---- |
| main     | voices/nice/happy.wav    | 0.9  |
| caixukun | voices/nice/caixukun.wav | 1.0  |
| guimi    | voices/nice/guimi.wav    | 1.0  |
| happy    | voices/nice/happy.wav    | 0.9  |

### f-a 情感音色

| 音色     | 路径                    | 语速 |
| -------- | ----------------------- | ---- |
| tender   | voices/f-a/tender.wav   | 1.0  |
| confused | voices/f-a/confused.wav | 0.9  |
| sad      | voices/f-a/sad.wav      | 1.0  |
| friendly | voices/f-a/friendly.wav | 1.0  |
| angry    | voices/f-a/angry.wav    | 1.0  |
| fear     | voices/f-a/fear.wav     | 1.0  |

### f-b 语气词

| 音色  | 路径                 | 语速 |
| ----- | -------------------- | ---- |
| haoya | voices/f-b/haoya.wav | 1.0  |
| heng  | voices/f-b/heng.wav  | 1.0  |
| wa    | voices/f-b/wa.wav    | 1.1  |

### f-c 口语化

| 音色       | 路径                      | 语速 |
| ---------- | ------------------------- | ---- |
| heihei     | voices/f-c/heihei.wav     | 0.6  |
| xiaoshagua | voices/f-c/xiaoshagua.wav | 1.0  |
| shiya      | voices/f-c/shiya.wav      | 1.0  |

### man 音色

| 音色         | 路径                    | 语速 |
| ------------ | ----------------------- | ---- |
| man          | voices/man/normal.wav   | 1.1  |
| man.angry    | voices/man/angry.wav    | 1.0  |
| man.happy    | voices/man/happy.wav    | 1.0  |
| man.sad      | voices/man/sad.wav      | 1.0  |
| man.surprise | voices/man/surprise.wav | 1.0  |
| man.control  | voices/man/control.wav  | 1.0  |

### vivian 音色

| 音色            | 路径                       | 语速 |
| --------------- | -------------------------- | ---- |
| vivian          | voices/vivian/normal.wav   | 1.0  |
| vivian.angry    | voices/vivian/angry.wav    | 1.0  |
| vivian.happy    | voices/vivian/happy.wav    | 1.0  |
| vivian.sad      | voices/vivian/sad.wav      | 1.0  |
| vivian.surprise | voices/vivian/surprise.wav | 1.0  |
| vivian.control  | voices/vivian/control.wav  | 1.0  |

## 参数说明

### 全局参数

| 参数           | 默认值 | 范围     | 说明                                   |
| -------------- | ------ | -------- | -------------------------------------- |
| `nfe_step`     | 32     | 16-64    | Flow matching 步数，越高越慢但质量越好 |
| `cfg_strength` | 2.0    | 1.0-4.0  | 音色相似度，越高越接近参考音色         |
| `speed`        | 1.0    | 0.5-2.0  | 语速                                   |
| `target_rms`   | 0.1    | 0.05-0.2 | 音量                                   |

### 音色参数

| 参数           | 说明                                             |
| -------------- | ------------------------------------------------ |
| `ref_audio`    | 参考音频路径                                     |
| `ref_text`     | 参考音频对应的文本（可选，从同名 .txt 文件读取） |
| `speed`        | 该音色的语速（覆盖全局设置）                     |
| `nfe_step`     | 该音色的步数（覆盖全局设置）                     |
| `cfg_strength` | 该音色的相似度（覆盖全局设置）                   |
| `target_rms`   | 该音色的音量（覆盖全局设置）                     |

## 多音字处理

由于 F5-TTS 的拼音转换可能不准确，可以通过配置同音字来解决：

```toml
polyphone_dict = {
    "偏好" = "偏浩",   # hao3 -> hao4
    "行长" = "航长",   # hang2zhang3 -> hang2zhang3
}
```

原理：将多音字替换为同音字，让 F5-TTS 读出正确的发音。

## 项目结构

```
.
├── config.toml              # 配置文件
├── speech.txt              # 输入文本（编辑这个）
├── pyproject.toml          # 项目配置
├── tts-article             # CLI 命令入口
├── output/                 # 输出目录
│   ├── audio/              # 音频片段
│   └── final_audio.wav     # 合并后的音频
├── voices/                 # 音色文件
│   ├── nice/
│   ├── f-a/
│   ├── f-b/
│   ├── f-c/
│   ├── man/
│   └── vivian/
└── src/tts_article/        # 源代码
    ├── config.py           # 配置加载
    ├── pipeline.py         # 生成流程
    ├── splitter.py         # 文本分割
    └── generator.py        # 音频生成
```

## CLI 用法

```bash
# 使用默认配置
tts-article

# 指定配置文件
tts-article --config config.toml

# 指定输入输出
tts-article --input speech.txt --output output

# 设置并发数
tts-article --workers 4
```

## 播放音频

```bash
# macOS
afplay output/final_audio.wav

# Linux
aplay output/final_audio.wav
```

## 依赖

- Python 3.10+
- f5-tts
- torch
- torchaudio
- pydub
- tomli (Python < 3.11)

## License

MIT License
