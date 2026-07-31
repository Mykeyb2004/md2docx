# Table Layout Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add theme-grid, three-line, and plain-grid table presets, expose them in the default configuration editor, and apply the selected preset during DOCX conversion without duplicating the existing table renderer.

**Architecture:** Add one backward-compatible `table.layout` selector to the packaged and hardcoded defaults. Keep `DocxRenderer.table()`, `table_head()`, `table_body()`, and `table_row()` as the single content-rendering path, with a small layout resolver and OOXML border helpers controlling only style, borders, and shading. Extend the schema-driven Tk editor with an optional display/stored-value mapping so it shows Chinese preset names while saving stable English YAML values.

**Tech Stack:** Python 3, `uv`, pytest, python-docx, WordprocessingML OOXML, Tkinter/ttk, PyYAML, GitNexus MCP.

---

## File Map

- Modify `md2docx/templates/default.yaml`: declare the packaged `table.layout` default used by conversion and the editor schema.
- Modify `md2docx/styles.py`: mirror the selector in `StyleManager.DEFAULT_CONFIG` for packaged-template fallback failures.
- Modify `md2docx/renderer.py`: normalize the selector, apply preset borders/style, and gate header/body shading while preserving the shared rendering path.
- Create `tests/test_table_layouts.py`: inspect generated OOXML for preset borders, shading, fallback behavior, and YAML-to-renderer data flow.
- Modify `md2docx/gui.py`: add Chinese labels, optional display/stored-value mapping, and the `表格样式` field label.
- Modify `tests/test_gui.py`: cover the mapped read-only selector, value round trip, label, and unchanged generic widget behavior.
- Modify `tests/test_styles.py`: pin the hardcoded and packaged default contract.

Do not modify the Markdown parser, `Converter`, `StyleManager.get_table_style()`, or the table width/alignment/margin helpers. They already provide the required shared data flow.

## Pre-Change Risk Gate

GitNexus currently reports:

- `LOW`: `DocxRenderer.table`, `table_head`, and `table_row`.
- `MEDIUM`: `StyleManager` (23 upstream symbols, including 8 direct dependents).
- `HIGH`: `resolve_field_widget_rule` (9 direct dependents), `create_field_widget` (4 editor flows), and `render_section_fields` (4 editor flows).

The `HIGH` GUI risk is accepted only with these constraints: new dataclass fields have empty defaults, raw enum fields keep their existing options and stored values, unknown fields remain entries, and import/restore/render workflows run through the existing methods. Re-run the exact impact calls in Task 3 immediately before editing, and stop if risk or direct callers have materially changed.

### Task 1: Add The Backward-Compatible Configuration Contract

**Files:**
- Modify: `tests/test_styles.py`
- Modify: `md2docx/templates/default.yaml:110`
- Modify: `md2docx/styles.py:48`

- [ ] **Step 1: Re-run impact analysis for the shared style manager**

Tool call:

```text
impact(target="StyleManager", file_path="md2docx/styles.py", kind="Class",
       direction="upstream", includeTests=true, repo="md2docx")
```

Expected: `MEDIUM`; no renderer behavior changes are introduced by adding one dictionary key.

- [ ] **Step 2: Write the failing default-contract test**

Append to `tests/test_styles.py`:

```python
def test_default_table_layout_is_accent_grid():
    """Both fallback and packaged defaults should preserve the current table layout."""
    packaged = StyleManager.load_packaged_template("default")

    assert StyleManager.DEFAULT_CONFIG["table"]["layout"] == "accent_grid"
    assert packaged["table"]["layout"] == "accent_grid"
```

- [ ] **Step 3: Run the test and verify the missing key fails**

Run:

```bash
uv run --offline pytest tests/test_styles.py::test_default_table_layout_is_accent_grid -q
```

Expected: `FAIL` with `KeyError: 'layout'` or an assertion showing the packaged key is absent.

- [ ] **Step 4: Add the selector to both default sources**

In `StyleManager.DEFAULT_CONFIG["table"]` add the first table key:

```python
"table": {
    "layout": "accent_grid",
    "style": "Light Grid Accent 1",
```

In `md2docx/templates/default.yaml` add the first table field:

```yaml
table:
  layout: accent_grid  # accent_grid=主题网格表；three_line=三线表；plain_grid=简洁网格表
  style: "Light Grid Accent 1"
```

- [ ] **Step 5: Run the focused style tests**

Run:

```bash
uv run --offline pytest tests/test_styles.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Check affected scope before committing**

Tool call:

```text
detect_changes(scope="all", repo="md2docx",
               worktree="/Users/zhangqijin/PycharmProjects/md2docx")
```

Expected: only default configuration/style-loading scope; no unrelated execution flow.

- [ ] **Step 7: Commit the configuration contract**

```bash
git add tests/test_styles.py md2docx/templates/default.yaml md2docx/styles.py
git commit -m "feat: add table layout configuration"
```

### Task 2: Apply All Three Presets Through The Shared Renderer

**Files:**
- Create: `tests/test_table_layouts.py`
- Modify: `md2docx/renderer.py:1-15`
- Modify: `md2docx/renderer.py:370-389`
- Modify: `md2docx/renderer.py:1687-1899`

- [ ] **Step 1: Re-run renderer impact analysis**

Tool calls:

```text
impact(target="table", file_path="md2docx/renderer.py", kind="Method",
       direction="upstream", includeTests=true, repo="md2docx")
impact(target="table_head", file_path="md2docx/renderer.py", kind="Method",
       direction="upstream", includeTests=true, repo="md2docx")
impact(target="table_row", file_path="md2docx/renderer.py", kind="Method",
       direction="upstream", includeTests=true, repo="md2docx")
```

Expected: `LOW`. The only direct renderer callers remain the existing table flow.

- [ ] **Step 2: Create OOXML-focused failing tests**

Create `tests/test_table_layouts.py`:

```python
"""Tests for selectable DOCX table layout presets."""
from pathlib import Path

from docx.oxml.ns import qn

from md2docx import Converter
from md2docx.config_utils import save_yaml_config


TABLE_MARKDOWN = """
| 姓名 | 分数 |
|------|------|
| 张三 | 95 |
| 李四 | 88 |
"""


def _render_table(layout=None, **table_overrides):
    table_config = dict(table_overrides)
    if layout is not None:
        table_config["layout"] = layout
    document = Converter(config_override={"table": table_config}).to_document(TABLE_MARKDOWN)
    return document.tables[0]


def _table_border(table, side):
    borders = table._tbl.tblPr.first_child_found_in("w:tblBorders")
    return None if borders is None else borders.find(qn(f"w:{side}"))


def _cell_border(cell, side):
    borders = cell._tc.tcPr.first_child_found_in("w:tcBorders")
    return None if borders is None else borders.find(qn(f"w:{side}"))


def _border_attributes(border):
    assert border is not None
    return {
        "value": border.get(qn("w:val")),
        "size": border.get(qn("w:sz")),
        "color": border.get(qn("w:color")),
    }


def _cell_shading(cell):
    shading = cell._tc.tcPr.find(qn("w:shd"))
    return None if shading is None else shading.get(qn("w:fill"))


def test_missing_and_invalid_layout_preserve_theme_grid():
    missing_converter = Converter()
    missing_converter.style_manager.config["table"].pop("layout", None)
    missing = missing_converter.to_document(TABLE_MARKDOWN).tables[0]
    invalid = _render_table("unsupported-layout")

    assert missing.style.name == "Light Grid Accent 1"
    assert invalid.style.name == "Light Grid Accent 1"


def test_explicit_accent_grid_preserves_style_and_configured_shading():
    table = _render_table(
        "accent_grid",
        alternating_rows=True,
        row_background_odd="#FFFFFF",
        row_background_even="#F9F9F9",
    )

    assert table.style.name == "Light Grid Accent 1"
    assert _cell_shading(table.rows[0].cells[0]) == "F2F2F2"
    assert _cell_shading(table.rows[1].cells[0]) == "FFFFFF"
    assert _cell_shading(table.rows[2].cells[0]) == "F9F9F9"


def test_plain_grid_has_black_half_point_grid_and_gray_header():
    table = _render_table(
        "plain_grid",
        alternating_rows=True,
        row_background_odd="#FF0000",
        row_background_even="#00FF00",
    )

    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        assert _border_attributes(_table_border(table, side)) == {
            "value": "single",
            "size": "4",
            "color": "000000",
        }
    assert table._tbl.tblPr.find(qn("w:tblStyle")) is None
    assert _cell_shading(table.rows[0].cells[0]) == "F2F2F2"
    assert _cell_shading(table.rows[1].cells[0]) is None
    assert _cell_shading(table.rows[2].cells[0]) is None


def test_three_line_has_only_top_header_separator_and_bottom_borders():
    table = _render_table(
        "three_line",
        alternating_rows=True,
        row_background_odd="#FF0000",
        row_background_even="#00FF00",
    )

    for side in ("top", "bottom"):
        assert _border_attributes(_table_border(table, side)) == {
            "value": "single",
            "size": "12",
            "color": "000000",
        }
    for side in ("left", "right", "insideH", "insideV"):
        assert _border_attributes(_table_border(table, side))["value"] == "nil"
    for cell in table.rows[0].cells:
        assert _border_attributes(_cell_border(cell, "bottom")) == {
            "value": "single",
            "size": "6",
            "color": "000000",
        }
    for row in table.rows[1:]:
        for cell in row.cells:
            assert _cell_border(cell, "bottom") is None
    assert table._tbl.tblPr.find(qn("w:tblStyle")) is None
    assert all(_cell_shading(cell) is None for row in table.rows for cell in row.cells)


def test_saved_yaml_layout_reaches_the_renderer(tmp_path: Path):
    config_path = tmp_path / "three-line.yaml"
    save_yaml_config(
        config_path,
        {
            "table": {
                "layout": "three_line",
                "font_name": "仿宋",
                "font_size": "12pt",
            }
        },
    )

    table = Converter(style_config=str(config_path)).to_document(TABLE_MARKDOWN).tables[0]

    assert _border_attributes(_table_border(table, "top"))["size"] == "12"
    assert _border_attributes(_cell_border(table.rows[0].cells[0], "bottom"))["size"] == "6"
```

- [ ] **Step 3: Run the new tests and verify preset assertions fail**

Run:

```bash
uv run --offline pytest tests/test_table_layouts.py -q
```

Expected: missing/invalid fallback may pass, while plain-grid and three-line tests fail because no explicit preset borders exist and shading is not gated.

- [ ] **Step 4: Add layout constants and border helpers**

Near the imports in `md2docx/renderer.py`, add:

```python
TABLE_LAYOUT_ACCENT_GRID = "accent_grid"
TABLE_LAYOUT_THREE_LINE = "three_line"
TABLE_LAYOUT_PLAIN_GRID = "plain_grid"
TABLE_LAYOUTS = frozenset(
    {
        TABLE_LAYOUT_ACCENT_GRID,
        TABLE_LAYOUT_THREE_LINE,
        TABLE_LAYOUT_PLAIN_GRID,
    }
)
```

After `_apply_table_cell_margins()`, add these methods:

```python
    def _resolve_table_layout(self, table_style: Dict[str, Any]) -> str:
        """Return a supported layout, preserving the historic default."""
        layout = str(table_style.get("layout", TABLE_LAYOUT_ACCENT_GRID)).strip().lower()
        if layout not in TABLE_LAYOUTS:
            return TABLE_LAYOUT_ACCENT_GRID
        return layout

    def _set_ooxml_borders(
        self,
        properties: Any,
        container_tag: str,
        borders: Dict[str, Tuple[str, Optional[int]]],
    ) -> None:
        """Set deterministic black borders on table or cell properties."""
        container = properties.first_child_found_in(container_tag)
        if container is None:
            container = OxmlElement(container_tag)
            properties.append(container)

        for side, (value, size) in borders.items():
            border = container.find(qn(f"w:{side}"))
            if border is None:
                border = OxmlElement(f"w:{side}")
                container.append(border)
            border.set(qn("w:val"), value)
            if value == "single" and size is not None:
                border.set(qn("w:sz"), str(size))
                border.set(qn("w:color"), "000000")
            else:
                border.attrib.pop(qn("w:sz"), None)
                border.attrib.pop(qn("w:color"), None)

    def _apply_table_layout(
        self,
        table: Any,
        table_style: Dict[str, Any],
        layout: str,
    ) -> None:
        """Apply only the visual properties owned by a table preset."""
        if layout == TABLE_LAYOUT_ACCENT_GRID:
            style_name = table_style.get("style")
            if style_name:
                try:
                    table.style = style_name
                except KeyError:
                    pass
            return

        table_properties = table._tbl.tblPr
        table_style_element = table_properties.find(qn("w:tblStyle"))
        if table_style_element is not None:
            table_properties.remove(table_style_element)

        if layout == TABLE_LAYOUT_PLAIN_GRID:
            self._set_ooxml_borders(
                table_properties,
                "w:tblBorders",
                {
                    side: ("single", 4)
                    for side in ("top", "left", "bottom", "right", "insideH", "insideV")
                },
            )
            return

        self._set_ooxml_borders(
            table_properties,
            "w:tblBorders",
            {
                "top": ("single", 12),
                "left": ("nil", None),
                "bottom": ("single", 12),
                "right": ("nil", None),
                "insideH": ("nil", None),
                "insideV": ("nil", None),
            },
        )
        for cell in table.rows[0].cells:
            self._set_ooxml_borders(
                cell._tc.get_or_add_tcPr(),
                "w:tcBorders",
                {"bottom": ("single", 6)},
            )
```

OOXML border sizes are eighths of a point: `12 = 1.5 pt`, `6 = 0.75 pt`, and `4 = 0.5 pt`.

- [ ] **Step 5: Route the existing table method through the preset helper**

In `table()`, resolve the layout immediately after retrieving `table_style`:

```python
        table_style = self.styles.get_table_style()
        table_layout = self._resolve_table_layout(table_style)
```

Replace the existing `if 'style' in table_style` block with:

```python
        self._apply_table_layout(table, table_style, table_layout)
```

Do not change table discovery, row counting, width calculation, or calls to `table_head()` and `table_body()`.

- [ ] **Step 6: Gate only the layout-specific shading behavior**

In `table_head()`, resolve the layout and change the header-shading condition:

```python
        table_style = self.styles.get_table_style()
        table_layout = self._resolve_table_layout(table_style)
```

```python
                if (
                    table_layout != TABLE_LAYOUT_THREE_LINE
                    and "header_background" in table_style
                ):
```

In `table_row()`, resolve the layout and replace the alternating-row assignment:

```python
        table_style = self.styles.get_table_style()
        table_layout = self._resolve_table_layout(table_style)
```

```python
        alternating_rows = (
            table_layout == TABLE_LAYOUT_ACCENT_GRID
            and table_style.get("alternating_rows", False)
        )
```

Keep all shared font, alignment, line-spacing, margin, width, and repeating-header code unchanged.

- [ ] **Step 7: Run the renderer and existing table regression tests**

Run:

```bash
uv run --offline pytest \
  tests/test_table_layouts.py \
  tests/test_tables.py \
  tests/test_table_alignment.py -q
```

Expected: all tests pass. The existing 14 table/alignment tests remain green alongside the new preset tests.

- [ ] **Step 8: Check affected scope before committing**

Tool call:

```text
detect_changes(scope="all", repo="md2docx",
               worktree="/Users/zhangqijin/PycharmProjects/md2docx")
```

Expected: table-rendering flows only, plus the new focused tests.

- [ ] **Step 9: Commit the renderer presets**

```bash
git add md2docx/renderer.py tests/test_table_layouts.py
git commit -m "feat: render selectable table layouts"
```

### Task 3: Synchronize The Default Configuration Editor UI

**Files:**
- Modify: `tests/test_gui.py:190-410`
- Modify: `md2docx/gui.py:20-268`
- Modify: `md2docx/gui.py:306-314`
- Modify: `md2docx/gui.py:548-685`

- [ ] **Step 1: Re-run and review the high-risk GUI impact reports**

Tool calls:

```text
impact(target="resolve_field_widget_rule", file_path="md2docx/gui.py",
       kind="Function", direction="upstream", includeTests=true, repo="md2docx")
impact(target="create_field_widget", file_path="md2docx/gui.py",
       kind="Method", direction="upstream", includeTests=true, repo="md2docx")
impact(target="render_section_fields", file_path="md2docx/gui.py",
       kind="Method", direction="upstream", includeTests=true, repo="md2docx")
impact(target="collect_config", file_path="md2docx/gui.py",
       kind="Method", direction="upstream", includeTests=true, repo="md2docx")
```

Expected: the first three remain `HIGH` because they serve editor initialization, import, restore-default, and render flows. Do not proceed if new non-editor callers appear.

- [ ] **Step 2: Add failing tests for label/value mapping and round trip**

Append the following focused tests to `tests/test_gui.py` near the existing widget-rule tests:

```python
def test_config_editor_rule_maps_table_layout_values_to_chinese_labels():
    rule = gui_module.resolve_field_widget_rule(("table", "layout"))

    assert rule.kind == gui_module.FIELD_WIDGET_COMBOBOX
    assert rule.readonly is True
    assert rule.options == (
        "主题网格表（当前默认）",
        "三线表",
        "简洁网格表",
    )
    assert rule.value_mapping == (
        ("主题网格表（当前默认）", "accent_grid"),
        ("三线表", "three_line"),
        ("简洁网格表", "plain_grid"),
    )


def test_config_editor_uses_chinese_table_layout_label():
    assert (
        gui_module.resolve_field_label(("table", "layout"), "layout", "accent_grid")
        == "表格样式"
    )


def test_config_editor_table_layout_display_value_roundtrip(monkeypatch):
    def make_widget(widget_type):
        def factory(*args, **kwargs):
            return _FakeWidget(widget_type, *args, **kwargs)

        return factory

    monkeypatch.setattr(gui_module.tk, "StringVar", _FakeStringVar)
    monkeypatch.setattr(gui_module.ttk, "Combobox", make_widget("combobox"))

    editor = gui_module.ConfigEditorWindow.__new__(gui_module.ConfigEditorWindow)
    editor.current_config = {"table": {"layout": "accent_grid"}}
    editor.field_bindings = []

    widget = editor.create_field_widget(
        object(),
        ("table", "layout"),
        "accent_grid",
        "accent_grid",
    )

    binding = editor.field_bindings[0]
    assert widget.widget_type == "combobox"
    assert widget.kwargs["state"] == "readonly"
    assert binding.variable.get() == "主题网格表（当前默认）"

    binding.variable.set("三线表")

    assert editor.collect_config()["table"]["layout"] == "three_line"
```

Also extend `test_config_editor_create_field_widget_dispatches_enhanced_controls` with the existing five controls unchanged; its current assertions are the backward-compatibility guard and must not be weakened.

- [ ] **Step 3: Run the GUI tests and verify the new contract fails**

Run:

```bash
uv run --offline pytest \
  tests/test_gui.py::test_config_editor_rule_maps_table_layout_values_to_chinese_labels \
  tests/test_gui.py::test_config_editor_uses_chinese_table_layout_label \
  tests/test_gui.py::test_config_editor_table_layout_display_value_roundtrip -q
```

Expected: `FAIL` because `value_mapping`, `resolve_field_label`, and the table-layout rule do not exist yet.

- [ ] **Step 4: Add optional mapping metadata with backward-compatible defaults**

Extend `FieldWidgetRule`:

```python
@dataclass(frozen=True)
class FieldWidgetRule:
    """Describe the editor widget to use for one config field."""

    kind: str = FIELD_WIDGET_ENTRY
    options: Tuple[str, ...] = ()
    readonly: bool = False
    value_mapping: Tuple[Tuple[str, str], ...] = ()
```

Add the preset and label constants after the existing option tuples:

```python
TABLE_LAYOUT_VALUE_MAPPING = (
    ("主题网格表（当前默认）", "accent_grid"),
    ("三线表", "three_line"),
    ("简洁网格表", "plain_grid"),
)

READONLY_FIELD_VALUE_MAPPINGS = {
    ("table", "layout"): TABLE_LAYOUT_VALUE_MAPPING,
}

FIELD_LABELS = {
    ("table", "layout"): "表格样式",
}
```

At the top of `resolve_field_widget_rule()`, after the empty-path guard, resolve mapped enums before raw enums:

```python
    value_mapping = READONLY_FIELD_VALUE_MAPPINGS.get(path)
    if value_mapping is not None:
        return FieldWidgetRule(
            kind=FIELD_WIDGET_COMBOBOX,
            options=tuple(display for display, _stored in value_mapping),
            readonly=True,
            value_mapping=value_mapping,
        )
```

Because `value_mapping` defaults to `()`, all existing rules retain the same equality, options, and widget behavior.

- [ ] **Step 5: Add explicit display/stored conversion and field-label helpers**

Add before `normalize_color_preview()`:

```python
def format_mapped_widget_value(
    value: Any,
    value_mapping: Tuple[Tuple[str, str], ...],
) -> str:
    """Format one stored config value for a mapped editor field."""
    stored_value = format_config_value(value)
    for display, stored in value_mapping:
        if stored == stored_value:
            return display
    return stored_value


def parse_mapped_widget_value(
    value: Any,
    value_mapping: Tuple[Tuple[str, str], ...],
) -> Any:
    """Map one displayed editor value back to its stable config value."""
    for display, stored in value_mapping:
        if display == value:
            return stored
    return value


def resolve_field_label(path: ConfigPath, key: str, schema_value: Any) -> str:
    """Return the user-facing field label while preserving unknown-field hints."""
    label = FIELD_LABELS.get(path, key)
    if schema_value is None:
        return f"{label} (留空 = null)"
    return label
```

- [ ] **Step 6: Carry mapping metadata through widget creation and collection**

Extend `FieldBinding`:

```python
@dataclass
class FieldBinding:
    """Keep a widget variable paired with its schema value."""

    path: ConfigPath
    variable: Any
    schema_value: Any
    value_mapping: Tuple[Tuple[str, str], ...] = ()
```

In the non-boolean path of `create_field_widget()`, resolve the rule before creating the variable:

```python
        rule = resolve_field_widget_rule(path)
        variable = tk.StringVar(
            value=format_mapped_widget_value(value, rule.value_mapping)
        )
```

Remove the later duplicate `rule = resolve_field_widget_rule(path)`. Replace the final binding append with:

```python
        self.field_bindings.append(
            FieldBinding(
                path=path,
                variable=variable,
                schema_value=schema_value,
                value_mapping=rule.value_mapping,
            )
        )
```

In `collect_config()`, map before coercion:

```python
        for binding in self.field_bindings:
            raw_value = parse_mapped_widget_value(
                binding.variable.get(),
                binding.value_mapping,
            )
            try:
                value = coerce_config_value(raw_value, binding.schema_value)
```

Boolean bindings continue using the empty default mapping.

- [ ] **Step 7: Use the Chinese label in the existing table tab**

In the dictionary branch of `render_section_fields()`, replace the inline `label_text` block with:

```python
                label_text = resolve_field_label(child_path, key, child_schema)
```

Leave tab creation and recursion unchanged. The packaged `table.layout` field will therefore appear automatically in the existing `表格` tab.

- [ ] **Step 8: Run all GUI/config tests**

Run:

```bash
uv run --offline pytest tests/test_gui.py tests/test_config_utils.py -q
```

Expected: all tests pass, including existing readonly enum, editable combobox, color, unknown-field, import, and conversion-selection tests.

- [ ] **Step 9: Check all editor flows before committing**

Tool call:

```text
detect_changes(scope="all", repo="md2docx",
               worktree="/Users/zhangqijin/PycharmProjects/md2docx")
```

Expected: initialization, import, restore defaults, rendering, save, and export flows are listed; no non-editor feature flow is unexpectedly affected.

- [ ] **Step 10: Commit the synchronized editor UI**

```bash
git add md2docx/gui.py tests/test_gui.py
git commit -m "feat: add table layout selector to config editor"
```

### Task 4: Verify Compatibility And Complete The Feature

**Files:**
- Verify: `md2docx/templates/default.yaml`
- Verify: `md2docx/styles.py`
- Verify: `md2docx/renderer.py`
- Verify: `md2docx/gui.py`
- Verify: `tests/test_table_layouts.py`
- Verify: `tests/test_tables.py`
- Verify: `tests/test_table_alignment.py`
- Verify: `tests/test_gui.py`
- Verify: `tests/test_styles.py`
- Verify: `tests/test_config_utils.py`

- [ ] **Step 1: Run the complete focused feature suite**

Run:

```bash
uv run --offline pytest \
  tests/test_table_layouts.py \
  tests/test_tables.py \
  tests/test_table_alignment.py \
  tests/test_gui.py \
  tests/test_styles.py \
  tests/test_config_utils.py -q
```

Expected: all focused tests pass with no warnings caused by the feature.

- [ ] **Step 2: Run the entire test suite**

Run:

```bash
uv run --offline pytest -q
```

Expected: the complete repository suite passes.

- [ ] **Step 3: Inspect the final change graph against `main`**

Tool call:

```text
detect_changes(scope="compare", base_ref="main", repo="md2docx",
               worktree="/Users/zhangqijin/PycharmProjects/md2docx")
```

If execution occurred directly on `main`, use `detect_changes(scope="all", ...)` before the last feature commit and review `git show --stat` across the three feature commits instead. Expected scope: table configuration, table rendering, and configuration-editor workflows only.

- [ ] **Step 4: Review repository status and commit boundaries**

Run:

```bash
git status --short
git log -4 --oneline
```

Expected: feature files are clean; the pre-existing user changes in `AGENTS.md` and `CLAUDE.md` remain untouched and uncommitted. The implementation is split into configuration, renderer, and UI commits.

