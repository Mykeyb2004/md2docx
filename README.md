# md2docx - Markdown to Word Converter

> 🚀 将 Markdown 文档转换为精美的 Word 文档，支持完整的样式控制。

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)



# 启动命令

```bash	
# 图形界面（可在任意目录运行）
uv run --project /Users/zhangqijin/PycharmProjects/md2docx md2docx-gui

# 命令行转换（可在任意目录运行）
uv run --project /Users/zhangqijin/PycharmProjects/md2docx md2docx /完整路径/input.md --output-file /完整路径/output.docx
```



## ✨ 特性

### 核心功能

- 🎨 **完整样式控制** - 通过 YAML 配置精确控制文档样式
- 📄 **文档级设置** - 页面大小、边距、默认行距
- 📝 **Markdown 语法支持** - 标题、段落、列表、表格、粗体、斜体、代码、LaTeX 公式
- 📊 **高级表格功能** - 对齐控制、斑马纹、表头样式
- 🔬 **LaTeX 公式渲染** - 行内和块级数学公式（基础+进阶）
- 🖥️ **双模式界面** - GUI 图形界面 + CLI 命令行
- 📜 **历史记录** - 自动保存转换历史，快速重用
- 🇨🇳 **中文优化** - 完美支持中文字体和排版规范

### 支持的 Markdown 语法

| 语法 | 支持状态 | 说明 |
|:-----|:-------:|:-----|
| **标题** (H1-H4) | ✅ | 完整样式控制 |
| **段落** | ✅ | 首行缩进、对齐、行距 |
| **粗体** `**text**` | ✅ | 支持自定义颜色 |
| **斜体** `*text*` | ✅ | 支持自定义颜色 |
| **列表** (有序/无序) | ✅ | 自动编号、缩进控制 |
| **表格** | ✅ | 对齐控制、斑马纹 |
| 表格对齐 (`:---`, `:--:`, `---:`) | ✅ | Markdown 对齐语法 |
| **行内代码** `` `code` `` | ✅ | 支持自定义样式 |
| **代码块** | ✅ | 语法高亮、背景色 |
| **LaTeX 行内公式** `$...$` | ✅ | 渲染为图片 |
| **LaTeX 块级公式** `$$...$$` | ✅ | 居中渲染 |
| **图片** | 🚧 | 计划中 |
| **链接** | 🚧 | 计划中 |

---

## 📦 安装

### 使用 uv (推荐)

```bash
# 克隆项目
git clone https://github.com/yourusername/md2docx.git
cd md2docx

# 安装依赖
uv sync
```

### 使用 pip

```bash
pip install -e .
```

### 依赖项

- Python 3.8+
- python-docx >= 1.1.0
- mistune >= 3.0.0
- PyYAML >= 6.0

---

## 🚀 快速开始

### 🎨 GUI 模式（推荐）

启动图形界面，享受可视化操作体验：

```bash
uv run --project /Users/zhangqijin/PycharmProjects/md2docx md2docx-gui
```

**功能特点：**
- 📂 **可视化文件选择** - 浏览器风格的文件选择
- 📜 **自动历史记录** - 记录所有转换历史
- ✅ **实时进度显示** - 转换进度一目了然
- 🔄 **快速重用** - 双击历史记录快速重新转换
- 💚 **状态标识** - 绿色=成功，红色=失败

![GUI Screenshot](docs/images/gui_screenshot.png)

📖 详细说明：[GUI 使用指南](docs/GUI_GUIDE.md)

---

### ⌨️ CLI 模式（命令行）

#### 基础用法

```bash
# 基本转换
uv run md2docx input.md

# 指定输出文件
uv run md2docx input.md --output-file output.docx

# 覆盖已存在的输出文件
uv run md2docx input.md --output-file output.docx --overwrite

# 指定输出目录，文件名保持为 input.docx
uv run md2docx input.md --output-dir output

# 递归转换整个目录下的所有 Markdown 文件，并统一输出到一个目录
uv run md2docx docs --output-dir output

# 在任意目录运行，并使用完整输入/输出路径
uv run --project /Users/zhangqijin/PycharmProjects/md2docx md2docx /完整路径/input.md --output-file /完整路径/output.docx

# 使用自定义样式配置
uv run md2docx input.md -s my_styles.yaml

# 查看帮助
uv run md2docx --help

# 查看版本
uv run md2docx --version
```

#### 高级用法

```bash
# 使用预定义模板
uv run md2docx report.md -t academic

# 转换并打开文件
uv run md2docx doc.md && open doc.docx
```

---

### 🐍 Python API

#### 基础使用

```python
from md2docx import Converter

# 创建转换器
converter = Converter()

# 转换文件
converter.convert('input.md', 'output.docx')
```

#### 使用自定义样式

```python
from md2docx import Converter

# 使用自定义配置文件
converter = Converter(style_config='my_styles.yaml')
converter.convert('input.md', 'output.docx')
```

#### 转换字符串

```python
from md2docx import Converter

# Markdown 字符串
md_content = """
# 标题

这是一段**粗体**文字和*斜体*文字。

| 列1 | 列2 |
|:---|---:|
| 左对齐 | 右对齐 |
"""

# 转换
converter = Converter()
converter.convert_string(md_content, 'output.docx')
```

#### 获取 Document 对象

```python
from md2docx import Converter

converter = Converter()
doc = converter.to_document("# Hello World")

# 进一步处理 document
doc.add_paragraph("Extra content")
doc.save('output.docx')
```

---

## ⚙️ 样式配置

### 配置文件结构

md2docx 使用 YAML 格式配置文档样式。常用结构如下，完整参数见文末链接：

```yaml
# 1. 文档级设置
document:
  page_size: A4          # A4, A3, Letter
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.17cm
  margin_right: 3.17cm
metadata:
  author: "张三"        # 建议填写真实作者
  title: "项目报告"      # 可选；默认取首个 Markdown 标题
  subject: "技术文档"
  keywords: ["md2docx", "报告"]

# 2. 标题样式 (heading1-4)
heading1:
  font_name: "方正小标宋简体"
  font_size: 22pt        # 二号
  font_color: "#000080"
  bold: true
  alignment: center

# 3. 段落样式
paragraph:
  font_name: "仿宋"
  font_size: 12pt        # 小四
  line_spacing: 1.5
  first_line_indent: 2   # 2个字符
  alignment: justify

# 4. 行内文本样式
inline:
  bold:
    font_color: null     # null = 继承父级
  italic:
    font_color: null

# 5. 表格样式
table:
  font_name: "仿宋"
  font_size: 12pt
  header_bold: true
  header_background: "#F2F2F2"
  header_alignment: center
  header_vertical_alignment: center
  # 斑马纹
  alternating_rows: true
  row_background_even: "#F9F9F9"

# 6. 列表样式
list:
  font_name: "仿宋"
  font_size: 12pt
  number_format: "1."
  ordered_list_as_text: false
  indent_size: 0.5in
  space_after: 3pt

# 7. Mermaid 图样式
mermaid:
  theme: default
  width: 5.5in
  alignment: center
  follow_previous_trigger_height_ratio: 0.24
  follow_previous_width_ratio: 0.55
  follow_previous_space_before: 0pt

# 8. 章节扫描配置
chapter_scan:
  target_dir: output
  glob: "*.md"
  recursive: true
```

### 配置文件位置

- **默认配置**: `md2docx/templates/default.yaml`
- **自定义配置**: 任意路径的 `.yaml` 文件

### 文档元数据

为了减少上传平台把文件误判成“第三方采集软件生成”的概率，建议显式填写 `metadata` 段中的作者、标题、主题和关键词。若不填写，程序会尽量从 Markdown 内容和当前系统用户中推导合理值，并写入 Word 的核心属性。

### 章节排版异常扫描

用于扫描输出目录中的章节 `.md` 文件，定位“序号单独成行、与后续小标题或段首正文拆开”的问题。

```bash
# 默认读取当前 default.yaml 中的 chapter_scan.target_dir
uv run python scripts/scan_chapter_issues.py

# 指定配置文件
uv run python scripts/scan_chapter_issues.py --config custom_styles.yaml

# 临时覆盖扫描目录
uv run python scripts/scan_chapter_issues.py --target-dir output/chapters
```

也可以直接使用正式 CLI 命令：

```bash
# 在项目目录内
uv run md2docx-scan-chapters --config config_统计台账.yaml

# 在任意目录
uv run --project /Users/zhangqijin/PycharmProjects/md2docx \
  md2docx-scan-chapters \
  --config /绝对路径/config_统计台账.yaml
```

### 中文字号对照

| 中文字号 | 磅值(pt) | 推荐用途 |
|:-------:|:-------:|:--------|
| 二号 | 22pt | 一级标题 ⭐ |
| 小二号 | 18pt | 重要标题 |
| 三号 | 16pt | 二级标题 ⭐ |
| 四号 | 14pt | 三级标题 |
| 小四号 | 12pt | 正文 ⭐ |
| 五号 | 10.5pt | 小字注释 |

📖 完整配置文档：[样式配置完整指南](docs/STYLES_CONFIG.md)

### Mermaid 小图布局

如果希望 Mermaid 转成图片后，在“图不高”的情况下更紧凑地跟在上一段后面，可以在配置文件里调整 `mermaid` 节：

```yaml
mermaid:
  theme: default
  width: 5.5in
  alignment: center
  keep_with_previous: true
  keep_with_previous_max_chars: 80
  force_page_break_before_oversized: false
  space_before: 6pt
  space_after: 6pt
  follow_previous_trigger_height_ratio: 0.24
  follow_previous_width_ratio: 0.55
  follow_previous_space_before: 0pt
```

参数说明：

- `alignment`
  Mermaid 图片的段落对齐方式，当前建议保持 `center`，插入时图片会居中。
- `theme`
  Mermaid 内置主题名，可设为 `default`、`dark`、`forest`、`neutral`、`base`。
- `keep_with_previous`
  是否允许小型 Mermaid 图片与上一段文字做“同页优先”绑定。默认 `true`，但只有命中“小图”规则时才会绑定，避免较大的“正文段 + 图片”整体被 Word 挤到下一页。
- `keep_with_previous_max_chars`
  允许绑定上一段的最长文本长度。默认 `80`，用于避免长正文段被图片拖到下一页；设为 `0` 可恢复不限制长度的绑定。
- `force_page_break_before_oversized`
  超大 Mermaid 图是否强制从新页开始。默认 `false`，避免导出后即使手工缩小图片，仍然被段落级硬分页卡住。
- `follow_previous_trigger_height_ratio`
  “小图”判定阈值，按“图片最终高度 / 当前页可用高度”计算。值越大，判定越宽松，更多图会贴近上一段。
- `follow_previous_width_ratio`
  命中“小图”规则后，图片最多缩到“当前页可用宽度”的多少。值越大，图更宽；值越小，图更紧凑。
- `follow_previous_space_before`
  小图贴靠上一段时的段前距。默认 `0pt`，让图片换行后尽量贴近上一段正文。

### Mermaid 颜色主题

如果你希望 Mermaid 导出的图片使用自定义配色，可以在 `mermaid` 节里设置内置主题，或者继续传入 `theme_variables`：

```yaml
mermaid:
  theme: base
  background_color: white
  theme_variables:
    primaryColor: "#E8F1FF"
    primaryTextColor: "#163A70"
    primaryBorderColor: "#2F6BFF"
    lineColor: "#2F6BFF"
    secondaryColor: "#FFF4D6"
    tertiaryColor: "#F6F8FA"
```

说明：

- 只想切换现成风格时，直接改 `theme` 即可。
- 想细调节点、边框、文字、连线颜色时，使用 `theme_variables`。
- 只要设置了 `theme_variables`，md2docx 会自动切到 Mermaid 的 `base` 主题，因为 Mermaid 只会在 `base` 主题上稳定应用这些颜色变量。

推荐取值：

- 更宽松：`follow_previous_trigger_height_ratio: 0.30`，`follow_previous_width_ratio: 0.60`
- 更严格：`follow_previous_trigger_height_ratio: 0.18`，`follow_previous_width_ratio: 0.45`

说明：

- 这些值是排版经验阈值，不是 Word 的固定规范。
- 当前实现默认会把 Mermaid 图片和上一段设置为“同页优先”，命中“小图”规则时还会进一步压缩间距和宽度。
- 如果你确实需要超大图强制从新页开始，可以显式设置 `force_page_break_before_oversized: true`。
- Word 的最终分页仍由 Word 自己决定，因此这里是强引导，不是逐页精确计算。

---

## 📊 表格功能

### 对齐控制

md2docx 完全支持 Markdown 表格对齐语法：

```markdown
| 左对齐 | 居中 | 右对齐 |
|:-------|:----:|-------:|
| Left | Center | Right |
```

**效果**：
- `:---` → 左对齐
- `:--:` → 居中
- `---:` → 右对齐

### 斑马纹（交替行颜色）

在配置文件中启用：

```yaml
table:
  alternating_rows: true
  row_background_odd: "#FFFFFF"
  row_background_even: "#F9F9F9"
```

**效果**：提升大型表格可读性

---

## 📂 项目结构

```
md2docx/
├── md2docx/
│   ├── __init__.py          # 包入口
│   ├── cli.py               # CLI 命令行工具
│   ├── gui.py               # GUI 图形界面 ✨
│   ├── converter.py         # 核心转换器
│   ├── parser.py            # Markdown 解析器
│   ├── renderer.py          # Word 渲染器
│   ├── styles.py            # 样式管理器
│   └── templates/
│       └── default.yaml     # 默认样式配置
├── docs/
│   ├── STYLES_CONFIG.md     # 样式配置完整指南 📖
│   ├── GUI_GUIDE.md         # GUI 使用指南 📖
│   ├── UV_GUIDE.md          # uv 使用指南
│   └── TABLE_FEATURES.md    # 表格功能说明
├── tests/                   # 测试文件
├── README.md                # 本文件
└── pyproject.toml           # 项目配置
```

---

## 🧪 开发

### 环境设置

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理。

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_converter.py

# 带覆盖率报告
uv run pytest --cov=md2docx --cov-report=term-missing

# 详细输出
uv run pytest -v
```

**当前测试状态**：✅ 32/32 测试通过 (100%)

### 代码质量

```bash
# 类型检查
uv run mypy md2docx

# 代码格式化
uv run black md2docx

# Lint 检查
uv run flake8 md2docx
```

---

## 📖 文档

### 用户文档

- 📘 [样式配置完整指南](docs/STYLES_CONFIG.md) - 所有配置参数详解
- 🎨 [GUI 使用指南](docs/GUI_GUIDE.md) - 图形界面使用说明
- 📊 [表格功能说明](docs/TABLE_FEATURES.md) - 表格高级功能

### 开发文档

- 🛠️ [PRD - 产品需求文档](PRD.md)
- 📝 [TODO - 开发任务清单](TODO.md)
- 🔧 [UV 使用指南](docs/UV_GUIDE.md)

---

## 🎯 使用示例

### 示例 1：学术论文

```bash
# 使用学术样式模板
uv run md2docx thesis.md -s academic_styles.yaml
```

**配置文件** (`academic_styles.yaml`):
```yaml
document:
  page_size: A4
  margin_left: 3.17cm
  margin_right: 3.17cm

heading1:
  font_name: "方正小标宋简体"
  font_size: 22pt
  alignment: center

paragraph:
  font_name: "仿宋"
  font_size: 12pt
  first_line_indent: 2
  line_spacing: 1.5
```

### 示例 2：技术文档

```markdown
# API 文档

## 接口列表

| 接口 | 方法 | 说明 |
|:-----|:----:|:-----|
| /api/users | GET | 获取用户列表 |
| /api/users/:id | GET | 获取用户详情 |
```

**转换**：
```bash
uv run md2docx api_doc.md
```

### 示例 3：报告文档

使用 GUI 模式，启用表格斑马纹：

1. 启动 GUI：`uv run md2docx-gui`
2. 选择 Markdown 文件
3. 点击转换
4. 自动保存到历史记录

---

## 🚧 路线图

### ✅ 已完成 (v1.0)

- [x] 核心 Markdown 语法支持
- [x] 完整样式配置系统
- [x] 表格对齐和斑马纹
- [x] GUI 图形界面
- [x] 历史记录功能
- [x] 文档级设置（页面、边距）
- [x] CLI 命令行工具
- [x] 行内代码和代码块
- [x] LaTeX 数学公式（行内+块级）
- [x] 50 个单元测试

### 🚧 计划中 (v1.1)

- [ ] 图片嵌入
- [ ] 超链接
- [ ] 引用块
- [ ] 水平线
- [ ] 矩阵公式支持

### 🔮 未来计划 (v2.0)

- [ ] 批量转换
- [ ] 转换预览
- [ ] 模板市场
- [ ] Word 转 Markdown
- [ ] 在线版本

---

## 📊 项目统计

| 指标 | 数值 |
|:-----|:-----|
| **代码行数** | ~2,700 行 |
| **测试覆盖率** | 59% |
| **测试通过率** | 100% (50/50) |
| **配置参数** | 50 个 |
| **参数实现率** | 84% (42/50) |
| **支持 Markdown 语法** | 11 种 |

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 如何贡献

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 贡献指南

- 遵循现有代码风格
- 添加测试覆盖新功能
- 更新相关文档
- 确保所有测试通过

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 🙏 致谢

- [python-docx](https://github.com/python-openxml/python-docx) - Word 文档操作
- [mistune](https://github.com/lepture/mistune) - Markdown 解析
- [uv](https://github.com/astral-sh/uv) - 依赖管理

---

## 📞 联系方式

- 项目主页：[GitHub](https://github.com/yourusername/md2docx)
- 问题反馈：[Issues](https://github.com/yourusername/md2docx/issues)
- 功能请求：[Discussions](https://github.com/yourusername/md2docx/discussions)

---

**Made with ❤️ by [Your Name]**

*最后更新：2025-11-20*
