# md2docx 样式配置参数完整说明

## 📋 配置文件概述

`md2docx` 使用 YAML 格式的配置文件来定义 Word 文档的所有样式。配置文件包含以下几个主要部分：

1. **document** - 文档级别设置
2. **heading1-4** - 标题样式（1-4级）
3. **paragraph** - 段落样式
4. **table** - 表格样式
5. **list** - 列表样式

---

## 🔧 详细参数说明

### 1. document（文档级别设置）

控制整个 Word 文档的页面设置。

| 参数 | 类型 | 说明 | 默认值 | 示例 |
|------|------|------|--------|------|
| `page_size` | 字符串 | 页面大小 | `A4` | `A4`, `Letter`, `A3` |
| `margin_top` | 字符串 | 上边距 | `2.54cm` | `2.54cm`, `1in` |
| `margin_bottom` | 字符串 | 下边距 | `2.54cm` | `2.54cm`, `1in` |
| `margin_left` | 字符串 | 左边距 | `3.17cm` | `3.17cm`, `1.25in` |
| `margin_right` | 字符串 | 右边距 | `3.17cm` | `3.17cm`, `1.25in` |
| `line_spacing` | 数字 | 行距倍数 | `1.5` | `1.0`, `1.5`, `2.0` |

**示例：**
```yaml
document:
  page_size: A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.17cm
  margin_right: 3.17cm
  line_spacing: 1.5
```

---

### 2. heading1-4（标题样式）

定义 1-4 级标题的样式。每个级别支持相同的参数。

| 参数 | 类型 | 说明 | 示例 | 备注 |
|------|------|------|------|------|
| `font_name` | 字符串 | 字体名称 | `"微软雅黑"`, `"仿宋"` | 使用系统已安装的字体 |
| `font_size` | 字符串 | 字体大小 | `18pt`, `16pt`, `14pt` | 使用 `pt`（磅）单位 |
| `font_color` | 字符串 | 字体颜色 | `"#000080"`, `"#000000"` | 十六进制颜色代码 |
| `bold` | 布尔值 | 是否加粗 | `true`, `false` | 标题通常设为 `true` |
| `space_before` | 字符串 | 段前间距 | `12pt`, `10pt` | 使用 `pt` 单位 |
| `space_after` | 字符串 | 段后间距 | `6pt`, `5pt` | 使用 `pt` 单位 |
| `alignment` | 字符串 | 对齐方式 | `left`, `center`, `right` | 标题通常为 `left` |

**示例：**
```yaml
heading1:
  font_name: "微软雅黑"
  font_size: 18pt
  font_color: "#000080"  # 深蓝色
  bold: true
  space_before: 12pt
  space_after: 6pt
  alignment: left

heading2:
  font_name: "微软雅黑"
  font_size: 16pt
  font_color: "#000000"  # 黑色
  bold: true
  space_before: 10pt
  space_after: 5pt
  alignment: left
```

---

### 3. paragraph（段落样式）

定义普通段落的样式。

| 参数 | 类型 | 说明 | 默认值 | 可选值/示例 |
|------|------|------|--------|------------|
| `font_name` | 字符串 | 字体名称 | `"仿宋"` | `"宋体"`, `"仿宋"`, `"楷体"` |
| `font_size` | 字符串 | 字体大小 | `12pt` | `10pt`, `11pt`, `12pt`, `14pt` |
| `line_spacing` | 数字 | 行距倍数 | `1.5` | `1.0`, `1.15`, `1.5`, `2.0` |
| `first_line_indent` | 数字 | 首行缩进字符数 | `2` | `0`, `2`, `4` |
| `alignment` | 字符串 | 对齐方式 | `justify` | `left`, `right`, `center`, `justify` |

**首行缩进说明：**
- `0` = 无缩进
- `2` = 缩进2个字符（中文规范）
- 实际缩进 = 字符数 × 字体大小

**对齐方式说明：**
- `left` - 左对齐
- `right` - 右对齐
- `center` - 居中
- `justify` - 两端对齐（推荐用于段落）

**示例：**
```yaml
paragraph:
  font_name: "仿宋"
  font_size: 12pt
  line_spacing: 1.5
  first_line_indent: 2  # 首行缩进2个字符
  alignment: justify
```

---

### 4. table（表格样式）

定义表格的样式。

| 参数 | 类型 | 说明 | 默认值 | 可选值/示例 |
|------|------|------|--------|------------|
| `style` | 字符串 | Word 内置表格样式 | `"Light Grid Accent 1"` | 见下方样式列表 |
| `font_name` | 字符串 | 表格字体 | `"宋体"` | 任意已安装字体 |
| `font_size` | 字符串 | 字体大小 | `11pt` | `9pt`, `10pt`, `11pt`, `12pt` |
| `header_bold` | 布尔值 | 表头是否加粗 | `true` | `true`, `false` |
| `header_background` | 字符串 | 表头背景色 | `"#F2F2F2"` | 十六进制颜色代码 |
| `border_color` | 字符串 | 边框颜色 | `"#CCCCCC"` | 十六进制颜色代码 |
| `alignment` | 字符串 | 单元格对齐 | `left` | `left`, `center`, `right` |

**Word 内置表格样式列表：**
- `"Light Grid Accent 1"` - 浅色网格（推荐）
- `"Medium Shading 1 Accent 1"` - 中等阴影
- `"Light List Accent 1"` - 浅色列表
- `"Table Grid"` - 简单网格
- `None` - 无样式

**示例：**
```yaml
table:
  style: "Light Grid Accent 1"
  font_name: "宋体"
  font_size: 11pt
  header_bold: true
  header_background: "#F2F2F2"  # 浅灰色
  border_color: "#CCCCCC"
  alignment: left
```

---

### 5. list（列表样式）

定义有序和无序列表的样式。

| 参数 | 类型 | 说明 | 默认值 | 可选值/示例 |
|------|------|------|--------|------------|
| `font_name` | 字符串 | 列表字体 | `"仿宋"` | 任意已安装字体 |
| `font_size` | 字符串 | 字体大小 | `12pt` | `10pt`, `11pt`, `12pt` |
| `bullet_char` | 字符串 | 无序列表符号 | `"•"` | `"•"`, `"-"`, `"■"`, `"○"` |
| `number_format` | 字符串 | 有序列表格式 | `"1."` | `"1."`, `"1)"`, `"(1)"` |
| `indent_size` | 字符串 | 每级缩进 | `0.5in` | `0.5in`, `1cm`, `0.75in` |
| `space_after` | 字符串 | 列表项后间距 | `3pt` | `2pt`, `3pt`, `6pt` |

**示例：**
```yaml
list:
  font_name: "仿宋"
  font_size: 12pt
  bullet_char: "•"
  number_format: "1."
  indent_size: 0.5in
  space_after: 3pt
```

---

## 📐 单位说明

配置文件支持以下计量单位：

| 单位 | 说明 | 示例 | 转换 |
|------|------|------|------|
| `pt` | 磅（Points） | `12pt` | 1pt = 1/72英寸 |
| `cm` | 厘米 | `2.54cm` | 1cm = 0.394英寸 |
| `in` | 英寸 | `1in` | 1in = 2.54cm |
| `mm` | 毫米 | `25.4mm` | 10mm = 1cm |

**常用字号对照：**
- 10pt = 五号
- 12pt = 小四
- 14pt = 四号
- 16pt = 三号
- 18pt = 二号

---

## 🎨 颜色代码

颜色使用十六进制代码表示，格式为 `"#RRGGBB"`。

**常用颜色：**
```yaml
"#000000"  # 黑色
"#FFFFFF"  # 白色
"#FF0000"  # 红色
"#00FF00"  # 绿色
"#0000FF"  # 蓝色
"#000080"  # 深蓝色
"#808080"  # 灰色
"#F2F2F2"  # 浅灰色
"#CCCCCC"  # 中灰色
```

---

## 📝 完整配置示例

```yaml
# 文档设置
document:
  page_size: A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.17cm
  margin_right: 3.17cm
  line_spacing: 1.5

# 一级标题
heading1:
  font_name: "微软雅黑"
  font_size: 18pt
  font_color: "#000080"
  bold: true
  space_before: 12pt
  space_after: 6pt
  alignment: left

# 段落
paragraph:
  font_name: "仿宋"
  font_size: 12pt
  line_spacing: 1.5
  first_line_indent: 2
  alignment: justify

# 表格
table:
  style: "Light Grid Accent 1"
  font_name: "宋体"
  font_size: 11pt
  header_bold: true
  header_background: "#F2F2F2"
  border_color: "#CCCCCC"
  alignment: left

# 列表
list:
  font_name: "仿宋"
  font_size: 12pt
  bullet_char: "•"
  number_format: "1."
  indent_size: 0.5in
  space_after: 3pt
```

---

## 🔍 使用自定义配置

### 方法1：通过 CLI
```bash
# 使用自定义配置文件
uv run md2docx input.md -s my_styles.yaml
```

### 方法2：通过 Python API
```python
from md2docx import Converter

converter = Converter(style_config='my_styles.yaml')
converter.convert('input.md', 'output.docx')
```

---

## ⚠️ 注意事项

1. **字体可用性**：确保配置中使用的字体在系统中已安装
2. **中文字体**：推荐使用"宋体"、"仿宋"、"黑体"、"楷体"、"微软雅黑"
3. **颜色格式**：必须使用引号，如 `"#000000"`
4. **单位必须带**：如 `12pt`、`2.54cm`，不能只写数字
5. **布尔值**：`true`/`false` 不需要引号
6. **YAML 语法**：注意缩进（2个空格），冒号后要有空格

---

## 📚 参考资源

- [python-docx 文档](https://python-docx.readthedocs.io/)
- [Word 内置样式参考](https://python-docx.readthedocs.io/en/latest/user/styles.html)
- [YAML 语法指南](https://yaml.org/)
