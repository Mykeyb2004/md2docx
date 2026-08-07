# GUI Configuration Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the GUI's competing configuration sources with one file-backed document model that restores the last successful configuration and protects unsaved work.

**Architecture:** Add a pure Python `ConfigDocument` responsible for saved/draft state, file association, conflict detection, and transactional state updates. Keep YAML serialization in `config_utils.py`; keep Tk dialogs and widget orchestration in `gui.py`. The converter receives a clone of `ConfigDocument.saved_config`.

**Tech Stack:** Python 3.8+, dataclasses, hashlib, pathlib, tempfile/os.replace, Tkinter, PyYAML, pytest, uv.

---

### Task 1: Configuration Document State

**Files:**
- Create: `md2docx/config_document.py`
- Create: `tests/test_config_document.py`

- [ ] **Step 1: Write failing state-transition tests**

```python
def test_update_and_discard_draft_are_isolated():
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})
    document.update_draft({"table": {"layout": "three_line"}})
    assert document.dirty is True
    assert document.saved_config["table"]["layout"] == "accent_grid"
    document.discard_draft()
    assert document.draft_config == document.saved_config
    assert document.dirty is False
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `uv run pytest tests/test_config_document.py -q`

Expected: collection fails because `md2docx.config_document` does not exist.

- [ ] **Step 3: Implement `ConfigDocument`**

```python
class MissingConfigPathError(RuntimeError):
    pass


class ExternalConfigChangeError(RuntimeError):
    pass


def _file_digest(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class ConfigDocument:
    current_path: Optional[Path]
    saved_config: Dict[str, Any]
    draft_config: Dict[str, Any]
    dirty: bool = False
    _disk_digest: Optional[str] = field(default=None, repr=False, compare=False)

    @classmethod
    def from_defaults(cls, defaults: Dict[str, Any]) -> "ConfigDocument":
        saved = clone_config(defaults)
        return cls(None, saved, clone_config(saved))

    @classmethod
    def load(cls, path: Path, defaults: Dict[str, Any]) -> "ConfigDocument":
        saved = merge_config(defaults, load_yaml_config(path))
        return cls(path, saved, clone_config(saved), _disk_digest=_file_digest(path))

    def update_draft(self, config: Dict[str, Any]) -> None:
        self.draft_config = clone_config(config)
        self.dirty = self.draft_config != self.saved_config

    def discard_draft(self) -> None:
        self.draft_config = clone_config(self.saved_config)
        self.dirty = False

    def reload(self, defaults: Dict[str, Any]) -> None:
        if self.current_path is None:
            raise MissingConfigPathError("Configuration has no file path")
        loaded = type(self).load(self.current_path, defaults)
        self.saved_config = loaded.saved_config
        self.draft_config = loaded.draft_config
        self.dirty = False
        self._disk_digest = loaded._disk_digest

    def save(self, *, overwrite: bool = False) -> None:
        if self.current_path is None:
            raise MissingConfigPathError("Configuration has no file path")
        if not overwrite and _file_digest(self.current_path) != self._disk_digest:
            raise ExternalConfigChangeError(str(self.current_path))
        save_yaml_config(self.current_path, self.draft_config)
        self.saved_config = clone_config(self.draft_config)
        self.dirty = False
        self._disk_digest = _file_digest(self.current_path)

    def save_as(self, path: Path) -> None:
        save_yaml_config(path, self.draft_config)
        self.current_path = path
        self.saved_config = clone_config(self.draft_config)
        self.dirty = False
        self._disk_digest = _file_digest(path)
```

`load` merges YAML over built-in defaults. `save` raises `MissingConfigPathError` without a path and `ExternalConfigChangeError` when the stored SHA-256 digest differs. All public configuration values are deep copies.

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest tests/test_config_document.py -q`

Expected: all document tests pass.

### Task 2: Atomic YAML Saving

**Files:**
- Modify: `md2docx/config_utils.py`
- Modify: `tests/test_config_utils.py`

- [ ] **Step 1: Add an atomicity regression test**

```python
def test_save_yaml_config_preserves_existing_file_when_replace_fails(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("original: true\n", encoding="utf-8")
    monkeypatch.setattr(config_utils.os, "replace", Mock(side_effect=OSError("blocked")))
    with pytest.raises(OSError, match="blocked"):
        save_yaml_config(path, {"replacement": True})
    assert path.read_text(encoding="utf-8") == "original: true\n"
```

- [ ] **Step 2: Verify the test fails**

Run: `uv run pytest tests/test_config_utils.py -q`

Expected: failure because the current implementation writes the destination directly.

- [ ] **Step 3: Replace direct writes with a same-directory temporary file**

```python
temporary_path: Optional[Path] = None
try:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
        suffix=".tmp", delete=False,
    ) as handle:
        temporary_path = Path(handle.name)
        handle.write(dump_yaml_config(config))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, path)
finally:
    if temporary_path is not None and temporary_path.exists():
        temporary_path.unlink()
```

- [ ] **Step 4: Run configuration utility and document tests**

Run: `uv run pytest tests/test_config_utils.py tests/test_config_document.py -q`

Expected: all tests pass.

### Task 3: Main Window Configuration Ownership

**Files:**
- Modify: `md2docx/gui.py`
- Modify: `tests/test_gui.py`

- [ ] **Step 1: Replace temporary-config tests with startup and transactional-open tests**

```python
def test_gui_loads_last_valid_config_on_startup(tmp_path):
    selected = tmp_path / "selected.yaml"
    selected.write_text("table:\n  layout: three_line\n", encoding="utf-8")
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = tmp_path / "preferences.json"
    gui.preferences_file.write_text(
        json.dumps({"last_config_path": str(selected)}), encoding="utf-8"
    )
    gui.packaged_default_config = {"table": {"layout": "accent_grid"}}
    document, error = gui.load_initial_config_document()
    assert error is None
    assert document.current_path == selected
    assert document.saved_config["table"]["layout"] == "three_line"


def test_gui_invalid_manual_open_keeps_document_and_preference(tmp_path, monkeypatch):
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("- not-a-mapping\n", encoding="utf-8")
    original = ConfigDocument.from_defaults({"document": {"page_size": "A4"}})
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.config_document = original
    gui.packaged_default_config = {"document": {"page_size": "A4"}}
    gui.config_file_var = _FakeStringVar("内置默认（未关联文件）")
    gui.status_var = _FakeStringVar()
    saved_paths = []
    gui.save_last_config_path = saved_paths.append
    monkeypatch.setattr(gui_module.filedialog, "askopenfilename", lambda **_kwargs: str(invalid))
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)
    gui.browse_config_file()
    assert gui.config_document is original
    assert saved_paths == []
```

- [ ] **Step 2: Verify the new GUI tests fail**

Run: `uv run pytest tests/test_gui.py -q`

Expected: failures reference the old temporary active-config fields and preference key.

- [ ] **Step 3: Make `Md2docxGUI` own one `ConfigDocument`**

```python
self.packaged_default_config = StyleManager.load_packaged_template("default")
self.config_document, self.startup_config_error = self.load_initial_config_document()
self.config_file_var = tk.StringVar(value=self.describe_current_config())
```

`load_last_config_path` reads `last_config_path` and the legacy `config_file`. `browse_config_file` loads into a temporary document, swaps only on success, then records the path. Remove `active_config`, `active_config_is_temporary`, `auto_fix_tables_var`, and their helper methods.

- [ ] **Step 4: Simplify the configuration controls**

Render one readonly current-config field plus `打开配置...` and `编辑配置...`. Remove the temporary-config status/clear button and main-window table-fix checkbox. Keep stable grid rows for progress and conversion actions.

- [ ] **Step 5: Run GUI tests**

Run: `uv run pytest tests/test_gui.py -q`

Expected: all main-window configuration tests pass.

### Task 4: Editor Save, Dirty Close, And Conflicts

**Files:**
- Modify: `md2docx/gui.py`
- Modify: `tests/test_gui.py`

- [ ] **Step 1: Add editor workflow tests**

```python
def test_editor_save_as_switches_current_file(tmp_path, monkeypatch):
    target = tmp_path / "saved.yaml"
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})
    editor = ConfigEditorWindow.__new__(ConfigEditorWindow)
    editor.window = object()
    editor.document = document
    editor.status_var = _FakeStringVar()
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    callbacks = []
    editor.on_saved = callbacks.append
    monkeypatch.setattr(gui_module.filedialog, "asksaveasfilename", lambda **_kwargs: str(target))
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)
    editor.save_config_as()
    assert document.current_path == target
    assert document.saved_config["table"]["layout"] == "three_line"
    assert callbacks == [target]


def test_editor_close_cancel_keeps_window_open(monkeypatch):
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})
    editor = ConfigEditorWindow.__new__(ConfigEditorWindow)
    editor.window = Mock()
    editor.document = document
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    monkeypatch.setattr(gui_module, "ask_unsaved_changes", lambda **_kwargs: "cancel")
    editor.close()
    editor.window.destroy.assert_not_called()


def test_editor_external_change_overwrite_saves_draft(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    path.write_text("table:\n  layout: plain_grid\n", encoding="utf-8")
    editor = ConfigEditorWindow.__new__(ConfigEditorWindow)
    editor.window = object()
    editor.document = document
    editor.status_var = _FakeStringVar()
    editor.collect_config = lambda: {"table": {"layout": "three_line"}}
    editor.on_saved = None
    monkeypatch.setattr(gui_module, "ask_external_change", lambda **_kwargs: "overwrite")
    monkeypatch.setattr(gui_module.messagebox, "showerror", lambda *args, **kwargs: None)
    editor.save_config()
    assert load_yaml_config(path)["table"]["layout"] == "three_line"
```

- [ ] **Step 2: Verify the editor tests fail**

Run: `uv run pytest tests/test_gui.py -q`

Expected: failures reference editor methods and decisions not yet implemented.

- [ ] **Step 3: Bind the editor to `ConfigDocument`**

The editor loads `document.draft_config`, updates the draft before decisions, saves to `document.current_path`, and uses Save As when the path is absent. Successful saves invoke the callback after state and path update. Restore defaults calls `document.update_draft(packaged_defaults)` and re-renders.

- [ ] **Step 4: Add explicit three-way Tk dialogs**

```python
decision = ask_three_way_choice(
    parent=self.window,
    title="配置已在磁盘上修改",
    message=f"{path}\n已被其他程序修改。",
    choices=(("reload", "重新载入"), ("overwrite", "覆盖"), ("cancel", "取消")),
)
```

Use the same helper for `save`, `discard`, and `cancel` on dirty close. Only error and conflict paths use modal dialogs.

- [ ] **Step 5: Run GUI tests**

Run: `uv run pytest tests/test_gui.py -q`

Expected: all editor workflow tests pass.

### Task 5: Conversion Isolation And Full Verification

**Files:**
- Modify: `md2docx/gui.py`
- Modify: `tests/test_gui.py`
- Modify: `docs/GUI_GUIDE.md`

- [ ] **Step 1: Assert conversion uses only the saved snapshot**

```python
def test_gui_conversion_uses_saved_config_not_dirty_draft(monkeypatch):
    gui.config_document.update_draft({"table": {"layout": "three_line"}})
    assert gui.build_effective_conversion_config()["table"]["layout"] == "accent_grid"
```

- [ ] **Step 2: Implement the minimal conversion path**

```python
def build_effective_conversion_config(self) -> Dict[str, Any]:
    return clone_config(self.config_document.saved_config)
```

Instantiate `Converter(config_data=config)` so conversion uses the complete saved
snapshot without merging a runtime-directory `default.yaml`. Do not persist
preferences during conversion.

- [ ] **Step 3: Update the GUI guide**

Document opening, automatic startup restoration, direct save, Save As switching, dirty-close decisions, and external-change handling. Remove references to temporary configuration or main-window table repair overrides.

- [ ] **Step 4: Run focused and full tests**

Run: `uv run pytest tests/test_config_document.py tests/test_config_utils.py tests/test_gui.py -q`

Expected: all focused tests pass.

Run: `uv run pytest -q`

Expected: the full suite passes.

- [ ] **Step 5: Inspect affected flows**

Run GitNexus `detect_changes(scope="all", repo="md2docx")`, review every changed symbol and affected process, and correct any unexpected scope before completion.
