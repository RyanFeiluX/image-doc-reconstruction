# Image Doc Reconstruction — 百度OCR版

> 使用百度OCR API将图片型PDF/扫描件转换为结构化Markdown。
> 智能页眉页脚过滤、PDF插图提取、字符一致性规范化。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Hermes Skill](https://img.shields.io/badge/Hermes-Skill-8A2BE2)](https://hermes-agent.nousresearch.com/)

## 📸 它能做什么

| 场景 | 说明 |
|:----|:------|
| **扫描件数字化** | 扫描版PDF → 结构化Markdown，保留标题层级 |
| **合同文档提取** | 图片型合同、协议的文字提取与结构化 |
| **学术论文转换** | 论文PDF转可编辑Markdown，含插图提取 |
| **技术手册处理** | 技术文档、操作手册的批量数字化 |

## ✨ 亮点

- **智能页眉页脚过滤** — 两遍遍历+位置指纹算法，自动探测并过滤页码/页眉/页脚
- **PDF原生插图提取** — Base64嵌入或独立文件引用模式
- **标题层级识别** — 基于字体统计 + 逻辑验证，自动识别# ## ###
- **字符一致性规范化** — 全半角标点统一、编号样式统一、括号配对矫正
- **自动PDF类型检测** — 文本型PDF直接提取（无需OCR，速度快），图片型自动走OCR
- **免费额度** — 百度OCR每天500次免费调用

## 🚀 快速开始

### 一分钟安装

```bash
# 安装依赖
pip install PyMuPDF Pillow baidu-aip

# 克隆仓库
git clone https://github.com/RyanFeiluX/image-doc-reconstruction.git
cd image-doc-reconstruction
```

### 配置百度OCR

1. 前往 [百度智能云控制台](https://console.bce.baidu.com/ai/) → 创建"通用文字识别"应用
2. 获取三个凭证：APP_ID、API Key、Secret Key
3. 配置环境变量：

```bash
export BAIDU_OCR_APP_ID="your_app_id"
export BAIDU_OCR_API_KEY="your_api_key"
export BAIDU_OCR_SECRET_KEY="your_secret_key"
```

如果使用 Hermes，添加到 `~/.hermes/.env`：

```bash
echo 'BAIDU_OCR_APP_ID="your_app_id"' >> ~/.hermes/.env
echo 'BAIDU_OCR_API_KEY="your_api_key"' >> ~/.hermes/.env
echo 'BAIDU_OCR_SECRET_KEY="your_secret_key"' >> ~/.hermes/.env
```

### 使用

```bash
# 基本用法
python scripts/reconstruct.py -i 扫描件.pdf -o 输出.md

# 通过便捷命令（安装后）
pdf2md-baidu -i 扫描件.pdf -o 输出.md
```

## 🔧 高级用法

```bash
# 禁用页眉页脚过滤（保留原文所有内容）
python scripts/reconstruct.py -i doc.pdf -o out.md --no-filter

# 禁用字符规范化（保留原始标点）
python scripts/reconstruct.py -i doc.pdf -o out.md --no-normalize

# 不提取插图（纯文本输出）
python scripts/reconstruct.py -i doc.pdf -o out.md --no-figures

# 引用模式（插图保存为独立文件）
python scripts/reconstruct.py -i doc.pdf -o out.md --no-embed

# 强制高精度OCR（更清晰但更慢）
python scripts/reconstruct.py -i doc.pdf -o out.md --accurate-ocr

# 指定英文文档
python scripts/reconstruct.py -i doc.pdf -o out.md --language en
```

## 📦 安装为 Hermes 技能

### 方式一：通过 tap 安装（推荐）

```bash
# 添加 tap 源
hermes skills tap add RyanFeiluX/image-doc-reconstruction

# 安装技能
hermes skills install image-doc-reconstruction
```

### 方式二：直接 URL 安装

```bash
hermes skills install https://raw.githubusercontent.com/RyanFeiluX/image-doc-reconstruction/main/skills/image-doc-reconstruction/SKILL.md
```

### 方式三：手动安装

```bash
cp -r skills/image-doc-reconstruction ~/.hermes/skills/productivity/
pip install -r requirements.txt
```

### 方式二：GitHub tap（需要 Skills Hub 注册）

```bash
hermes skills tap add RyanFeiluX/image-doc-reconstruction
hermes skills install image-doc-reconstruction
```

## 📁 项目结构

```
image-doc-reconstruction/
├── skills/
│   └── image-doc-reconstruction/    # Hermes 技能包
│       ├── SKILL.md                 # 技能描述
│       ├── scripts/
│       │   ├── reconstruct.py       # 核心引擎（PDF渲染+OCR+后处理）
│       │   └── pdf2md-baidu         # CLI 快捷命令
│       ├── references/
│       │   ├── format-guide.md
│       │   ├── header-footer-detection.md
│       │   └── figure-detection.md
│       └── assets/
│           └── templates/
├── README.md             # 本文件
├── requirements.txt      # Python 依赖
└── LICENSE               # MIT License
```

## 🔄 与Qwen VL版对比

| | 百度OCR版（本仓库） | Qwen VL版 |
|:----|:----|:----|
| **原理** | 传统OCR引擎（文字识别） | 大模型视觉理解 |
| **依赖** | 3个pip包（baidu-aip, PyMuPDF, Pillow） | 3个pip包（openai, PyMuPDF, Pillow） |
| **强项** | 小字体密集文档、表格、免费额度 | 设备标签、手写、复杂排版 |
| **费用** | 免费500次/天 | ~0.003元/张 |
| **仓库** | 当前仓库 | [text-vision-recognition](https://github.com/RyanFeiluX/text-vision-recognition) |

两个工具互补，**场景建议**：
- 密集文字扫描件/合同 → **百度OCR版**
- 拍摄的设备标签/铭牌 → **Qwen VL版**
- 两者都装，看效果选

## 🔑 环境变量

| 变量 | 必需 | 说明 |
|:----|:----|:------|
| `BAIDU_OCR_APP_ID` | 是 | 百度智能云应用ID |
| `BAIDU_OCR_API_KEY` | 是 | API密钥 |
| `BAIDU_OCR_SECRET_KEY` | 是 | 加密密钥 |

也支持通过 `--app-id / --api-key / --secret-key` 命令行参数传入。

## 💰 费用说明

百度OCR API 免费额度 **500次/天**，超出后按量计费：

- 通用文字识别（高精度）：约 0.01元/次
- 通用文字识别（普通）：约 0.004元/次

处理一本100页的书大约 0.4-1.0 元。

## 📄 许可

MIT License
