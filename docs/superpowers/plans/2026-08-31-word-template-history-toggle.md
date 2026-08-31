# Word Template History and Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent recent-Word-template drop-down to the desktop GUI and a session-only switch that lets conversions ignore the selected template without clearing it.

**Architecture:** Keep template preferences in the existing JSON preferences file. `Md2docxGUI` normalizes a bounded most-recently-used path list, keeps `last_word_template_path` for compatibility, renders the state through a read-only `ttk.Combobox`, and makes `selected_word_template()` the single gate for the session-only enable switch. The converter, CLI, Python API, background worker signature, and conversion-history schema remain unchanged.

**Tech Stack:** Python 3, Tkinter/ttk, `pathlib.Path`, JSON, pytest, `uv`, GitNexus.

---

### Task 1: Persist and normalize Word-template history

**Files:**
- Modify: `tests/test_gui.py` near the existing Word-template preference tests
- Modify: `md2docx/gui.py:24-31,1447-1464,1850-1896`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Update the browse-persistence assertion and add failing state-loading tests**

In `test_gui_browse_word_template_persists_without_dropping_other_preferences`, update the expected JSON object to include the new history key:

```python
    assert json.loads(preferences_file.read_text(encoding="utf-8")) == {
        "last_config_path": str(tmp_path / "config.yaml"),
        "config_file": str(tmp_path / "legacy.yaml"),
        "last_word_template_path": str(template_path),
        "word_template_history": [str(template_path)],
    }
```

Add these tests after the existing Word-template persistence tests:

```python
def test_gui_legacy_word_template_seeds_template_history(tmp_path: Path):
    """The former single-path preference should become the first history item."""
    template_path = tmp_path / "legacy-template.docx"
    template_path.write_bytes(b"template")
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"last_word_template_path": str(template_path)}),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    current, history, warning = gui.load_word_template_state()

    assert current == template_path
    assert history == [str(template_path)]
    assert warning is None


def test_gui_normalizes_and_limits_word_template_history(tmp_path: Path):
    """Template history should contain ten unique, nonblank path strings."""
    template_paths = [str(tmp_path / f"template-{index}.docx") for index in range(12)]
    current_path = Path(template_paths[5])
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps(
            {
                "last_word_template_path": str(current_path),
                "word_template_history": [
                    None,
                    "",
                    template_paths[0],
                    template_paths[0],
                    *template_paths[1:],
                ],
            }
        ),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    current, history, warning = gui.load_word_template_state()

    expected = [
        str(current_path),
        *[path for path in template_paths if path != str(current_path)],
    ][:10]
    assert current == current_path
    assert history == expected
    assert warning is not None
    assert "不存在" in warning


@pytest.mark.parametrize("raw_history", [None, "not-a-list", {"path": "x.docx"}])
def test_gui_ignores_malformed_word_template_history(tmp_path: Path, raw_history):
    """A malformed history value should not prevent preferences from loading."""
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps({"word_template_history": raw_history}),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file

    assert gui.load_word_template_state() == (None, [], None)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run pytest \
  tests/test_gui.py::test_gui_browse_word_template_persists_without_dropping_other_preferences \
  tests/test_gui.py::test_gui_legacy_word_template_seeds_template_history \
  tests/test_gui.py::test_gui_normalizes_and_limits_word_template_history \
  tests/test_gui.py::test_gui_ignores_malformed_word_template_history -v
```

Expected: FAIL because the persisted object has no `word_template_history` and `Md2docxGUI.load_word_template_state` does not exist.

- [ ] **Step 3: Add the history limit and initialize the complete template state**

Add the constant near the other module-level constants in `md2docx/gui.py`:

```python
WORD_TEMPLATE_HISTORY_LIMIT = 10
```

Replace the current two-value Word-template initialization in `Md2docxGUI.__init__` with:

```python
        (
            self.last_word_template_path,
            self.word_template_history,
            self.startup_word_template_error,
        ) = self.load_word_template_state()
```

- [ ] **Step 4: Add normalization/loading and extend persistence**

Replace `load_last_word_template` and `save_last_word_template_path` with the following methods. Keep `clear_last_word_template_path` immediately after them unchanged.

```python
    @staticmethod
    def normalize_word_template_history(
        raw_history: Any,
        current_path: Optional[Path] = None,
    ) -> List[str]:
        """Return a bounded MRU list of expanded, unique template paths."""
        candidates: List[Any] = []
        if current_path is not None:
            candidates.append(str(current_path.expanduser()))
        if isinstance(raw_history, list):
            candidates.extend(raw_history)

        normalized: List[str] = []
        for candidate in candidates:
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            path = str(Path(candidate).expanduser())
            if path in normalized:
                continue
            normalized.append(path)
            if len(normalized) == WORD_TEMPLATE_HISTORY_LIMIT:
                break
        return normalized

    def load_word_template_state(
        self,
    ) -> Tuple[Optional[Path], List[str], Optional[str]]:
        """Load the current template, normalized history, and startup warning."""
        preferences = self.load_preferences()
        raw_path = preferences.get("last_word_template_path")
        template_path: Optional[Path] = None
        warning: Optional[str] = None

        if isinstance(raw_path, str) and raw_path.strip():
            template_path = Path(raw_path).expanduser()
            if template_path.suffix.lower() != ".docx":
                warning = f"上次记录的模板不是 .docx 文件：{template_path}"
            elif not template_path.is_file():
                warning = f"上次记录的模板不存在：{template_path}"

        history = self.normalize_word_template_history(
            preferences.get("word_template_history"),
            template_path,
        )
        return template_path, history, warning

    def load_last_word_template(self) -> Tuple[Optional[Path], Optional[str]]:
        """Load the remembered template using the compatible state reader."""
        template_path, _history, warning = self.load_word_template_state()
        return template_path, warning

    def save_last_word_template_path(self, template_path: Path) -> bool:
        """Merge and persist the selected path and bounded template history."""
        preferences = self.load_preferences()
        normalized_path = template_path.expanduser()
        self.word_template_history = self.normalize_word_template_history(
            getattr(
                self,
                "word_template_history",
                preferences.get("word_template_history"),
            ),
            normalized_path,
        )
        preferences["last_word_template_path"] = str(normalized_path)
        preferences["word_template_history"] = list(self.word_template_history)
        return self.save_preferences(preferences)
```

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run the command from Step 2 again.

Expected: PASS for all six parametrized/test cases, with no warnings or errors.

- [ ] **Step 6: Run all current GUI tests**

Run:

```bash
uv run pytest tests/test_gui.py -v
```

Expected: PASS. If an existing exact JSON assertion now expects the old single-key shape, update it only when the tested action selects a Word template and therefore must persist history.

- [ ] **Step 7: Commit the persistence slice**

```bash
git add md2docx/gui.py tests/test_gui.py
git commit -m "feat: persist recent Word templates" -- md2docx/gui.py tests/test_gui.py
```

Expected: one commit containing only the GUI persistence code and its tests. The already staged design document remains staged because the commit uses explicit pathspecs.

---

### Task 2: Render the history combobox and support MRU selection

**Files:**
- Modify: `tests/test_gui.py:29-59,416-510`
- Modify: `md2docx/gui.py:1576-1616,1748-1770`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Extend the Tk stand-in and add failing combobox tests**

Extend `_FakeWidget` as follows:

```python
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
```

Replace `test_gui_conversion_section_initializes_from_remembered_template` with:

```python
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
```

Replace `test_main_window_buttons_use_chinese_labels` with:

```python
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
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run pytest \
  tests/test_gui.py::test_gui_conversion_section_builds_enabled_template_history_combobox \
  tests/test_gui.py::test_gui_selecting_history_moves_template_to_front \
  tests/test_gui.py::test_main_window_buttons_use_chinese_labels -v
```

Expected: FAIL because the GUI still creates an `Entry`, has no Boolean variable, and has no history-selection handler.

- [ ] **Step 3: Replace the Word-template row with a checkbutton and combobox**

In `setup_conversion_section`, replace the current `Word 模板：` label and template `Entry` block with:

```python
        self.use_word_template_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            conv_frame,
            text="使用 Word 模板",
            variable=self.use_word_template_var,
        ).grid(row=2, column=0, sticky=tk.W, pady=5)

        self.word_template_var = tk.StringVar(
            value=(
                str(self.last_word_template_path)
                if getattr(self, "last_word_template_path", None) is not None
                else ""
            )
        )
        self.word_template_combobox = ttk.Combobox(
            conv_frame,
            textvariable=self.word_template_var,
            values=list(getattr(self, "word_template_history", [])),
            width=50,
            state="readonly",
        )
        self.word_template_combobox.grid(
            row=2,
            column=1,
            sticky=(tk.W, tk.E),
            padx=5,
        )
        self.word_template_combobox.bind(
            "<<ComboboxSelected>>",
            self.select_word_template_from_history,
        )
```

Keep the existing `选择...` and `清除` buttons in columns 2 and 3.

- [ ] **Step 4: Centralize in-memory selection and add the combobox event handler**

Add these methods immediately before `browse_word_template`:

```python
    def remember_word_template(self, template_path: Path) -> bool:
        """Select a template, promote it in history, and persist the state."""
        normalized_path = template_path.expanduser()
        self.last_word_template_path = normalized_path
        self.word_template_var.set(str(normalized_path))
        saved = self.save_last_word_template_path(normalized_path)

        combobox = getattr(self, "word_template_combobox", None)
        if combobox is not None:
            combobox.configure(values=list(self.word_template_history))
        return saved

    def select_word_template_from_history(self, _event: Any = None) -> None:
        """Promote the template chosen from the history combobox."""
        selected_path = self.word_template_var.get().strip()
        if not selected_path:
            return
        if not self.remember_word_template(Path(selected_path)):
            messagebox.showwarning(
                "偏好保存失败",
                "Word模板已选择，但无法更新模板历史。",
                parent=self.dialog_parent(),
            )
```

Replace the `if filename:` body of `browse_word_template` with:

```python
        if filename and not self.remember_word_template(Path(filename)):
            messagebox.showwarning(
                "偏好保存失败",
                "Word模板已选择，但无法记录为下次启动模板。",
                parent=self.dialog_parent(),
            )
```

- [ ] **Step 5: Run focused and complete GUI tests**

Run the Step 2 command, then:

```bash
uv run pytest tests/test_gui.py -v
```

Expected: both commands PASS with no warnings or errors.

- [ ] **Step 6: Commit the combobox slice**

```bash
git add md2docx/gui.py tests/test_gui.py
git commit -m "feat: select recent Word templates" -- md2docx/gui.py tests/test_gui.py
```

Expected: one commit containing the combobox, MRU event handling, and focused tests.

---

### Task 3: Gate conversion with the session-only template switch

**Files:**
- Modify: `tests/test_gui.py:372-396,554-615`
- Modify: `md2docx/gui.py:1771-1783,1936-1940`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Add failing tests for clearing history preservation and disabled conversion**

Replace `test_gui_clear_word_template_removes_only_template_preference` with:

```python
def test_gui_clear_word_template_removes_only_current_preference(tmp_path: Path):
    """Clearing should retain configuration preferences and template history."""
    template_path = tmp_path / "template.docx"
    older_path = tmp_path / "older.docx"
    preferences_file = tmp_path / "preferences.json"
    preferences_file.write_text(
        json.dumps(
            {
                "last_config_path": str(tmp_path / "config.yaml"),
                "config_file": str(tmp_path / "legacy.yaml"),
                "last_word_template_path": str(template_path),
                "word_template_history": [
                    str(template_path),
                    str(older_path),
                ],
            }
        ),
        encoding="utf-8",
    )
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.preferences_file = preferences_file
    gui.word_template_history = [str(template_path), str(older_path)]
    gui.word_template_var = _FakeStringVar(str(template_path))

    gui.clear_word_template()

    assert gui.word_template_var.get() == ""
    assert gui.word_template_history == [str(template_path), str(older_path)]
    assert json.loads(preferences_file.read_text(encoding="utf-8")) == {
        "last_config_path": str(tmp_path / "config.yaml"),
        "config_file": str(tmp_path / "legacy.yaml"),
        "word_template_history": [str(template_path), str(older_path)],
    }
```

Add this test after `test_gui_passes_selected_word_template_to_background_conversion`:

```python
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
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run pytest \
  tests/test_gui.py::test_gui_clear_word_template_removes_only_current_preference \
  tests/test_gui.py::test_gui_disabled_word_template_skips_validation_and_worker_argument -v
```

Expected: the disabled-conversion test FAILS because `selected_word_template()` still returns and validates the `.txt` path.

- [ ] **Step 3: Make `selected_word_template` enforce the switch**

Replace `selected_word_template` with:

```python
    def selected_word_template(self) -> str:
        """Return the selected template only when template use is enabled."""
        enabled_variable = getattr(self, "use_word_template_var", None)
        if enabled_variable is not None and not enabled_variable.get():
            return ""

        template_variable = getattr(self, "word_template_var", None)
        return template_variable.get().strip() if template_variable is not None else ""
```

Update `clear_word_template`'s docstring to make its history behavior explicit:

```python
        """Clear the current template selection without deleting its history."""
```

No change is required in `convert_file`: its existing conditional validation and worker-argument construction already treat an empty selected template as disabled.

- [ ] **Step 4: Run focused and complete GUI tests**

Run the Step 2 command, then:

```bash
uv run pytest tests/test_gui.py -v
```

Expected: both commands PASS. The existing enabled-template tests continue to prove validation and worker handoff.

- [ ] **Step 5: Commit the switch slice**

```bash
git add md2docx/gui.py tests/test_gui.py
git commit -m "feat: toggle Word template per session" -- md2docx/gui.py tests/test_gui.py
```

Expected: one commit containing only the switch behavior and its tests.

---

### Task 4: Update documentation and verify the complete change

**Files:**
- Modify: `docs/GUI_GUIDE.md:38-41,105`
- Verify: `md2docx/gui.py`, `tests/test_gui.py`, `docs/GUI_GUIDE.md`

- [ ] **Step 1: Update the GUI guide's Word-template instructions**

Replace the current `可选 Word 模板` bullets with:

```markdown
3. **可选 Word 模板**
   - 点击 "选择..." 选择 `.docx` 模板；最近使用的 10 个模板会保存在下拉列表中
   - 从下拉列表选择历史模板后，该模板会移动到列表首位
   - 关闭 "使用 Word 模板" 可让当前会话中的转换暂不套用模板，同时保留当前选择
   - 点击 "清除" 只清除当前选择，历史模板仍可从下拉列表重新选择
   - 模板会保留页眉、页脚中的文字、图片和格式
```

Update the corresponding layout line to:

```text
│  [✓] 使用 Word 模板 [历史模板 ▼] [选择...] [清除] │
```

- [ ] **Step 2: Run syntax and complete automated verification**

Run:

```bash
uv run python -m py_compile md2docx/gui.py
uv run pytest tests/test_gui.py -v
uv run pytest
```

Expected: each command exits with status 0; the complete suite reports zero failures.

- [ ] **Step 3: Inspect the final diff for whitespace and scope**

Run:

```bash
git diff --check
git status --short
git diff -- md2docx/gui.py tests/test_gui.py docs/GUI_GUIDE.md
```

Expected: no whitespace errors. The feature diff contains only the GUI, its tests, and the GUI guide; the pre-existing `docs/MACOS_APP_STARTUP_OPTIMIZATION.md` remains untouched.

- [ ] **Step 4: Run GitNexus change detection before the final commit**

Run `detect_changes({scope: "all", repo: "md2docx"})`.

Expected: changed symbols are confined to `Md2docxGUI` template preference/UI methods and the focused GUI tests. Review every affected execution flow; stop and report before committing if the risk is HIGH or CRITICAL or if unrelated symbols appear.

- [ ] **Step 5: Commit documentation and any remaining approved artifacts**

```bash
git add docs/GUI_GUIDE.md \
  docs/superpowers/specs/2026-08-31-word-template-history-toggle-design.md \
  docs/superpowers/plans/2026-08-31-word-template-history-toggle.md
git commit -m "docs: document Word template history"
```

Expected: the approved design, implementation plan, and user guide are committed without the unrelated startup-optimization document.
