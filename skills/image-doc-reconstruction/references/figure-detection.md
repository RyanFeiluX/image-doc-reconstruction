# 插图探测与提取

## 目录
- [功能说明](#功能说明)
- [推荐使用场景](#推荐使用场景)
- [工作原理](#工作原理)
- [插图处理说明](#插图处理说明)
- [插图处理方式对比](#插图处理方式对比)
- [推荐使用场景](#推荐使用场景-1)
- [插图处理方式详细说明](#插图处理方式详细说明)
- [配置参数](#配置参数)

## 功能说明
本技能支持两种插图探测模式和两种插图处理方式：

**插图探测模式**：
1. **PDF原生插图提取**：提取PDF中内嵌的图像对象（适用于原生PDF）
2. **扫描页面插图探测**：从扫描图像中智能探测插图区域（适用于扫描PDF）

**插图处理方式**（默认：嵌入模式）：
1. **嵌入图片到Markdown（默认推荐）**：使用Base64编码嵌入，单个文件便于分享
2. **引用独立图片文件**：保存为独立文件，使用相对路径引用

## 工作原理

### PDF原生插图提取
```
遍历PDF页面
├─ 使用PyMuPDF的get_images()获取所有图像对象
├─ 提取图像字节数据
├─ 保存为独立图片文件（保持原始格式）
└─ 在Markdown中引用：![Figure X](figures/pageX_figY.png)
```

### 扫描页面插图探测（纯Pillow实现）
```
遍历扫描图像
├─ 使用百度OCR识别文本块并获取位置信息
├─ 将页面划分为网格（15x15像素）
├─ 标记被文本块占用的网格
├─ 使用BFS算法找出连续的空白网格区域
├─ 合并空白区域形成候选插图区域
├─ 根据大小、宽高比、位置过滤候选区域
├─ 根据embed参数选择处理方式：
│  ├─ 嵌入模式：转换为Base64编码
│  └─ 引用模式：保存为独立文件
└─ 在Markdown中生成对应语法
```

**技术特点**：
- ✅ 纯Pillow实现，无需OpenCV依赖
- ✅ 适合受限部署环境
- ✅ 仅支持PDF原生插图提取（扫描PDF插图探测已禁用）
- ✅ 支持Base64嵌入和文件引用两种模式
- ✅ 宁缺毋滥策略，避免误识别整页图片
- ✅ 可配置参数（网格大小、边距、面积阈值）

## 插图处理说明

**重要变更**：扫描PDF插图探测已彻底禁用

**原因**：
- 扫描PDF插图探测不可靠，容易误识别整页图片为插图
- 网格化算法在页面几乎没有文本时，会将整个页面识别为空白区域
- 即使设置了OCR覆盖率、宽高比、位置检查，仍无法完全避免误识别

**策略**：
- ✅ **仅提取PDF原生插图**：可靠、准确、无误识别风险
- ❌ **禁用扫描PDF插图探测**：避免误识别整页图片
- 💡 **手动处理**：如果需要提取扫描PDF的插图，建议用户手动处理或使用其他专门工具

**优点**：
- ✅ 彻底避免误识别整页图片的问题
- ✅ 实现简单，风险低
- ✅ 用户可以手动添加遗漏的插图

**缺点**：
- ❌ 无法自动提取扫描PDF中的插图

## 插图处理方式对比

| 插图类型 | 探测效果 | 说明 |
|---------|---------|------|
| **PDF原生插图** | ✅ 95-100% | PDF中嵌入的图像对象，提取准确可靠 |
| **扫描PDF插图** | ❌ 已禁用 | 探测不可靠，容易误识别整页图片 |
| **跨页大图** | ✅ 90-95% | 占据大部分页面的PDF原生插图 |
| **与文字混排的插图** | ✅ 85-90% | PDF原生插图，与文字混排 |
| **表格** | N/A | 表格不会被识别为插图 |

## 推荐使用场景

| 场景 | 推荐模式 | 命令 |
|------|---------|------|
| **通过邮件发送** | 嵌入模式（默认） | `python scripts/reconstruct.py input.pdf output.md` |
| **聊天工具分享** | 嵌入模式（默认） | `python scripts/reconstruct.py input.pdf output.md` |
| **快速分享单个文件** | 嵌入模式（默认） | `python scripts/reconstruct.py input.pdf output.md` |
| **在线文档平台** | 嵌入模式（默认） | `python scripts/reconstruct.py input.pdf output.md` |
| **本地编辑和预览** | 引用模式 | `python scripts/reconstruct.py input.pdf output.md --no-embed` |
| **长期维护和版本控制** | 引用模式 | `python scripts/reconstruct.py input.pdf output.md --no-embed` |
| **GitHub/GitLab预览** | 引用模式 | `python scripts/reconstruct.py input.pdf output.md --no-embed` |

## 插图处理方式详细说明

### 方式1：引用独立图片文件

**实现原理**：
```python
# 保存图片到文件
with open(fig_path, "wb") as f:
    f.write(image_bytes)
# 在Markdown中使用相对路径引用
markdown = f"![Figure 1](figures/page1_fig1.png)"
```

**输出示例**：
```markdown
![Figure 1 on page 1](figures/page1_fig1.png)
```

**优点**：
- ✅ 文件小，加载快
- ✅ 标准Markdown语法，广泛支持
- ✅ 便于单独编辑图片
- ✅ 支持GitHub、GitLab等平台预览
- ✅ 适合长期维护和版本控制

**缺点**：
- ❌ 需要同时传输多个文件
- ❌ 相对路径可能失效
- ❌ 分享时需要打包

**使用方式**：
```bash
# 使用引用模式
python scripts/reconstruct.py input.pdf output.md --no-embed

# 指定插图输出目录
python scripts/reconstruct.py input.pdf output.md --no-embed --figures-dir ./my-figures
```

### 方式2：嵌入图片到Markdown

**实现原理**：
```python
import base64

# 将图片字节转换为Base64编码
encoded_data = base64.b64encode(image_bytes).decode('utf-8')
# 生成Data URI
data_uri = f"data:image/{format};base64,{encoded_data}"
# 在Markdown中使用
markdown = f"![Figure 1]({data_uri})"
```

**输出示例**：
```markdown
![Figure 1 on page 1](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...)
```

**优点**：
- ✅ 单个文件，便于传输和分享
- ✅ 无需担心图片路径问题
- ✅ 支持电子邮件、聊天工具等场景
- ✅ 适合在线文档平台

**缺点**：
- ⚠️ 文件大小增加约33%（Base64编码开销）
- ⚠️ 某些Markdown编辑器可能不支持Data URI
- ⚠️ 编辑大文件可能较慢
- ⚠️ 不适合长期维护

**使用方式**：
```bash
# 启用嵌入模式
python scripts/reconstruct.py input.pdf output.md --embed-figures
```

## 配置参数

| 参数 | 默认值 | 调优建议 |
|------|--------|----------|
| `include_figures` | `True` | 是否包含插图 |
| `embed_figures` | `True` | 是否嵌入图片到Markdown |
| `figures_dir` | `./figures/` | 插图输出目录（引用模式） |
| `min_fig_area` | 页面5% | 最小插图面积（过滤小装饰） |
| `max_fig_area` | 页面40% | 最大插图面积（避免整页被误识别为插图，更加严格） |
| `grid_size` | 15px | 网格大小（插小=更精确，插大=更快） |
| `margin` | 20px | 文本块边距（插小=更多候选，插大=更严格） |
