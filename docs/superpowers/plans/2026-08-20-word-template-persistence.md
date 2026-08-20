# Word Template Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remember the last Word `.docx` template selected in the desktop GUI and restore it on the next launch without overwriting other preferences.

**Architecture:** Extend `Md2docxGUI`'s existing JSON preference file with a `last_word_template_path` key. A shared preference loader returns a dictionary and every writer reads, mutates, and rewrites that dictionary; template loading returns both the retained expanded path and an optional startup warning payload. The GUI initializes the read-only field from that path, persists browse/clear actions, and continues to validate the path immediately before conversion.

**Tech Stack:** Python 3, Tkinter, `pathlib.Path`, JSON, pytest, `uv`.

---

### Task 1: Add failing GUI preference tests

**Files:**
- Modify: `tests/test_gui.py` near the existing Word template and preference tests
- Test: `tests/test_gui.py`

- [ ] **Step 1: Write the failing tests**

Add these tests after `test_word_template_dialog_is_parented_and_can_be_cleared`:

```python
def test_gui_browse_word_template_persists_without_dropping_other_preferences(
    tmp_path: Path, monkeypatch
):
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
    }


def test_gui_loads_last_word_template_path_and_reports_stale_file(tmp_path: Path):
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


def test_gui_loads_existing_last_word_template_without_warning(tmp_path: Path):
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


def test_gui_clear_word_template_removes_only_template_preference(tmp_path: Path):
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps(
            {
                "last_config_path": str(tmp_path / "config.yaml"),
                "config_file": str(tmp_path / "legacy.yaml"),
                "last_word_template_path": str(tmp_path / "template.docx"),
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
    }


def test_gui_save_last_config_path_merges_last_word_template(tmp_path: Path):
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
```

Add this invalid-suffix case after the stale-file test:

```python
def test_gui_invalid_last_word_template_is_retained_and_warned(tmp_path: Path):
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
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
uv run pytest tests/test_gui.py -k 'word_template and (persist or loads or clear or invalid)' -q
```

Expected: FAIL because `Md2docxGUI` has no `load_last_word_template` method and browse/clear do not write `last_word_template_path`.

### Task 2: Implement merged preference storage and startup restoration

**Files:**
- Modify: `md2docx/gui.py:1435-1470` (`Md2docxGUI.__init__`)
- Modify: `md2docx/gui.py:1540-1570` (`setup_conversion_section`)
- Modify: `md2docx/gui.py:1705-1725` (`browse_word_template`, `clear_word_template`)
- Modify: `md2docx/gui.py:1790-1845` (preference loading and saving methods)

- [ ] **Step 1: Run GitNexus impact analysis before editing existing symbols**

Run `mcp__gitnexus__impact` for `Md2docxGUI.__init__`, `Md2docxGUI.setup_conversion_section`, `Md2docxGUI.browse_word_template`, `Md2docxGUI.clear_word_template`, and `Md2docxGUI.save_last_config_path` with `direction="upstream"`, `repo="md2docx"`, and `file_path="md2docx/gui.py"`. Record any HIGH or CRITICAL risk and notify the user before proceeding if returned.

- [ ] **Step 2: Add shared preference helpers and template loading**

Insert these methods before `load_last_config_path`:

```python
    def load_preferences(self) -> Dict[str, Any]:
        """Load the JSON preferences object, falling back to an empty mapping."""
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    return loaded
        except Exception:
            pass
        return {}

    def save_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Persist the complete merged preferences object."""
        try:
            self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preferences_file, "w", encoding="utf-8") as handle:
                json.dump(preferences, handle, indent=2, ensure_ascii=False)
        except Exception as exc:
            print(f"Failed to save preferences: {exc}")
            return False
        return True

    def load_last_word_template(self) -> Tuple[Optional[Path], Optional[str]]:
        """Load the remembered template and describe a stale or invalid path."""
        raw_path = self.load_preferences().get("last_word_template_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None, None

        template_path = Path(raw_path).expanduser()
        if template_path.suffix.lower() != ".docx":
            return template_path, f"上次记录的模板不是 .docx 文件：{template_path}"
        if not template_path.is_file():
            return template_path, f"上次记录的模板不存在：{template_path}"
        return template_path, None

    def save_last_word_template_path(self, template_path: Path) -> bool:
        """Merge and persist the selected Word template path."""
        preferences = self.load_preferences()
        preferences["last_word_template_path"] = str(template_path.expanduser())
        return self.save_preferences(preferences)

    def clear_last_word_template_path(self) -> bool:
        """Remove only the remembered Word template preference."""
        preferences = self.load_preferences()
        preferences.pop("last_word_template_path", None)
        return self.save_preferences(preferences)
```

- [ ] **Step 3: Merge existing config writes**

Replace `save_last_config_path` with:

```python
    def save_last_config_path(self, config_path: Path) -> bool:
        """Persist the last successfully opened or saved config path."""
        preferences = self.load_preferences()
        preferences["last_config_path"] = str(config_path.expanduser())
        return self.save_preferences(preferences)
```

Update `load_last_config_path` to read `loaded = self.load_preferences()` and retain its existing `last_config_path` then legacy `config_file` lookup.

- [ ] **Step 4: Load and display the remembered template at startup**

In `__init__`, immediately after assigning `self.preferences_file`, add:

```python
        (
            self.last_word_template_path,
            self.startup_word_template_error,
        ) = self.load_last_word_template()
```

After the existing `startup_config_error` warning block, add:

```python
        if self.startup_word_template_error:
            self.root.after(
                0,
                lambda error=self.startup_word_template_error: messagebox.showwarning(
                    "Word模板读取提示",
                    f"上次记录的Word模板无法使用，但路径已保留：\n\n{error}",
                    parent=self.root,
                ),
            )
```

Initialize the template variable in `setup_conversion_section` with:

```python
        self.word_template_var = tk.StringVar(
            value=(
                str(self.last_word_template_path)
                if getattr(self, "last_word_template_path", None) is not None
                else ""
            )
        )
```

- [ ] **Step 5: Persist browse and clear actions without blocking conversion**

Replace `browse_word_template`'s non-empty branch with:

```python
        if filename:
            template_path = Path(filename).expanduser()
            self.word_template_var.set(str(template_path))
            if not self.save_last_word_template_path(template_path) and hasattr(
                self, "preferences_file"
            ):
                messagebox.showwarning(
                    "偏好保存失败",
                    "Word模板已选择，但无法记录为下次启动模板。",
                    parent=self.dialog_parent(),
                )
```

Replace `clear_word_template` with:

```python
        self.word_template_var.set("")
        if not self.clear_last_word_template_path() and hasattr(self, "preferences_file"):
            messagebox.showwarning(
                "偏好保存失败",
                "Word模板已清除，但无法更新下次启动偏好。",
                parent=self.dialog_parent(),
            )
```

Keep `convert_file` unchanged so it still expands, validates, and snapshots the selected path before creating the worker thread.

- [ ] **Step 6: Run the focused tests to verify they pass**

Run:

```bash
uv run pytest tests/test_gui.py -k 'word_template or preference or config' -q
```

Expected: PASS, including the new persistence, merge, stale-path, and clear-only-template tests.

### Task 3: Regression verification and change-scope review

**Files:**
- Modify: none
- Test: `tests/test_gui.py`, full repository test suite

- [ ] **Step 1: Run all GUI tests**

Run `uv run pytest tests/test_gui.py -q` and expect all GUI tests to pass.

- [ ] **Step 2: Run the full suite and whitespace validation**

Run `uv run pytest -q` followed by `git diff --check`; expect zero test failures and no whitespace errors.

- [ ] **Step 3: Run GitNexus change detection before committing**

Run `mcp__gitnexus__detect_changes` with `repo="md2docx"` and `scope="all"`. Confirm only the planned GUI methods, tests, and the implementation plan/design documentation are affected; investigate any unexpected process or symbol before declaring completion.

- [ ] **Step 4: Review the final diff**

Run `git diff -- md2docx/gui.py tests/test_gui.py docs/superpowers/plans/2026-08-20-word-template-persistence.md` and verify that the JSON merge behavior preserves `last_config_path` and `config_file`, stale template paths remain visible, and conversion validation/snapshot code is unchanged.
