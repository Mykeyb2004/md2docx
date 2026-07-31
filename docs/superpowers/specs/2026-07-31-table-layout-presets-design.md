# Table Layout Presets Design

## Goal

Add three selectable table layouts while preserving the existing Markdown table parsing and DOCX rendering pipeline:

- `accent_grid`: **主题网格表（当前默认）**
- `three_line`: **三线表**
- `plain_grid`: **简洁网格表**

The default configuration editor must expose the selector in its existing **表格** tab, display the Chinese names, persist the stable English values, and apply the selected layout during conversion.

## Confirmed Visual Definitions

### Theme Grid (`accent_grid`)

This is the current behavior and remains the default:

- Keep the configured Word table style, currently `Light Grid Accent 1`.
- Keep the configured light-gray header background.
- Keep the existing header, alignment, column-width, cell-margin, and optional alternating-row behavior.
- Preserve output from old configuration files that do not contain `table.layout`.

### Three-Line (`three_line`)

Use the conventional three-line structure:

- Black top border.
- Black separator below the header row.
- Black bottom border.
- No left or right border.
- No internal vertical borders.
- No other internal horizontal borders.
- No header background or alternating-row background.
- Use a thicker top and bottom border than the header separator.

Initial fixed widths are 1.5 pt for the top and bottom borders and 0.75 pt for the header separator. These are preset behavior, not new user-editable fields in this iteration.

### Plain Grid (`plain_grid`)

Use a neutral, non-themed grid:

- Black thin borders around every cell.
- Light-gray header background from `table.header_background`.
- No theme accent color.
- No alternating-row background.
- Keep the shared font, alignment, column-width, and cell-margin settings.

The thin grid border is fixed at 0.5 pt in this iteration.

## Configuration Contract

Add one field to the packaged table configuration:

```yaml
table:
  layout: accent_grid
```

Supported values are exactly:

```text
accent_grid
three_line
plain_grid
```

Missing or unsupported values fall back to `accent_grid`. This preserves existing YAML files and avoids conversion failures caused by manually edited configurations.

Existing table settings remain shared across all layouts. Layout-specific rules override only the visual properties that define the preset:

| Setting | Theme grid | Three-line | Plain grid |
|---|---|---|---|
| `style` | Honored | Ignored | Ignored |
| `header_background` | Honored | Suppressed | Honored |
| `alternating_rows` | Honored | Suppressed | Suppressed |
| Font and size | Honored | Honored | Honored |
| Horizontal/vertical alignment | Honored | Honored | Honored |
| Column-width strategy | Honored | Honored | Honored |
| Cell margins and line spacing | Honored | Honored | Honored |

The existing unused `border_color` field is not activated for the theme-grid layout because doing so would change historical output. The two new neutral layouts use black borders by definition.

## Architecture

### Renderer

Keep `DocxRenderer.table()`, `table_head()`, `table_body()`, and `table_row()` as the single rendering path.

Add a small layout resolver that normalizes `table.layout` to one of the three supported values. Add one table-layout helper responsible for:

- Selecting or clearing the Word built-in table style.
- Writing explicit table borders for `three_line` and `plain_grid`.
- Writing the header separator for `three_line`.
- Reporting whether header and row shading are allowed.

`table()` creates the table and applies the layout. Existing width calculation and fixed table-grid sizing remain unchanged. `table_head()` and `table_row()` consult the normalized layout before applying shading, but otherwise keep their current formatting behavior.

Use direct OOXML borders for the two new layouts. Relying only on Word built-in styles cannot precisely control line presence and thickness, and may introduce theme colors, banding, or first-column emphasis.

### Style Management

Add `layout: accent_grid` to both the hardcoded fallback and packaged default configuration. `StyleManager.get_table_style()` remains unchanged.

Runtime configuration overrides continue to use the existing recursive merge. External configurations without `layout` remain valid because the renderer supplies the compatibility fallback.

### Default Configuration Editor

Reuse the existing schema-driven **表格** tab. Do not create a separate table editor or duplicate the table configuration form.

Add a read-only selector for `table.layout` with these display/value mappings:

| Display text | Stored value |
|---|---|
| 主题网格表（当前默认） | `accent_grid` |
| 三线表 | `three_line` |
| 简洁网格表 | `plain_grid` |

Extend the existing generic combobox rule with an optional display-to-value mapping. Existing enum fields continue using their current raw values. The table layout field uses the mapping so the UI remains clear while YAML remains stable.

Label the field **表格样式** in the table tab. Importing, restoring defaults, exporting, saving, and reopening the editor must preserve the stored English value.

This is intentionally a selector, not three independently editable nested configuration blocks. Shared table fields remain visible once, which avoids duplicating settings and matches the requirement to reuse the existing table code.

## Data Flow

1. The editor loads packaged defaults and the selected YAML using the existing merge logic.
2. The table tab displays the selected layout using its Chinese label.
3. Saving maps the display label back to the English configuration value.
4. `Converter` loads the saved YAML through the existing `StyleManager` path.
5. `DocxRenderer.table()` resolves the layout and applies its border/style preset.
6. Existing header and row methods render content using the same shared formatting code.

## Error Handling And Compatibility

- Missing `table.layout`: render `accent_grid`.
- Unknown `table.layout`: render `accent_grid` without aborting conversion.
- Unknown Word style in `accent_grid`: retain the existing `KeyError` fallback behavior.
- Existing custom YAML fields remain accepted and round-trip through the editor.
- Existing default table output must remain unchanged when `layout` is omitted or set to `accent_grid`.
- The editor exposes only valid values, preventing new invalid configurations through normal UI use.

## Considered Approaches

### 1. One Layout Selector With Shared Settings — Recommended

Add `table.layout` and centralize only the layout-specific visual behavior. This has the smallest configuration surface, preserves the existing renderer, and keeps the editor compact.

### 2. Three Nested Editable Preset Blocks

Store complete `accent_grid`, `three_line`, and `plain_grid` dictionaries and let users edit all three. This duplicates fonts, spacing, alignment, and width settings, makes the table tab much larger, and creates unclear override rules. It is unnecessary for the confirmed requirement.

### 3. Word Built-In Styles Only

Map each option to a Word style name. This requires almost no renderer code, but Word styles cannot reliably provide a standards-compliant three-line table and may add banding, theme colors, or first-column emphasis. This approach was rejected.

## Testing

### Renderer Tests

- Missing layout preserves the current theme-grid style and output properties.
- Explicit `accent_grid` matches missing-layout behavior.
- `three_line` writes only top, header-separator, and bottom borders with the specified widths.
- `three_line` omits header and body shading even when the shared configuration enables it.
- `plain_grid` writes black 0.5 pt outer and inner borders.
- `plain_grid` retains the configured light-gray header background and suppresses alternating rows.
- Invalid layout falls back to `accent_grid`.
- Existing column-width, alignment, vertical alignment, cell-margin, and repeating-header tests continue to pass for the default layout.

### GUI Tests

- The table-layout field is a read-only combobox.
- The combobox displays the three approved Chinese names.
- Each display name saves the correct English value.
- Loading an English value selects the correct Chinese display name.
- Restoring packaged defaults selects `主题网格表（当前默认）`.
- Import/export and save/reopen preserve `table.layout`.
- Existing widget-rule and unknown-field tests continue to pass.

### Verification

Run focused tests first, then the complete suite with `uv run`. Inspect generated OOXML for border presence, absence, color, and width rather than relying only on python-docx object properties.

## Scope

In scope:

- Three table layout presets.
- Backward-compatible YAML selection.
- Synchronized default configuration editor UI.
- Deterministic DOCX borders for the two new layouts.
- Focused documentation and automated tests.

Out of scope:

- Per-table layout directives inside Markdown.
- Editing three independent preset configurations.
- User-configurable border widths.
- Custom DOCX template import.
- Table captions, merged cells, manual column widths, or table-level page alignment.
