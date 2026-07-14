"""
Tests for GUI runtime conversion options.
"""
import json
from pathlib import Path

import md2docx.gui as gui_module
from md2docx.gui import Md2docxGUI


class _FakeBooleanVar:
    """Minimal BooleanVar stand-in for non-Tk unit tests."""

    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value


class _FakeStringVar:
    """Minimal StringVar stand-in for non-Tk unit tests."""

    def __init__(self, value: str = "") -> None:
        self.value = value
        self.callbacks = []

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value
        for callback in self.callbacks:
            callback()

    def trace_add(self, _mode: str, callback) -> str:
        self.callbacks.append(callback)
        return f"trace-{len(self.callbacks)}"


class _FakeWidget:
    """Minimal Tk widget stand-in that records construction and layout calls."""

    def __init__(self, widget_type: str, *args, **kwargs) -> None:
        self.widget_type = widget_type
        self.args = args
        self.kwargs = kwargs
        self.columnconfigure_calls = []
        self.grid_calls = []
        self.configured = {}

    def columnconfigure(self, *args, **kwargs) -> None:
        self.columnconfigure_calls.append((args, kwargs))

    def grid(self, *args, **kwargs) -> None:
        self.grid_calls.append((args, kwargs))

    def configure(self, **kwargs) -> None:
        self.configured.update(kwargs)


class _FakeProgress:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class _ImmediateRoot:
    def after(self, _delay_ms, callback=None) -> None:
        if callback:
            callback()


def test_gui_builds_runtime_override_for_auto_fix_tables():
    """Main GUI toggle should feed the table auto-fix override into conversions."""
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.auto_fix_tables_var = _FakeBooleanVar(True)

    assert gui.build_runtime_config_override() == {
        "document": {"auto_fix_tables": True}
    }


def test_gui_defaults_to_packaged_template_when_no_config_preference(tmp_path: Path):
    """Missing preferences should fall back to the bundled default.yaml."""
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = tmp_path / "preferences.json"
    gui.packaged_default_config_path = tmp_path / "templates" / "default.yaml"

    assert gui.load_selected_config_path() == gui.packaged_default_config_path


def test_gui_persists_selected_config_path(tmp_path: Path):
    """The selected conversion config should survive across app starts."""
    selected_config = tmp_path / "custom.yaml"
    selected_config.write_text("document:\n  auto_fix_tables: true\n", encoding="utf-8")

    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = tmp_path / "preferences.json"
    gui.packaged_default_config_path = tmp_path / "templates" / "default.yaml"

    gui.save_selected_config_path(selected_config)

    assert json.loads(gui.preferences_file.read_text(encoding="utf-8")) == {
        "config_file": str(selected_config)
    }
    assert gui.load_selected_config_path() == selected_config


def test_gui_ignores_missing_saved_config_path(tmp_path: Path):
    """A stale preference should not break startup or conversion."""
    missing_config = tmp_path / "missing.yaml"
    packaged_default = tmp_path / "templates" / "default.yaml"
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"config_file": str(missing_config)}),
        encoding="utf-8",
    )

    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file
    gui.packaged_default_config_path = packaged_default

    assert gui.load_selected_config_path() == packaged_default


def test_gui_browse_config_file_saves_selection(tmp_path: Path, monkeypatch):
    """Choosing a YAML config in the UI should persist and apply it."""
    selected_config = tmp_path / "selected.yaml"
    selected_config.write_text("document:\n  auto_fix_tables: true\n", encoding="utf-8")

    monkeypatch.setattr(
        gui_module.filedialog,
        "askopenfilename",
        lambda **_kwargs: str(selected_config),
    )

    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = tmp_path / "preferences.json"
    gui.packaged_default_config_path = tmp_path / "templates" / "default.yaml"
    gui.config_file_var = _FakeStringVar()
    gui.auto_fix_tables_var = _FakeStringVar()
    gui.status_var = _FakeStringVar()

    gui.browse_config_file()

    assert gui.config_file_var.get() == str(selected_config)
    assert json.loads(gui.preferences_file.read_text(encoding="utf-8")) == {
        "config_file": str(selected_config)
    }
    assert gui.auto_fix_tables_var.get() is True
    assert gui.status_var.get() == f"Config selected: {selected_config}"


def test_gui_conversion_uses_selected_config_file(tmp_path: Path, monkeypatch):
    """Conversions should instantiate Converter with the config selected in the GUI."""
    selected_config = tmp_path / "selected.yaml"
    selected_config.write_text("paragraph:\n  font_name: ConfigFont\n", encoding="utf-8")
    captured = {}

    class FakeConverter:
        def __init__(self, *, style_config=None, config_override=None):
            captured["style_config"] = style_config
            captured["config_override"] = config_override

        def convert(self, input_file, output_file):
            captured["convert"] = (input_file, output_file)

    monkeypatch.setattr(gui_module, "Converter", FakeConverter)
    monkeypatch.setattr(gui_module.messagebox, "showinfo", lambda *args, **kwargs: None)

    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = _ImmediateRoot()
    gui.progress = _FakeProgress()
    gui.status_var = _FakeStringVar()
    gui.config_file_var = _FakeStringVar(str(selected_config))
    gui.auto_fix_tables_var = _FakeBooleanVar(False)
    gui.history = []
    gui.add_to_history = lambda *args: None
    gui.refresh_history_list = lambda: None

    gui._do_conversion("input.md", "output.docx")

    assert captured["style_config"] == str(selected_config)
    assert captured["config_override"] == {"document": {"auto_fix_tables": False}}
    assert captured["convert"] == ("input.md", "output.docx")


def test_config_editor_rule_uses_editable_combobox_for_font_fields():
    """Frequent font fields should offer suggestions without blocking custom fonts."""
    rule = gui_module.resolve_field_widget_rule(("heading1", "font_name"))

    assert rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert rule.readonly is False
    assert "仿宋" in rule.options
    assert "Consolas" in rule.options


def test_config_editor_rule_uses_color_control_for_color_fields():
    """Frequent color fields should render as color composite controls."""
    assert (
        gui_module.resolve_field_widget_rule(("heading1", "font_color")).kind
        == gui_module.FIELD_WIDGET_COLOR
    )
    assert (
        gui_module.resolve_field_widget_rule(("table", "header_background")).kind
        == gui_module.FIELD_WIDGET_COLOR
    )
    assert (
        gui_module.resolve_field_widget_rule(
            ("mermaid", "theme_variables", "primaryColor")
        ).kind
        == gui_module.FIELD_WIDGET_COLOR
    )


def test_config_editor_rule_keeps_fixed_enums_readonly():
    """Known fixed-value fields should prevent unsupported free text."""
    page_rule = gui_module.resolve_field_widget_rule(("document", "page_size"))
    table_rule = gui_module.resolve_field_widget_rule(
        ("table", "column_width_strategy")
    )

    assert page_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert page_rule.readonly is True
    assert page_rule.options == ("A4", "A3", "Letter")
    assert table_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert table_rule.readonly is True
    assert table_rule.options == ("content-weighted", "balanced")


def test_config_editor_rule_keeps_common_sizes_editable():
    """Sizes, spacing, and numeric values should remain editable suggestions."""
    margin_rule = gui_module.resolve_field_widget_rule(("document", "margin_top"))
    spacing_rule = gui_module.resolve_field_widget_rule(("paragraph", "line_spacing"))
    indent_rule = gui_module.resolve_field_widget_rule(
        ("paragraph", "first_line_indent")
    )

    assert margin_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert margin_rule.readonly is False
    assert "2.54cm" in margin_rule.options
    assert spacing_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert spacing_rule.readonly is False
    assert "1.5" in spacing_rule.options
    assert indent_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert indent_rule.readonly is False
    assert "2" in indent_rule.options


def test_config_editor_rule_covers_nested_default_fields_after_path_gating():
    """Known nested default-template fields should still use enhanced controls."""
    inline_color_rule = gui_module.resolve_field_widget_rule(
        ("inline", "code", "background")
    )
    math_height_rule = gui_module.resolve_field_widget_rule(("math_inline", "height"))
    mermaid_width_rule = gui_module.resolve_field_widget_rule(("mermaid", "width"))
    table_margin_rule = gui_module.resolve_field_widget_rule(
        ("table", "cell_margin_horizontal")
    )
    math_dpi_rule = gui_module.resolve_field_widget_rule(("math_block", "dpi"))

    assert inline_color_rule.kind == gui_module.FIELD_WIDGET_COLOR
    assert math_height_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert mermaid_width_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert table_margin_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert math_dpi_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX


def test_config_editor_rule_leaves_unknown_fields_as_entry():
    """Imported or unsupported fields should retain the existing plain input path."""
    rule = gui_module.resolve_field_widget_rule(("custom", "unrecognized"))

    assert rule.kind == gui_module.FIELD_WIDGET_ENTRY
    assert rule.options == ()
    assert rule.readonly is False


def test_config_editor_rule_leaves_custom_name_collisions_as_entry():
    """Unknown sections should not inherit enhanced controls by leaf-name collision."""
    for path in (
        ("custom", "background"),
        ("custom", "font_size"),
        ("custom", "width"),
        ("custom", "dpi"),
    ):
        rule = gui_module.resolve_field_widget_rule(path)

        assert rule.kind == gui_module.FIELD_WIDGET_ENTRY
        assert rule.options == ()
        assert rule.readonly is False


def test_config_editor_rule_leaves_nested_unknown_font_names_as_entry():
    """Unknown nested fields should not inherit font controls from known parents."""
    for path in (
        ("paragraph", "custom", "font_name"),
        ("table", "custom", "font_name"),
        ("inline", "code", "custom", "font_name"),
    ):
        rule = gui_module.resolve_field_widget_rule(path)

        assert rule.kind == gui_module.FIELD_WIDGET_ENTRY
        assert rule.options == ()
        assert rule.readonly is False


def test_normalize_color_preview_accepts_long_and_short_hex_values():
    """Preview helper should normalize supported hex colors for the swatch."""
    assert gui_module.normalize_color_preview("#24292e") == "#24292E"
    assert gui_module.normalize_color_preview("D14") == "#DD1144"


def test_normalize_color_preview_rejects_empty_null_and_named_values():
    """Unsupported preview values should remain editable text without swatch errors."""
    assert gui_module.normalize_color_preview("") is None
    assert gui_module.normalize_color_preview("null") is None
    assert gui_module.normalize_color_preview("white") is None


def test_config_editor_create_field_widget_dispatches_enhanced_controls(monkeypatch):
    """Field widget creation should use the resolved high-frequency control rules."""
    def make_widget(widget_type):
        def factory(*args, **kwargs):
            return _FakeWidget(widget_type, *args, **kwargs)

        return factory

    def create_color_widget(_self, parent, variable):
        return _FakeWidget("color", parent, variable=variable)

    monkeypatch.setattr(gui_module.tk, "BooleanVar", _FakeBooleanVar)
    monkeypatch.setattr(gui_module.tk, "StringVar", _FakeStringVar)
    monkeypatch.setattr(gui_module.ttk, "Checkbutton", make_widget("checkbutton"))
    monkeypatch.setattr(gui_module.ttk, "Combobox", make_widget("combobox"))
    monkeypatch.setattr(gui_module.ttk, "Entry", make_widget("entry"))
    monkeypatch.setattr(
        gui_module.ConfigEditorWindow,
        "create_color_field_widget",
        create_color_widget,
    )

    editor = gui_module.ConfigEditorWindow.__new__(gui_module.ConfigEditorWindow)
    editor.field_bindings = []
    parent = object()

    checkbox = editor.create_field_widget(
        parent,
        ("document", "auto_fix_tables"),
        True,
        False,
    )
    color = editor.create_field_widget(
        parent,
        ("heading1", "font_color"),
        "#24292e",
        "#000000",
    )
    editable_combo = editor.create_field_widget(
        parent,
        ("heading1", "font_name"),
        "CustomFont",
        "",
    )
    readonly_combo = editor.create_field_widget(
        parent,
        ("document", "page_size"),
        "A4",
        "A4",
    )
    entry = editor.create_field_widget(parent, ("custom", "field"), "value", "")

    assert checkbox.widget_type == "checkbutton"
    assert isinstance(editor.field_bindings[0].variable, _FakeBooleanVar)
    assert editor.field_bindings[0].variable.get() is True

    assert color.widget_type == "color"
    assert color.kwargs["variable"].get() == "#24292e"

    assert editable_combo.widget_type == "combobox"
    assert editable_combo.kwargs["state"] == "normal"
    assert "仿宋" in editable_combo.kwargs["values"]

    assert readonly_combo.widget_type == "combobox"
    assert readonly_combo.kwargs["state"] == "readonly"
    assert readonly_combo.kwargs["values"] == ("A4", "A3", "Letter")

    assert entry.widget_type == "entry"
    assert len(editor.field_bindings) == 5


def test_config_editor_color_field_widget_wires_preview_entry_and_button(monkeypatch):
    """The color composite control should keep text input as the source of truth."""
    created = {}

    def make_widget(widget_type):
        def factory(*args, **kwargs):
            widget = _FakeWidget(widget_type, *args, **kwargs)
            created.setdefault(widget_type, []).append(widget)
            return widget

        return factory

    monkeypatch.setattr(gui_module.ttk, "Frame", make_widget("frame"))
    monkeypatch.setattr(gui_module.tk, "Label", make_widget("label"))
    monkeypatch.setattr(gui_module.ttk, "Entry", make_widget("entry"))
    monkeypatch.setattr(gui_module.ttk, "Button", make_widget("button"))

    editor = gui_module.ConfigEditorWindow.__new__(gui_module.ConfigEditorWindow)
    variable = _FakeStringVar("#abc")

    frame = editor.create_color_field_widget(object(), variable)

    assert frame.widget_type == "frame"
    assert frame.columnconfigure_calls == [((1,), {"weight": 1})]
    assert created["entry"][0].kwargs["textvariable"] is variable
    assert created["button"][0].kwargs["text"] == "选择"
    assert callable(created["button"][0].kwargs["command"])
    assert created["label"][0].configured["background"] == "#AABBCC"

    variable.set("white")

    assert created["label"][0].configured["background"] == "#FFFFFF"


def test_config_editor_choose_color_writes_selected_hex(monkeypatch):
    """Choosing a system color should update the field text with uppercase hex."""
    editor = gui_module.ConfigEditorWindow.__new__(gui_module.ConfigEditorWindow)
    editor.window = object()
    calls = []

    def choose_color(**kwargs):
        calls.append(kwargs)
        return (None, "#a1b2c3")

    monkeypatch.setattr(gui_module.colorchooser, "askcolor", choose_color)
    variable = _FakeStringVar("#123")

    editor.choose_color(variable)

    assert calls == [{"color": "#112233", "parent": editor.window}]
    assert variable.get() == "#A1B2C3"

    monkeypatch.setattr(
        gui_module.colorchooser,
        "askcolor",
        lambda **_kwargs: (None, None),
    )
    variable.set("#445566")

    editor.choose_color(variable)

    assert variable.get() == "#445566"
