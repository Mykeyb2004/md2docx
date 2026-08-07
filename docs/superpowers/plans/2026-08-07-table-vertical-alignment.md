# Table Vertical Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make table header and body text render vertically centered by default for all three table layouts.

**Architecture:** Keep the existing layout-specific border, shading, and Word table-style behavior. Normalize paragraph spacing at the table-cell rendering boundary by explicitly setting zero spacing before and after text paragraphs, while retaining the configured line spacing and vertical cell alignment.

**Tech Stack:** Python, `python-docx`, pytest, `uv run`.

---

### Task 1: Add regression coverage

**Files:**
- Modify: `tests/test_table_layouts.py`

- [x] **Step 1: Add a parameterized test for all layouts**

Assert that every layout sets header and body cells to `WD_CELL_VERTICAL_ALIGNMENT.CENTER`, with paragraph `space_before` and `space_after` explicitly set to zero.

- [x] **Step 2: Run the focused test and verify it fails**

Run: `MPLCONFIGDIR=/private/tmp/md2docx-mpl-cache UV_CACHE_DIR=/private/tmp/md2docx-uv-cache uv run pytest tests/test_table_layouts.py -k vertical -q`

Expected: FAIL for `plain_grid` and `three_line` because cell paragraph spacing is currently inherited rather than explicitly zeroed.

### Task 2: Normalize table-cell paragraph spacing

**Files:**
- Modify: `md2docx/renderer.py`

- [x] **Step 1: Add a small renderer helper**

Create `_apply_table_paragraph_spacing(paragraph, table_style)` near the existing cell-margin helper. Preserve configured `line_spacing`; set `space_before` and `space_after` to `Pt(0)`.

- [x] **Step 2: Use the helper for header and body paragraphs**

Call it in `table_head` and `table_row` immediately after text/line-spacing setup.

- [x] **Step 3: Run focused tests**

Run: `MPLCONFIGDIR=/private/tmp/md2docx-mpl-cache UV_CACHE_DIR=/private/tmp/md2docx-uv-cache uv run pytest tests/test_table_layouts.py -k vertical -q`

Expected: PASS for all three layouts.

### Task 3: Regression verification

**Files:** None

- [x] **Step 1: Run table regression tests**

Run: `MPLCONFIGDIR=/private/tmp/md2docx-mpl-cache UV_CACHE_DIR=/private/tmp/md2docx-uv-cache uv run pytest tests/test_table_layouts.py tests/test_tables.py -q`

Expected: all tests pass.

- [x] **Step 2: Run the broader suite**

Run: `MPLCONFIGDIR=/private/tmp/md2docx-mpl-cache UV_CACHE_DIR=/private/tmp/md2docx-uv-cache uv run pytest -q`

Expected: all tests pass.
