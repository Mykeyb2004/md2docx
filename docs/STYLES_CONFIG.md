# md2docx 样式配置完整指南

> **版本**: v1.0  
> **最后更新**: 2026-04-06

## 📋 目录

1. [配置文件概述](#配置文件概述)
2. [配置节说明](#配置节说明)
3. [参数速查表](#参数速查表)
4. [单位与字号对照](#单位与字号对照)
5. [颜色代码](#颜色代码)
6. [完整配置示例](#完整配置示例)
7. [使用方法](#使用方法)

---

## 配置文件概述

`md2docx` 使用 **YAML 格式**的配置文件定义 Word 文档样式。配置文件包含以下 10 个配置节/配置组：

| 配置节 | 说明 | 必需 |
|:------|:-----|:----:|
| `document` | 文档级设置（页面、边距） | ✅ |
| `heading1-4` | 标题样式（1-4级） | ✅ |
| `paragraph` | 段落样式 | ✅ |
| `inline` | 行内文本样式（粗体、斜体、代码） | ⭕ |
| `code_block` | 代码块样式 | ⭕ |
| `table` | 表格样式 | ⭕ |
| `list` | 列表样式 | ⭕ |
| `math_inline` | 行内公式图片样式 | ⭕ |
| `math_block` | 块级公式图片样式 | ⭕ |
| `mermaid` | Mermaid 图片样式与分页策略 | ⭕ |

---

## 配置节说明

### 1️⃣ document - 文档设置

控制整个 Word 文档的页面布局。

```yaml
document:
  page_size: A4           # 页面大小
  margin_top: 2.54cm      # 上边距
  margin_bottom: 2.54cm   # 下边距
  margin_left: 3.17cm     # 左边距
  margin_right: 3.17cm    # 右边距
  line_spacing: 1.5       # 默认行距倍数
  ignore_thematic_breaks: true  # 是否忽略 Markdown 分割线
```

**参数说明**：

| 参数 | 类型 | 默认值 | 可选值 | 说明 |
|:-----|:----:|:-------|:-------|:-----|
| `page_size` | 字符串 | `A4` | `A4`, `A3`, `Letter` | 纸张大小 |
| `margin_top/bottom/left/right` | 字符串 | `2.54cm` | 任意尺寸 + 单位 | 页边距 |
| `line_spacing` | 数字 | `1.5` | `1.0`, `1.5`, `2.0` | 行距倍数 |
| `ignore_thematic_breaks` | 布尔值 | `true` | `true`/`false` | 是否忽略 Markdown 分割线（`---`、`***`、`___`） |

---

### 2️⃣ heading1-4 - 标题样式

定义 1-4 级标题的样式（所有标题支持相同参数）。

```yaml
heading1:
  font_name: "方正小标宋简体"  # 字体
  font_size: 22pt             # 字号
  font_color: "#000080"       # 颜色
  bold: true                  # 加粗
  italic: false               # 斜体
  space_before: 6pt           # 段前间距
  space_after: 6pt            # 段后间距
  alignment: center           # 对齐方式
  first_line_indent: 0        # 首行缩进（字符数）
```

**参数说明**：

| 参数 | 类型 | 默认值 | 可选值 | 说明 |
|:-----|:----:|:-------|:-------|:-----|
| `font_name` | 字符串 | `"微软雅黑"` | 任意已安装字体 | 字体名称 |
| `font_size` | 字符串 | `18pt` | `12pt`-`42pt` | 字号（见字号对照表） |
| `font_color` | 字符串 | `"#000000"` | 十六进制颜色 | 文字颜色 |
| `bold` | 布尔值 | `true` | `true`/`false` | 是否加粗 |
| `italic` | 布尔值 | `false` | `true`/`false` | 是否斜体 |
| `space_before` | 字符串 | `12pt` | 任意尺寸 + `pt` | 段前间距 |
| `space_after` | 字符串 | `6pt` | 任意尺寸 + `pt` | 段后间距 |
| `alignment` | 字符串 | `left` | `left`, `center`, `right` | 对齐方式 |
| `first_line_indent` | 数字 | `0` | `0`, `2`, `4` | 首行缩进字符数 |

**各级标题推荐配置**：

| 标题级别 | 推荐字体 | 推荐字号 | 推荐样式 |
|:-----:|:--------|:--------|:--------|
| heading1 | 方正小标宋/黑体 | 22pt (二号) | 加粗、居中 |
| heading2 | 黑体 | 16pt (三号) | 加粗、左对齐 |
| heading3 | 楷体 | 16pt (三号) | 加粗、左对齐 |
| heading4 | 仿宋 | 12pt (小四) | 普通、左对齐 |

---

### 3️⃣ paragraph - 段落样式

定义普通段落的样式。

```yaml
paragraph:
  font_name: "仿宋"           # 字体
  font_size: 12pt             # 字号
  line_spacing: 1.5           # 行距倍数
  first_line_indent: 2        # 首行缩进（字符数）
  alignment: justify          # 对齐方式
  space_before: 0pt           # 段前间距
  space_after: 0pt            # 段后间距
```

**参数说明**：

| 参数 | 类型 | 默认值 | 可选值 | 说明 |
|:-----|:----:|:-------|:-------|:-----|
| `font_name` | 字符串 | `"仿宋"` | 任意已安装字体 | 字体名称 |
| `font_size` | 字符串 | `12pt` | `10pt`-`14pt` | 字号 |
| `line_spacing` | 数字 | `1.5` | `1.0`-`2.0` | 行距倍数 |
| `first_line_indent` | 数字 | `2` | `0`, `2`, `4` | 首行缩进字符数 |
| `alignment` | 字符串 | `justify` | `left`, `right`, `center`, `justify` | 对齐方式 |
| `space_before` | 字符串 | `0pt` | 任意尺寸 + `pt` | 段前间距 |
| `space_after` | 字符串 | `0pt` | 任意尺寸 + `pt` | 段后间距 |

**对齐方式说明**：
- `left` - 左对齐
- `right` - 右对齐
- `center` - 居中
- `justify` - 两端对齐（推荐用于正文）

**首行缩进说明**：
- `0` = 无缩进
- `2` = 缩进2个字符（中文规范）
- 实际缩进宽度 = 字符数 × 字体大小

---

### 4️⃣ inline - 行内文本样式

定义 Markdown 行内强调文本的样式。

```yaml
inline:
  # 粗体 (**text**)
  bold:
    font_color: null  # null=继承父级，或指定颜色
  
  # 斜体 (*text*)
  italic:
    font_color: null
  
  # 行内代码 (`code`)
  code:
    font_name: "Consolas"
    font_size: 11pt
    font_color: "#D14"
    background: "#F5F5F5"
```

**参数说明**：

| 子节.参数 | 类型 | 默认值 | 说明 |
|:---------|:----:|:-------|:-----|
| `bold.font_color` | 字符串/null | `null` | 粗体文本颜色（null=继承） |
| `italic.font_color` | 字符串/null | `null` | 斜体文本颜色（null=继承） |
| `code.font_name` | 字符串 | `"Consolas"` | 代码字体（等宽字体） |
| `code.font_size` | 字符串 | `11pt` | 代码字号 |
| `code.font_color` | 字符串 | `"#D14"` | 代码文字颜色 |
| `code.background` | 字符串 | `"#F5F5F5"` | 代码背景颜色 |

**Markdown 语法对应**：
- `**粗体**` 或 `__粗体__` → `inline.bold`
- `*斜体*` 或 `_斜体_` → `inline.italic`
- `` `代码` `` → `inline.code`

---

### 5️⃣ code_block - 代码块样式

定义 Markdown 代码块（使用三个反引号 ``` 包围）的样式。

```yaml
code_block:
  font_name: "Consolas"
  font_size: 10pt
  font_color: "#24292E"  # GitHub 深灰色
  background: "#F6F8FA"  # GitHub 浅灰背景
  border_color: "#D0D7DE"  # 边框颜色
  bold: false  # 是否加粗
  italic: false  # 是否斜体
  line_spacing: 1.2
  space_before: 6pt
  space_after: 6pt
  padding: 6pt  # 内边距
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|:-----|:----:|:-------|:-----|
| `font_name` | 字符串 | `"Consolas"` | 代码字体（建议等宽字体） |
| `font_size` | 字符串 | `10pt` | 代码字号 |
| `font_color` | 字符串 | `"#24292E"` | 代码文字颜色 |
| `background` | 字符串 | `"#F6F8FA"` | 代码块背景颜色 |
| `border_color` | 字符串 | `"#D0D7DE"` | 边框颜色（预留） |
| `bold` | 布尔值 | `false` | 是否加粗 |
| `italic` | 布尔值 | `false` | 是否斜体 |
| `line_spacing` | 数字 | `1.2` | 行距倍数 |
| `space_before` | 字符串 | `6pt` | 段前间距 |
| `space_after` | 字符串 | `6pt` | 段后间距 |
| `padding` | 字符串 | `6pt` | 内边距 |

**Markdown 语法对应**：

````markdown
```python
def hello():
    print("Hello")
```
````

**推荐字体**：
- **Consolas** - Windows 系统等宽字体（推荐）
- **Courier New** - 跨平台等宽字体
- **Monaco** - macOS 等宽字体
- **Source Code Pro** - 开源等宽字体

**颜色方案**：

| 方案 | 背景色 | 文字色 | 说明 |
|:-----|:-------|:-------|:-----|
| GitHub 风格 | `#F6F8FA` | `#24292E` | 默认推荐 |
| VS Code 亮色 | `#F5F5F5` | `#333333` | 浅灰背景 |
| 极简风格 | `#FAFAFA` | `#000000` | 接近白色 |
| 深色风格 | `#2D2D2D` | `#F8F8F2` | 深色背景 |

---

### 6️⃣ table - 表格样式

定义表格的样式。

```yaml
table:
  style: "Light Grid Accent 1"  # Word 内置表格样式
  font_name: "仿宋"              # 字体
  font_size: 12pt                # 字号
  line_spacing: 1.5              # 行距
  header_bold: true              # 表头加粗
  header_background: "#F2F2F2"   # 表头背景色
  header_alignment: center       # 表头水平对齐
  header_vertical_alignment: center  # 表头垂直对齐
  border_color: "#CCCCCC"        # 边框颜色
  alignment: left                # 默认对齐（可被Markdown对齐语法覆盖）
  
  # 斑马纹（可选）
  alternating_rows: false        # 是否启用交替行颜色
  row_background_odd: "#FFFFFF"  # 奇数行背景
  row_background_even: "#F9F9F9" # 偶数行背景
```

**参数说明**：

| 参数 | 类型 | 默认值 | 可选值 | 说明 |
|:-----|:----:|:-------|:-------|:-----|
| `style` | 字符串 | `"Light Grid Accent 1"` | Word 内置样式名 | 表格样式 |
| `font_name` | 字符串 | `"仿宋"` | 任意已安装字体 | 表格字体 |
| `font_size` | 字符串 | `12pt` | `9pt`-`14pt` | 字号 |
| `line_spacing` | 数字 | `1.5` | `1.0`-`2.0` | 行距 |
| `header_bold` | 布尔值 | `true` | `true`/`false` | 表头是否加粗 |
| `header_background` | 字符串 | `"#F2F2F2"` | 十六进制颜色 | 表头背景色 |
| `header_alignment` | 字符串 | `center` | `left`, `center`, `right`, `inherit` | 表头水平对齐 |
| `header_vertical_alignment` | 字符串 | `center` | `top`, `center`, `bottom` | 表头垂直对齐 |
| `border_color` | 字符串 | `"#CCCCCC"` | 十六进制颜色 | 边框颜色 |
| `alignment` | 字符串 | `left` | `left`, `center`, `right` | 默认对齐 |
| `alternating_rows` | 布尔值 | `false` | `true`/`false` | 启用斑马纹 |
| `row_background_odd` | 字符串 | `"#FFFFFF"` | 十六进制颜色 | 奇数行背景 |
| `row_background_even` | 字符串 | `"#F9F9F9"` | 十六进制颜色 | 偶数行背景 |

**表格对齐说明**：

md2docx 完全支持 Markdown 表格对齐语法：

| Markdown 语法 | 效果 |
|:-------------|:-----|
| `\| :--- \|` | 左对齐 |
| `\| :--: \|` | 居中 |
| `\| ---: \|` | 右对齐 |
| `\| --- \|` | 默认对齐 |

**Word 内置表格样式**：
- `"Light Grid Accent 1"` - 浅色网格（推荐）
- `"Table Grid"` - 简单网格
- `"Medium Shading 1 Accent 1"` - 中等阴影
- `None` - 无样式

---

### 6️⃣ list - 列表样式

定义有序和无序列表的样式。

```yaml
list:
  font_name: "仿宋"    # 字体
  font_size: 12pt      # 字号
  bullet_char: "•"     # 无序列表符号
  number_format: "1."  # 有序列表格式
  ordered_list_as_text: false  # true=输出“1. 文本”，不用 Word 自动编号
  indent_size: 0.5in   # 每级缩进
  space_after: 3pt     # 列表项后间距
```

**参数说明**：

| 参数 | 类型 | 默认值 | 可选值 | 说明 |
|:-----|:----:|:-------|:-------|:-----|
| `font_name` | 字符串 | `"仿宋"` | 任意已安装字体 | 列表字体 |
| `font_size` | 字符串 | `12pt` | `10pt`-`14pt` | 字号 |
| `bullet_char` | 字符串 | `"•"` | `"•"`, `"-"`, `"■"`, `"○"` | 无序列表符号 |
| `number_format` | 字符串 | `"1."` | `"1."`, `"1)"`, `"(1)"` | 有序列表格式 |
| `ordered_list_as_text` | 布尔值 | `false` | `true`/`false` | 是否把有序列表写成普通文本序号 |
| `indent_size` | 字符串 | `0.5in` | 任意尺寸 + 单位 | 每级缩进大小 |
| `space_after` | 字符串 | `3pt` | 任意尺寸 + `pt` | 列表项后间距 |

---

### 7️⃣ mermaid - Mermaid 图样式

定义 Mermaid 代码块渲染为图片后的尺寸、对齐和紧凑排版策略。

```yaml
mermaid:
  command: mmdc
  format: png
  theme: default
  width: 5.5in
  alignment: center
  space_before: 6pt
  space_after: 6pt
  background_color: white
  # Mermaid recommends pairing themeVariables with theme: base
  # theme_variables:
  #   primaryColor: "#E8F1FF"
  #   primaryTextColor: "#163A70"
  #   primaryBorderColor: "#2F6BFF"
  #   lineColor: "#2F6BFF"
  soft_max_height_ratio: 0.68
  hard_max_height_ratio: 0.82
  page_max_height_ratio: 0.92
  page_break_threshold_ratio: 0.90
  min_readable_width: 3.2in
  oversized_strategy: page
  force_page_break_before_oversized: false
  keep_with_previous: true
  follow_previous_trigger_height_ratio: 0.24
  follow_previous_width_ratio: 0.55
  follow_previous_space_before: 0pt
  keep_together: true
  keep_with_next: false
  widow_control: false
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|:-----|:----:|:-------|:-----|
| `command` | 字符串 | `mmdc` | Mermaid CLI 命令名或路径 |
| `format` | 字符串 | `png` | 输出图片格式 |
| `theme` | 字符串 | `default` | Mermaid 内置主题，如 `default`、`dark`、`forest`、`neutral`、`base` |
| `width` | 字符串 | `5.5in` | Mermaid 图片的首选宽度 |
| `alignment` | 字符串 | `center` | 图片段落对齐方式，建议保持居中 |
| `space_before` | 字符串 | `6pt` | 常规 Mermaid 图片的段前距 |
| `space_after` | 字符串 | `6pt` | Mermaid 图片的段后距 |
| `background_color` | 字符串 | `white` | Mermaid 导出背景色 |
| `theme_variables` | 对象 | 空 | 传给 Mermaid CLI 的 `themeVariables`，用于覆写节点、边线、文字等颜色；一旦设置，md2docx 会自动改用 `base` 主题以确保颜色生效 |
| `soft_max_height_ratio` | 数字 | `0.68` | 软高度上限，占可用页高的比例 |
| `hard_max_height_ratio` | 数字 | `0.82` | 硬高度上限，超过后会缩放 |
| `page_max_height_ratio` | 数字 | `0.92` | 需要另起页时允许的最大高度比例 |
| `page_break_threshold_ratio` | 数字 | `0.90` | 超过该比例时优先考虑分页 |
| `min_readable_width` | 字符串 | `3.2in` | 如果缩放后宽度低于该值，可触发分页策略 |
| `oversized_strategy` | 字符串 | `page` | 超大图处理策略，`page` 表示按整页优先的尺寸上限处理 |
| `force_page_break_before_oversized` | 布尔值 | `false` | 是否对超大图写入硬性的段前分页 |
| `keep_with_previous` | 布尔值 | `true` | 是否默认把 Mermaid 图片与上一段设置为同页优先 |
| `follow_previous_trigger_height_ratio` | 数字 | `0.24` | “小图”阈值，按图片最终高度占可用页高的比例判断。值越大越宽松 |
| `follow_previous_width_ratio` | 数字 | `0.55` | 命中“小图”规则后，图片最多占可用页宽的比例 |
| `follow_previous_space_before` | 字符串 | `0pt` | 小图贴靠上一段时的段前距 |
| `keep_together` | 布尔值 | `true` | 图片段内部尽量保持在一起 |
| `keep_with_next` | 布尔值 | `false` | 图片段是否与后续段落绑定 |
| `widow_control` | 布尔值 | `false` | 是否启用孤行控制 |

**颜色主题示例**：

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

这类配置会生成 Mermaid CLI 的配置文件并随渲染一起传入。为避免 `themeVariables` 在 `default/dark/forest/neutral` 上失效，md2docx 会自动使用 `base` 主题，然后应用你定义的颜色变量。

**与上一段跟随的行为**：

- 默认情况下，只要 Mermaid 图片前面存在一个正文段落，就会把上一段设置为“与下段同页”优先。
- 这样即使导出后你在 Word 里手工缩小图片，Word 也更容易把“上一段 + 图片”重新排到同一页。
- 只有当你显式设置 `force_page_break_before_oversized: true` 时，超大图才会带上硬性的段前分页。

**小图贴靠上一段的行为**：

- 当 Mermaid 图按常规缩放后高度不超过 `follow_previous_trigger_height_ratio` 时，会被视为“小图”。
- 命中该规则后，图片会进一步按 `follow_previous_width_ratio` 收紧宽度，并保持居中单独成行。
- 如果图片前面紧邻一个正文段落，渲染器会进一步把图片段前距改为 `follow_previous_space_before`，让“上一段 + 图片”尽量留在同一页。

**推荐调参**：

- 想更容易贴近上一段：`follow_previous_trigger_height_ratio: 0.30`，`follow_previous_width_ratio: 0.60`
- 想更谨慎，只让很小的图贴近上一段：`follow_previous_trigger_height_ratio: 0.18`，`follow_previous_width_ratio: 0.45`

**注意**：

- 这些阈值属于排版经验值，不是 Word 的固定标准。
- 默认实现刻意避免给超大 Mermaid 图写死段前分页，目的是保留后续人工缩放后的回流空间。
- Word 最终如何分页仍由其版式引擎决定，因此这里实现的是“强引导”，不是逐页精确计算。

---

## 参数速查表

### 通用参数

| 参数名 | 适用配置节 | 类型 | 说明 |
|:------|:----------|:----:|:-----|
| `font_name` | heading, paragraph, table, list | 字符串 | 字体名称 |
| `font_size` | heading, paragraph, inline.code, table, list | 字符串 | 字号（需带单位） |
| `font_color` | heading, inline.bold/italic/code | 字符串 | 文字颜色 |
| `bold` | heading | 布尔值 | 是否加粗 |
| `italic` | heading | 布尔值 | 是否斜体 |
| `alignment` | heading, paragraph, table | 字符串 | 对齐方式 |
| `line_spacing` | document, paragraph, table | 数字 | 行距倍数 |
| `space_before` | heading, paragraph | 字符串 | 段前间距 |
| `space_after` | heading, paragraph, list | 字符串 | 段后间距 |
| `first_line_indent` | heading, paragraph | 数字 | 首行缩进字符数 |

---

## 单位与字号对照

### 支持的单位

| 单位 | 说明 | 示例 | 转换 |
|:----:|:-----|:-----|:-----|
| `pt` | 磅（Points） | `12pt` | 1pt = 1/72英寸 |
| `cm` | 厘米 | `2.54cm` | 1cm ≈ 28.35pt |
| `in` | 英寸 | `1in` | 1in = 72pt = 2.54cm |
| `mm` | 毫米 | `25.4mm` | 10mm = 1cm |

### 中文字号对照表

| 中文字号 | 磅值（pt） | 使用场景 | 推荐用途 |
|:--------:|:---------:|:---------|:---------|
| **初号** | 42pt | 封面大标题 | - |
| **小初号** | 36pt | 重要标题 | heading1（特大） |
| **一号** | 26pt | 章节大标题 | heading1 |
| **小一号** | 24pt | 章节标题 | heading1 |
| **二号** | 22pt | 副标题 | **heading1（推荐）** ⭐ |
| **小二号** | 18pt | 一级标题 | **heading2** ⭐ |
| **三号** | 16pt | 二级标题 | **heading2/3（推荐）** ⭐ |
| **小三号** | 15pt | 强调标题 | heading3 |
| **四号** | 14pt | 三级标题 | **heading3/4** ⭐ |
| **小四号** | 12pt | 正文 | **paragraph（最常用）** ⭐ |
| **五号** | 10.5pt | 小字正文 | 注释 |
| **小五号** | 9pt | 脚注 | table, 图表说明 |
| **六号** | 7.5pt | 页眉页脚 | - |
| **小六号** | 6.5pt | 小字备注 | - |
| **七号** | 5.5pt | 极小字 | - |
| **八号** | 5pt | 最小字号 | - |

### 推荐字号配置

```yaml
# 学术文档推荐
heading1: 22pt  # 二号
heading2: 18pt  # 小二号
heading3: 16pt  # 三号
heading4: 14pt  # 四号
paragraph: 12pt # 小四号

# 商务报告推荐
heading1: 18pt  # 小二号
heading2: 16pt  # 三号
heading3: 14pt  # 四号
heading4: 12pt  # 小四号（加粗）
paragraph: 12pt # 小四号
```

---

## 颜色代码

颜色使用十六进制代码，格式为 `"#RRGGBB"`。

### 常用颜色

| 颜色 | 代码 | 适用场景 |
|:-----|:-----|:---------|
| 黑色 | `"#000000"` | 正文、标题 |
| 白色 | `"#FFFFFF"` | 背景 |
| 深蓝色 | `"#000080"` | 重要标题 |
| 红色 | `"#FF0000"` | 强调、警告 |
| 深红色 | `"#D14"` | 行内代码 |
| 深灰色 | `"#333333"` | 次要文字 |
| 灰色 | `"#808080"` | 辅助文字 |
| 浅灰色 | `"#F2F2F2"` | 表头背景 |
| 极浅灰 | `"#F5F5F5"` | 代码背景 |
| 浅灰边框 | `"#CCCCCC"` | 表格边框 |
| 米色 | `"#F9F9F9"` | 斑马纹 |

### 中文推荐字体

| 字体名称 | 适用场景 | 特点 |
|:--------|:---------|:-----|
| **仿宋** | 正文、段落 | 中文正式文档标准字体 ✅ |
| **宋体** | 正文、表格 | 传统正文字体 |
| **黑体** | 标题 | 醒目、现代 |
| **楷体** | 标题、强调 | 传统、优雅 |
| **微软雅黑** | 标题 | 现代、清晰 |
| **方正小标宋** | 一级标题 | 正式文档标题专用字体 ⭐ |
| **Consolas** | 代码 | 等宽字体（英文） |
| **Courier New** | 代码 | 等宽字体（备选） |

---

## 完整配置示例

### 示例1：学术论文样式

```yaml
document:
  page_size: A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.17cm
  margin_right: 3.17cm
  line_spacing: 1.5

heading1:
  font_name: "方正小标宋简体"
  font_size: 22pt  # 二号
  font_color: "#000080"
  bold: true
  space_before: 6pt
  space_after: 6pt
  alignment: center

heading2:
  font_name: "黑体"
  font_size: 16pt  # 三号
  bold: true
  space_before: 10pt
  space_after: 10pt
  alignment: left
  first_line_indent: 2

heading3:
  font_name: "楷体"
  font_size: 16pt  # 三号
  bold: true
  space_before: 8pt
  space_after: 8pt
  alignment: left
  first_line_indent: 2

heading4:
  font_name: "仿宋"
  font_size: 12pt  # 小四
  space_before: 3pt
  space_after: 3pt
  alignment: left
  first_line_indent: 2

paragraph:
  font_name: "仿宋"
  font_size: 12pt  # 小四
  line_spacing: 1.5
  first_line_indent: 2
  alignment: justify
  space_before: 0pt
  space_after: 0pt

inline:
  bold:
    font_color: null
  italic:
    font_color: null
  code:
    font_name: "Consolas"
    font_size: 11pt
    font_color: "#D14"
    background: "#F5F5F5"

table:
  style: "Light Grid Accent 1"
  font_name: "仿宋"
  font_size: 12pt
  header_bold: true
  header_background: "#F2F2F2"
  header_alignment: center
  header_vertical_alignment: center
  alignment: left
  alternating_rows: false

list:
  font_name: "仿宋"
  font_size: 12pt
  bullet_char: "•"
  number_format: "1."
  indent_size: 0.5in
  space_after: 3pt
```

---

## 使用方法

### 方法1：CLI 命令行

```bash
# 使用默认配置
uv run md2docx input.md

# 指定自定义配置文件
uv run md2docx input.md -s custom_styles.yaml

# 指定输出文件
uv run md2docx input.md -o output.docx -s my_styles.yaml
```

### 方法2：Python API

```python
from md2docx import Converter

# 使用默认配置
converter = Converter()
converter.convert('input.md', 'output.docx')

# 使用自定义配置
converter = Converter(style_config='custom_styles.yaml')
converter.convert('input.md', 'output.docx')

# 转换字符串
md_content = "# 标题\n\n这是一段文字"
converter.convert_string(md_content, 'output.docx')
```

---

## 注意事项

### ⚠️ 重要提示

1. **字体可用性**
   - 确保配置中使用的字体在系统中已安装
   - Windows/Mac 字体名称可能不同
   - 推荐使用系统通用字体

2. **YAML 语法**
   - 使用 2 个空格缩进（不要用 Tab）
   - 冒号后必须有空格：`key: value`
   - 字符串建议加引号：`"仿宋"`

3. **单位必须带上**
   - 字号：`12pt`（不能只写 `12`）
   - 边距：`2.54cm`（不能只写 `2.54`）

4. **颜色格式**
   - 必须用引号：`"#000000"`（不能写成 `#000000`）
   - 使用 6 位十六进制：`#RRGGBB`

5. **布尔值**
   - 直接写：`true` 或 `false`
   - 不要加引号

6. **null 值**
   - 表示继承或不设置
   - 直接写：`null`（不加引号）

---

## 常见问题

**Q: 如何让段落不首行缩进？**  
A: 设置 `paragraph.first_line_indent: 0`

**Q: 如何启用表格斑马纹？**  
A: 设置 `table.alternating_rows: true`

**Q: 如何自定义粗体和斜体的颜色？**  
A: 设置 `inline.bold.font_color` 和 `inline.italic.font_color`

**Q: 支持哪些对齐方式？**  
A: `left`（左对齐）、`center`（居中）、`right`（右对齐）、`justify`（两端对齐）

**Q: Markdown 表格对齐语法会覆盖配置吗？**  
A: 是的，Markdown 中的 `:---`、`:--:`、`---:` 会覆盖 `table.alignment` 设置

---

## 参考资源

- [python-docx 官方文档](https://python-docx.readthedocs.io/)
- [Markdown 语法指南](https://www.markdownguide.org/)
- [YAML 语法参考](https://yaml.org/)

---

**文档版本**: v1.0  
**适用版本**: md2docx >= 1.0  
**最后更新**: 2025-11-20
