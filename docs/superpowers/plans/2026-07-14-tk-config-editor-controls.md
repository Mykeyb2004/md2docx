# Tk Config Editor Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the Tk default configuration editor by using high-frequency field controls for editable suggestions, fixed enumerations, and color picking while preserving YAML compatibility.

**Architecture:** Keep the existing recursive Tk form in `md2docx/gui.py`. Add a small field-rule layer that maps config paths to widget kinds, then let `ConfigEditorWindow.create_field_widget()` dispatch to checkbox, combobox, color composite, or plain entry widgets.

**Tech Stack:** Python 3.8+, Tkinter/ttk, pytest, uv, GitNexus MCP.

---

## Impact And Scope

GitNexus impact for `ConfigEditorWindow.create_field_widget` in `md2docx/gui.py` is **HIGH**:

- Direct callers: 1 (`render_section_fields`)
- Affected processes: 3 (`import_config`, `ConfigEditorWindow.__init__`, `restore_packaged_defaults`)
- Affected module: `Md2docx`

During implementation, run impact analysis again before editing `create_field_widget`, and stop for user confirmation if the result is HIGH or CRITICAL and differs materially from this plan.

## File Structure

- Modify `md2docx/gui.py`: add field widget rule constants, rule resolver, color preview helper, color picker widget, and `create_field_widget()` dispatch.
- Modify `tests/test_gui.py`: add pure unit tests for field rules and color normalization without requiring a real Tk display.
- No new runtime dependencies.
- No YAML schema or converter changes.

## Task 1: Add Pure Tests For Field Rule Resolution

**Files:**
- Modify: `tests/test_gui.py`
- Later Modify: `md2docx/gui.py`

- [ ] **Step 1: Add failing tests for high-frequency field rules**

Append this test block to `tests/test_gui.py`:

```python
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


def test_config_editor_rule_leaves_unknown_fields_as_entry():
    """Imported or unsupported fields should retain the existing plain input path."""
    rule = gui_module.resolve_field_widget_rule(("custom", "unrecognized"))

    assert rule.kind == gui_module.FIELD_WIDGET_ENTRY
    assert rule.options == ()
    assert rule.readonly is False
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
uv run pytest tests/test_gui.py -q
```

Expected: FAIL with `AttributeError: module 'md2docx.gui' has no attribute 'resolve_field_widget_rule'`.

- [ ] **Step 3: Commit the failing tests**

Run:

```bash
git add tests/test_gui.py
git commit -m "test: cover config editor field rules"
```

Expected: commit succeeds with only `tests/test_gui.py` staged.

## Task 2: Implement Field Rule Constants And Resolver

**Files:**
- Modify: `md2docx/gui.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Run GitNexus impact before editing `create_field_widget`**

Use the GitNexus MCP `impact` tool with these parameters:

```json
{
  "repo": "md2docx",
  "target": "create_field_widget",
  "file_path": "md2docx/gui.py",
  "kind": "Method",
  "direction": "upstream",
  "summaryOnly": true
}
```

Expected: HIGH risk with direct caller `render_section_fields` and affected processes including `import_config`, `__init__`, and `restore_packaged_defaults`. If the result is HIGH or CRITICAL with a broader blast radius than this, stop and report it before editing.

- [ ] **Step 2: Add `colorchooser` import**

Change the Tk import in `md2docx/gui.py` from:

```python
from tkinter import filedialog, messagebox, ttk
```

to:

```python
from tkinter import colorchooser, filedialog, messagebox, ttk
```

- [ ] **Step 3: Add field widget rule data under `ConfigPath`**

Insert this block immediately after `ConfigPath = Tuple[str, ...]` in `md2docx/gui.py`:

```python
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

# Backwards-compatible alias for existing code and callers.
FIELD_OPTIONS = READONLY_FIELD_OPTIONS

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
```

- [ ] **Step 4: Replace the old `FIELD_OPTIONS` block**

Remove the original `FIELD_OPTIONS = { ... }` block that starts after `ConfigPath = Tuple[str, ...]`. Keep `SECTION_GROUPS` unchanged.

- [ ] **Step 5: Add the resolver function before `center_window_on_screen`**

Insert this function after `SECTION_GROUPS`:

```python
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
```

- [ ] **Step 6: Run the field-rule tests**

Run:

```bash
uv run pytest tests/test_gui.py -q
```

Expected: all tests in `tests/test_gui.py` pass.

- [ ] **Step 7: Commit rule implementation**

Run:

```bash
git add md2docx/gui.py
git commit -m "feat: add config editor field rules"
```

Expected: commit succeeds with only `md2docx/gui.py` staged.

## Task 3: Add Pure Color Normalization Tests And Helper

**Files:**
- Modify: `tests/test_gui.py`
- Modify: `md2docx/gui.py`

- [ ] **Step 1: Add failing color normalization tests**

Append this test block to `tests/test_gui.py`:

```python
def test_normalize_color_preview_accepts_long_and_short_hex_values():
    """Preview helper should normalize supported hex colors for the swatch."""
    assert gui_module.normalize_color_preview("#24292e") == "#24292E"
    assert gui_module.normalize_color_preview("D14") == "#DD1144"


def test_normalize_color_preview_rejects_empty_null_and_named_values():
    """Unsupported preview values should remain editable text without swatch errors."""
    assert gui_module.normalize_color_preview("") is None
    assert gui_module.normalize_color_preview("null") is None
    assert gui_module.normalize_color_preview("white") is None
```

- [ ] **Step 2: Run the color tests and verify they fail**

Run:

```bash
uv run pytest tests/test_gui.py -q
```

Expected: FAIL with `AttributeError: module 'md2docx.gui' has no attribute 'normalize_color_preview'`.

- [ ] **Step 3: Add the color preview helper**

Insert this function after `resolve_field_widget_rule()` in `md2docx/gui.py`:

```python
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
```

- [ ] **Step 4: Run GUI tests**

Run:

```bash
uv run pytest tests/test_gui.py -q
```

Expected: all tests in `tests/test_gui.py` pass.

- [ ] **Step 5: Commit color helper**

Run:

```bash
git add md2docx/gui.py tests/test_gui.py
git commit -m "feat: normalize config editor color previews"
```

Expected: commit succeeds with `md2docx/gui.py` and `tests/test_gui.py` staged.

## Task 4: Integrate Rules Into Tk Widgets

**Files:**
- Modify: `md2docx/gui.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Add `ConfigEditorWindow` color widget helpers**

Insert these methods inside `ConfigEditorWindow`, immediately before `create_field_widget()`:

```python
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
```

- [ ] **Step 2: Replace `create_field_widget()` dispatch**

Replace the full body of `create_field_widget()` with:

```python
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
            self.field_bindings.append(
                FieldBinding(path=path, variable=variable, schema_value=expected_value)
            )
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

        self.field_bindings.append(
            FieldBinding(path=path, variable=variable, schema_value=schema_value)
        )
        return widget
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
uv run pytest tests/test_gui.py -q
```

Expected: all tests in `tests/test_gui.py` pass.

- [ ] **Step 4: Manually smoke-test the editor if a display is available**

Run:

```bash
uv run md2docx-gui
```

Expected:

- Main GUI opens.
- Clicking the default configuration editor button opens the editor.
- `heading1.font_name` appears as an editable combobox.
- `heading1.font_color` appears as a swatch, text input, and `选择` button.
- `document.page_size` appears as a readonly combobox.
- Closing the GUI exits cleanly.

- [ ] **Step 5: Commit widget integration**

Run:

```bash
git add md2docx/gui.py
git commit -m "feat: use enhanced config editor widgets"
```

Expected: commit succeeds with only `md2docx/gui.py` staged.

## Task 5: Verify Full Behavior And Affected Scope

**Files:**
- No planned file edits.

- [ ] **Step 1: Run the full test suite**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run GitNexus change detection**

Use the GitNexus MCP `detect_changes` tool:

```json
{
  "repo": "md2docx",
  "scope": "all"
}
```

Expected:

- Changed symbols include the new rule helpers and `ConfigEditorWindow.create_field_widget`.
- Affected processes align with the known editor load/import/restore flows.
- Risk does not exceed the HIGH impact already documented for `create_field_widget`.

- [ ] **Step 3: Review the final diff**

Run:

```bash
git status --short
git diff --stat
git diff
```

Expected:

- No unrelated files changed.
- Only `md2docx/gui.py` and `tests/test_gui.py` contain implementation/test changes.
- No `.superpowers/brainstorm/` files are staged or modified.

- [ ] **Step 4: Final commit if any verification-only fixes were needed**

If Step 1 or Step 2 required small fixes, commit them:

```bash
git add md2docx/gui.py tests/test_gui.py
git commit -m "test: verify config editor controls"
```

Expected: commit succeeds only when there are actual verification fixes. If there are no changes after Task 4, skip this commit.
