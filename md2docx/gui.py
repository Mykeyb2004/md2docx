"""
GUI application for md2docx converter.
Provides visual interface for file conversion with history tracking.
"""
import json
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from md2docx import Converter
from md2docx.config_document import (
    ConfigDocument,
    ExternalConfigChangeError,
)
from md2docx.config_utils import (
    build_config_schema,
    clone_config,
    coerce_config_value,
    format_config_value,
    set_value_at_path,
)
from md2docx.styles import StyleManager


ConfigPath = Tuple[str, ...]

FIELD_WIDGET_ENTRY = "entry"
FIELD_WIDGET_COMBOBOX = "combobox"
FIELD_WIDGET_COLOR = "color"


@dataclass(frozen=True)
class FieldWidgetRule:
    """Describe the editor widget to use for one config field."""

    kind: str = FIELD_WIDGET_ENTRY
    options: Tuple[str, ...] = ()
    readonly: bool = False
    value_mapping: Tuple[Tuple[str, str], ...] = ()


DEFAULT_FIELD_WIDGET_RULE = FieldWidgetRule()

HEADING_SECTIONS = ("heading1", "heading2", "heading3", "heading4")
STYLE_SECTIONS = (
    "heading1",
    "heading2",
    "heading3",
    "heading4",
    "paragraph",
    "code_block",
    "table",
    "list",
)

FONT_OPTIONS = (
    "仿宋",
    "宋体",
    "黑体",
    "楷体",
    "微软雅黑",
    "方正小标宋简体",
    "Consolas",
    "Courier New",
    "Menlo",
    "Monaco",
)
FONT_SIZE_OPTIONS = ("10.5pt", "11pt", "12pt", "14pt", "16pt", "18pt", "22pt")
LINE_SPACING_OPTIONS = ("1.0", "1.15", "1.2", "1.5", "2.0")
INDENT_OPTIONS = ("0", "2", "4")
DPI_OPTIONS = ("150", "200", "300", "600")
DIMENSION_OPTIONS = (
    "0pt",
    "3pt",
    "5.4pt",
    "6pt",
    "12pt",
    "0.15in",
    "0.5in",
    "3.2in",
    "4in",
    "5.5in",
    "2.54cm",
    "3.17cm",
)
HORIZONTAL_ALIGNMENT_OPTIONS = ("left", "center", "right", "justify")
IMAGE_ALIGNMENT_OPTIONS = ("left", "center", "right")
VERTICAL_ALIGNMENT_OPTIONS = ("top", "center", "bottom")
HEADER_ALIGNMENT_OPTIONS = ("left", "center", "right", "justify", "inherit")
LIST_BULLET_OPTIONS = ("•", "-", "*", "·", "○", "▪")
NUMBER_FORMAT_OPTIONS = ("1.", "1)", "(1)")
TABLE_LAYOUT_VALUE_MAPPING = (
    ("主题网格表（当前默认）", "accent_grid"),
    ("三线表", "three_line"),
    ("简洁网格表", "plain_grid"),
)
PAGE_SIZE_VALUE_MAPPING = (
    ("A4", "A4"),
    ("A3", "A3"),
    ("Letter（信纸）", "Letter"),
)
HORIZONTAL_ALIGNMENT_VALUE_MAPPING = (
    ("左对齐", "left"),
    ("居中", "center"),
    ("右对齐", "right"),
    ("两端对齐", "justify"),
)
IMAGE_ALIGNMENT_VALUE_MAPPING = (
    ("左对齐", "left"),
    ("居中", "center"),
    ("右对齐", "right"),
)
VERTICAL_ALIGNMENT_VALUE_MAPPING = (
    ("顶端对齐", "top"),
    ("垂直居中", "center"),
    ("底端对齐", "bottom"),
)
HEADER_ALIGNMENT_VALUE_MAPPING = (
    *HORIZONTAL_ALIGNMENT_VALUE_MAPPING,
    ("继承列对齐", "inherit"),
)
COLUMN_WIDTH_STRATEGY_VALUE_MAPPING = (
    ("按内容分配", "content-weighted"),
    ("均衡分配", "balanced"),
)
MERMAID_FORMAT_VALUE_MAPPING = (
    ("PNG 图片", "png"),
    ("SVG 矢量图", "svg"),
    ("PDF 文件", "pdf"),
)
MERMAID_THEME_VALUE_MAPPING = (
    ("默认主题", "default"),
    ("Base 主题（适合自定义变量）", "base"),
    ("深色主题", "dark"),
    ("森林主题", "forest"),
    ("中性主题", "neutral"),
)
MERMAID_OVERSIZED_STRATEGY_VALUE_MAPPING = (
    ("页面布局", "page"),
    ("仅按比例缩放", "scale"),
)

READONLY_FIELD_VALUE_MAPPINGS: Dict[ConfigPath, Tuple[Tuple[str, str], ...]] = {
    ("document", "page_size"): PAGE_SIZE_VALUE_MAPPING,
    ("table", "layout"): TABLE_LAYOUT_VALUE_MAPPING,
    ("heading1", "alignment"): HORIZONTAL_ALIGNMENT_VALUE_MAPPING,
    ("heading2", "alignment"): HORIZONTAL_ALIGNMENT_VALUE_MAPPING,
    ("heading3", "alignment"): HORIZONTAL_ALIGNMENT_VALUE_MAPPING,
    ("heading4", "alignment"): HORIZONTAL_ALIGNMENT_VALUE_MAPPING,
    ("paragraph", "alignment"): HORIZONTAL_ALIGNMENT_VALUE_MAPPING,
    ("table", "alignment"): HORIZONTAL_ALIGNMENT_VALUE_MAPPING,
    ("table", "header_alignment"): HEADER_ALIGNMENT_VALUE_MAPPING,
    ("table", "vertical_alignment"): VERTICAL_ALIGNMENT_VALUE_MAPPING,
    ("table", "header_vertical_alignment"): VERTICAL_ALIGNMENT_VALUE_MAPPING,
    ("table", "column_width_strategy"): COLUMN_WIDTH_STRATEGY_VALUE_MAPPING,
    ("math_block", "alignment"): IMAGE_ALIGNMENT_VALUE_MAPPING,
    ("mermaid", "format"): MERMAID_FORMAT_VALUE_MAPPING,
    ("mermaid", "theme"): MERMAID_THEME_VALUE_MAPPING,
    ("mermaid", "alignment"): IMAGE_ALIGNMENT_VALUE_MAPPING,
    ("mermaid", "oversized_strategy"): MERMAID_OVERSIZED_STRATEGY_VALUE_MAPPING,
}

READONLY_FIELD_OPTIONS: Dict[ConfigPath, Tuple[str, ...]] = {
}

LEGACY_FIELD_OPTIONS: Dict[ConfigPath, Tuple[str, ...]] = {
    ("document", "page_size"): ("A4", "A3", "Letter"),
    ("heading1", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("heading2", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("heading3", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("heading4", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("paragraph", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("table", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("table", "header_alignment"): HEADER_ALIGNMENT_OPTIONS,
    ("table", "header_vertical_alignment"): VERTICAL_ALIGNMENT_OPTIONS,
    ("mermaid", "format"): ("png", "svg", "pdf"),
    ("mermaid", "theme"): ("default", "base", "dark", "forest", "neutral"),
    ("mermaid", "alignment"): IMAGE_ALIGNMENT_OPTIONS,
    ("mermaid", "oversized_strategy"): ("page", "scale"),
}

# Legacy public mapping for callers that inspect the previous fixed enum options.
# The enhanced editor uses resolve_field_widget_rule() for richer widget metadata.
FIELD_OPTIONS = LEGACY_FIELD_OPTIONS

SECTION_LABELS: Dict[ConfigPath, str] = {
    ("document",): "文档设置",
    ("metadata",): "文档属性",
    ("heading1",): "一级标题",
    ("heading2",): "二级标题",
    ("heading3",): "三级标题",
    ("heading4",): "四级标题",
    ("outline",): "中文大纲",
    ("outline", "level1"): "一级大纲覆盖",
    ("outline", "level2"): "二级大纲覆盖",
    ("outline", "level3"): "三级大纲覆盖",
    ("outline", "level4"): "四级大纲覆盖",
    ("paragraph",): "正文段落",
    ("inline",): "行内样式",
    ("inline", "bold"): "加粗文本",
    ("inline", "italic"): "斜体文本",
    ("inline", "code"): "行内代码",
    ("code_block",): "代码块",
    ("table",): "表格样式",
    ("list",): "列表样式",
    ("math_inline",): "行内公式",
    ("math_block",): "块级公式",
    ("mermaid",): "Mermaid 图",
    ("mermaid", "theme_variables"): "Mermaid 主题变量",
    ("chapter_scan",): "章节扫描",
}

COMMON_FIELD_LABELS: Dict[str, str] = {
    "font_name": "字体",
    "font_size": "字号",
    "font_color": "字体颜色",
    "bold": "加粗",
    "italic": "斜体",
    "space_before": "段前间距",
    "space_after": "段后间距",
    "alignment": "水平对齐",
    "first_line_indent": "首行缩进",
    "line_spacing": "行距",
    "background": "背景色",
    "border_color": "边框颜色",
    "width": "宽度",
    "height": "高度",
    "dpi": "渲染分辨率",
}

FIELD_LABELS: Dict[ConfigPath, str] = {
    ("document", "page_size"): "页面大小",
    ("document", "margin_top"): "上页边距",
    ("document", "margin_bottom"): "下页边距",
    ("document", "margin_left"): "左页边距",
    ("document", "margin_right"): "右页边距",
    ("document", "line_spacing"): "文档行距",
    ("document", "ignore_thematic_breaks"): "忽略分割线",
    ("document", "auto_fix_tables"): "自动修复表格",
    ("document", "outline_mode"): "大纲识别模式",
    ("metadata", "author"): "作者",
    ("metadata", "last_modified_by"): "最后修改者",
    ("metadata", "title"): "标题",
    ("metadata", "subject"): "主题",
    ("metadata", "keywords"): "关键词",
    ("metadata", "comments"): "备注",
    ("metadata", "category"): "类别",
    ("outline", "level1_style"): "一级大纲继承样式",
    ("outline", "level2_style"): "二级大纲继承样式",
    ("outline", "level3_style"): "三级大纲继承样式",
    ("outline", "level4_style"): "四级大纲继承样式",
    ("inline", "bold", "font_color"): "加粗文本颜色",
    ("inline", "italic", "font_color"): "斜体文本颜色",
    ("inline", "code", "font_name"): "行内代码字体",
    ("inline", "code", "font_size"): "行内代码字号",
    ("inline", "code", "font_color"): "行内代码文字颜色",
    ("inline", "code", "background"): "行内代码背景色",
    ("code_block", "font_name"): "代码块字体",
    ("code_block", "font_size"): "代码块字号",
    ("code_block", "font_color"): "代码文字颜色",
    ("code_block", "background"): "代码块背景色",
    ("code_block", "border_color"): "代码块边框颜色",
    ("code_block", "padding"): "代码块内边距",
    ("table", "layout"): "表格样式",
    ("table", "style"): "Word 表格样式",
    ("table", "font_name"): "表格字体",
    ("table", "font_size"): "表格字号",
    ("table", "line_spacing"): "表格行距",
    ("table", "header_bold"): "表头加粗",
    ("table", "header_background"): "表头背景色",
    ("table", "header_alignment"): "表头水平对齐",
    ("table", "vertical_alignment"): "表体垂直对齐",
    ("table", "cell_margin_vertical"): "单元格上下内边距",
    ("table", "cell_margin_horizontal"): "单元格左右内边距",
    ("table", "header_vertical_alignment"): "表头垂直对齐",
    ("table", "column_width_strategy"): "列宽策略",
    ("table", "alignment"): "表体水平对齐",
    ("table", "alternating_rows"): "启用斑马纹",
    ("table", "row_background_odd"): "奇数行背景色",
    ("table", "row_background_even"): "偶数行背景色",
    ("list", "font_name"): "列表字体",
    ("list", "font_size"): "列表字号",
    ("list", "line_spacing"): "列表行距",
    ("list", "bullet_char"): "无序列表符号",
    ("list", "number_format"): "有序编号格式",
    ("list", "ordered_list_as_text"): "有序列表转文本",
    ("list", "indent_size"): "嵌套缩进",
    ("list", "space_after"): "列表段后间距",
    ("math_inline", "height"): "行内公式图片高度",
    ("math_inline", "dpi"): "行内公式分辨率",
    ("math_block", "width"): "块级公式图片宽度",
    ("math_block", "alignment"): "块级公式对齐",
    ("math_block", "space_before"): "公式段前间距",
    ("math_block", "space_after"): "公式段后间距",
    ("math_block", "dpi"): "块级公式分辨率",
    ("mermaid", "command"): "Mermaid 命令",
    ("mermaid", "format"): "输出格式",
    ("mermaid", "theme"): "主题",
    ("mermaid", "width"): "图片宽度",
    ("mermaid", "alignment"): "图片对齐",
    ("mermaid", "space_before"): "图前间距",
    ("mermaid", "space_after"): "图后间距",
    ("mermaid", "background_color"): "图片背景色",
    ("mermaid", "theme_variables", "primaryColor"): "主色",
    ("mermaid", "theme_variables", "primaryTextColor"): "主文字色",
    ("mermaid", "theme_variables", "primaryBorderColor"): "主边框色",
    ("mermaid", "theme_variables", "lineColor"): "连线颜色",
    ("mermaid", "theme_variables", "secondaryColor"): "辅助色",
    ("mermaid", "theme_variables", "tertiaryColor"): "第三级颜色",
    ("mermaid", "theme_variables", "clusterBkg"): "子图背景色",
    ("mermaid", "theme_variables", "clusterBorder"): "子图边框色",
    ("mermaid", "theme_variables", "edgeLabelBackground"): "连线标签背景色",
    ("mermaid", "soft_max_height_ratio"): "软高度比例",
    ("mermaid", "hard_max_height_ratio"): "硬高度比例",
    ("mermaid", "page_max_height_ratio"): "页面最大高度比例",
    ("mermaid", "page_break_threshold_ratio"): "分页阈值比例",
    ("mermaid", "min_readable_width"): "最小可读宽度",
    ("mermaid", "oversized_strategy"): "超大图处理策略",
    ("mermaid", "force_page_break_before_oversized"): "超大图前强制分页",
    ("mermaid", "keep_with_previous"): "与前段同页",
    ("mermaid", "keep_with_previous_max_chars"): "前段最长字符数",
    ("mermaid", "follow_previous_trigger_height_ratio"): "跟随前段高度阈值",
    ("mermaid", "follow_previous_width_ratio"): "跟随前段宽度比例",
    ("mermaid", "follow_previous_space_before"): "跟随前段图前距",
    ("mermaid", "keep_together"): "图段落保持完整",
    ("mermaid", "keep_with_next"): "与后段同页",
    ("mermaid", "widow_control"): "孤行控制",
    ("chapter_scan", "target_dir"): "扫描目录",
    ("chapter_scan", "glob"): "文件匹配模式",
    ("chapter_scan", "recursive"): "递归扫描",
}

COMMON_FIELD_TIPS: Dict[str, str] = {
    "font_name": "设置该样式使用的字体名称，同时用于中文字体映射。",
    "font_size": "设置文字字号，通常使用 pt 单位，例如 14pt。",
    "font_color": "设置文字颜色，支持 #RRGGBB、短 hex 或 null 继承。",
    "bold": "控制该样式文字是否加粗。",
    "italic": "控制该样式文字是否斜体。",
    "space_before": "设置段落前方间距，支持 pt、cm、mm、in 等单位。",
    "space_after": "设置段落后方间距，支持 pt、cm、mm、in 等单位。",
    "alignment": "设置段落或图片的水平对齐方式。",
    "first_line_indent": "设置首行缩进字符数，按当前字号换算为 pt。",
    "line_spacing": "设置该样式的行距倍数。",
    "background": "设置背景色，通常使用 #RRGGBB。",
    "border_color": "设置边框颜色；部分模板字段当前仅保留，不一定直接渲染。",
    "width": "设置图片或块级元素的首选宽度。",
    "height": "设置图片或行内元素的首选高度。",
    "dpi": "设置回退图片渲染分辨率；数值越大图片越清晰但体积更大。",
}

FIELD_TIPS: Dict[ConfigPath, str] = {
    ("document", "page_size"): "设置 Word 第一节页面尺寸，支持 A4、A3 和 Letter。",
    ("document", "margin_top"): "设置页面上边距，支持 cm、mm、in、pt。",
    ("document", "margin_bottom"): "设置页面下边距，支持 cm、mm、in、pt。",
    ("document", "margin_left"): "设置页面左边距，支持 cm、mm、in、pt。",
    ("document", "margin_right"): "设置页面右边距，支持 cm、mm、in、pt。",
    ("document", "line_spacing"): "模板保留的文档级行距；正文、表格、列表请分别配置各自行距。",
    ("document", "ignore_thematic_breaks"): "控制是否忽略 Markdown 分割线 ---、*** 等。",
    ("document", "auto_fix_tables"): "控制是否尝试修复缺少 separator 行的不规范 Markdown 表格。",
    ("document", "outline_mode"): "控制中文公文式大纲识别：auto 自动、on 强制开启、off 关闭。",
    ("metadata", "author"): "写入 Word 文档属性中的作者；为空时会尝试使用当前系统用户。",
    ("metadata", "last_modified_by"): "写入 Word 文档属性中的最后修改者；为空时使用作者。",
    ("metadata", "title"): "写入 Word 文档标题；为空时会从 Markdown 内容推导。",
    ("metadata", "subject"): "写入 Word 文档属性中的主题。",
    ("metadata", "keywords"): "写入 Word 文档关键词；列表会用英文逗号拼接。",
    ("metadata", "comments"): "写入 Word 文档属性中的备注。",
    ("metadata", "category"): "写入 Word 文档属性中的类别。",
    ("outline", "level1_style"): "指定一级中文大纲先继承的样式块。",
    ("outline", "level2_style"): "指定二级中文大纲先继承的样式块。",
    ("outline", "level3_style"): "指定三级中文大纲先继承的样式块。",
    ("outline", "level4_style"): "指定四级中文大纲先继承的样式块。",
    ("inline", "bold", "font_color"): "设置 Markdown 加粗文本颜色；null 表示继承原颜色。",
    ("inline", "italic", "font_color"): "设置 Markdown 斜体文本颜色；null 表示继承原颜色。",
    ("inline", "code", "font_name"): "设置 Markdown 行内代码的字体。",
    ("inline", "code", "font_size"): "设置 Markdown 行内代码的字号。",
    ("inline", "code", "font_color"): "设置 Markdown 行内代码的文字颜色。",
    ("inline", "code", "background"): "设置 Markdown 行内代码的背景色。",
    ("code_block", "font_name"): "设置 fenced code block 的字体。",
    ("code_block", "font_size"): "设置 fenced code block 的字号。",
    ("code_block", "font_color"): "设置代码块文字颜色。",
    ("code_block", "background"): "设置代码块段落背景色。",
    ("code_block", "border_color"): "代码块边框颜色字段当前保留，渲染代码暂未直接读取。",
    ("code_block", "padding"): "设置代码块近似内边距，当前通过行首空格模拟。",
    ("table", "layout"): "选择表格预设样式；界面显示中文，保存为稳定 YAML 值。",
    ("table", "style"): "设置 Word 内置表格样式名；样式不存在时会忽略并使用默认样式。",
    ("table", "font_name"): "设置表格单元格文字字体。",
    ("table", "font_size"): "设置表格单元格文字字号。",
    ("table", "line_spacing"): "设置表格单元格段落行距。",
    ("table", "header_bold"): "模板字段当前保留；表头目前总是加粗。",
    ("table", "header_background"): "设置表头单元格背景色。",
    ("table", "header_alignment"): "设置表头水平对齐；继承时跟随列对齐或表格默认对齐。",
    ("table", "vertical_alignment"): "设置表体单元格垂直对齐。",
    ("table", "cell_margin_vertical"): "设置单元格上下内边距。",
    ("table", "cell_margin_horizontal"): "设置单元格左右内边距。",
    ("table", "header_vertical_alignment"): "设置表头单元格垂直对齐。",
    ("table", "column_width_strategy"): "设置列宽策略：按内容分配或更均衡保守。",
    ("table", "border_color"): "表格边框颜色字段当前保留，部分布局不直接读取。",
    ("table", "alignment"): "设置表体单元格默认水平对齐；Markdown 列对齐优先级更高。",
    ("table", "alternating_rows"): "控制是否启用表体奇偶行交替背景色。",
    ("table", "row_background_odd"): "设置奇数表体行背景色，表头不计入表体行。",
    ("table", "row_background_even"): "设置偶数表体行背景色，表头不计入表体行。",
    ("list", "font_name"): "设置列表项文字字体。",
    ("list", "font_size"): "设置列表项文字字号。",
    ("list", "line_spacing"): "设置列表项行距。",
    ("list", "bullet_char"): "设置无序列表符号；默认符号使用 Word 列表样式。",
    ("list", "number_format"): "设置文本编号格式，仅在有序列表转文本时生效。",
    ("list", "ordered_list_as_text"): "控制有序列表是否写成普通文本而非 Word 自动编号。",
    ("list", "indent_size"): "设置嵌套列表每级缩进。",
    ("list", "space_after"): "设置列表项段后间距。",
    ("math_inline", "height"): "行内公式图片回退高度字段；当前行为等同默认值。",
    ("math_inline", "dpi"): "行内公式图片回退分辨率字段；当前行为等同默认值。",
    ("math_block", "width"): "块级公式回退为图片时的图片宽度。",
    ("math_block", "alignment"): "设置块级公式段落对齐，未知值回退为居中。",
    ("math_block", "space_before"): "设置块级公式段前间距。",
    ("math_block", "space_after"): "设置块级公式段后间距。",
    ("math_block", "dpi"): "块级公式图片回退分辨率字段；当前行为等同默认值。",
    ("mermaid", "command"): "设置 Mermaid CLI 命令或可执行文件路径。",
    ("mermaid", "format"): "设置 Mermaid 转换输出格式；插入 Word 最稳妥的是 PNG。",
    ("mermaid", "theme"): "设置 Mermaid 内置主题；使用主题变量时建议 base。",
    ("mermaid", "width"): "设置 Mermaid 图首选宽度，最终不会超过页面可用宽度。",
    ("mermaid", "alignment"): "设置 Mermaid 图片所在段落的水平对齐。",
    ("mermaid", "space_before"): "设置 Mermaid 图前间距。",
    ("mermaid", "space_after"): "设置 Mermaid 图后间距。",
    ("mermaid", "background_color"): "设置 Mermaid 输出图片背景色。",
    ("mermaid", "theme_variables", "primaryColor"): "设置 Mermaid 节点主背景色。",
    ("mermaid", "theme_variables", "primaryTextColor"): "设置 Mermaid 主节点文字颜色。",
    ("mermaid", "theme_variables", "primaryBorderColor"): "设置 Mermaid 主节点边框颜色。",
    ("mermaid", "theme_variables", "lineColor"): "设置 Mermaid 连线颜色。",
    ("mermaid", "theme_variables", "secondaryColor"): "设置 Mermaid 辅助节点颜色。",
    ("mermaid", "theme_variables", "tertiaryColor"): "设置 Mermaid 第三级节点颜色。",
    ("mermaid", "theme_variables", "clusterBkg"): "设置 Mermaid 子图背景色。",
    ("mermaid", "theme_variables", "clusterBorder"): "设置 Mermaid 子图边框色。",
    ("mermaid", "theme_variables", "edgeLabelBackground"): "设置 Mermaid 连线标签背景色。",
    ("mermaid", "soft_max_height_ratio"): "软高度限制标记，当前暂无直接可见效果。",
    ("mermaid", "hard_max_height_ratio"): "图高度超过页面可用高度该比例时会按比例缩小。",
    ("mermaid", "page_max_height_ratio"): "页面布局模式下超大图允许使用的最大高度比例。",
    ("mermaid", "page_break_threshold_ratio"): "首选高度超过该阈值时进入页面布局模式。",
    ("mermaid", "min_readable_width"): "缩放后宽度低于该值时进入页面布局模式。",
    ("mermaid", "oversized_strategy"): "设置超大 Mermaid 图采用页面布局还是仅缩放。",
    ("mermaid", "force_page_break_before_oversized"): "控制页面布局模式下是否强制图前分页。",
    ("mermaid", "keep_with_previous"): "控制小图是否允许与前一个短段落同页。",
    ("mermaid", "keep_with_previous_max_chars"): "允许绑定上一段的最长字符数，小于等于 0 表示不限制。",
    ("mermaid", "follow_previous_trigger_height_ratio"): "图高度不超过页面可用高度该比例时才尝试跟随前段。",
    ("mermaid", "follow_previous_width_ratio"): "跟随前段时，图宽最多占页面可用宽度的比例。",
    ("mermaid", "follow_previous_space_before"): "跟随前段时使用的图前间距。",
    ("mermaid", "keep_together"): "设置 Mermaid 图段落的 Word keep-together。",
    ("mermaid", "keep_with_next"): "设置 Mermaid 图段落与后一段保持在一起。",
    ("mermaid", "widow_control"): "设置 Mermaid 图段落的 Word 孤行控制。",
    ("chapter_scan", "target_dir"): "设置章节 Markdown 后置扫描的目标目录。",
    ("chapter_scan", "glob"): "设置章节扫描文件匹配模式。",
    ("chapter_scan", "recursive"): "控制章节扫描是否递归进入子目录。",
}

COLOR_FIELD_PATHS = {
    *((section, "font_color") for section in STYLE_SECTIONS),
    ("inline", "bold", "font_color"),
    ("inline", "italic", "font_color"),
    ("inline", "code", "font_color"),
    ("inline", "code", "background"),
    ("code_block", "background"),
    ("code_block", "border_color"),
    ("table", "header_background"),
    ("table", "border_color"),
    ("table", "row_background_odd"),
    ("table", "row_background_even"),
    ("mermaid", "background_color"),
}

FONT_NAME_FIELD_PATHS = {
    *((section, "font_name") for section in STYLE_SECTIONS),
    ("inline", "code", "font_name"),
}

FONT_SIZE_FIELD_PATHS = {
    *((section, "font_size") for section in STYLE_SECTIONS),
    ("inline", "code", "font_size"),
}

LINE_SPACING_FIELD_PATHS = {
    ("document", "line_spacing"),
    ("paragraph", "line_spacing"),
    ("code_block", "line_spacing"),
    ("table", "line_spacing"),
    ("list", "line_spacing"),
}

FIRST_LINE_INDENT_FIELD_PATHS = {
    *((section, "first_line_indent") for section in HEADING_SECTIONS),
    ("paragraph", "first_line_indent"),
}

DPI_FIELD_PATHS = {
    ("math_inline", "dpi"),
    ("math_block", "dpi"),
}

DIMENSION_FIELD_PATHS = {
    *(
        (section, field_name)
        for section in HEADING_SECTIONS
        for field_name in ("space_before", "space_after")
    ),
    ("document", "margin_top"),
    ("document", "margin_bottom"),
    ("document", "margin_left"),
    ("document", "margin_right"),
    ("paragraph", "space_before"),
    ("paragraph", "space_after"),
    ("code_block", "space_before"),
    ("code_block", "space_after"),
    ("code_block", "padding"),
    ("table", "cell_margin_vertical"),
    ("table", "cell_margin_horizontal"),
    ("list", "indent_size"),
    ("list", "space_after"),
    ("math_inline", "height"),
    ("math_block", "width"),
    ("math_block", "space_before"),
    ("math_block", "space_after"),
    ("mermaid", "width"),
    ("mermaid", "space_before"),
    ("mermaid", "space_after"),
    ("mermaid", "min_readable_width"),
}

SECTION_GROUPS = [
    ("文档", ("document",)),
    ("标题", ("heading1", "heading2", "heading3", "heading4")),
    ("段落", ("paragraph",)),
    ("行内与代码", ("inline", "code_block")),
    ("表格", ("table",)),
    ("列表", ("list",)),
    ("公式", ("math_inline", "math_block")),
    ("Mermaid", ("mermaid",)),
]


def resolve_field_widget_rule(path: ConfigPath) -> FieldWidgetRule:
    """Return the editor widget rule for a config path."""
    if not path:
        return DEFAULT_FIELD_WIDGET_RULE

    readonly_value_mapping = READONLY_FIELD_VALUE_MAPPINGS.get(path)
    if readonly_value_mapping is not None:
        return FieldWidgetRule(
            kind=FIELD_WIDGET_COMBOBOX,
            options=tuple(display for display, _stored in readonly_value_mapping),
            readonly=True,
            value_mapping=readonly_value_mapping,
        )

    readonly_options = READONLY_FIELD_OPTIONS.get(path)
    if readonly_options is not None:
        return FieldWidgetRule(
            kind=FIELD_WIDGET_COMBOBOX,
            options=readonly_options,
            readonly=True,
        )

    section = path[0]

    if path in COLOR_FIELD_PATHS:
        return FieldWidgetRule(kind=FIELD_WIDGET_COLOR)

    if section == "mermaid" and len(path) >= 3 and path[1] == "theme_variables":
        return FieldWidgetRule(kind=FIELD_WIDGET_COLOR)

    if path in FONT_NAME_FIELD_PATHS:
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=FONT_OPTIONS)

    if path in FONT_SIZE_FIELD_PATHS:
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=FONT_SIZE_OPTIONS)

    if path in LINE_SPACING_FIELD_PATHS:
        return FieldWidgetRule(
            kind=FIELD_WIDGET_COMBOBOX,
            options=LINE_SPACING_OPTIONS,
        )

    if path in FIRST_LINE_INDENT_FIELD_PATHS:
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=INDENT_OPTIONS)

    if path in DPI_FIELD_PATHS:
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=DPI_OPTIONS)

    if path in DIMENSION_FIELD_PATHS:
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=DIMENSION_OPTIONS)

    if path == ("list", "bullet_char"):
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=LIST_BULLET_OPTIONS)

    if path == ("list", "number_format"):
        return FieldWidgetRule(
            kind=FIELD_WIDGET_COMBOBOX,
            options=NUMBER_FORMAT_OPTIONS,
        )

    return DEFAULT_FIELD_WIDGET_RULE


def format_mapped_widget_value(raw_value: Any, value_mapping: Tuple[Tuple[str, str], ...]) -> str:
    """Return the display label for a stored mapped widget value."""
    text_value = format_config_value(raw_value)
    for display_value, stored_value in value_mapping:
        if text_value == stored_value:
            return display_value
    return text_value


def parse_mapped_widget_value(raw_value: Any, value_mapping: Tuple[Tuple[str, str], ...]) -> Any:
    """Return the stored value for a mapped widget display label."""
    for display_value, stored_value in value_mapping:
        if raw_value == display_value:
            return stored_value
    return raw_value


def resolve_section_label(path: ConfigPath, section_name: str) -> str:
    """Return the display label for one config section or nested group."""
    return SECTION_LABELS.get(path, section_name)


def resolve_field_label(path: ConfigPath, field_name: str, _value: Any) -> str:
    """Return the display label for one editor field."""
    return FIELD_LABELS.get(path, COMMON_FIELD_LABELS.get(field_name, field_name))


def resolve_field_tip(path: ConfigPath, _value: Any) -> str:
    """Return a concise help tip for one editor field."""
    if not path:
        return ""
    return FIELD_TIPS.get(path, COMMON_FIELD_TIPS.get(path[-1], ""))


def normalize_color_preview(raw_value: Any) -> Optional[str]:
    """Normalize a hex color for preview, returning None for unsupported text."""
    text = str(raw_value or "").strip()
    if not text or text.lower() == "null":
        return None

    if text.startswith("#"):
        text = text[1:]

    if len(text) == 3 and all(char in "0123456789abcdefABCDEF" for char in text):
        text = "".join(char * 2 for char in text)

    if len(text) == 6 and all(char in "0123456789abcdefABCDEF" for char in text):
        return f"#{text.upper()}"

    return None


def _safe_winfo_int(widget: tk.Misc, method_name: str, default: int) -> int:
    """Return an integer Tk geometry value, falling back for unmapped widgets."""
    try:
        value = getattr(widget, method_name)()
    except (AttributeError, tk.TclError):
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _window_dimension(widget: tk.Misc, actual_method: str, requested_method: str) -> int:
    """Return a useful current or requested Tk window dimension."""
    requested = _safe_winfo_int(widget, requested_method, 1)
    actual = _safe_winfo_int(widget, actual_method, requested)
    return max(actual if actual > 1 else requested, 1)


def _format_geometry(width: int, height: int, x: int, y: int) -> str:
    """Format Tk geometry with correct signs for positive and negative offsets."""
    return f"{width}x{height}{x:+d}{y:+d}"


def _clamp(value: int, lower: int, upper: int) -> int:
    """Clamp a coordinate, tolerating windows larger than the available bounds."""
    if upper < lower:
        return lower
    return min(max(value, lower), upper)


def center_window_on_screen(window: tk.Misc, parent: Optional[tk.Misc] = None) -> None:
    """Place a Tk window near its parent and keep it within visible desktop bounds."""
    window.update_idletasks()
    if parent is not None:
        parent.update_idletasks()

    width = _window_dimension(window, "winfo_width", "winfo_reqwidth")
    height = _window_dimension(window, "winfo_height", "winfo_reqheight")

    anchor = parent if parent is not None else window
    screen_width = _safe_winfo_int(anchor, "winfo_screenwidth", width)
    screen_height = _safe_winfo_int(anchor, "winfo_screenheight", height)
    vroot_x = _safe_winfo_int(anchor, "winfo_vrootx", 0)
    vroot_y = _safe_winfo_int(anchor, "winfo_vrooty", 0)
    vroot_width = _safe_winfo_int(anchor, "winfo_vrootwidth", screen_width)
    vroot_height = _safe_winfo_int(anchor, "winfo_vrootheight", screen_height)

    if parent is None:
        anchor_x = vroot_x
        anchor_y = vroot_y
        anchor_width = max(vroot_width, width)
        anchor_height = max(vroot_height, height)
    else:
        anchor_x = _safe_winfo_int(parent, "winfo_rootx", vroot_x)
        anchor_y = _safe_winfo_int(parent, "winfo_rooty", vroot_y)
        anchor_width = _window_dimension(parent, "winfo_width", "winfo_reqwidth")
        anchor_height = _window_dimension(parent, "winfo_height", "winfo_reqheight")

    vroot_right = vroot_x + max(vroot_width, width)
    vroot_bottom = vroot_y + max(vroot_height, height)
    anchor_right = anchor_x + anchor_width
    anchor_bottom = anchor_y + anchor_height

    anchor_outside_reported_x = anchor_right <= vroot_x or anchor_x >= vroot_right
    anchor_outside_reported_y = anchor_bottom <= vroot_y or anchor_y >= vroot_bottom
    bounds_left = min(vroot_x, anchor_x) if anchor_outside_reported_x else vroot_x
    bounds_right = max(vroot_right, anchor_right) if anchor_outside_reported_x else vroot_right
    bounds_top = min(vroot_y, anchor_y) if anchor_outside_reported_y else vroot_y
    bounds_bottom = (
        max(vroot_bottom, anchor_bottom) if anchor_outside_reported_y else vroot_bottom
    )

    x = anchor_x + (anchor_width - width) // 2
    y = anchor_y + (anchor_height - height) // 2
    x = _clamp(x, bounds_left, bounds_right - width)
    y = _clamp(y, bounds_top, bounds_bottom - height)

    window.geometry(_format_geometry(width, height, x, y))


def ask_three_way_choice(
    *,
    parent: tk.Misc,
    title: str,
    message: str,
    choices: Tuple[Tuple[str, str], ...],
) -> str:
    """Show a modal prompt with explicit labels and return the selected value."""
    cancel_value = choices[-1][0]
    result = {"value": cancel_value}
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.transient(parent)

    body = ttk.Frame(dialog, padding="16")
    body.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    body.columnconfigure(0, weight=1)
    ttk.Label(body, text=message, justify=tk.LEFT, wraplength=440).grid(
        row=0,
        column=0,
        sticky=(tk.W, tk.E),
    )

    buttons = ttk.Frame(body)
    buttons.grid(row=1, column=0, sticky=tk.E, pady=(16, 0))

    def choose(value: str) -> None:
        result["value"] = value
        dialog.destroy()

    for index, (value, label) in enumerate(choices):
        ttk.Button(
            buttons,
            text=label,
            command=lambda selected=value: choose(selected),
        ).grid(row=0, column=index, padx=(8 if index else 0, 0))

    dialog.protocol("WM_DELETE_WINDOW", lambda: choose(cancel_value))
    dialog.grab_set()
    dialog.after(0, lambda: center_window_on_screen(dialog, parent=parent))
    dialog.wait_window()
    return result["value"]


def ask_unsaved_changes(*, parent: tk.Misc, path: Optional[Path]) -> str:
    """Ask how to handle a dirty draft before closing the editor."""
    target = str(path) if path is not None else "尚未关联文件的配置"
    return ask_three_way_choice(
        parent=parent,
        title="配置尚未保存",
        message=f"{target}\n包含未保存的修改。",
        choices=(("save", "保存"), ("discard", "放弃"), ("cancel", "取消")),
    )


def ask_external_change(*, parent: tk.Misc, path: Path) -> str:
    """Ask how to resolve a file changed outside the application."""
    return ask_three_way_choice(
        parent=parent,
        title="配置已在磁盘上修改",
        message=f"{path}\n已被其他程序修改。",
        choices=(("reload", "重新载入"), ("overwrite", "覆盖"), ("cancel", "取消")),
    )


class Tooltip:
    """Small hover tooltip for Tk widgets."""

    def __init__(self, widget: tk.Misc, text: str, delay_ms: int = 400) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: Optional[str] = None
        self._tip_window: Optional[tk.Toplevel] = None

        self.widget.bind("<Enter>", self.schedule, add="+")
        self.widget.bind("<Leave>", self.hide, add="+")
        self.widget.bind("<ButtonPress>", self.hide, add="+")

    def schedule(self, _event: Optional[tk.Event] = None) -> None:
        """Show the tooltip after a short hover delay."""
        self.cancel()
        self._after_id = self.widget.after(self.delay_ms, self.show)

    def cancel(self) -> None:
        """Cancel a pending tooltip display."""
        if self._after_id is None:
            return
        self.widget.after_cancel(self._after_id)
        self._after_id = None

    def show(self) -> None:
        """Create the tooltip popup near the target widget."""
        self._after_id = None
        if self._tip_window is not None or not self.text:
            return

        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self._tip_window = tk.Toplevel(self.widget)
        self._tip_window.wm_overrideredirect(True)
        self._tip_window.wm_geometry(f"+{x}+{y}")

        tk.Label(
            self._tip_window,
            text=self.text,
            justify=tk.LEFT,
            background="#FFF8DC",
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=5,
            wraplength=360,
        ).pack()

    def hide(self, _event: Optional[tk.Event] = None) -> None:
        """Hide the tooltip popup and cancel pending display."""
        self.cancel()
        if self._tip_window is None:
            return
        self._tip_window.destroy()
        self._tip_window = None


@dataclass
class FieldBinding:
    """Keep a widget variable paired with its schema value."""

    path: ConfigPath
    variable: Any
    schema_value: Any
    value_mapping: Tuple[Tuple[str, str], ...] = ()


class ConfigEditorWindow:
    """Popup editor for the main window's current configuration document."""

    def __init__(
        self,
        root: tk.Tk,
        document: ConfigDocument,
        packaged_default_config: Dict[str, Any],
        on_saved: Optional[Callable[[Path], None]] = None,
    ) -> None:
        self.root = root
        self.document = document
        self.on_saved = on_saved
        self.packaged_default_config = clone_config(packaged_default_config)

        self.window = tk.Toplevel(root)
        self.window.geometry("980x760")
        self.window.minsize(860, 640)
        self.window.transient(root)

        self.source_var = tk.StringVar(value=self.describe_document())
        self.status_var = tk.StringVar(value="已加载当前配置")

        self.form_host: Optional[ttk.Frame] = None
        self.notebook: Optional[ttk.Notebook] = None
        self.field_bindings: List[FieldBinding] = []
        self.tooltips: List[Tooltip] = []
        self.current_config = clone_config(self.document.draft_config)
        self.schema_config: Dict[str, Any] = {}

        self.update_window_title()
        self.setup_ui()
        self.load_config_data(self.document.draft_config, self.describe_document())

        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.grab_set()
        self.window.after(0, lambda: center_window_on_screen(self.window, parent=root))

    def setup_ui(self) -> None:
        """Build the editor layout."""
        container = ttk.Frame(self.window, padding="12")
        container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        title = ttk.Label(
            container,
            text="编辑配置",
            font=("Helvetica", 16, "bold"),
        )
        title.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        info_frame = ttk.LabelFrame(container, text="当前配置", padding="10")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)

        ttk.Label(info_frame, text="当前文件：").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(
            info_frame,
            textvariable=self.source_var,
            state="readonly",
        ).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(8, 0), pady=2)

        self.form_host = ttk.Frame(container)
        self.form_host.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.form_host.columnconfigure(0, weight=1)
        self.form_host.rowconfigure(0, weight=1)

        button_frame = ttk.Frame(container)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        button_frame.columnconfigure(0, weight=1)

        action_frame = ttk.Frame(button_frame)
        action_frame.grid(row=0, column=0, sticky=tk.W)

        ttk.Button(
            action_frame,
            text="恢复内置默认",
            command=self.restore_packaged_defaults,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            action_frame,
            text="另存为",
            command=self.save_config_as,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            button_frame,
            text="保存",
            command=self.save_config,
        ).grid(row=0, column=1, sticky=tk.E, padx=(8, 8))

        ttk.Button(
            button_frame,
            text="关闭",
            command=self.close,
        ).grid(row=0, column=2, sticky=tk.E)

        ttk.Label(
            container,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
        ).grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

    def load_config_data(self, loaded_config: Dict[str, Any], source_text: str) -> None:
        """Load config data into the form."""
        self.current_config = clone_config(loaded_config)
        self.schema_config = build_config_schema(self.packaged_default_config, loaded_config)
        self.source_var.set(source_text)
        self.render_form()

    def describe_document(self) -> str:
        """Return the editor's current file label."""
        if self.document.current_path is None:
            return "内置默认（未关联文件）"
        return str(self.document.current_path)

    def update_window_title(self) -> None:
        """Keep the editor title associated with the file being edited."""
        name = (
            self.document.current_path.name
            if self.document.current_path is not None
            else "内置默认"
        )
        self.window.title(f"编辑配置 - {name}")

    def render_form(self) -> None:
        """Render all config sections into tabs."""
        if self.form_host is None:
            return

        for child in self.form_host.winfo_children():
            child.destroy()

        self.field_bindings = []
        self.notebook = ttk.Notebook(self.form_host)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        rendered_sections = set()

        for tab_label, section_keys in SECTION_GROUPS:
            visible_keys = [key for key in section_keys if key in self.current_config]
            if not visible_keys:
                continue

            tab_frame, body_frame = self.create_scrollable_tab(self.notebook)
            self.notebook.add(tab_frame, text=tab_label)

            for index, section_key in enumerate(visible_keys):
                section_frame = ttk.LabelFrame(
                    body_frame,
                    text=resolve_section_label((section_key,), section_key),
                    padding="10",
                )
                section_frame.grid(
                    row=index,
                    column=0,
                    sticky=(tk.W, tk.E),
                    pady=(0, 10),
                )
                section_frame.columnconfigure(0, weight=1)
                self.render_section_fields(
                    parent=section_frame,
                    data=self.current_config[section_key],
                    schema=self.schema_config.get(section_key),
                    path=(section_key,),
                )
                rendered_sections.add(section_key)

        extra_keys = [key for key in self.current_config.keys() if key not in rendered_sections]
        for section_key in extra_keys:
            tab_frame, body_frame = self.create_scrollable_tab(self.notebook)
            section_label = resolve_section_label((section_key,), section_key)
            self.notebook.add(tab_frame, text=section_label)

            section_frame = ttk.LabelFrame(body_frame, text=section_label, padding="10")
            section_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
            section_frame.columnconfigure(0, weight=1)

            self.render_section_fields(
                parent=section_frame,
                data=self.current_config[section_key],
                schema=self.schema_config.get(section_key),
                path=(section_key,),
            )

    def create_scrollable_tab(self, notebook: ttk.Notebook) -> Tuple[ttk.Frame, ttk.Frame]:
        """Create a scrollable notebook tab."""
        outer = ttk.Frame(notebook)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        body = ttk.Frame(canvas, padding="10")

        body.columnconfigure(0, weight=1)

        window_id = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        body.bind(
            "<Configure>",
            lambda event, widget=canvas: widget.configure(scrollregion=widget.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event, widget=canvas, item=window_id: widget.itemconfigure(item, width=event.width),
        )

        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        return outer, body

    def render_section_fields(
        self,
        parent: ttk.Frame,
        data: Any,
        schema: Any,
        path: ConfigPath,
    ) -> None:
        """Render nested config fields recursively."""
        if isinstance(data, dict):
            for index, (key, value) in enumerate(data.items()):
                child_schema = schema.get(key) if isinstance(schema, dict) else None
                child_path = path + (key,)

                if isinstance(value, dict):
                    group = ttk.LabelFrame(
                        parent,
                        text=resolve_section_label(child_path, key),
                        padding="10",
                    )
                    group.grid(row=index, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
                    group.columnconfigure(0, weight=1)
                    self.render_section_fields(group, value, child_schema, child_path)
                    continue

                row = ttk.Frame(parent)
                row.grid(row=index, column=0, sticky=(tk.W, tk.E), pady=4)
                row.columnconfigure(2, weight=1)

                label_text = resolve_field_label(child_path, key, value)
                if child_schema is None:
                    label_text = f"{label_text} (留空 = null)"

                ttk.Label(row, text=label_text, width=32).grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
                self.create_field_tip_widget(
                    row,
                    resolve_field_tip(child_path, value),
                ).grid(row=0, column=1, sticky=tk.W, padx=(0, 8))

                widget = self.create_field_widget(row, child_path, value, child_schema)
                widget.grid(row=0, column=2, sticky=(tk.W, tk.E))
            return

        row = ttk.Frame(parent)
        row.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=4)
        row.columnconfigure(2, weight=1)

        label_text = resolve_field_label(path, path[-1], data)
        ttk.Label(row, text=label_text, width=32).grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        self.create_field_tip_widget(row, resolve_field_tip(path, data)).grid(
            row=0,
            column=1,
            sticky=tk.W,
            padx=(0, 8),
        )
        widget = self.create_field_widget(row, path, data, schema)
        widget.grid(row=0, column=2, sticky=(tk.W, tk.E))

    def create_field_tip_widget(self, parent: ttk.Frame, tip_text: str) -> ttk.Label:
        """Create a visible field help marker with an attached tooltip."""
        label_options = {
            "text": "?" if tip_text else "",
            "width": 2,
            "anchor": tk.CENTER,
        }
        if tip_text:
            label_options["cursor"] = "question_arrow"

        label = ttk.Label(parent, **label_options)
        if tip_text:
            self.tooltips.append(Tooltip(label, tip_text))
        return label

    def create_color_field_widget(
        self,
        parent: ttk.Frame,
        variable: tk.StringVar,
    ) -> ttk.Frame:
        """Create a color swatch, text input, and chooser button."""
        frame = ttk.Frame(parent)
        frame.columnconfigure(1, weight=1)

        preview = tk.Label(frame, width=3, relief=tk.SOLID, borderwidth=1)
        preview.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 6))

        entry = ttk.Entry(frame, textvariable=variable)
        entry.grid(row=0, column=1, sticky=(tk.W, tk.E))

        ttk.Button(
            frame,
            text="选择",
            command=lambda: self.choose_color(variable),
        ).grid(row=0, column=2, sticky=tk.E, padx=(6, 0))

        variable.trace_add(
            "write",
            lambda *_args, widget=preview, value=variable: self.update_color_preview(
                widget,
                value.get(),
            ),
        )
        self.update_color_preview(preview, variable.get())
        return frame

    def update_color_preview(self, preview: tk.Label, raw_value: Any) -> None:
        """Refresh the swatch for a text color value."""
        color_value = normalize_color_preview(raw_value)
        if color_value is None:
            preview.configure(background="#FFFFFF", text="")
            return

        preview.configure(background=color_value, text="")

    def choose_color(self, variable: tk.StringVar) -> None:
        """Open the system color chooser and write the selected hex value."""
        initial_color = normalize_color_preview(variable.get())
        _rgb, selected = colorchooser.askcolor(
            color=initial_color,
            parent=self.window,
        )
        if selected:
            variable.set(selected.upper())

    def create_field_widget(
        self,
        parent: ttk.Frame,
        path: ConfigPath,
        value: Any,
        schema_value: Any,
    ) -> ttk.Widget:
        """Create a suitable input widget for a config field."""
        expected_value = schema_value if schema_value is not None else value

        if isinstance(expected_value, bool):
            variable = tk.BooleanVar(value=bool(value))
            widget = ttk.Checkbutton(parent, variable=variable)
            self.field_bindings.append(FieldBinding(path=path, variable=variable, schema_value=expected_value))
            return widget

        rule = resolve_field_widget_rule(path)
        display_value = format_config_value(value)
        if rule.value_mapping:
            display_value = format_mapped_widget_value(value, rule.value_mapping)
        variable = tk.StringVar(value=display_value)

        if rule.kind == FIELD_WIDGET_COLOR:
            widget = self.create_color_field_widget(parent, variable)
        elif rule.kind == FIELD_WIDGET_COMBOBOX:
            widget = ttk.Combobox(
                parent,
                textvariable=variable,
                values=rule.options,
                state="readonly" if rule.readonly else "normal",
            )
        else:
            widget = ttk.Entry(parent, textvariable=variable)

        self.field_bindings.append(
            FieldBinding(
                path=path,
                variable=variable,
                schema_value=schema_value,
                value_mapping=rule.value_mapping,
            )
        )
        return widget

    def collect_config(self) -> Dict[str, Any]:
        """Collect all widget values into a config dict."""
        collected = clone_config(self.current_config)

        for binding in self.field_bindings:
            raw_value = binding.variable.get()
            raw_value = parse_mapped_widget_value(raw_value, binding.value_mapping)
            try:
                value = coerce_config_value(raw_value, binding.schema_value)
            except ValueError as exc:
                field_name = ".".join(binding.path)
                raise ValueError(f"{field_name}: {exc}") from exc
            set_value_at_path(collected, binding.path, value)

        return collected

    def update_document_draft(self) -> bool:
        """Collect form values and update the document's editable snapshot."""
        try:
            config = self.collect_config()
        except Exception as exc:
            messagebox.showerror(
                "配置内容无效",
                f"无法读取当前编辑内容：\n\n{exc}",
                parent=self.window,
            )
            return False

        self.current_config = config
        self.document.update_draft(config)
        return True

    def finish_successful_save(self) -> None:
        """Refresh editor state and notify the main window after a save."""
        config_path = self.document.current_path
        if config_path is None:
            return

        self.current_config = clone_config(self.document.saved_config)
        self.source_var.set(str(config_path))
        self.update_window_title()
        self.status_var.set(f"已保存到 {config_path}")

        if self.on_saved:
            self.on_saved(config_path)

    def save_current_draft_as(self) -> bool:
        """Choose a target, save the existing draft, and switch to that file."""
        filename = filedialog.asksaveasfilename(
            parent=self.window,
            title="配置另存为",
            defaultextension=".yaml",
            filetypes=[("YAML 文件", "*.yaml"), ("YML 文件", "*.yml"), ("所有文件", "*.*")],
        )

        if not filename:
            return False

        target_path = Path(filename).expanduser()
        if (
            self.document.current_path is not None
            and target_path.resolve(strict=False)
            == self.document.current_path.resolve(strict=False)
        ):
            return self.save_config()

        try:
            self.document.save_as(target_path)
        except Exception as exc:
            messagebox.showerror(
                "保存失败",
                f"无法保存配置文件：\n\n{exc}",
                parent=self.window,
            )
            return False

        self.finish_successful_save()
        return True

    def save_config_as(self) -> bool:
        """Save the form to a new YAML file and make it the current file."""
        if not self.update_document_draft():
            return False
        return self.save_current_draft_as()

    def save_config(self) -> bool:
        """Save the form to its current file, resolving external changes."""
        if not self.update_document_draft():
            return False

        if self.document.current_path is None:
            return self.save_current_draft_as()

        try:
            self.document.save()
        except ExternalConfigChangeError:
            decision = ask_external_change(
                parent=self.window,
                path=self.document.current_path,
            )
            if decision == "cancel":
                return False
            if decision == "reload":
                try:
                    self.document.reload(self.packaged_default_config)
                except Exception as exc:
                    messagebox.showerror(
                        "重新载入失败",
                        f"无法重新载入配置文件：\n\n{exc}",
                        parent=self.window,
                    )
                    return False

                self.load_config_data(
                    self.document.draft_config,
                    self.describe_document(),
                )
                self.status_var.set("已重新载入磁盘上的配置")
                return False

            try:
                self.document.save(overwrite=True)
            except Exception as exc:
                messagebox.showerror(
                    "保存失败",
                    f"无法覆盖配置文件：\n\n{exc}",
                    parent=self.window,
                )
                return False
        except Exception as exc:
            messagebox.showerror(
                "保存失败",
                f"无法保存配置文件：\n\n{exc}",
                parent=self.window,
            )
            return False

        self.finish_successful_save()
        return True

    def restore_packaged_defaults(self) -> None:
        """Reset the editor to the packaged default template."""
        if not messagebox.askyesno(
            "恢复默认",
            "这会用内置默认模板覆盖当前编辑内容。是否继续？",
            parent=self.window,
        ):
            return

        self.document.update_draft(self.packaged_default_config)
        self.load_config_data(self.document.draft_config, self.describe_document())
        self.status_var.set("已恢复内置默认，保存后才会写入文件")

    def close(self) -> None:
        """Close the popup after resolving any unsaved draft."""
        form_is_valid = self.update_document_draft()
        if not form_is_valid or self.document.dirty:
            decision = ask_unsaved_changes(
                parent=self.window,
                path=self.document.current_path,
            )
            if decision == "cancel":
                return
            if decision == "save" and not self.save_config():
                return
            if decision == "discard":
                self.document.discard_draft()

        self.window.grab_release()
        self.window.destroy()


class Md2docxGUI:
    """Graphical user interface for md2docx converter."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize GUI application."""
        self.root = root
        self.root.title("Markdown to Word Converter")
        self.root.geometry("900x680")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        app_state_dir = Path.home() / ".md2docx"
        app_state_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = app_state_dir / "history.json"
        self.preferences_file = app_state_dir / "preferences.json"
        self.packaged_default_config = StyleManager.load_packaged_template("default")
        self.config_editor: Optional[ConfigEditorWindow] = None
        self.config_document, self.startup_config_error = self.load_initial_config_document()
        self.config_file_var = tk.StringVar(value=self.describe_current_config())

        self.history = self.load_history()

        self.setup_ui()
        self.refresh_history_list()
        if self.startup_config_error:
            self.root.after(
                0,
                lambda error=self.startup_config_error: messagebox.showwarning(
                    "配置读取失败",
                    f"无法载入上次使用的配置，已改用内置默认配置。\n\n{error}",
                    parent=self.root,
                ),
            )
        self.root.after(0, lambda: center_window_on_screen(self.root))

    def close(self) -> None:
        """Close the application after resolving an open editor's draft."""
        editor = self.config_editor
        if editor is not None:
            try:
                if editor.window.winfo_exists():
                    editor.close()
                    if editor.window.winfo_exists():
                        return
            except tk.TclError:
                pass
            self.config_editor = None

        self.root.destroy()

    def setup_ui(self) -> None:
        """Setup user interface components."""
        style = ttk.Style()
        style.theme_use("clam")

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        title_label = ttk.Label(
            main_frame,
            text="📄 Markdown to Word Converter",
            font=("Helvetica", 18, "bold"),
        )
        title_label.grid(row=0, column=0, pady=(0, 20), sticky=tk.W)

        self.setup_conversion_section(main_frame)
        self.setup_history_section(main_frame)

        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
        )
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

    def setup_conversion_section(self, parent: ttk.Frame) -> None:
        """Setup file selection and conversion controls."""
        conv_frame = ttk.LabelFrame(parent, text="File Conversion", padding="10")
        conv_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        conv_frame.columnconfigure(1, weight=1)

        ttk.Label(conv_frame, text="Markdown File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_var = tk.StringVar()
        input_entry = ttk.Entry(conv_frame, textvariable=self.input_var, width=50)
        input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)

        browse_btn = ttk.Button(
            conv_frame,
            text="Browse...",
            command=self.browse_input_file,
            width=12,
        )
        browse_btn.grid(row=0, column=2, padx=5)

        ttk.Label(conv_frame, text="Output File:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(conv_frame, textvariable=self.output_var, width=50)
        output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)

        output_btn = ttk.Button(
            conv_frame,
            text="Save As...",
            command=self.browse_output_file,
            width=12,
        )
        output_btn.grid(row=1, column=2, padx=5)

        ttk.Label(conv_frame, text="Word Template:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.word_template_var = tk.StringVar()
        template_entry = ttk.Entry(
            conv_frame,
            textvariable=self.word_template_var,
            width=50,
            state="readonly",
        )
        template_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)

        ttk.Button(
            conv_frame,
            text="Choose...",
            command=self.browse_word_template,
            width=12,
        ).grid(row=2, column=2, padx=5)

        ttk.Button(
            conv_frame,
            text="Clear",
            command=self.clear_word_template,
            width=12,
        ).grid(row=2, column=3, padx=5, sticky=(tk.W, tk.E))

        ttk.Label(conv_frame, text="当前配置：").grid(row=3, column=0, sticky=tk.W, pady=5)
        config_entry = ttk.Entry(
            conv_frame,
            textvariable=self.config_file_var,
            width=50,
            state="readonly",
        )
        config_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5)

        ttk.Button(
            conv_frame,
            text="打开配置...",
            command=self.browse_config_file,
            width=12,
        ).grid(row=3, column=2, padx=5)

        ttk.Button(
            conv_frame,
            text="编辑配置...",
            command=self.open_config_editor,
            width=12,
        ).grid(row=3, column=3, padx=5, sticky=(tk.W, tk.E))

        self.progress = ttk.Progressbar(conv_frame, mode="indeterminate", length=240)
        self.progress.grid(
            row=4,
            column=0,
            columnspan=3,
            padx=(0, 5),
            pady=(15, 0),
            sticky=(tk.W, tk.E),
        )

        ttk.Button(
            conv_frame,
            text="转换格式",
            command=self.convert_file,
            style="Accent.TButton",
            width=12,
        ).grid(
            row=4,
            column=3,
            padx=5,
            pady=(15, 0),
            sticky=(tk.W, tk.E),
        )

    def setup_history_section(self, parent: ttk.Frame) -> None:
        """Setup history list display."""
        history_frame = ttk.LabelFrame(parent, text="Conversion History", padding="10")
        history_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        columns = ("Time", "Input", "Output", "Status")
        self.history_tree = ttk.Treeview(
            history_frame,
            columns=columns,
            show="headings",
            height=10,
        )

        self.history_tree.heading("Time", text="Time")
        self.history_tree.heading("Input", text="Input File")
        self.history_tree.heading("Output", text="Output File")
        self.history_tree.heading("Status", text="Status")

        self.history_tree.column("Time", width=150)
        self.history_tree.column("Input", width=250)
        self.history_tree.column("Output", width=250)
        self.history_tree.column("Status", width=180)

        scrollbar = ttk.Scrollbar(
            history_frame,
            orient=tk.VERTICAL,
            command=self.history_tree.yview,
        )
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        btn_frame = ttk.Frame(history_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(
            btn_frame,
            text="🔄 Reload Selected",
            command=self.reload_from_history,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="🗑️ Clear History",
            command=self.clear_history,
        ).pack(side=tk.LEFT, padx=5)

        self.history_tree.bind("<Double-1>", lambda event: self.reload_from_history())

    def dialog_parent(self) -> Optional[tk.Misc]:
        """Return the active owner for native dialogs when a root exists."""
        return getattr(self, "root", None)

    def browse_input_file(self) -> None:
        """Open file dialog to select input Markdown file."""
        filename = filedialog.askopenfilename(
            parent=self.dialog_parent(),
            title="Select Markdown File",
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if filename:
            self.input_var.set(filename)
            input_path = Path(filename)
            self.output_var.set(str(input_path.with_suffix(".docx")))

    def browse_output_file(self) -> None:
        """Open file dialog to select output Word file."""
        filename = filedialog.asksaveasfilename(
            parent=self.dialog_parent(),
            title="Save Word Document As",
            defaultextension=".docx",
            filetypes=[
                ("Word documents", "*.docx"),
                ("All files", "*.*"),
            ],
        )

        if filename:
            self.output_var.set(filename)

    def browse_word_template(self) -> None:
        """Open a file dialog to select an optional Word document template."""
        filename = filedialog.askopenfilename(
            parent=self.dialog_parent(),
            title="Select Word Template",
            filetypes=[
                ("Word documents", "*.docx"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            self.word_template_var.set(filename)

    def clear_word_template(self) -> None:
        """Clear the optional Word document template selection."""
        self.word_template_var.set("")

    def browse_config_file(self) -> None:
        """Open file dialog to select the YAML configuration file."""
        filename = filedialog.askopenfilename(
            parent=self.dialog_parent(),
            title="Select Configuration File",
            filetypes=[
                ("YAML files", "*.yaml *.yml"),
                ("All files", "*.*"),
            ],
        )

        if not filename:
            return

        config_path = Path(filename).expanduser()
        try:
            loaded_document = ConfigDocument.load(
                config_path,
                self.packaged_default_config,
            )
        except Exception as exc:
            messagebox.showerror(
                "配置读取失败",
                f"无法打开配置文件：\n{config_path}\n\n{exc}",
                parent=self.root if hasattr(self, "root") else None,
            )
            return

        self.config_document = loaded_document
        self.config_file_var.set(self.describe_current_config())
        preference_saved = self.save_last_config_path(config_path)
        self.status_var.set(f"已打开配置：{config_path}")

        if not preference_saved:
            messagebox.showwarning(
                "偏好保存失败",
                "配置已打开，但无法记录为下次启动配置。",
                parent=self.root if hasattr(self, "root") else None,
            )

    def open_config_editor(self) -> None:
        """Open the configuration popup from the main window."""
        if self.config_editor and self.config_editor.window.winfo_exists():
            self.config_editor.window.lift()
            self.config_editor.window.focus_force()
            return

        self.config_editor = ConfigEditorWindow(
            self.root,
            document=self.config_document,
            packaged_default_config=self.packaged_default_config,
            on_saved=self.on_config_saved,
        )
        self.status_var.set("已打开配置编辑器")

    def on_config_saved(self, config_path: Path) -> None:
        """Handle successful config saves from the popup."""
        self.config_file_var.set(self.describe_current_config())
        preference_saved = self.save_last_config_path(config_path)
        self.status_var.set(f"已保存配置：{config_path}")

        if not preference_saved:
            messagebox.showwarning(
                "偏好保存失败",
                "配置已保存，但无法记录为下次启动配置。",
                parent=self.root,
            )

    def load_last_config_path(self) -> Optional[Path]:
        """Load the last successfully used path, including the legacy key."""
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)

                if isinstance(loaded, dict):
                    config_file = loaded.get("last_config_path") or loaded.get("config_file")
                    if isinstance(config_file, str) and config_file:
                        return Path(config_file).expanduser()
        except Exception:
            pass

        return None

    def load_initial_config_document(self) -> Tuple[ConfigDocument, Optional[str]]:
        """Load the last file transactionally, falling back to built-in defaults."""
        config_path = self.load_last_config_path()
        if config_path is None:
            return ConfigDocument.from_defaults(self.packaged_default_config), None

        try:
            return ConfigDocument.load(config_path, self.packaged_default_config), None
        except Exception as exc:
            return (
                ConfigDocument.from_defaults(self.packaged_default_config),
                f"{config_path}\n{exc}",
            )

    def save_last_config_path(self, config_path: Path) -> bool:
        """Persist the last successfully opened or saved config path."""
        try:
            self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preferences_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {"last_config_path": str(config_path)},
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as exc:
            print(f"Failed to save preferences: {exc}")
            return False
        return True

    def describe_current_config(self) -> str:
        """Return the path label displayed in the main window and editor."""
        if self.config_document.current_path is None:
            return "内置默认（未关联文件）"
        return str(self.config_document.current_path)

    def build_effective_conversion_config(self) -> Dict[str, Any]:
        """Return an isolated copy of the last loaded or saved config."""
        return clone_config(self.config_document.saved_config)

    def selected_word_template(self) -> str:
        """Return the selected Word template without requiring a fully built GUI."""
        variable = getattr(self, "word_template_var", None)
        return variable.get().strip() if variable is not None else ""

    def convert_file(self) -> None:
        """Convert Markdown file to Word document."""
        input_file = self.input_var.get()
        output_file = self.output_var.get()
        word_template_file = self.selected_word_template()

        if not input_file:
            messagebox.showerror(
                "Error",
                "Please select an input Markdown file.",
                parent=self.dialog_parent(),
            )
            return

        if not output_file:
            messagebox.showerror(
                "Error",
                "Please specify an output file path.",
                parent=self.dialog_parent(),
            )
            return

        if not Path(input_file).exists():
            messagebox.showerror(
                "Error",
                f"Input file not found:\n{input_file}",
                parent=self.dialog_parent(),
            )
            return

        if word_template_file:
            template_path = Path(word_template_file).expanduser()
            if template_path.suffix.lower() != ".docx":
                messagebox.showerror(
                    "Error",
                    f"Word template must be a .docx file:\n{template_path}",
                    parent=self.dialog_parent(),
                )
                return
            if not template_path.is_file():
                messagebox.showerror(
                    "Error",
                    f"Word template not found:\n{template_path}",
                    parent=self.dialog_parent(),
                )
                return
            word_template_file = str(template_path)

        output_path = Path(output_file)
        if output_path.exists() and not messagebox.askyesno(
            "Confirm Overwrite",
            f"The output file already exists:\n{output_path}\n\nDo you want to overwrite it?",
            parent=self.dialog_parent(),
            default=messagebox.NO,
        ):
            return

        thread_args = (input_file, output_file)
        if word_template_file:
            thread_args += (word_template_file,)
        thread = threading.Thread(target=self._do_conversion, args=thread_args)
        thread.daemon = True
        thread.start()

    def _do_conversion(
        self,
        input_file: str,
        output_file: str,
        word_template_file: Optional[str] = None,
    ) -> None:
        """Perform actual conversion (runs in background thread)."""
        try:
            self.root.after(
                0,
                lambda: self.progress.configure(mode="indeterminate", value=0),
            )
            self.root.after(0, self.progress.start)
            self.root.after(0, lambda: self.status_var.set("Converting..."))
            config_data = self.build_effective_conversion_config()
            converter_kwargs: Dict[str, Any] = {"config_data": config_data}
            if word_template_file:
                converter_kwargs["word_template"] = word_template_file
            converter = Converter(**converter_kwargs)

            converter.convert(input_file, output_file)

            self.add_to_history(input_file, output_file, "Success")

            def finish_progress() -> None:
                self.progress.stop()
                self.progress.configure(mode="determinate", value=100)
                self.root.update_idletasks()

            self.root.after(0, finish_progress)
            self.root.after(0, lambda: self.status_var.set(f"✓ Conversion successful: {output_file}"))
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Success",
                    f"File converted successfully!\n\nOutput: {output_file}",
                    parent=self.dialog_parent(),
                ),
            )
            self.root.after(0, self.refresh_history_list)

        except Exception as exc:
            self.add_to_history(input_file, output_file, f"Failed: {str(exc)}")

            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.status_var.set("✗ Conversion failed"))
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Conversion Error",
                    f"Failed to convert file:\n\n{str(exc)}",
                    parent=self.dialog_parent(),
                ),
            )
            self.root.after(0, self.refresh_history_list)

    def load_history(self) -> List[Dict[str, str]]:
        """Load conversion history from JSON file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, list):
                    return loaded
            except Exception:
                return []
        return []

    def save_history(self) -> None:
        """Save conversion history to JSON file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as handle:
                json.dump(self.history, handle, indent=2, ensure_ascii=False)
        except Exception as exc:
            print(f"Failed to save history: {exc}")

    def add_to_history(self, input_file: str, output_file: str, status: str) -> None:
        """Add conversion record to history."""
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "input": input_file,
            "output": output_file,
            "status": status,
        }

        self.history.insert(0, record)
        self.history = self.history[:100]
        self.save_history()

    def refresh_history_list(self) -> None:
        """Refresh history display in treeview."""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for record in self.history:
            input_short = Path(record["input"]).name
            output_short = Path(record["output"]).name
            status = record["status"]

            if status == "Success":
                tag = "Success"
            elif str(status).startswith("Failed"):
                tag = "Failed"
            else:
                tag = ""

            self.history_tree.insert(
                "",
                tk.END,
                values=(record["time"], input_short, output_short, status),
                tags=(tag,),
            )

        self.history_tree.tag_configure("Success", foreground="green")
        self.history_tree.tag_configure("Failed", foreground="red")

    def reload_from_history(self) -> None:
        """Load selected history item into input fields."""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showinfo(
                "Info",
                "Please select a history item first.",
                parent=self.dialog_parent(),
            )
            return

        item = selection[0]
        index = self.history_tree.index(item)

        if index < len(self.history):
            record = self.history[index]
            self.input_var.set(record["input"])
            self.output_var.set(record["output"])
            self.status_var.set(f"Loaded from history: {record['time']}")

    def clear_history(self) -> None:
        """Clear all conversion history."""
        if messagebox.askyesno(
            "Confirm Clear History",
            "Are you sure you want to clear all conversion history?",
            parent=self.dialog_parent(),
        ):
            self.history = []
            self.save_history()
            self.refresh_history_list()
            self.status_var.set("History cleared")


def main() -> None:
    """Main entry point for GUI application."""
    root = tk.Tk()
    Md2docxGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
