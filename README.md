# md2docx

将 Markdown 转换为可编辑的 Word (`.docx`) 文档，面向中文文档排版，支持 YAML 样式配置、命令行和图形界面。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

## 功能概览

- CLI 支持单文件转换和目录递归批量转换。
- GUI 支持文件选择、进度与历史记录、配置文件打开和保存。
- YAML 可配置页面、页边距、元数据、标题、段落、代码、列表、表格、数学公式、Mermaid 和章节扫描。
- 支持本地 Markdown 图片；相对路径以 Markdown 文件所在目录为基准解析。
- 公式优先输出为 Word 原生 OMML；无法使用 Pandoc 时回退为 PNG。
- Mermaid 代码块可转为图片，并按页面空间调整大小和分页。
- 可选套用 Word `.docx` 模板，保留模板页眉、页脚中的文字、图片及原有格式。

## 支持的 Markdown

| 语法 | 状态 | 说明 |
| --- | --- | --- |
| 标题（H1-H4） | 支持 | 可单独配置字体、字号、对齐和间距。 |
| 段落、换行、粗体、斜体 | 支持 | 支持首行缩进、行距和颜色。 |
| 行内代码、代码块 | 支持 | 应用字体、背景、间距和内边距样式；不提供通用语法高亮。 |
| 有序、无序和嵌套列表 | 支持 | 默认使用 Word 自动编号；可配置为普通文本编号。 |
| 表格 | 支持 | 支持 Markdown 列对齐、表头重复、垂直对齐、列宽策略和可选斑马纹。 |
| 本地图片 | 支持 | 嵌入相对或绝对路径的本地图片；缺失或不支持的图片会显示占位内容。 |
| 行内与块级 LaTeX | 支持 | 优先 OMML，随后回退为图片。 |
| Mermaid 围栏代码块 | 支持 | 需要可用的 `mmdc`；渲染失败时保留为代码块。 |
| 水平线（`---`、`***`、`___`） | 可配置 | 默认忽略；设置 `document.ignore_thematic_breaks: false` 后渲染。 |
| 超链接 | 未支持 | 当前不会生成 Word 超链接。 |
| 引用块 | 未支持 | 当前不保留为独立引用样式。 |

## 安装

项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 环境和依赖。

```bash
git clone https://github.com/Mykeyb2004/md2docx.git
cd md2docx
uv sync
```

基本要求：

- Python 3.8 或更高版本
- `uv`

可选外部工具：

- [Pandoc](https://pandoc.org/)：将 LaTeX 转为 Word 原生 OMML。未安装时会尝试图片回退。
- [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli) 的 `mmdc` 命令：渲染 Mermaid 图。例如：`npm install -g @mermaid-js/mermaid-cli`。

## 快速开始

### 命令行

```bash
# 输出到与输入文件同名的 .docx
uv run md2docx input.md

# 指定输出文件
uv run md2docx input.md --output-file output.docx

# 输出到目录
uv run md2docx input.md --output-dir output

# 递归转换目录内全部 Markdown 文件
uv run md2docx docs --output-dir output

# 覆盖已有输出
uv run md2docx input.md --output-file output.docx --overwrite

# 使用自定义 YAML 样式
uv run md2docx input.md --style-file my_styles.yaml

# 套用 Word 模板（保留页眉页脚）
uv run md2docx input.md --word-template letterhead.docx --output-file output.docx

# 查看全部选项
uv run md2docx --help
```

目录输入必须指定 `--output-dir`。目录中的 Markdown 文件会递归转换到该输出目录；请避免不同子目录中出现同名文件。

从任意目录调用项目：

```bash
uv run --project /path/to/md2docx md2docx /path/to/input.md --output-file /path/to/output.docx
```

`--template` 接口当前仅有内置 `default` 模板；实际项目建议通过 `--style-file` 使用自己的 YAML 配置。

`--word-template` 只接受 `.docx` 文件，并要求模板包含一个 section。转换时会清空模板正文占位内容，保留模板的页眉、页脚、图片、关系和页面几何设置；模板页面设置优先于 YAML 中的 `document` 设置。它可以与 `--template` 或 `--style-file` 一起使用。

### 图形界面

```bash
uv run md2docx-gui
```

GUI 提供单文件转换、进度显示、历史记录和配置文件工作流：

- 自动恢复上一次成功载入或保存的 YAML 配置。
- 在编辑器中维护已保存配置与编辑草稿，未保存草稿不会影响转换。
- 支持另存为、恢复内置默认、外部修改冲突检测以及原子保存。
- 配置编辑器提供颜色控件、常用枚举、表格版式和字段说明。
- 在 `Word Template` 行选择可选的 `.docx` 模板；点击 `Clear` 可恢复普通无模板转换。模板选择只对当前转换生效，不会写入偏好设置。

详细操作见 [GUI 使用指南](docs/GUI_GUIDE.md)。GUI 目前只转换单个文件；批量转换请使用 CLI。

### Python API

```python
from md2docx import Converter

# 转换 Markdown 文件；相对图片路径会按 input.md 所在目录解析
converter = Converter(style_config="my_styles.yaml")
converter.convert("input.md", "output.docx")

# 使用 Word 模板保留页眉页脚；可同时传入 YAML 样式配置
template_converter = Converter(
    style_config="my_styles.yaml",
    word_template="letterhead.docx",
)
template_converter.convert("input.md", "output.docx")

# 转换字符串；需要显式传入 base_dir 才能解析相对图片路径
content = """# 报告标题

这是一段**加粗**文本。
"""
converter.convert_string(content, "output.docx", base_dir=".")

# 获取 python-docx Document 以做后续处理
document = converter.to_document("# Hello")
document.add_paragraph("Extra content")
document.save("output.docx")
```

## 样式配置

默认配置位于 [md2docx/templates/default.yaml](md2docx/templates/default.yaml)。CLI 和 Python API 会直接读取自定义 YAML，建议先复制默认配置再修改，以免遗漏关键样式字段。GUI 打开配置文件时会将其与内置默认配置合并。

```yaml
document:
  page_size: A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.17cm
  margin_right: 3.17cm
  line_spacing: 1.5
  ignore_thematic_breaks: false
  auto_fix_tables: false

metadata:
  author: "张三"
  title: "项目报告"
  subject: "技术文档"
  keywords: ["md2docx", "报告"]

heading1:
  font_name: "方正小标宋简体"
  font_size: 22pt
  alignment: center

paragraph:
  font_name: "仿宋"
  font_size: 14pt
  first_line_indent: 2
  line_spacing: 1.5

table:
  layout: accent_grid          # accent_grid、plain_grid、three_line
  column_width_strategy: content-weighted  # 或 balanced
  header_alignment: center
  vertical_alignment: center
  alternating_rows: false

mermaid:
  command: mmdc
  format: png
  theme: base
  width: 5.5in

chapter_scan:
  target_dir: output
  glob: "*.md"
  recursive: true
```

主要配置节包括：`document`、`metadata`、`heading1` 至 `heading4`、`outline`、`paragraph`、`inline`、`code_block`、`table`、`list`、`math_inline`、`math_block`、`mermaid` 和 `chapter_scan`。

### 表格

`table.layout` 提供三种版式：

- `accent_grid`：主题网格表，可启用表头填充和斑马纹。
- `plain_grid`：黑色细网格和灰色表头。
- `three_line`：三线表边框。

列宽默认采用 `content-weighted`，会按内容长度分配；可改为更均衡的 `balanced`。完整字段和示例见[样式配置指南](docs/STYLES_CONFIG.md)与[表格功能说明](docs/TABLE_FEATURES.md)。

### 数学公式与 Mermaid

行内公式使用 `$...$`，块级公式使用 `$$...$$` 或标注为 `latex` / `tex` 的代码块。安装 Pandoc 后会生成可编辑的 Word 数学对象；否则使用图片回退。

Mermaid 使用围栏代码块：

````markdown
```mermaid
flowchart LR
  A[Markdown] --> B[DOCX]
```
````

`mmdc` 不可用或图形渲染失败时，原 Mermaid 源码会按普通代码块输出。

### 章节排版异常扫描

扫描器用于找出章节 Markdown 中“序号单独成行、与后续小标题或正文分开”的可疑排版：

```bash
# 读取默认配置的 chapter_scan 设置
uv run md2docx-scan-chapters

# 使用指定配置或临时覆盖扫描目录、文件模式
uv run md2docx-scan-chapters --config custom.yaml
uv run md2docx-scan-chapters --target-dir output/chapters --pattern "*.md"
```

发现问题时命令以状态码 `1` 退出；没有问题时以 `0` 退出，适合用于文档发布前检查。

## 项目结构

```text
md2docx/
├── md2docx/
│   ├── cli.py                    # 主 CLI
│   ├── gui.py                    # Tkinter GUI 与配置编辑器
│   ├── converter.py              # Converter 公共 API
│   ├── parser.py                 # Markdown 预处理与 Mistune 解析
│   ├── renderer.py               # python-docx 渲染器
│   ├── styles.py                 # YAML 样式管理
│   ├── config_document.py        # GUI 配置草稿与保存状态
│   ├── math_converter.py         # 公式图片回退
│   ├── omml_converter.py         # Pandoc/OMML 公式转换
│   ├── mermaid_converter.py      # Mermaid CLI 集成
│   ├── chapter_issue_scanner.py  # 章节扫描 CLI
│   └── templates/default.yaml    # 默认样式
├── docs/                         # 用户与开发文档
├── examples/                     # Markdown 示例
├── tests/                        # 自动化测试
└── pyproject.toml                # 项目与 CLI 入口定义
```

## 开发与验证

```bash
# 安装开发依赖
uv sync

# 运行测试
uv run pytest

# 查看覆盖率
uv run pytest --cov=md2docx --cov-report=term-missing

# 类型与风格检查
uv run mypy md2docx
uv run flake8 md2docx
```

## 文档

- [样式配置完整指南](docs/STYLES_CONFIG.md)
- [GUI 使用指南](docs/GUI_GUIDE.md)
- [表格功能说明](docs/TABLE_FEATURES.md)
- [uv 使用指南](docs/UV_GUIDE.md)
- [Nuitka 构建说明](docs/NUITKA_BUILD.md)
- [示例文档](examples/README.md)

## 当前限制与后续方向

- Word 超链接和引用块尚未实现。
- GUI 仅支持单文件转换；CLI 已支持目录批量转换。
- 表格尚不支持单元格合并、手动列宽和表题。
- 暂不提供转换预览、Word 转 Markdown 或在线版本。

## 许可证与反馈

仓库当前未包含 `LICENSE` 文件；在补充许可证文本前，请勿假定项目以 MIT 或其他许可证发布。

- 项目主页：[Mykeyb2004/md2docx](https://github.com/Mykeyb2004/md2docx)
- 问题反馈：[Issues](https://github.com/Mykeyb2004/md2docx/issues)
- 功能讨论：[Discussions](https://github.com/Mykeyb2004/md2docx/discussions)
