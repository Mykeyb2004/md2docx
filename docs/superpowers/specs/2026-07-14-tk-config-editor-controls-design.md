# Tk 默认配置编辑器高频控件优化设计

日期：2026-07-14
状态：设计已确认，等待书面规格复核

## 1. 背景

md2docx 当前已有 Tk 默认配置编辑器，用于编辑默认 YAML 配置。编辑器通过递归表单渲染配置节，布尔字段已经使用 `Checkbutton`，少量字段通过 `FIELD_OPTIONS` 使用 `Combobox`，其余字段主要使用普通文本输入框。

默认配置中有不少字段具备明确语义：颜色、字体、字号、对齐、行距、段前段后、页边距、表格布局、列表编号等。继续让用户手输这些值容易产生拼写、单位和格式错误，也不利于发现常用可选值。

本设计先优化 Tk 编辑器中的高频字段控件体验，不改变 YAML 格式，不改转换核心，不提前实现完整 Web 样式编辑器。

## 2. 目标

首版目标：

1. 为高频配置字段提供更合适的 Tk 控件。
2. 保持辅助输入而非强限制：常用值易选，特殊值仍可手输。
3. 颜色字段支持色块预览、系统颜色选择器和文本输入。
4. 常见枚举字段使用只读下拉，避免转换代码无法识别的值。
5. 常见尺寸、字号、行距、缩进等字段使用可编辑下拉，降低手输成本。
6. 未知字段和暂未覆盖字段继续使用当前普通输入框。
7. 保存后的 YAML 数据类型和文本格式保持兼容。

## 3. 非目标

首版不包含：

- 搜索字段、中文标签、帮助说明、基础/高级分组、恢复默认等表单组织能力。
- Mermaid 高级比例字段的专用滑块或范围控件，例如 `soft_max_height_ratio`、`hard_max_height_ratio`、`follow_previous_width_ratio`。
- 完整配置 schema、Pydantic 校验层或 Web 样式编辑器。
- YAML 保存结构迁移。
- 转换渲染行为调整。
- 新增第三方依赖。

## 4. 已选方案

采用轻量字段控件规则表。

在现有 `ConfigEditorWindow` 的递归表单框架上新增字段规则数据结构，用字段路径匹配控件类型、常用选项和只读策略。`create_field_widget()` 根据字段规则派发控件：布尔值、颜色组合控件、下拉控件或普通输入框。

未选择只扩展 `FIELD_OPTIONS`，因为它无法表达颜色组合控件，也难以区分只读枚举与可编辑建议值。未选择完整 schema 层，因为它与后续 Web 样式编辑器方向重叠，且对本次高频控件优化来说范围偏大。

## 5. 控件规则范围

首版只覆盖默认模板里的高频字段。导入 YAML 中的未知字段继续走普通输入框。

### 5.1 字体字段

适用字段：

- `heading1-4.font_name`
- `paragraph.font_name`
- `inline.code.font_name`
- `code_block.font_name`
- `table.font_name`
- `list.font_name`

控件：可编辑 `Combobox`。

常用值建议包含：

- 中文排版字体：`仿宋`、`宋体`、`黑体`、`楷体`、`微软雅黑`、`方正小标宋简体`
- 代码字体：`Consolas`、`Courier New`、`Menlo`、`Monaco`

### 5.2 字号字段

适用字段：

- 各样式节的 `font_size`

控件：可编辑 `Combobox`。

常用值建议包含：`10.5pt`、`11pt`、`12pt`、`14pt`、`16pt`、`18pt`、`22pt`。

### 5.3 颜色字段

适用字段：

- `font_color`
- `background`
- `border_color`
- `header_background`
- `row_background_odd`
- `row_background_even`
- Mermaid 高频颜色字段：`background_color` 和 `theme_variables` 下的常见颜色值

控件：颜色组合控件。

组合控件包括：

- 左侧色块预览当前值。
- 中间文本输入，保留 hex 或命名颜色输入能力。
- 右侧“选择”按钮，打开系统颜色选择器。

颜色选择器返回值写回为 `#RRGGBB`。如果文本为空且字段 schema 允许 `null`，保存时继续保存为 `null`。如果输入为 `white` 等命名颜色，文本照常保存，色块显示为空态或默认边框，不强制报错。

### 5.4 对齐字段

适用字段：

- `alignment`
- `header_alignment`
- `vertical_alignment`
- `header_vertical_alignment`
- `math_block.alignment`
- `mermaid.alignment`

控件：只读 `Combobox`。

常用值：

- 水平对齐：`left`、`center`、`right`、`justify`
- 表头对齐额外支持：`inherit`
- 垂直对齐：`top`、`center`、`bottom`
- Mermaid 和公式图片对齐：`left`、`center`、`right`

### 5.5 尺寸和间距字段

适用字段：

- `document.margin_top`
- `document.margin_bottom`
- `document.margin_left`
- `document.margin_right`
- `space_before`
- `space_after`
- `padding`
- `width`
- `height`
- `indent_size`
- `cell_margin_vertical`
- `cell_margin_horizontal`
- `min_readable_width`

控件：可编辑 `Combobox`。

第一版不拆成数值输入和单位下拉，避免重写取值和校验逻辑。常用值按字段语义提供，例如页边距使用 `2.54cm`、`3.17cm`，段落间距使用 `0pt`、`3pt`、`6pt`、`12pt`，图片宽高使用 `0.15in`、`3.2in`、`4in`、`5.5in`。

### 5.6 数字字段

适用字段：

- `line_spacing`
- `first_line_indent`
- `dpi`

控件：可编辑 `Combobox`。

常用值：

- 行距：`1.0`、`1.15`、`1.2`、`1.5`、`2.0`
- 首行缩进：`0`、`2`、`4`
- DPI：`150`、`200`、`300`、`600`

保存时继续由现有类型转换逻辑根据 schema 转为 `float` 或 `int`。

### 5.7 列表和表格字段

适用字段：

- `list.bullet_char`
- `list.number_format`
- `table.column_width_strategy`
- `document.page_size`
- `mermaid.format`
- `mermaid.theme`
- `mermaid.oversized_strategy`

控件：

- `bullet_char`、`number_format` 使用可编辑 `Combobox`，允许用户输入自定义符号或编号模板。
- `column_width_strategy`、`page_size`、`format`、`theme`、`oversized_strategy` 使用只读 `Combobox`。

建议选项：

- 列表符号：`•`、`-`、`*`、`·`、`○`、`▪`
- 编号格式：`1.`、`1)`、`(1)`
- 表格列宽策略：`content-weighted`、`balanced`
- 页面大小：`A4`、`A3`、`Letter`
- Mermaid 格式：`png`、`svg`、`pdf`
- Mermaid 主题：`default`、`base`、`dark`、`forest`、`neutral`
- Mermaid 超大图策略：`page`、`scale`

## 6. 交互行为

增强控件遵循以下规则：

1. 可编辑下拉既可选择建议值，也可输入自定义值。
2. 只读下拉用于转换逻辑只识别固定值的字段。
3. 颜色字段始终保留文本输入，不以颜色选择器替代文本框。
4. 颜色色块只做预览，不作为保存数据的来源。
5. 字段保存仍依赖现有 `FieldBinding` 和 `collect_config()` 流程。
6. 未命中规则的字段行为保持不变。

## 7. 代码结构

改动集中在 `md2docx/gui.py`：

- 新增轻量规则数据结构，例如 `FieldWidgetRule`。
- 新增规则表，表达控件类型、选项和只读策略。
- 保留或迁移现有 `FIELD_OPTIONS`，避免一次性大重构。
- 抽出字段规则解析函数，便于单元测试。
- 新增颜色组合控件创建函数。
- `create_field_widget()` 负责根据规则选择控件。

颜色组合控件返回一个 `ttk.Frame`，但内部仍绑定同一个 `StringVar`。这样 `field_bindings` 和 `collect_config()` 可以保持基本不变。

## 8. 测试策略

测试使用 `uv run pytest`。

新增测试重点：

1. 字段路径能够解析到预期规则。
2. 可编辑下拉和只读下拉的规则区分正确。
3. 高频颜色字段被识别为颜色控件。
4. 未知字段不会误匹配高频规则。
5. 颜色选择写回变量的纯逻辑可测试。

如果 GUI 环境在无显示测试中不稳定，应将规则选择和颜色格式处理拆成纯函数优先测试。窗口级测试只做最小覆盖。

## 9. 风险与缓解

主要风险是字段路径规则过宽，导致本应普通输入的字段被错误渲染为下拉或颜色控件。缓解方式是优先使用字段名和路径组合匹配，并为未知字段保留普通输入框。

第二个风险是 `ttk.Combobox` 的只读策略过强，阻碍用户输入合法但未列出的值。缓解方式是只对明确枚举字段使用 `readonly`，对字体、字号、尺寸、行距和列表格式使用可编辑模式。

第三个风险是颜色字段存在 `null`、hex、短 hex 和命名颜色等多种形式。缓解方式是文本值始终作为真实数据来源，色块和选择器只辅助输入，不改变现有保存兼容性。

## 10. 验收标准

完成后应满足：

1. 默认配置编辑器可正常打开、导入、导出和保存。
2. 高频字段显示增强控件。
3. 未覆盖字段仍显示普通输入框。
4. 颜色字段能通过颜色选择器写入 `#RRGGBB`。
5. 可编辑下拉允许输入选项外的值。
6. 只读下拉字段只能选择已知枚举值。
7. 保存后的配置可被现有转换流程读取。
8. `uv run pytest` 通过，或清楚说明无法运行的环境原因。
