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
from md2docx.config_utils import (
    build_config_schema,
    clone_config,
    coerce_config_value,
    format_config_value,
    load_yaml_config,
    merge_config,
    save_yaml_config,
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

# Backwards-compatible alias for the currently wired editor path.
FIELD_OPTIONS = LEGACY_FIELD_OPTIONS

COLOR_FIELD_NAMES = {
    "font_color",
    "background",
    "border_color",
    "header_background",
    "row_background_odd",
    "row_background_even",
    "background_color",
}

DIMENSION_FIELD_NAMES = {
    "margin_top",
    "margin_bottom",
    "margin_left",
    "margin_right",
    "space_before",
    "space_after",
    "padding",
    "width",
    "height",
    "indent_size",
    "cell_margin_vertical",
    "cell_margin_horizontal",
    "min_readable_width",
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

    readonly_options = READONLY_FIELD_OPTIONS.get(path)
    if readonly_options is not None:
        return FieldWidgetRule(
            kind=FIELD_WIDGET_COMBOBOX,
            options=readonly_options,
            readonly=True,
        )

    section = path[0]
    field_name = path[-1]

    if field_name in COLOR_FIELD_NAMES:
        return FieldWidgetRule(kind=FIELD_WIDGET_COLOR)

    if section == "mermaid" and len(path) >= 3 and path[1] == "theme_variables":
        return FieldWidgetRule(kind=FIELD_WIDGET_COLOR)

    if field_name == "font_name" and (
        section in STYLE_SECTIONS or path[:2] == ("inline", "code")
    ):
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=FONT_OPTIONS)

    if field_name == "font_size":
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=FONT_SIZE_OPTIONS)

    if field_name == "line_spacing":
        return FieldWidgetRule(
            kind=FIELD_WIDGET_COMBOBOX,
            options=LINE_SPACING_OPTIONS,
        )

    if field_name == "first_line_indent":
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=INDENT_OPTIONS)

    if field_name == "dpi":
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=DPI_OPTIONS)

    if field_name in DIMENSION_FIELD_NAMES:
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=DIMENSION_OPTIONS)

    if path == ("list", "bullet_char"):
        return FieldWidgetRule(kind=FIELD_WIDGET_COMBOBOX, options=LIST_BULLET_OPTIONS)

    if path == ("list", "number_format"):
        return FieldWidgetRule(
            kind=FIELD_WIDGET_COMBOBOX,
            options=NUMBER_FORMAT_OPTIONS,
        )

    return DEFAULT_FIELD_WIDGET_RULE


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


def center_window_on_screen(window: tk.Misc) -> None:
    """Place a Tk window in the center of the current screen."""
    window.update_idletasks()

    width = window.winfo_width() or window.winfo_reqwidth()
    height = window.winfo_height() or window.winfo_reqheight()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 2, 0)

    window.geometry(f"{width}x{height}+{x}+{y}")


@dataclass
class FieldBinding:
    """Keep a widget variable paired with its schema value."""

    path: ConfigPath
    variable: Any
    schema_value: Any


class ConfigEditorWindow:
    """Popup editor for the default YAML configuration."""

    def __init__(self, root: tk.Tk, on_saved: Optional[Callable[[Path], None]] = None) -> None:
        self.root = root
        self.on_saved = on_saved
        self.default_config_path = StyleManager.get_editable_template_path("default")
        self.packaged_default_config = StyleManager.load_packaged_template("default")

        self.window = tk.Toplevel(root)
        self.window.title("默认配置编辑器")
        self.window.geometry("980x760")
        self.window.minsize(860, 640)
        self.window.transient(root)

        self.source_var = tk.StringVar()
        self.target_var = tk.StringVar(value=str(self.default_config_path))
        self.status_var = tk.StringVar(value="已加载当前配置")

        self.form_host: Optional[ttk.Frame] = None
        self.notebook: Optional[ttk.Notebook] = None
        self.field_bindings: List[FieldBinding] = []
        self.current_config: Dict[str, Any] = {}
        self.schema_config: Dict[str, Any] = {}

        self.setup_ui()
        self.load_effective_config()

        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.grab_set()
        self.window.after(0, lambda: center_window_on_screen(self.window))

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
            text="默认配置文件编辑器",
            font=("Helvetica", 16, "bold"),
        )
        title.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        info_frame = ttk.LabelFrame(container, text="当前配置", padding="10")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)

        ttk.Label(info_frame, text="保存目标:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(
            info_frame,
            textvariable=self.target_var,
            state="readonly",
        ).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(8, 0), pady=2)

        ttk.Label(info_frame, text="当前来源:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(
            info_frame,
            textvariable=self.source_var,
            state="readonly",
        ).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(8, 0), pady=2)

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
            text="从 YAML 导入",
            command=self.import_config,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            action_frame,
            text="另存为 YAML",
            command=self.export_config,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            action_frame,
            text="恢复默认",
            command=self.restore_packaged_defaults,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            button_frame,
            text="保存到默认配置",
            command=self.save_default_config,
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

    def load_effective_config(self) -> None:
        """Load the editable default config if present, else use packaged defaults."""
        loaded_config: Dict[str, Any] = {}
        source_text = "内置默认模板"

        if self.default_config_path.exists():
            try:
                loaded_config = load_yaml_config(self.default_config_path)
                source_text = str(self.default_config_path)
            except Exception as exc:
                messagebox.showwarning(
                    "配置读取失败",
                    (
                        "读取默认配置文件失败，已回退到内置默认模板。\n\n"
                        f"{exc}\n\n"
                        "你仍然可以编辑后重新保存覆盖这个文件。"
                    ),
                    parent=self.window,
                )

        self.load_config_data(loaded_config, source_text)

    def load_config_data(self, loaded_config: Dict[str, Any], source_text: str) -> None:
        """Load config data into the form."""
        self.current_config = merge_config(self.packaged_default_config, loaded_config)
        self.schema_config = build_config_schema(self.packaged_default_config, loaded_config)
        self.source_var.set(source_text)
        self.status_var.set("配置已载入，可编辑后保存")
        self.render_form()

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

                label_text = key
                if child_schema is None:
                    label_text = f"{key} (留空 = null)"

                ttk.Label(row, text=label_text, width=32).grid(row=0, column=0, sticky=tk.W, padx=(0, 8))

                widget = self.create_field_widget(row, child_path, value, child_schema)
                widget.grid(row=0, column=1, sticky=(tk.W, tk.E))
            return

        row = ttk.Frame(parent)
        row.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=4)
        row.columnconfigure(1, weight=1)

        ttk.Label(row, text=path[-1], width=32).grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
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

        variable = tk.StringVar(value=format_config_value(value))
        rule = resolve_field_widget_rule(path)

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

        self.field_bindings.append(FieldBinding(path=path, variable=variable, schema_value=schema_value))
        return widget

    def collect_config(self) -> Dict[str, Any]:
        """Collect all widget values into a config dict."""
        collected = clone_config(self.current_config)

        for binding in self.field_bindings:
            raw_value = binding.variable.get()
            try:
                value = coerce_config_value(raw_value, binding.schema_value)
            except ValueError as exc:
                field_name = ".".join(binding.path)
                raise ValueError(f"{field_name}: {exc}") from exc
            set_value_at_path(collected, binding.path, value)

        return collected

    def save_default_config(self) -> None:
        """Save the current form to the editable default.yaml."""
        try:
            config = self.collect_config()
            save_yaml_config(self.default_config_path, config)
        except Exception as exc:
            messagebox.showerror(
                "保存失败",
                f"保存默认配置文件失败：\n\n{exc}",
                parent=self.window,
            )
            return

        self.current_config = config
        self.source_var.set(str(self.default_config_path))
        self.status_var.set(f"已保存到 {self.default_config_path}")

        if self.on_saved:
            self.on_saved(self.default_config_path)

        messagebox.showinfo(
            "保存成功",
            f"默认配置已保存到：\n{self.default_config_path}",
            parent=self.window,
        )

    def export_config(self) -> None:
        """Export the current form to another YAML file."""
        filename = filedialog.asksaveasfilename(
            parent=self.window,
            title="另存为 YAML",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("YML files", "*.yml"), ("All files", "*.*")],
        )

        if not filename:
            return

        try:
            config = self.collect_config()
            save_yaml_config(Path(filename), config)
        except Exception as exc:
            messagebox.showerror(
                "导出失败",
                f"导出配置文件失败：\n\n{exc}",
                parent=self.window,
            )
            return

        self.status_var.set(f"已导出到 {filename}")
        messagebox.showinfo(
            "导出成功",
            f"配置已导出到：\n{filename}",
            parent=self.window,
        )

    def import_config(self) -> None:
        """Import values from another YAML file into the form."""
        filename = filedialog.askopenfilename(
            parent=self.window,
            title="从 YAML 导入",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )

        if not filename:
            return

        try:
            loaded_config = load_yaml_config(Path(filename))
        except Exception as exc:
            messagebox.showerror(
                "导入失败",
                f"读取配置文件失败：\n\n{exc}",
                parent=self.window,
            )
            return

        self.load_config_data(loaded_config, str(Path(filename)))
        self.status_var.set(f"已导入 {filename}，可以保存到默认配置")

    def restore_packaged_defaults(self) -> None:
        """Reset the editor to the packaged default template."""
        if not messagebox.askyesno(
            "恢复默认",
            "这会用内置默认模板覆盖当前编辑内容。是否继续？",
            parent=self.window,
        ):
            return

        self.load_config_data({}, "内置默认模板")
        self.status_var.set("已恢复到内置默认模板，可保存覆盖默认配置文件")

    def close(self) -> None:
        """Close the popup."""
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

        app_state_dir = Path.home() / ".md2docx"
        app_state_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = app_state_dir / "history.json"
        self.preferences_file = app_state_dir / "preferences.json"
        self.packaged_default_config_path = (
            Path(__file__).resolve().parent / "templates" / "default.yaml"
        )
        self.default_config_path = StyleManager.get_editable_template_path("default")
        self.config_editor: Optional[ConfigEditorWindow] = None
        self.config_file_var = tk.StringVar(value=str(self.load_selected_config_path()))
        self.auto_fix_tables_var = tk.BooleanVar(value=self.load_auto_fix_tables_setting())

        self.history = self.load_history()

        self.setup_ui()
        self.refresh_history_list()
        self.root.after(0, lambda: center_window_on_screen(self.root))

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

        ttk.Label(conv_frame, text="Config File:").grid(row=2, column=0, sticky=tk.W, pady=5)
        config_entry = ttk.Entry(
            conv_frame,
            textvariable=self.config_file_var,
            width=50,
            state="readonly",
        )
        config_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)

        config_btn = ttk.Button(
            conv_frame,
            text="Browse...",
            command=self.browse_config_file,
            width=12,
        )
        config_btn.grid(row=2, column=2, padx=5)

        table_fix_toggle = ttk.Checkbutton(
            conv_frame,
            text="自动修复不规范表格（补 separator）",
            variable=self.auto_fix_tables_var,
        )
        table_fix_toggle.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=5, pady=(6, 0))

        self.progress = ttk.Progressbar(conv_frame, mode="indeterminate", length=240)
        self.progress.grid(row=4, column=0, pady=(15, 0), sticky=(tk.W, tk.E))

        action_frame = ttk.Frame(conv_frame)
        action_frame.grid(row=4, column=1, columnspan=2, pady=(15, 0), sticky=tk.E)

        ttk.Button(
            action_frame,
            text="⚙️ 配置...",
            command=self.open_config_editor,
        ).pack(side=tk.LEFT, padx=(0, 8))

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

    def browse_input_file(self) -> None:
        """Open file dialog to select input Markdown file."""
        filename = filedialog.askopenfilename(
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
            title="Select Configuration File",
            filetypes=[
                ("YAML files", "*.yaml *.yml"),
                ("All files", "*.*"),
            ],
        )

        if filename:
            config_path = Path(filename)
            self.config_file_var.set(str(config_path))
            self.save_selected_config_path(config_path)
            self.auto_fix_tables_var.set(self.load_auto_fix_tables_setting())
            self.status_var.set(f"Config selected: {config_path}")

    def open_config_editor(self) -> None:
        """Open the configuration popup from the main window."""
        if self.config_editor and self.config_editor.window.winfo_exists():
            self.config_editor.window.lift()
            self.config_editor.window.focus_force()
            return

        self.config_editor = ConfigEditorWindow(self.root, on_saved=self.on_config_saved)
        self.status_var.set(f"Config editor opened: {self.default_config_path}")

    def on_config_saved(self, config_path: Path) -> None:
        """Handle successful config saves from the popup."""
        self.config_file_var.set(str(config_path))
        self.save_selected_config_path(config_path)
        self.auto_fix_tables_var.set(self.load_auto_fix_tables_setting())
        self.status_var.set(f"Default config saved and selected: {config_path}")

    def load_selected_config_path(self) -> Path:
        """Load the user's selected conversion config path."""
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)

                if isinstance(loaded, dict):
                    config_file = loaded.get("config_file")
                    if isinstance(config_file, str) and config_file:
                        config_path = Path(config_file).expanduser()
                        if config_path.exists():
                            return config_path
        except Exception:
            pass

        return self.packaged_default_config_path

    def save_selected_config_path(self, config_path: Path) -> None:
        """Persist the user's selected conversion config path."""
        try:
            self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preferences_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {"config_file": str(config_path)},
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as exc:
            print(f"Failed to save preferences: {exc}")

    def get_selected_config_path(self) -> Path:
        """Return the current config path, falling back to the bundled default."""
        config_file = self.config_file_var.get().strip()
        config_path = (
            Path(config_file).expanduser()
            if config_file
            else self.packaged_default_config_path
        )

        if config_path.exists():
            return config_path

        self.config_file_var.set(str(self.packaged_default_config_path))
        return self.packaged_default_config_path

    def load_auto_fix_tables_setting(self) -> bool:
        """Load the selected config value for malformed-table auto-fixing."""
        config = StyleManager.load_packaged_template("default")
        config_path = self.get_selected_config_path()

        if config_path.exists():
            try:
                config = merge_config(config, load_yaml_config(config_path))
            except Exception:
                pass

        return bool(config.get("document", {}).get("auto_fix_tables", False))

    def build_runtime_config_override(self) -> Dict[str, Any]:
        """Build per-run config overrides from the main GUI switches."""
        return {
            "document": {
                "auto_fix_tables": bool(self.auto_fix_tables_var.get()),
            }
        }

    def convert_file(self) -> None:
        """Convert Markdown file to Word document."""
        input_file = self.input_var.get()
        output_file = self.output_var.get()

        if not input_file:
            messagebox.showerror("Error", "Please select an input Markdown file.")
            return

        if not output_file:
            messagebox.showerror("Error", "Please specify an output file path.")
            return

        if not Path(input_file).exists():
            messagebox.showerror("Error", f"Input file not found:\n{input_file}")
            return

        thread = threading.Thread(target=self._do_conversion, args=(input_file, output_file))
        thread.daemon = True
        thread.start()

    def _do_conversion(self, input_file: str, output_file: str) -> None:
        """Perform actual conversion (runs in background thread)."""
        try:
            self.root.after(0, self.progress.start)
            self.root.after(0, lambda: self.status_var.set("Converting..."))
            config_override = self.build_runtime_config_override()
            config_path = self.get_selected_config_path()

            if config_path.exists():
                self.save_selected_config_path(config_path)
                converter = Converter(
                    style_config=str(config_path),
                    config_override=config_override,
                )
            else:
                converter = Converter(config_override=config_override)

            converter.convert(input_file, output_file)

            self.add_to_history(input_file, output_file, "Success")

            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.status_var.set(f"✓ Conversion successful: {output_file}"))
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Success",
                    f"File converted successfully!\n\nOutput: {output_file}",
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
            messagebox.showinfo("Info", "Please select a history item first.")
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
