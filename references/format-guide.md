# 图片文档重建 - 格式参考

## 目录
- [输入格式](#输入格式)
- [输出格式](#输出格式)
- [参数说明](#参数说明)
- [输出目录结构](#输出目录结构)
- [常见问题](#常见问题)

## 输入格式

### 输入文件
- **文件类型**：PDF格式（.pdf）
- **文档类型**：图片型PDF（扫描版、截图版）
- **支持场景**：
  - 扫描的学术论文
  - 截图保存的技术文档
  - 扫描的书籍、报告
  - 包含图表的PDF文档

### 输入要求
- PDF文件应可正常打开和阅读
- 建议DPI≥150，更高DPI会提升OCR准确率
- 文件大小：建议≤100MB（更大文件处理时间会显著增加）
- 支持加密PDF（需提供密码，但脚本当前版本不支持）

### 百度OCR API要求
- 需要有效的百度OCR API凭证（APP_ID、API Key和Secret Key）
- 百度OCR有免费额度（通常为500次/天）
- 超出免费额度需要付费，详见[百度OCR价格说明](https://cloud.baidu.com/product/ocr/pricing)
- 需要稳定的网络连接调用API
- 使用官方baidu-aip SDK，自动处理token管理和错误重试

## 输出格式

### Markdown文件结构
生成的Markdown文件包含以下部分：

#### 1. 元数据头部
```markdown
---
# 重建的文档
源文件: example.pdf
生成时间: 2026-01-29 10:30:00
页面数: 25
插图策略: 包含插图
OCR引擎: 百度OCR API
---
```

#### 2. 文档主体
- **标题**：使用 `#`、`##`、`###` 标记不同层级
- **段落**：普通文本段落
- **列表**：使用 `- ` 标记列表项
- **表格**：基础表格识别（Markdown表格格式）
- **分页标记**：每页之间使用 `---` 分隔

#### 3. 插图引用（如果启用）
```markdown
![Figure 1 on page 3](figures/page3_fig1.png)
```

### 输出示例
```markdown
---
# 重建的文档
源文件: research_paper.pdf
生成时间: 2026-01-29 10:30:00
页面数: 12
插图策略: 包含插图
OCR引擎: 百度OCR API
---

# Introduction

Artificial Intelligence has transformed many industries in recent years.

## Key Technologies

- Machine Learning
- Deep Learning
- Natural Language Processing

The figure below illustrates the overall architecture.

![System Architecture](figures/page2_fig1.png)

Components communicate through REST APIs and message queues.

---

# Methodology

We propose a novel approach for document reconstruction...

```

## 参数说明

### reconstruct.py 脚本参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | 字符串 | ✓ | - | 输入PDF文件路径 |
| `--output` | 字符串 | ✓ | - | 输出Markdown文件路径 |
| `--app-id` | 字符串 | ✓* | - | 百度OCR APP ID（或通过环境变量BAIDU_OCR_APP_ID设置） |
| `--api-key` | 字符串 | ✓* | - | 百度OCR API Key（或通过环境变量BAIDU_OCR_API_KEY设置） |
| `--secret-key` | 字符串 | ✓* | - | 百度OCR Secret Key（或通过环境变量BAIDU_OCR_SECRET_KEY设置） |
| `--include-figures` | 布尔 | - | True | 包含插图（提取并嵌入图像） |
| `--no-figures` | - | - | - | 不包含插图（等价于 --include-figures=False） |
| `--language` | 枚举 | - | ch | OCR语言：zh/ch=中文，en=英文 |
| `--figures-dir` | 字符串 | - | output_dir/figures | 插图输出目录 |

*注：`--app-id`、`--api-key`和`--secret-key`至少通过命令行参数或环境变量提供其中一种方式

### 参数使用示例

#### 示例1：包含插图的中文学术论文
```bash
python scripts/reconstruct.py \
  --input ./paper.pdf \
  --output ./paper.md \
  --app-id 121973148 \
  --api-key ltECE7t3xVfv8WmovjVSEMcF \
  --secret-key g8RKsh1RrBZqIjgep8s1kiMpNpNWJcwz \
  --include-figures \
  --language ch
```

#### 示例2：不含插图的英文技术文档
```bash
python scripts/reconstruct.py \
  --input ./manual.pdf \
  --output ./manual.md \
  --app-id 121973148 \
  --api-key ltECE7t3xVfv8WmovjVSEMcF \
  --secret-key g8RKsh1RrBZqIjgep8s1kiMpNpNWJcwz \
  --no-figures \
  --language en \
  --figures-dir ./my_figures
```

#### 示例3：使用环境变量配置凭证
```bash
# 设置环境变量
export BAIDU_OCR_APP_ID="121973148"
export BAIDU_OCR_API_KEY="ltECE7t3xVfv8WmovjVSEMcF"
export BAIDU_OCR_SECRET_KEY="g8RKsh1RrBZqIjgep8s1kiMpNpNWJcwz"

# 执行转换（无需再次传递API凭证参数）
python scripts/reconstruct.py \
  --input ./report.pdf \
  --output ./report.md
```

## 输出目录结构

### 当 include_figures=True 时
```
output_directory/
├── document.md              # 生成的Markdown文件
└── figures/                 # 插图目录
    ├── page1_fig1.png
    ├── page1_fig2.png
    ├── page2_fig1.png
    └── ...
```

### 当 include_figures=False 时
```
output_directory/
└── document.md              # 仅生成Markdown文件
```

## 常见问题

### Q1: 如何获取百度OCR API凭证？
**A**:
1. 登录[百度智能云控制台](https://console.bce.baidu.com/ai/)
2. 进入"人工智能" → "文字识别"服务
3. 创建应用，选择"通用文字识别"
4. 获取API Key和Secret Key

### Q2: OCR识别准确率如何提升？
**A**:
- 确保源PDF的DPI≥150（推荐200-300）
- 使用百度OCR的高精度识别（脚本默认启用）
- 对于模糊文档，建议在PDF编辑工具中预处理

### Q3: 百度OCR API有调用限额吗？
**A**:
- 百度OCR有免费额度（通常为500次/天）
- 超出免费额度需要付费，按次计费
- 建议监控API使用量，避免超额收费

### Q4: 插图质量如何保证？
**A**:
- 插图直接从PDF提取，不进行额外处理
- 如果源PDF中的插图质量较差，建议：
  1. 在PDF编辑工具中优化插图
  2. 或使用 `--no-figures` 参数，生成纯文字版本

### Q5: 表格识别准确率如何？
**A**:
- 百度OCR支持表格识别，准确率较高
- 复杂表格（合并单元格、嵌套表格）可能需要手动调整
- 建议生成后检查表格格式

### Q6: 首次运行速度很慢？
**A**:
- 首次运行需要获取access_token，速度正常
- access_token会缓存（有效期约30天），后续运行更快
- 网络状况会影响API调用速度

### Q7: 内存不足怎么办？
**A**:
- 对于大型PDF（>50页），建议分批处理
- 可以修改脚本中的DPI设置（降低DPI可减少内存占用）
- 关闭其他占用内存的程序

### Q8: 标题层级不准确怎么办？
**A**:
- 脚本基于字体大小自动推断标题层级
- 生成的Markdown可以手动调整标题层级
- 对于特殊格式的文档（如PPT转的PDF），建议人工校验标题

### Q9: 如何处理加密PDF？
**A**:
- 当前版本不支持加密PDF
- 建议先使用PDF工具（如PDFtk、Adobe Acrobat）解密

### Q10: 支持哪些语言？
**A**:
- 默认支持中文和英文
- 中文使用 `--language ch` 或 `--language zh`
- 英文使用 `--language en`
- 百度OCR还支持其他语言，需要修改脚本配置

### Q11: API调用失败怎么办？
**A**:
- 检查网络连接是否正常
- 确认API Key和Secret Key是否正确
- 查看API余额是否充足
- 查看日志输出的详细错误信息

### Q12: 如何批量处理多个PDF？
**A**:
- 编写shell脚本循环调用
- 示例：
```bash
for file in *.pdf; do
  python scripts/reconstruct.py \
    --input "$file" \
    --output "output/${file%.pdf}.md" \
    --api-key YOUR_API_KEY \
    --secret-key YOUR_SECRET_KEY
done
```

## 质量评估标准

### 优秀输出（满足以下条件）
- ✓ OCR字符准确率≥95%（清晰文档）
- ✓ 标题层级正确率≥85%
- ✓ 列表识别正确率≥90%
- ✓ 插图提取完整（如果启用）
- ✓ Markdown格式规范，可直接使用

### 可接受输出（满足以下条件）
- ✓ OCR字符准确率≥80%
- ✓ 主要标题可识别
- ✓ 段落分割基本正确
- ✓ 少量OCR错误需要人工修正

### 需要重新处理
- ✗ OCR字符准确率<70%
- ✗ 结构完全错误（标题、段落混乱）
- ✗ 大量乱码
- ✗ 表格识别完全错误

## 最佳实践

1. **API凭证管理**：
   - 使用环境变量存储API Key和Secret Key
   - 不要将凭证硬编码在脚本中
   - 定期检查API使用量和余额

2. **预处理建议**：
   - 使用高DPI扫描（建议300 DPI）
   - 确保文档平整无倾斜
   - 避免阴影和反光
   - 百度OCR服务端已做预处理，无需客户端处理

3. **参数选择**：
   - 学术论文：启用插图，使用对应语言
   - 技术手册：根据需要决定是否包含插图
   - 笔记/草稿：可禁用插图，生成纯文字版本

4. **后处理优化**：
   - 使用智能体润色内容
   - 手动修正OCR错误
   - 调整标题层级
   - 优化表格格式

5. **性能优化**：
   - 批量处理多个文档
   - 监控API调用次数
   - 合理安排处理时间（避开高峰期）
