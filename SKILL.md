---
name: image-doc-reconstruction
description: 使用百度OCR API将图片型PDF/扫描件转换为结构化Markdown，支持智能页眉页脚过滤、PDF原生插图提取、字符一致性规范化（标点/编号/括号）、标题层级自动识别。适用于学术论文、技术手册、合同文档等。
version: 1.0.0
author: RyanFeiluX
license: MIT
metadata:
  hermes:
    tags: [pdf, ocr, baidu, document, markdown, reconstruction]
    related_skills: [text-vision-recognition]
---

# 图片文档重建 (image-doc-reconstruction)

## 概述

将图片型PDF（扫描件、截图）转换为结构化Markdown文档，使用百度OCR API进行文字识别。

### 核心能力

| 功能 | 说明 |
|:----|:-----|
| **PDF类型自动检测** | 文本型→直接提取（无需OCR），图片型→走OCR |
| **百度OCR识别** | 高精度/普通双模式，自动选择 |
| **智能页眉页脚过滤** | 两遍遍历+位置指纹算法，自动探测并过滤 | 
| **PDF原生插图提取** | Base64嵌入或独立文件引用 |
| **标题层级识别** | 基于字体统计 + 层次逻辑验证 |
| **字符一致性规范化** | 标点符号、编号样式、括号配对统一 |

## 前置准备

### 1. 百度OCR API凭证

在 [百度智能云控制台](https://console.bce.baidu.com/ai/) 创建"通用文字识别"应用，获取三个凭证：

| 凭证 | 环境变量 | 说明 |
|:----|:--------|:----|
| APP_ID | `BAIDU_OCR_APP_ID` | 应用ID |
| API Key | `BAIDU_OCR_API_KEY` | API密钥 |
| Secret Key | `BAIDU_OCR_SECRET_KEY` | 加密密钥 |

配置方式（二选一）：

**方式A：** 编辑 `~/.hermes/.env` 文件，添加以下内容（随 Hermes 自动加载）：
```
BAIDU_OCR_APP_ID="your_app_id"
BAIDU_OCR_API_KEY="your...port BAIDU_OCR_SECRET_KEY="your...```

**方式B：** 环境变量（临时）
```bash
export BAIDU_OCR_APP_ID="your_app_id"
export BAIDU_OCR_API_KEY="your...ort BAIDU_OCR_SECRET_KEY="your...```

### 2. 安装依赖

```bash
pip install PyMuPDF Pillow baidu-aip
```

> PyMuPDF 直接渲染 PDF 页面为图片，无需额外系统依赖。

### 3. 验证安装

```bash
python scripts/reconstruct.py --help
```

## 使用方式

### 基本用法

```bash
# 转换PDF为Markdown
python scripts/reconstruct.py -i document.pdf -o output.md

# 通过便捷命令（如果已安装）
pdf2md-baidu -i 扫描件.pdf -o 结果.md
```

### 高级参数

```bash
# 禁用页眉页脚过滤（保留原文所有内容）
python scripts/reconstruct.py -i doc.pdf -o out.md --no-filter

# 禁用字符规范化（保留原始标点）
python scripts/reconstruct.py -i doc.pdf -o out.md --no-normalize

# 不提取插图（纯文本输出）
python scripts/reconstruct.py -i doc.pdf -o out.md --no-figures

# 引用模式（插图保存为独立文件，非Base64嵌入）
python scripts/reconstruct.py -i doc.pdf -o out.md --no-embed

# 强制高精度OCR
python scripts/reconstruct.py -i doc.pdf -o out.md --accurate-ocr

# 指定英文文档
python scripts/reconstruct.py -i doc.pdf -o out.md --language en

# 使用命令行参数传递API凭证（不推荐，仅临时用）
python scripts/reconstruct.py -i doc.pdf -o out.md \
  --app-id xxx --api-key xxx --secret-key xxx
```

## 处理流程

```
用户上传PDF
    ↓
PDF类型检测
├─ 文本型 → 直接提取文本（无需OCR，速度快）
└─ 图片型/混合型 → OCR处理
         ↓
第一遍遍历：探测页眉页脚模式
（统计每页相同位置出现的内容，≥3次标记为页眉页脚）
         ↓
第二遍遍历：实际处理
├─ 提取PDF原生插图
├─ OCR识别（自动选择普通/高精度模式）
├─ 应用页眉页脚过滤
├─ 应用辅助元素过滤（页码、分隔线、关键词）
├─ 分类文本块（标题/段落/列表）
└─ 生成该页Markdown
         ↓
全局后处理
├─ 全局标题标准化（跨页面统一标题层级）
├─ 标点符号规范化
├─ 编号样式一致性（全局统一编号格式）
├─ 括号配对统一
         ↓
输出结构化Markdown ✓
```

## 费用说明

百度OCR API 有免费额度（通常 **500次/天**），超出后按量计费：

- 通用文字识别（高精度）：约 0.01元/次
- 通用文字识别（普通）：约 0.004元/次

处理一本100页的书大约 0.4-1.0 元。

## 常见问题

### Q: 识别质量不好怎么办？
A: 尝试：① 使用 `--accurate-ocr` 高精度模式 ② 确保源PDF清晰 ③ 禁用页眉页脚过滤 `--no-filter`

### Q: PDF是文本型的还需要OCR吗？
A: 不需要。脚本自动检测PDF类型，文本型PDF直接提取，不走OCR，不消耗API额度。

### Q: 和Qwen VL版本比哪个好？
A: 百度OCR更擅长表格/票据/固定格式文档，Qwen VL更擅长上下文理解和多页连贯文档。两个可以互补使用。

### Q: 如何批量处理？
```bash
for f in *.pdf; do
  python scripts/reconstruct.py -i "$f" -o "output/${f%.pdf}.md"
done
```
