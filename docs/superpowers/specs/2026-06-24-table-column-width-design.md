# Table Column Width Design

## Goal

Improve Markdown table conversion so generated Word tables have more natural column widths. The default should reduce wasted space in short columns and give longer text columns more room, while still allowing a more conservative balanced strategy from YAML.

## Current Behavior

`DocxRenderer.table()` creates a Word table with the detected row and column count, then renders header and body cells. It does not explicitly set table or column widths, so Word decides layout. This can make Chinese business tables look uneven: short label columns may take too much width, and long description columns may wrap too aggressively.

## Configuration

Add `table.column_width_strategy` to the style configuration.

Supported values:

- `content-weighted`: default. Estimate each column's content weight from header and body cell text, then assign widths proportionally.
- `balanced`: estimate content weight, but apply stronger bounds so the result stays closer to equal-width columns.

Invalid or missing values fall back to `content-weighted`.

Example:

```yaml
table:
  column_width_strategy: balanced
```

## Width Calculation

Both strategies calculate widths against the document's available page width after margins.

`content-weighted`:

- Use rendered cell text to estimate column weight.
- Count wide CJK characters as heavier than narrow ASCII characters.
- Add small minimum weight for empty or very short columns.
- Clamp final column percentages to avoid unusably narrow or dominant columns.
- Normalize the clamped values so all columns fill the available table width.

`balanced`:

- Start from the same content weights.
- Blend the content-weighted result toward equal column widths.
- Apply tighter minimum and maximum bounds than `content-weighted`.
- Normalize the final widths to fill the available table width.

## Rendering Behavior

Set the Word table to fixed layout and apply calculated widths to:

- The table grid columns.
- Each cell's preferred width.

This makes the generated `.docx` carry stable width instructions instead of relying on Word's auto layout.

## Scope

In scope:

- Default content-weighted column widths.
- YAML override for balanced widths.
- Tests that inspect generated `.docx` table widths.
- Documentation update for the new table setting.

Out of scope:

- Per-column manual width declarations.
- Table caption detection changes.
- UI controls for choosing the strategy.
- Row height or cell padding changes.

## Tests

Add focused tests that:

- Convert a table with one short column and one long column, then assert default widths are not equal and the long column is wider.
- Convert the same table with `column_width_strategy: balanced`, then assert the widths are closer to equal than the default strategy.
- Keep existing table rendering tests passing.

Run tests with `uv run`, following project instructions.
