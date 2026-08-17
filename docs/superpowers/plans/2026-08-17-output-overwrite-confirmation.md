# Output Overwrite Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent the GUI from silently overwriting an existing DOCX output file by requiring explicit confirmation whose default action is cancellation.

**Architecture:** Keep overwrite policy at the GUI action boundary. `Md2docxGUI.convert_file` validates the paths, checks whether the selected output exists, prompts through `tkinter.messagebox`, and starts the existing worker thread only after confirmation. The CLI and `Converter` public API remain unchanged.

**Tech Stack:** Python 3.10+, Tkinter, pathlib, pytest, uv

---

### Task 1: Add a failing GUI overwrite-confirmation test

**Files:**
- Modify: `tests/test_gui.py:233`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Add the parameterized behavior test**

Place this test after `test_main_validation_errors_are_parented_to_root`:

```python
import pytest


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

    assert captured["title"] == "Confirm Overwrite"
    assert str(output_path) in captured["message"]
    assert captured["parent"] is root
    assert captured["default"] == gui_module.messagebox.NO
    assert captured.get("started", False) is should_start
    if should_start:
        assert captured["thread_args"] == (str(input_path), str(output_path))
    else:
        assert "thread_args" not in captured
```

- [ ] **Step 2: Run the test and verify the red state**

Run:

```bash
uv run pytest tests/test_gui.py::test_gui_confirms_before_overwriting_existing_output -v
```

Expected: FAIL because `convert_file` does not call `messagebox.askyesno` and starts the conversion thread even when confirmation should be declined.

### Task 2: Add the minimal GUI overwrite guard

**Files:**
- Modify: `md2docx/gui.py:1805`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Add the confirmation immediately before thread creation**

Insert this block after the input-file existence validation and before `threading.Thread(...)`:

```python
        output_path = Path(output_file)
        if output_path.exists() and not messagebox.askyesno(
            "Confirm Overwrite",
            f"The output file already exists:\n{output_path}\n\nDo you want to overwrite it?",
            parent=self.dialog_parent(),
            default=messagebox.NO,
        ):
            return
```

Do not change `_do_conversion`, the existing progress behavior, the CLI, or `Converter.convert`.

- [ ] **Step 2: Run the focused test and verify the green state**

Run:

```bash
uv run pytest tests/test_gui.py::test_gui_confirms_before_overwriting_existing_output -v
```

Expected: both parameterized cases PASS.

- [ ] **Step 3: Run adjacent GUI validation tests**

Run:

```bash
uv run pytest tests/test_gui.py -k "main_validation_errors_are_parented_to_root or confirms_before_overwriting_existing_output or gui_conversion_uses_saved_config" -v
```

Expected: all selected tests PASS, including the existing dirty-config and progress assertions.

### Task 3: Verify regressions and affected scope

**Files:**
- Verify: `md2docx/gui.py`
- Verify: `tests/test_gui.py`
- Verify: `md2docx/cli.py`
- Verify: `tests/test_cli.py`

- [ ] **Step 1: Run GUI and CLI regression tests**

Run:

```bash
uv run pytest tests/test_gui.py tests/test_cli.py -v
```

Expected: all GUI and CLI tests PASS; CLI still refuses existing files unless `--overwrite` is supplied.

- [ ] **Step 2: Run the full test suite**

Run:

```bash
uv run pytest
```

Expected: the full suite PASSes. If an unrelated pre-existing failure occurs, record it without changing unrelated code.

- [ ] **Step 3: Check formatting and diff hygiene**

Run:

```bash
git diff --check
git status --short
```

Expected: `git diff --check` exits successfully. Status contains only the user's existing progress changes, this feature's GUI/test changes, and the design/plan documents.

- [ ] **Step 4: Verify graph impact**

Run GitNexus `detect_changes(scope="unstaged", repo="md2docx")`.

Expected: the affected production symbol is limited to `Md2docxGUI.convert_file`; existing `_do_conversion` changes may also appear because they were already present in the worktree.

No commit is included because repository changes must not be committed without explicit user authorization.
