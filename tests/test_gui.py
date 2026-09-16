"""
Tests for GUI runtime conversion options.
"""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import md2docx.gui as gui_module
from md2docx.config_document import ConfigDocument
from md2docx.config_utils import load_yaml_config
from md2docx.gui import Md2docxGUI


class _FakeBooleanVar:
    """Minimal BooleanVar stand-in for non-Tk unit tests."""

    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = value


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
        self.bind_calls = []
        self.configured = {}

    def columnconfigure(self, *args, **kwargs) -> None:
        self.columnconfigure_calls.append((args, kwargs))

    def grid(self, *args, **kwargs) -> None:
        self.grid_calls.append((args, kwargs))

    def bind(self, *args, **kwargs) -> None:
        self.bind_calls.append((args, kwargs))

    def configure(self, **kwargs) -> None:
        self.configured.update(kwargs)


class _DeferredRoot:
    """Tk root stand-in that records callbacks until the test runs them."""

    def __init__(self) -> None:
        self.after_callbacks = []

    def title(self, _value: str) -> None:
        pass

    def geometry(self, _value: str) -> None:
        pass

    def resizable(self, _width: bool, _height: bool) -> None:
        pass

    def protocol(self, _name: str, _callback) -> None:
        pass

    def after(self, _delay_ms: int, callback=None) -> None:
        if callback:
            self.after_callbacks.append(callback)


def _iter_leaf_config_paths(data, path=()):
    """Yield leaf paths from a nested config dictionary."""
    if isinstance(data, dict):
        for key, value in data.items():
            yield from _iter_leaf_config_paths(value, path + (key,))
        return

    yield path, data


class _FakeProgress:
    def __init__(self) -> None:
        self.events = []

    def start(self) -> None:
        self.events.append(("start",))

    def stop(self) -> None:
        self.events.append(("stop",))

    def configure(self, **kwargs) -> None:
        self.events.append(("configure", kwargs))


class _ImmediateRoot:
    def after(self, _delay_ms, callback=None) -> None:
        if callback:
            callback()

    def update_idletasks(self) -> None:
        pass


class _PositionedWindow:
    """Tk-like window stand-in for geometry placement tests."""

    def __init__(
        self,
        *,
        width: int,
        height: int,
        root_x: int = 0,
        root_y: int = 0,
        screen_width: int = 1920,
        screen_height: int = 1080,
        vroot_x: int = 0,
        vroot_y: int = 0,
        vroot_width: int = 1920,
        vroot_height: int = 1080,
    ) -> None:
        self.width = width
        self.height = height
        self.root_x = root_x
        self.root_y = root_y
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.vroot_x = vroot_x
        self.vroot_y = vroot_y
        self.vroot_width = vroot_width
        self.vroot_height = vroot_height
        self.geometry_value = ""

    def update_idletasks(self) -> None:
        pass

    def winfo_width(self) -> int:
        return self.width

    def winfo_height(self) -> int:
        return self.height

    def winfo_reqwidth(self) -> int:
        return self.width

    def winfo_reqheight(self) -> int:
        return self.height

    def winfo_rootx(self) -> int:
        return self.root_x

    def winfo_rooty(self) -> int:
        return self.root_y

    def winfo_screenwidth(self) -> int:
        return self.screen_width

    def winfo_screenheight(self) -> int:
        return self.screen_height

    def winfo_vrootx(self) -> int:
        return self.vroot_x

    def winfo_vrooty(self) -> int:
        return self.vroot_y

    def winfo_vrootwidth(self) -> int:
        return self.vroot_width

    def winfo_vrootheight(self) -> int:
        return self.vroot_height

    def geometry(self, value: str) -> None:
        self.geometry_value = value


def test_center_window_uses_parent_origin_on_negative_secondary_screen():
    """Child dialogs should follow a parent placed on a left-hand monitor."""
    parent = _PositionedWindow(
        width=1000,
        height=800,
        root_x=-1600,
        root_y=100,
        vroot_x=-1920,
        vroot_width=3840,
    )
    dialog = _PositionedWindow(
        width=400,
        height=200,
        vroot_x=-1920,
        vroot_width=3840,
    )

    gui_module.center_window_on_screen(dialog, parent=parent)

    assert dialog.geometry_value == "400x200-1300+400"


def test_center_window_clamps_dialog_to_virtual_screen_bounds():
    """Centered child dialogs should stay visible near desktop edges."""
    parent = _PositionedWindow(width=320, height=260, root_x=1780, root_y=900)
    dialog = _PositionedWindow(width=500, height=240)

    gui_module.center_window_on_screen(dialog, parent=parent)

    assert dialog.geometry_value == "500x240+1420+840"


def test_main_file_dialogs_are_parented_to_root(monkeypatch):
    """Native file dialogs should stay associated with the main window."""
    root = object()
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = root
    gui.input_var = _FakeStringVar()
    gui.output_var = _FakeStringVar()
    captured_open = {}
    captured_save = {}

    monkeypatch.setattr(
        gui_module.filedialog,
        "askopenfilename",
        lambda **kwargs: captured_open.update(kwargs) or "",
    )
    monkeypatch.setattr(
        gui_module.filedialog,
        "asksaveasfilename",
        lambda **kwargs: captured_save.update(kwargs) or "",
    )

    gui.browse_input_file()
    gui.browse_output_file()

    assert captured_open["parent"] is root
    assert captured_save["parent"] is root


def test_word_template_dialog_is_parented_and_can_be_cleared(tmp_path, monkeypatch):
    """The Word template selector should use the main window and support clearing."""
    root = object()
    template_path = tmp_path / "template.docx"
    template_path.write_bytes(b"template")
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = root
    gui.preferences_file = tmp_path / "preferences.json"
    gui.word_template_var = _FakeStringVar()
    captured = {}
    monkeypatch.setattr(
        gui_module.filedialog,
        "askopenfilename",
        lambda **kwargs: captured.update(kwargs) or str(template_path),
    )

    gui.browse_word_template()

    assert gui.word_template_var.get() == str(template_path)
    assert captured["parent"] is root
    assert captured["filetypes"][0] == ("Word documents", "*.docx")

    gui.clear_word_template()
    assert gui.word_template_var.get() == ""


def test_gui_browse_word_template_persists_without_dropping_other_preferences(
    tmp_path: Path, monkeypatch
):
    """Selecting a template must merge, rather than replace, preferences."""
    template_path = tmp_path / "template.docx"
    template_path.write_bytes(b"template")
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps(
            {
                "last_config_path": str(tmp_path / "config.yaml"),
                "config_file": str(tmp_path / "legacy.yaml"),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        gui_module.filedialog,
        "askopenfilename",
        lambda **_kwargs: str(template_path),
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = object()
    gui.preferences_file = preferences_file
    gui.word_template_var = _FakeStringVar()

    gui.browse_word_template()

    assert gui.word_template_var.get() == str(template_path)
    assert json.loads(preferences_file.read_text(encoding="utf-8")) == {
        "last_config_path": str(tmp_path / "config.yaml"),
        "config_file": str(tmp_path / "legacy.yaml"),
        "last_word_template_path": str(template_path),
        "word_template_history": [str(template_path)],
    }


def test_gui_loads_last_word_template_path_and_reports_stale_file(tmp_path: Path):
    """A missing remembered template should remain visible with a warning."""
    template_path = tmp_path / "missing.docx"
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"last_word_template_path": str(template_path)}),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    path, warning = gui.load_last_word_template()

    assert path == template_path
    assert warning is not None
    assert str(template_path) in warning
    assert "不存在" in warning


def test_gui_load_word_template_state_migrates_legacy_last_path(tmp_path: Path):
    """Legacy single-path preferences should populate the new history state."""
    template_path = tmp_path / "template.docx"
    template_path.write_bytes(b"template")
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"last_word_template_path": str(template_path)}),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    assert gui.load_word_template_state() == (template_path, [str(template_path)], None)


def test_gui_load_word_template_state_normalizes_history_and_warns_for_missing_current(
    tmp_path: Path,
):
    """History should prioritize the current path, deduplicate, and stay bounded."""
    current_path = tmp_path / "current.docx"
    current_path.write_bytes(b"template")
    history_paths = [tmp_path / f"template-{index}.docx" for index in range(12)]
    raw_history = [
        None,
        "",
        "   ",
        str(history_paths[0]),
        str(history_paths[0]),
        *map(str, history_paths[1:]),
        {"path": "invalid"},
    ]
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps(
            {
                "last_word_template_path": str(current_path),
                "word_template_history": raw_history,
            }
        ),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    path, history, warning = gui.load_word_template_state()

    assert path == current_path
    assert history == [
        str(current_path),
        *[str(history_path) for history_path in history_paths[:9]],
    ]
    assert warning is None

    missing_current = tmp_path / "missing.docx"
    preferences_file.write_text(
        json.dumps(
            {
                "last_word_template_path": str(missing_current),
                "word_template_history": raw_history,
            }
        ),
        encoding="utf-8",
    )

    path, history, warning = gui.load_word_template_state()

    assert path == missing_current
    assert history[0] == str(missing_current)
    assert len(history) == 10
    assert warning is not None
    assert "不存在" in warning


def test_gui_normalize_word_template_history_expands_current_path(tmp_path: Path):
    """The current Path object should be expanded before history deduplication."""
    expanded_path = tmp_path / "expanded.docx"
    path_type = type(Path())

    class CurrentPath(path_type):
        def expanduser(self):
            return expanded_path

    current_path = CurrentPath("~/template.docx")

    assert Md2docxGUI.normalize_word_template_history(
        [str(expanded_path)], current_path
    ) == [str(expanded_path)]


def test_gui_normalize_word_template_history_skips_unexpandable_items(tmp_path: Path):
    """An unknown user's home path should not discard valid history entries."""
    valid_path = tmp_path / "valid.docx"
    unexpandable_path = "~md2docx_user_that_does_not_exist_20260831/template.docx"

    assert Md2docxGUI.normalize_word_template_history(
        [unexpandable_path, str(valid_path)]
    ) == [str(valid_path)]


def test_gui_load_word_template_state_ignores_unexpandable_current_path(tmp_path: Path):
    """An unknown user's current path should not prevent GUI state loading."""
    valid_path = tmp_path / "valid.docx"
    unexpandable_path = "~md2docx_user_that_does_not_exist_20260831/template.docx"
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps(
            {
                "last_word_template_path": unexpandable_path,
                "word_template_history": [unexpandable_path, str(valid_path)],
            }
        ),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    assert gui.load_word_template_state() == (None, [str(valid_path)], None)


@pytest.mark.parametrize("raw_history", [None, "template.docx", {"path": "template.docx"}])
def test_gui_load_word_template_state_without_current_ignores_invalid_history(
    tmp_path: Path, raw_history
):
    """Malformed history without a current path should produce an empty state."""
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"word_template_history": raw_history}),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    assert gui.load_word_template_state() == (None, [], None)


def test_gui_loads_existing_last_word_template_without_warning(tmp_path: Path):
    """A valid remembered template should restore silently."""
    template_path = tmp_path / "template.docx"
    template_path.write_bytes(b"template")
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"last_word_template_path": str(template_path)}),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    assert gui.load_last_word_template() == (template_path, None)


def test_gui_invalid_last_word_template_is_retained_and_warned(tmp_path: Path):
    """An invalid remembered suffix must not silently erase the selected path."""
    template_path = tmp_path / "template.txt"
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"last_word_template_path": str(template_path)}),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    path, warning = gui.load_last_word_template()

    assert path == template_path
    assert warning is not None
    assert ".docx" in warning


def test_gui_clear_word_template_removes_only_template_preference(tmp_path: Path):
    """Clearing a template must leave current and legacy config keys intact."""
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps(
            {
                "last_config_path": str(tmp_path / "config.yaml"),
                "config_file": str(tmp_path / "legacy.yaml"),
                "last_word_template_path": str(tmp_path / "template.docx"),
                "word_template_history": [
                    str(tmp_path / "template.docx"),
                    str(tmp_path / "older.docx"),
                ],
            }
        ),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file
    gui.word_template_var = _FakeStringVar(str(tmp_path / "template.docx"))

    gui.clear_word_template()

    assert gui.word_template_var.get() == ""
    assert json.loads(preferences_file.read_text(encoding="utf-8")) == {
        "last_config_path": str(tmp_path / "config.yaml"),
        "config_file": str(tmp_path / "legacy.yaml"),
        "word_template_history": [
            str(tmp_path / "template.docx"),
            str(tmp_path / "older.docx"),
        ],
    }


def test_gui_clear_word_template_preserves_history_migrated_from_legacy_path(
    tmp_path: Path,
):
    """Clearing a migrated legacy selection should persist its new history."""
    template_path = tmp_path / "legacy-template.docx"
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"last_word_template_path": str(template_path)}),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file
    current_path, gui.word_template_history, _warning = gui.load_word_template_state()
    gui.last_word_template_path = current_path
    gui.word_template_var = _FakeStringVar(str(current_path))

    gui.clear_word_template()

    assert json.loads(preferences_file.read_text(encoding="utf-8")) == {
        "word_template_history": [str(template_path)],
    }


def test_gui_save_last_config_path_merges_last_word_template(tmp_path: Path):
    """Saving a config must retain the template preference."""
    template_path = tmp_path / "template.docx"
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"last_word_template_path": str(template_path)}),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    assert gui.save_last_config_path(config_path) is True
    assert json.loads(preferences_file.read_text(encoding="utf-8")) == {
        "last_word_template_path": str(template_path),
        "last_config_path": str(config_path),
    }


def test_gui_conversion_section_builds_enabled_template_history_combobox(
    monkeypatch, tmp_path
):
    """The template row should start enabled and expose remembered paths."""
    current_path = tmp_path / "current.docx"
    older_path = tmp_path / "older.docx"
    history = [str(current_path), str(older_path)]
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.last_word_template_path = current_path
    gui.word_template_history = history
    gui.config_file_var = _FakeStringVar()
    parent = _FakeWidget("frame")

    monkeypatch.setattr(gui_module.tk, "StringVar", _FakeStringVar)
    monkeypatch.setattr(gui_module.tk, "BooleanVar", _FakeBooleanVar)
    for widget_name in (
        "LabelFrame",
        "Label",
        "Entry",
        "Combobox",
        "Checkbutton",
        "Button",
        "Progressbar",
    ):
        monkeypatch.setattr(
            gui_module.ttk,
            widget_name,
            lambda *args, _widget_name=widget_name, **kwargs: _FakeWidget(
                _widget_name,
                *args,
                **kwargs,
            ),
        )

    gui.setup_conversion_section(parent)

    assert gui.use_word_template_var.get() is True
    assert gui.word_template_var.get() == str(current_path)
    assert gui.word_template_combobox.kwargs["values"] == history
    assert gui.word_template_combobox.kwargs["state"] == "readonly"
    assert gui.word_template_combobox.bind_calls == [
        (("<<ComboboxSelected>>", gui.select_word_template_from_history), {})
    ]


def test_gui_selecting_history_moves_template_to_front(tmp_path: Path):
    """Choosing an older template should persist it as the MRU selection."""
    current_path = tmp_path / "current.docx"
    older_path = tmp_path / "older.docx"
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps(
            {
                "last_word_template_path": str(current_path),
                "word_template_history": [str(current_path), str(older_path)],
            }
        ),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file
    gui.word_template_history = [str(current_path), str(older_path)]
    gui.word_template_var = _FakeStringVar(str(older_path))
    gui.word_template_combobox = _FakeWidget("Combobox")

    gui.select_word_template_from_history()

    assert gui.last_word_template_path == older_path
    assert gui.word_template_history == [str(older_path), str(current_path)]
    assert gui.word_template_combobox.configured["values"] == [
        str(older_path),
        str(current_path),
    ]
    assert json.loads(preferences_file.read_text(encoding="utf-8")) == {
        "last_word_template_path": str(older_path),
        "word_template_history": [str(older_path), str(current_path)],
    }


def test_gui_loads_the_packaged_app_icon_for_the_title(monkeypatch):
    """The header should use the same PNG asset as the application icon."""
    loaded_paths = []

    class FakePhotoImage:
        def subsample(self, horizontal: int, vertical: int):
            assert (horizontal, vertical) == (32, 32)
            return self

    monkeypatch.setattr(
        gui_module.tk,
        "PhotoImage",
        lambda *, file: loaded_paths.append(file) or FakePhotoImage(),
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)

    icon = gui.load_title_icon()

    assert icon is not None
    assert loaded_paths == [str(gui_module.app_icon_png_path())]


def test_main_window_buttons_use_chinese_labels(monkeypatch):
    """All commands and the template switch should use Chinese labels."""
    buttons = []
    labels = []
    checkbuttons = []

    def make_widget(widget_type):
        def factory(*args, **kwargs):
            widget = _FakeWidget(widget_type, *args, **kwargs)
            if widget_type == "Label" and "text" in kwargs:
                labels.append(widget)
            return widget

        return factory

    def make_button(*args, **kwargs):
        widget = _FakeWidget("button", *args, **kwargs)
        buttons.append(widget)
        return widget

    def make_checkbutton(*args, **kwargs):
        widget = _FakeWidget("checkbutton", *args, **kwargs)
        checkbuttons.append(widget)
        return widget

    monkeypatch.setattr(gui_module.tk, "StringVar", _FakeStringVar)
    monkeypatch.setattr(gui_module.tk, "BooleanVar", _FakeBooleanVar)
    for widget_name in ("LabelFrame", "Label", "Entry", "Combobox", "Progressbar"):
        monkeypatch.setattr(gui_module.ttk, widget_name, make_widget(widget_name))
    monkeypatch.setattr(gui_module.ttk, "Button", make_button)
    monkeypatch.setattr(gui_module.ttk, "Checkbutton", make_checkbutton)

    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.last_word_template_path = None
    gui.word_template_history = []
    gui.config_file_var = _FakeStringVar()
    gui.setup_conversion_section(_FakeWidget("frame"))

    assert [widget.kwargs["text"] for widget in buttons] == [
        "浏览...",
        "另存为...",
        "选择...",
        "清除",
        "打开配置...",
        "编辑配置...",
        "转换为 Word",
    ]
    assert [widget.kwargs["text"] for widget in labels] == [
        "Markdown 文件：",
        "输出文件：",
        "当前配置：",
    ]
    assert [widget.kwargs["text"] for widget in checkbuttons] == ["使用 Word 模板"]


def test_gui_startup_warns_once_for_remembered_invalid_template(tmp_path, monkeypatch):
    """Startup retains an unusable path and schedules one user-visible warning."""
    missing_template = tmp_path / "missing.docx"
    app_state_dir = tmp_path / ".md2docx"
    app_state_dir.mkdir()
    (app_state_dir / "preferences.json").write_text(
        json.dumps({"last_word_template_path": str(missing_template)}),
        encoding="utf-8",
    )
    root = _DeferredRoot()
    warnings = []

    monkeypatch.setattr(gui_module.Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.setattr(gui_module.tk, "StringVar", _FakeStringVar)
    monkeypatch.setattr(
        gui_module.StyleManager,
        "load_packaged_template",
        lambda _name: {},
    )
    monkeypatch.setattr(Md2docxGUI, "load_history", lambda _self: [])
    monkeypatch.setattr(Md2docxGUI, "setup_ui", lambda _self: None)
    monkeypatch.setattr(Md2docxGUI, "refresh_history_list", lambda _self: None)
    monkeypatch.setattr(gui_module, "center_window_on_screen", lambda _root: None)
    monkeypatch.setattr(
        gui_module.messagebox,
        "showwarning",
        lambda title, message, **kwargs: warnings.append((title, message, kwargs)),
    )

    gui = Md2docxGUI(root)
    for callback in root.after_callbacks:
        callback()

    assert gui.last_word_template_path == missing_template
    assert warnings == [
        (
            "Word模板读取提示",
            f"上次记录的Word模板无法使用，但路径已保留：\n\n"
            f"上次记录的模板不存在：{missing_template}",
            {"parent": root},
        )
    ]


def test_gui_rejects_invalid_word_template_before_starting_thread(tmp_path, monkeypatch):
    """Invalid template paths should show an error and never start conversion."""
    input_path = tmp_path / "input.md"
    output_path = tmp_path / "output.docx"
    invalid_path = tmp_path / "template.txt"
    input_path.write_text("# Input\n", encoding="utf-8")
    invalid_path.write_text("not a docx", encoding="utf-8")
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = object()
    gui.input_var = _FakeStringVar(str(input_path))
    gui.output_var = _FakeStringVar(str(output_path))
    gui.word_template_var = _FakeStringVar(str(invalid_path))
    errors = []
    started = []
    monkeypatch.setattr(
        gui_module.messagebox,
        "showerror",
        lambda title, message, **kwargs: errors.append((title, message, kwargs)),
    )
    monkeypatch.setattr(
        gui_module.threading,
        "Thread",
        lambda **kwargs: started.append(kwargs),
    )

    gui.convert_file()

    assert errors
    assert ".docx" in errors[0][1]
    assert started == []


def test_gui_passes_selected_word_template_to_background_conversion(tmp_path, monkeypatch):
    """A selected template should be captured in the background thread arguments."""
    input_path = tmp_path / "input.md"
    output_path = tmp_path / "output.docx"
    template_path = tmp_path / "template.docx"
    input_path.write_text("# Input\n", encoding="utf-8")
    template_path.write_bytes(b"template")
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = object()
    gui.input_var = _FakeStringVar(str(input_path))
    gui.output_var = _FakeStringVar(str(output_path))
    gui.word_template_var = _FakeStringVar(str(template_path))
    captured = {}

    class FakeThread:
        def __init__(self, *, target, args):
            captured["target"] = target
            captured["args"] = args

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(gui_module.threading, "Thread", FakeThread)

    gui.convert_file()

    assert captured["args"] == (str(input_path), str(output_path), str(template_path))
    assert captured["started"] is True


def test_gui_disabled_word_template_skips_validation_and_worker_argument(
    tmp_path: Path, monkeypatch
):
    """Turning template use off should preserve its path but omit it this time."""
    input_path = tmp_path / "input.md"
    output_path = tmp_path / "output.docx"
    invalid_template_path = tmp_path / "missing-template.txt"
    input_path.write_text("# Input\n", encoding="utf-8")
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = object()
    gui.input_var = _FakeStringVar(str(input_path))
    gui.output_var = _FakeStringVar(str(output_path))
    gui.word_template_var = _FakeStringVar(str(invalid_template_path))
    gui.use_word_template_var = _FakeBooleanVar(False)
    captured = {}
    errors = []

    class FakeThread:
        def __init__(self, *, target, args):
            captured["target"] = target
            captured["args"] = args

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(gui_module.threading, "Thread", FakeThread)
    monkeypatch.setattr(
        gui_module.messagebox,
        "showerror",
        lambda title, message, **kwargs: errors.append((title, message, kwargs)),
    )

    gui.convert_file()

    assert gui.word_template_var.get() == str(invalid_template_path)
    assert captured["args"] == (str(input_path), str(output_path))
    assert captured["started"] is True
    assert errors == []


def test_main_validation_errors_are_parented_to_root(monkeypatch):
    """Validation popups should belong to the active main window."""
    root = object()
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = root
    gui.input_var = _FakeStringVar("")
    gui.output_var = _FakeStringVar("")
    captured = {}
    monkeypatch.setattr(
        gui_module.messagebox,
        "showerror",
        lambda title, message, **kwargs: captured.update(kwargs),
    )

    gui.convert_file()

    assert captured["parent"] is root


@pytest.mark.parametrize(
    ("confirm_overwrite", "should_start"),
    [(False, False), (True, True)],
)
def test_gui_confirms_before_overwriting_existing_output(
    tmp_path: Path,
    monkeypatch,
    confirm_overwrite: bool,
    should_start: bool,
):
    """An existing output should require explicit confirmation before conversion."""
    input_path = tmp_path / "input.md"
    output_path = tmp_path / "output.docx"
    input_path.write_text("# Input\n", encoding="utf-8")
    output_path.write_text("existing", encoding="utf-8")

    root = object()
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = root
    gui.input_var = _FakeStringVar(str(input_path))
    gui.output_var = _FakeStringVar(str(output_path))
    captured = {}

    def askyesno(title, message, **kwargs):
        captured["title"] = title
        captured["message"] = message
        captured.update(kwargs)
        return confirm_overwrite

    class FakeThread:
        def __init__(self, *, target, args):
            captured["thread_args"] = args
            self.daemon = False

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(gui_module.messagebox, "askyesno", askyesno)
    monkeypatch.setattr(gui_module.threading, "Thread", FakeThread)

    gui.convert_file()

    assert captured["title"] == "确认覆盖"
    assert str(output_path) in captured["message"]
    assert captured["parent"] is root
    assert captured["default"] == gui_module.messagebox.NO
    assert captured.get("started", False) is should_start
    if should_start:
        assert captured["thread_args"] == (str(input_path), str(output_path))
    else:
        assert "thread_args" not in captured


def test_gui_defaults_to_packaged_template_when_no_config_preference(tmp_path: Path):
    """Missing preferences should use built-in defaults without inventing a file."""
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = tmp_path / "preferences.json"
    gui.packaged_default_config = {"document": {"page_size": "A4"}}

    document, error = gui.load_initial_config_document()

    assert document.current_path is None
    assert document.saved_config == {"document": {"page_size": "A4"}}
    assert error is None


def test_gui_persists_and_loads_last_config_path(tmp_path: Path):
    """The last successfully used config should survive across app starts."""
    selected_config = tmp_path / "custom.yaml"
    selected_config.write_text("document:\n  auto_fix_tables: true\n", encoding="utf-8")

    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = tmp_path / "preferences.json"
    gui.packaged_default_config = {"document": {"auto_fix_tables": False}}

    assert gui.save_last_config_path(selected_config) is True
    document, error = gui.load_initial_config_document()

    assert json.loads(gui.preferences_file.read_text(encoding="utf-8")) == {
        "last_config_path": str(selected_config)
    }
    assert document.current_path == selected_config
    assert document.saved_config["document"]["auto_fix_tables"] is True
    assert error is None


def test_gui_loads_legacy_config_file_preference(tmp_path: Path):
    """Existing installations should migrate the former preference key."""
    selected_config = tmp_path / "legacy.yaml"
    selected_config.write_text("table:\n  layout: three_line\n", encoding="utf-8")
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"config_file": str(selected_config)}),
        encoding="utf-8",
    )

    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    assert gui.load_last_config_path() == selected_config


def test_gui_missing_last_config_reports_error_and_uses_defaults(tmp_path: Path):
    """A stale preference should produce a warning payload and a usable document."""
    missing_config = tmp_path / "missing.yaml"
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"last_config_path": str(missing_config)}),
        encoding="utf-8",
    )

    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file
    gui.packaged_default_config = {"document": {"page_size": "A4"}}

    document, error = gui.load_initial_config_document()

    assert document.current_path is None
    assert document.saved_config["document"]["page_size"] == "A4"
    assert str(missing_config) in error


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
    gui.packaged_default_config = {"document": {"auto_fix_tables": False}}
    gui.config_document = ConfigDocument.from_defaults(gui.packaged_default_config)
    gui.config_file_var = _FakeStringVar("内置默认（未关联文件）")
    gui.status_var = _FakeStringVar()
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)

    gui.browse_config_file()

    assert gui.config_file_var.get() == str(selected_config)
    assert json.loads(gui.preferences_file.read_text(encoding="utf-8")) == {
        "last_config_path": str(selected_config)
    }
    assert gui.config_document.current_path == selected_config
    assert gui.config_document.saved_config["document"]["auto_fix_tables"] is True
    assert gui.status_var.get() == f"已打开配置：{selected_config}"


def test_gui_invalid_browse_keeps_document_and_preference(tmp_path: Path, monkeypatch):
    """A failed open must not replace the current document or remembered path."""
    selected_config = tmp_path / "selected.yaml"
    selected_config.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text("- not-a-mapping\n", encoding="utf-8")
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = tmp_path / "preferences.json"
    gui.packaged_default_config = {"table": {"layout": "accent_grid"}}
    gui.config_document = ConfigDocument.load(selected_config, gui.packaged_default_config)
    gui.config_file_var = _FakeStringVar(str(selected_config))
    gui.status_var = _FakeStringVar()
    gui.save_last_config_path(selected_config)
    original_document = gui.config_document
    original_preferences = gui.preferences_file.read_text(encoding="utf-8")
    errors = []
    monkeypatch.setattr(
        gui_module.filedialog,
        "askopenfilename",
        lambda **_kwargs: str(invalid_config),
    )
    monkeypatch.setattr(
        gui_module.messagebox,
        "showerror",
        lambda title, message, **_kwargs: errors.append((title, message)),
    )

    gui.browse_config_file()

    assert gui.config_document is original_document
    assert gui.config_file_var.get() == str(selected_config)
    assert gui.preferences_file.read_text(encoding="utf-8") == original_preferences
    assert errors and errors[0][0] == "配置读取失败"


def test_gui_conversion_uses_saved_config_not_dirty_draft(monkeypatch):
    """Conversions must ignore unsaved editor values."""
    from md2docx.mermaid_converter import MermaidReport
    from md2docx.omml_converter import FormulaReport
    captured = {}

    class FakeConverter:
        mermaid_report = MermaidReport()
        formula_report = FormulaReport()

        def __init__(
            self,
            *,
            style_config=None,
            config_override=None,
            config_data=None,
        ):
            captured["style_config"] = style_config
            captured["config_override"] = config_override
            captured["config_data"] = config_data

        def convert(self, input_file, output_file):
            captured["convert"] = (input_file, output_file)

    monkeypatch.setattr(gui_module, "Converter", FakeConverter)
    monkeypatch.setattr(gui_module.messagebox, "showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)

    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = _ImmediateRoot()
    gui.progress = _FakeProgress()
    gui.status_var = _FakeStringVar()
    gui.config_document = ConfigDocument.from_defaults(
        {
            "document": {"auto_fix_tables": True},
            "table": {"layout": "accent_grid"},
        }
    )
    gui.config_document.update_draft(
        {
            "document": {"auto_fix_tables": False},
            "table": {"layout": "three_line"},
        }
    )
    gui.history = []
    gui.add_to_history = lambda *args: None
    gui.refresh_history_list = lambda: None

    gui._do_conversion("input.md", "output.docx")

    assert captured["style_config"] is None
    assert captured["config_override"] is None
    assert captured["config_data"]["table"]["layout"] == "accent_grid"
    assert captured["config_data"]["document"]["auto_fix_tables"] is True
    assert captured["convert"] == ("input.md", "output.docx")
    assert gui.progress.events == [
        ("configure", {"mode": "indeterminate", "value": 0}),
        ("start",),
        ("stop",),
        ("configure", {"mode": "determinate", "value": 100}),
    ]


def test_gui_formats_empty_conversion_errors_with_exception_type():
    """The UI should show a useful type when an exception has no message."""
    assert Md2docxGUI.format_conversion_error(NotImplementedError()) == "NotImplementedError"
    assert Md2docxGUI.format_conversion_error(ValueError("bad template")) == (
        "ValueError: bad template"
    )


def test_gui_close_preserves_root_when_editor_close_is_cancelled():
    """Closing the app must honor a config editor's cancel decision."""
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = Mock()
    editor_window = Mock()
    editor_window.winfo_exists.return_value = True
    gui.config_editor = Mock(window=editor_window)

    gui.close()

    gui.config_editor.close.assert_called_once_with()
    gui.root.destroy.assert_not_called()


def test_gui_build_effective_config_returns_an_independent_saved_snapshot():
    """Building conversion data should neither expose nor update GUI state."""
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.config_document = ConfigDocument.from_defaults(
        {"document": {"auto_fix_tables": True}}
    )

    effective_config = gui.build_effective_conversion_config()
    effective_config["document"]["auto_fix_tables"] = False

    assert gui.config_document.saved_config["document"]["auto_fix_tables"] is True


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
    alignment_rule = gui_module.resolve_field_widget_rule(("paragraph", "alignment"))
    table_rule = gui_module.resolve_field_widget_rule(
        ("table", "column_width_strategy")
    )

    assert page_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert page_rule.readonly is True
    assert page_rule.options == ("A4", "A3", "Letter（信纸）")
    assert page_rule.value_mapping[-1] == ("Letter（信纸）", "Letter")
    assert alignment_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert alignment_rule.readonly is True
    assert alignment_rule.options == ("左对齐", "居中", "右对齐", "两端对齐")
    assert table_rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert table_rule.readonly is True
    assert table_rule.options == ("按内容分配", "均衡分配")
    assert table_rule.value_mapping == (
        ("按内容分配", "content-weighted"),
        ("均衡分配", "balanced"),
    )


def test_config_editor_rule_maps_table_layout_presets_to_stable_values():
    """Table layout should show Chinese presets while retaining YAML-safe values."""
    rule = gui_module.resolve_field_widget_rule(("table", "layout"))

    assert rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert rule.readonly is True
    assert rule.options == ("主题网格表（当前默认）", "三线表", "简洁网格表")
    assert rule.value_mapping == (
        ("主题网格表（当前默认）", "accent_grid"),
        ("三线表", "three_line"),
        ("简洁网格表", "plain_grid"),
    )


def test_config_editor_resolves_table_layout_label():
    """The table tab should use a clear label for the layout preset field."""
    assert (
        gui_module.resolve_field_label(("table", "layout"), "layout", "accent_grid")
        == "表格样式"
    )


def test_config_editor_translates_packaged_default_fields_and_tips():
    """Every default config field should show a Chinese label with field help."""
    default_config = load_yaml_config(Path("md2docx/templates/default.yaml"))
    untranslated = []
    missing_tips = []

    for path, value in _iter_leaf_config_paths(default_config):
        field_name = path[-1]
        label = gui_module.resolve_field_label(path, field_name, value)
        tip = gui_module.resolve_field_tip(path, value)
        if label == field_name:
            untranslated.append(".".join(path))
        if not tip:
            missing_tips.append(".".join(path))

    assert untranslated == []
    assert missing_tips == []


def test_config_editor_create_field_tip_widget_keeps_tooltip_alive(monkeypatch):
    """Field tips should render a visible help marker with retained tooltip state."""
    created_tooltips = []

    def make_widget(widget_type):
        def factory(*args, **kwargs):
            return _FakeWidget(widget_type, *args, **kwargs)

        return factory

    class FakeTooltip:
        def __init__(self, widget, text):
            self.widget = widget
            self.text = text
            created_tooltips.append(self)

    monkeypatch.setattr(gui_module.ttk, "Label", make_widget("label"))
    monkeypatch.setattr(gui_module, "Tooltip", FakeTooltip, raising=False)

    editor = gui_module.ConfigEditorWindow.__new__(gui_module.ConfigEditorWindow)
    editor.tooltips = []

    widget = editor.create_field_tip_widget(object(), "设置 Word 第一节页面尺寸。")

    assert widget.widget_type == "label"
    assert widget.kwargs["text"] == "?"
    assert created_tooltips[0].widget is widget
    assert created_tooltips[0].text == "设置 Word 第一节页面尺寸。"
    assert editor.tooltips == created_tooltips


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
    assert readonly_combo.kwargs["values"] == ("A4", "A3", "Letter（信纸）")

    assert entry.widget_type == "entry"
    assert len(editor.field_bindings) == 5


def test_config_editor_table_layout_widget_displays_and_saves_mapped_values(monkeypatch):
    """Table style presets should display Chinese labels and save stable YAML values."""
    def make_widget(widget_type):
        def factory(*args, **kwargs):
            return _FakeWidget(widget_type, *args, **kwargs)

        return factory

    monkeypatch.setattr(gui_module.tk, "StringVar", _FakeStringVar)
    monkeypatch.setattr(gui_module.ttk, "Combobox", make_widget("combobox"))

    editor = gui_module.ConfigEditorWindow.__new__(gui_module.ConfigEditorWindow)
    editor.field_bindings = []
    editor.current_config = {"table": {"layout": "accent_grid"}}

    widget = editor.create_field_widget(
        object(),
        ("table", "layout"),
        "accent_grid",
        "accent_grid",
    )

    assert widget.widget_type == "combobox"
    assert widget.kwargs["textvariable"].get() == "主题网格表（当前默认）"
    assert widget.kwargs["values"] == ("主题网格表（当前默认）", "三线表", "简洁网格表")

    editor.field_bindings[0].variable.set("三线表")

    assert editor.collect_config()["table"]["layout"] == "three_line"


def _make_config_editor(document: ConfigDocument):
    """Build a non-Tk editor shell for document workflow tests."""
    editor = gui_module.ConfigEditorWindow.__new__(gui_module.ConfigEditorWindow)
    editor.window = Mock()
    editor.status_var = _FakeStringVar()
    editor.source_var = _FakeStringVar()
    editor.document = document
    editor.packaged_default_config = {"table": {"layout": "accent_grid"}}
    editor.current_config = document.draft_config
    editor.on_saved = None
    return editor


def test_unsaved_changes_dialog_uses_save_discard_cancel_choices(monkeypatch):
    """The dirty-close prompt should expose explicit user actions."""
    captured = {}

    def choose(**kwargs):
        captured.update(kwargs)
        return "discard"

    monkeypatch.setattr(gui_module, "ask_three_way_choice", choose, raising=False)

    result = gui_module.ask_unsaved_changes(parent=object(), path=Path("config.yaml"))

    assert result == "discard"
    assert captured["choices"] == (
        ("save", "保存"),
        ("discard", "放弃"),
        ("cancel", "取消"),
    )


def test_external_change_dialog_uses_reload_overwrite_cancel_choices(monkeypatch):
    """The conflict prompt should make overwrite an explicit decision."""
    captured = {}

    def choose(**kwargs):
        captured.update(kwargs)
        return "reload"

    monkeypatch.setattr(gui_module, "ask_three_way_choice", choose, raising=False)

    result = gui_module.ask_external_change(parent=object(), path=Path("config.yaml"))

    assert result == "reload"
    assert captured["choices"] == (
        ("reload", "重新载入"),
        ("overwrite", "覆盖"),
        ("cancel", "取消"),
    )


def test_config_editor_save_as_switches_current_file(tmp_path: Path, monkeypatch):
    """Save As should switch the document only after writing the selected file."""
    target = tmp_path / "saved.yaml"
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    saved_paths = []
    editor.on_saved = saved_paths.append
    monkeypatch.setattr(
        gui_module.filedialog,
        "asksaveasfilename",
        lambda **_kwargs: str(target),
    )
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)

    assert editor.save_config_as() is True

    assert document.current_path == target
    assert document.saved_config["table"]["layout"] == "three_line"
    assert document.dirty is False
    assert saved_paths == [target]
    assert editor.source_var.get() == str(target)


def test_config_editor_save_as_current_path_uses_external_change_dialog(
    tmp_path: Path,
    monkeypatch,
):
    """Selecting the current file in Save As must retain conflict choices."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    path.write_text("table:\n  layout: plain_grid\n", encoding="utf-8")
    choices = []
    monkeypatch.setattr(
        gui_module.filedialog,
        "asksaveasfilename",
        lambda **_kwargs: str(path),
    )
    monkeypatch.setattr(
        gui_module,
        "ask_external_change",
        lambda **kwargs: choices.append(kwargs["path"]) or "cancel",
        raising=False,
    )
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)

    assert editor.save_config_as() is False

    assert choices == [path]
    assert load_yaml_config(path)["table"]["layout"] == "plain_grid"
    assert document.draft_config["table"]["layout"] == "three_line"
    assert document.dirty is True


def test_config_editor_save_overwrites_current_file(tmp_path: Path, monkeypatch):
    """Save should write the draft without changing the associated file."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    saved_paths = []
    editor.on_saved = saved_paths.append
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)

    assert editor.save_config() is True

    assert document.current_path == path
    assert document.saved_config["table"]["layout"] == "three_line"
    assert load_yaml_config(path)["table"]["layout"] == "three_line"
    assert document.dirty is False
    assert saved_paths == [path]


def test_config_editor_restore_defaults_only_changes_draft(tmp_path: Path, monkeypatch):
    """Restoring built-in defaults should require a later save to affect conversion."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: three_line\n", encoding="utf-8")
    document = ConfigDocument.load(path, {"table": {"layout": "accent_grid"}})
    editor = _make_config_editor(document)
    editor.load_config_data = lambda config, source: setattr(editor, "current_config", config)
    monkeypatch.setattr(gui_module.messagebox, "askyesno", lambda *args, **kwargs: True)

    editor.restore_packaged_defaults()

    assert document.saved_config["table"]["layout"] == "three_line"
    assert document.draft_config["table"]["layout"] == "accent_grid"
    assert document.dirty is True


def test_config_editor_close_cancel_keeps_dirty_editor_open(monkeypatch):
    """Cancel should preserve both the editor window and unsaved draft."""
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    monkeypatch.setattr(
        gui_module,
        "ask_unsaved_changes",
        lambda **_kwargs: "cancel",
        raising=False,
    )

    editor.close()

    editor.window.destroy.assert_not_called()
    assert document.draft_config["table"]["layout"] == "three_line"
    assert document.dirty is True


def test_config_editor_close_discard_resets_draft_and_closes(monkeypatch):
    """Discard should restore the saved snapshot before closing the editor."""
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    monkeypatch.setattr(
        gui_module,
        "ask_unsaved_changes",
        lambda **_kwargs: "discard",
        raising=False,
    )

    editor.close()

    assert document.draft_config == document.saved_config
    assert document.dirty is False
    editor.window.destroy.assert_called_once_with()


def test_config_editor_close_save_commits_draft_and_closes(tmp_path: Path, monkeypatch):
    """Save from the dirty-close prompt should commit before closing."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    monkeypatch.setattr(
        gui_module,
        "ask_unsaved_changes",
        lambda **_kwargs: "save",
        raising=False,
    )
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)

    editor.close()

    assert load_yaml_config(path)["table"]["layout"] == "three_line"
    assert document.dirty is False
    editor.window.grab_release.assert_called_once_with()
    editor.window.destroy.assert_called_once_with()


def test_config_editor_close_can_discard_invalid_form_values(monkeypatch):
    """An invalid draft must still offer a way to abandon the editor."""
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: (_ for _ in ()).throw(ValueError("bad value"))
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        gui_module,
        "ask_unsaved_changes",
        lambda **_kwargs: "discard",
        raising=False,
    )

    editor.close()

    assert document.draft_config == document.saved_config
    assert document.dirty is False
    editor.window.destroy.assert_called_once_with()


def test_config_editor_external_change_can_overwrite(tmp_path: Path, monkeypatch):
    """Explicit overwrite should save the current draft over an external edit."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    path.write_text("table:\n  layout: plain_grid\n", encoding="utf-8")
    monkeypatch.setattr(
        gui_module,
        "ask_external_change",
        lambda **_kwargs: "overwrite",
        raising=False,
    )
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)

    assert editor.save_config() is True

    assert document.saved_config["table"]["layout"] == "three_line"
    assert document.dirty is False


def test_config_editor_external_change_can_reload(tmp_path: Path, monkeypatch):
    """Reload should adopt the external version and discard the current draft."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    editor.load_config_data = lambda config, source: setattr(editor, "current_config", config)
    path.write_text("table:\n  layout: plain_grid\n", encoding="utf-8")
    monkeypatch.setattr(
        gui_module,
        "ask_external_change",
        lambda **_kwargs: "reload",
        raising=False,
    )
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)

    assert editor.save_config() is False

    assert document.saved_config["table"]["layout"] == "plain_grid"
    assert document.draft_config == document.saved_config
    assert document.dirty is False


def test_config_editor_external_change_cancel_preserves_both_versions(
    tmp_path: Path,
    monkeypatch,
):
    """Cancel should keep the external file and the unsaved draft untouched."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    editor = _make_config_editor(document)
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    path.write_text("table:\n  layout: plain_grid\n", encoding="utf-8")
    monkeypatch.setattr(
        gui_module,
        "ask_external_change",
        lambda **_kwargs: "cancel",
        raising=False,
    )
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)

    assert editor.save_config() is False

    assert load_yaml_config(path)["table"]["layout"] == "plain_grid"
    assert document.saved_config["table"]["layout"] == "accent_grid"
    assert document.draft_config["table"]["layout"] == "three_line"
    assert document.dirty is True


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
