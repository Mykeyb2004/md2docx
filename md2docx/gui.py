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

READONLY_FIELD_VALUE_MAPPINGS: Dict[ConfigPath, Tuple[Tuple[str, str], ...]] = {
    ("table", "layout"): TABLE_LAYOUT_VALUE_MAPPING,
}

READONLY_FIELD_OPTIONS: Dict[ConfigPath, Tuple[str, ...]] = {
    ("document", "page_size"): ("A4", "A3", "Letter"),
    ("heading1", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("heading2", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("heading3", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("heading4", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("paragraph", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("table", "alignment"): HORIZONTAL_ALIGNMENT_OPTIONS,
    ("table", "header_alignment"): HEADER_ALIGNMENT_OPTIONS,
    ("table", "vertical_alignment"): VERTICAL_ALIGNMENT_OPTIONS,
    ("table", "header_vertical_alignment"): VERTICAL_ALIGNMENT_OPTIONS,
    ("table", "column_width_strategy"): ("content-weighted", "balanced"),
    ("math_block", "alignment"): IMAGE_ALIGNMENT_OPTIONS,
    ("mermaid", "format"): ("png", "svg", "pdf"),
    ("mermaid", "theme"): ("default", "base", "dark", "forest", "neutral"),
    ("mermaid", "alignment"): IMAGE_ALIGNMENT_OPTIONS,
    ("mermaid", "oversized_strategy"): ("page", "scale"),
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

FIELD_LABELS: Dict[ConfigPath, str] = {
    ("table", "layout"): "表格样式",
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


def resolve_field_label(path: ConfigPath, field_name: str, _value: Any) -> str:
    """Return the display label for one editor field."""
    return FIELD_LABELS.get(path, field_name)


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
                section_frame = ttk.LabelFrame(body_frame, text=section_key, padding="10")
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
            self.notebook.add(tab_frame, text=section_key)

            section_frame = ttk.LabelFrame(body_frame, text=section_key, padding="10")
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
                    group = ttk.LabelFrame(parent, text=key, padding="10")
                    group.grid(row=index, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
                    group.columnconfigure(0, weight=1)
                    self.render_section_fields(group, value, child_schema, child_path)
                    continue

                row = ttk.Frame(parent)
                row.grid(row=index, column=0, sticky=(tk.W, tk.E), pady=4)
                row.columnconfigure(1, weight=1)

                label_text = resolve_field_label(child_path, key, value)
                if child_schema is None:
                    label_text = f"{label_text} (留空 = null)"

                ttk.Label(row, text=label_text, width=32).grid(row=0, column=0, sticky=tk.W, padx=(0, 8))

                widget = self.create_field_widget(row, child_path, value, child_schema)
                widget.grid(row=0, column=1, sticky=(tk.W, tk.E))
            return

        row = ttk.Frame(parent)
        row.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=4)
        row.columnconfigure(1, weight=1)

        label_text = resolve_field_label(path, path[-1], data)
        ttk.Label(row, text=label_text, width=32).grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        widget = self.create_field_widget(row, path, data, schema)
        widget.grid(row=0, column=1, sticky=(tk.W, tk.E))

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
            filetypes=[("YAML files", "*.yaml"), ("YML files", "*.yml"), ("All files", "*.*")],
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

        ttk.Label(conv_frame, text="当前配置：").grid(row=2, column=0, sticky=tk.W, pady=5)
        config_entry = ttk.Entry(
            conv_frame,
            textvariable=self.config_file_var,
            width=50,
            state="readonly",
        )
        config_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)

        ttk.Button(
            conv_frame,
            text="打开配置...",
            command=self.browse_config_file,
            width=12,
        ).grid(row=2, column=2, padx=5)

        ttk.Button(
            conv_frame,
            text="编辑配置...",
            command=self.open_config_editor,
            width=12,
        ).grid(row=2, column=3, padx=5)

        self.progress = ttk.Progressbar(conv_frame, mode="indeterminate", length=240)
        self.progress.grid(row=3, column=0, pady=(15, 0), sticky=(tk.W, tk.E))

        action_frame = ttk.Frame(conv_frame)
        action_frame.grid(row=3, column=1, columnspan=3, pady=(15, 0), sticky=tk.E)

        ttk.Button(
            action_frame,
            text="🔄 Convert to Word",
            command=self.convert_file,
            style="Accent.TButton",
        ).pack(side=tk.LEFT)

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

    def convert_file(self) -> None:
        """Convert Markdown file to Word document."""
        input_file = self.input_var.get()
        output_file = self.output_var.get()

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

        thread = threading.Thread(target=self._do_conversion, args=(input_file, output_file))
        thread.daemon = True
        thread.start()

    def _do_conversion(self, input_file: str, output_file: str) -> None:
        """Perform actual conversion (runs in background thread)."""
        try:
            self.root.after(0, self.progress.start)
            self.root.after(0, lambda: self.status_var.set("Converting..."))
            config_data = self.build_effective_conversion_config()
            converter = Converter(config_data=config_data)

            converter.convert(input_file, output_file)

            self.add_to_history(input_file, output_file, "Success")

            self.root.after(0, self.progress.stop)
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
