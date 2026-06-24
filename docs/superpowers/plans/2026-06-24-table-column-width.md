# Table Column Width Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate Word tables with content-aware column widths by default, while allowing a YAML switch to a more conservative balanced strategy.

**Architecture:** Keep the change inside `DocxRenderer`: calculate column widths from the full table token before rendering cells, then apply fixed table/grid/cell widths to the python-docx table. Expose one configuration key, `table.column_width_strategy`, with `content-weighted` as the default and `balanced` as the alternate strategy.

**Tech Stack:** Python, python-docx, mistune table tokens, YAML style configuration, pytest via `uv run`.

---

## Context And Safety

- GitNexus impact analysis was run before planning changes.
- `DocxRenderer.table` upstream impact: LOW, 0 direct callers, 0 affected processes.
- `StyleManager.get_table_style` upstream impact: LOW, 0 direct callers, 0 affected processes.
- The worktree already contains unrelated user changes in `README.md`, `docs/STYLES_CONFIG.md`, `docs/UV_GUIDE.md`, `md2docx/cli.py`, `tests/CLI_TEST.md`, `tests/test_cli.py`, and `heading-center.yaml`. Do not revert them.

## File Structure

- Modify `md2docx/renderer.py`: add column-width helper methods and call them from `DocxRenderer.table()`.
- Modify `md2docx/styles.py`: add the default `table.column_width_strategy` fallback.
- Modify `md2docx/templates/default.yaml`: document the default packaged setting.
- Modify `tests/test_tables.py`: add focused tests that inspect generated table grid widths.
- Modify `docs/STYLES_CONFIG.md`: document the new YAML option.
- Modify `docs/TABLE_FEATURES.md`: include column width strategy in the table feature summary.

---

### Task 1: Add Failing Width Tests

**Files:**
- Modify: `tests/test_tables.py`

- [ ] **Step 1: Add XML width helpers and two failing tests**

Add these imports near the existing imports:

```python
from docx.oxml.ns import qn
```

Add these helpers after the imports:

```python
def _table_grid_widths(table):
    """Return table grid column widths in twips."""
    grid_cols = table._tbl.tblGrid.gridCol_lst
    widths = [col.get(qn("w:w")) for col in grid_cols]
    assert all(width is not None for width in widths)
    return [int(width) for width in widths]


def _width_spread(widths):
    """Return the absolute spread between the widest and narrowest columns."""
    return max(widths) - min(widths)
```

Add these tests after `test_table_with_chinese`:

```python
def test_default_table_column_widths_are_content_weighted():
    """Default table widths should give longer text columns more room."""
    converter = Converter()

    md_content = """
| 阶段 | 核心任务 | 成果 |
|------|----------|------|
| 采集 | 跨源提取、字段标准化、重复记录识别与基础数据质量校验 | 数据集 |
| 审核 | 表内表间逻辑比对、异常规则核查、疑似问题回溯定位 | 报告 |
"""

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name

    try:
        converter.convert_string(md_content, output_path)
        doc = Document(output_path)
        widths = _table_grid_widths(doc.tables[0])

        assert len(widths) == 3
        assert widths[1] > widths[0]
        assert widths[1] > widths[2]
        assert len(set(widths)) > 1
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_balanced_table_column_widths_are_more_even_than_default():
    """Balanced strategy should reduce the width spread for the same table."""
    md_content = """
| 阶段 | 核心任务 | 成果 |
|------|----------|------|
| 采集 | 跨源提取、字段标准化、重复记录识别与基础数据质量校验 | 数据集 |
| 审核 | 表内表间逻辑比对、异常规则核查、疑似问题回溯定位 | 报告 |
"""

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as default_file:
        default_output_path = default_file.name
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as balanced_file:
        balanced_output_path = balanced_file.name

    try:
        Converter().convert_string(md_content, default_output_path)
        Converter(
            config_override={"table": {"column_width_strategy": "balanced"}}
        ).convert_string(md_content, balanced_output_path)

        default_doc = Document(default_output_path)
        balanced_doc = Document(balanced_output_path)
        default_widths = _table_grid_widths(default_doc.tables[0])
        balanced_widths = _table_grid_widths(balanced_doc.tables[0])

        assert len(balanced_widths) == 3
        assert balanced_widths[1] > balanced_widths[0]
        assert balanced_widths[1] > balanced_widths[2]
        assert _width_spread(balanced_widths) < _width_spread(default_widths)
    finally:
        Path(default_output_path).unlink(missing_ok=True)
        Path(balanced_output_path).unlink(missing_ok=True)
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
uv run pytest tests/test_tables.py::test_default_table_column_widths_are_content_weighted tests/test_tables.py::test_balanced_table_column_widths_are_more_even_than_default -v
```

Expected: both tests fail because the generated table grid widths are equal or missing content-aware differences.

---

### Task 2: Implement Column Width Calculation

**Files:**
- Modify: `md2docx/renderer.py`

- [ ] **Step 1: Add python-docx XML imports**

Update the imports near the top of `md2docx/renderer.py`:

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
```

- [ ] **Step 2: Add helper methods to `DocxRenderer`**

Add these methods after `_get_available_page_width()`:

```python
    def _weighted_text_length(self, text: str) -> float:
        """Estimate text width, counting CJK characters as wider than ASCII."""
        weight = 0.0
        for char in text:
            if char.isspace():
                weight += 0.25
            elif '\u4e00' <= char <= '\u9fff':
                weight += 1.8
            elif ord(char) > 127:
                weight += 1.4
            else:
                weight += 1.0
        return weight

    def _plain_token_text(self, token: Dict[str, Any]) -> str:
        """Extract readable text from a mistune token tree without rendering."""
        if 'raw' in token:
            return str(token['raw'])

        if 'text' in token:
            return str(token['text'])

        children = token.get('children', [])
        if isinstance(children, list):
            return ''.join(self._plain_token_text(child) for child in children)

        return ''

    def _collect_table_column_weights(
        self,
        table_head: Optional[Dict[str, Any]],
        table_body: Optional[Dict[str, Any]],
        col_count: int,
    ) -> list[float]:
        """Estimate content weight for each table column."""
        weights = [1.0 for _ in range(col_count)]

        rows = []
        if table_head:
            rows.append(table_head)
        if table_body:
            rows.extend(table_body.get('children', []))

        for row_token in rows:
            cells = row_token.get('children', [])
            for col_idx, cell_token in enumerate(cells[:col_count]):
                text = self._plain_token_text(cell_token).strip()
                weights[col_idx] = max(weights[col_idx], self._weighted_text_length(text))

        return weights

    def _normalize_width_ratios(self, ratios: list[float], minimum: float, maximum: float) -> list[float]:
        """Clamp and normalize width ratios until they sum to 1.0."""
        if not ratios:
            return []

        clamped = [min(max(ratio, minimum), maximum) for ratio in ratios]
        total = sum(clamped)
        if total <= 0:
            return [1 / len(ratios) for _ in ratios]

        normalized = [ratio / total for ratio in clamped]
        for _ in range(4):
            adjusted = [min(max(ratio, minimum), maximum) for ratio in normalized]
            total = sum(adjusted)
            normalized = [ratio / total for ratio in adjusted]

        return normalized

    def _calculate_table_column_widths(
        self,
        table_head: Optional[Dict[str, Any]],
        table_body: Optional[Dict[str, Any]],
        col_count: int,
        table_style: Dict[str, Any],
    ) -> list[int]:
        """Calculate table column widths in EMUs."""
        if col_count <= 0:
            return []

        available_width = int(self._get_available_page_width())
        equal_ratio = 1 / col_count
        strategy = str(table_style.get('column_width_strategy', 'content-weighted')).lower()
        weights = self._collect_table_column_weights(table_head, table_body, col_count)
        weight_total = sum(weights)

        if weight_total <= 0:
            ratios = [equal_ratio for _ in range(col_count)]
        else:
            ratios = [weight / weight_total for weight in weights]

        if strategy == 'balanced':
            ratios = [(ratio * 0.45) + (equal_ratio * 0.55) for ratio in ratios]
            ratios = self._normalize_width_ratios(
                ratios,
                minimum=max(0.12, equal_ratio * 0.72),
                maximum=min(0.48, equal_ratio * 1.45),
            )
        else:
            ratios = self._normalize_width_ratios(
                ratios,
                minimum=max(0.08, equal_ratio * 0.38),
                maximum=min(0.62, equal_ratio * 2.15),
            )

        widths = [max(1, int(round(available_width * ratio))) for ratio in ratios]
        width_delta = available_width - sum(widths)
        if widths:
            widths[-1] += width_delta

        return widths

    def _set_table_column_widths(self, table: Any, widths: list[int]) -> None:
        """Apply fixed table and column widths to a python-docx table."""
        if not widths:
            return

        table.autofit = False
        table.allow_autofit = False

        tbl_pr = table._tbl.tblPr
        tbl_layout = tbl_pr.first_child_found_in('w:tblLayout')
        if tbl_layout is None:
            tbl_layout = OxmlElement('w:tblLayout')
            tbl_pr.append(tbl_layout)
        tbl_layout.set(qn('w:type'), 'fixed')

        table_width = sum(widths)
        tbl_w = tbl_pr.first_child_found_in('w:tblW')
        if tbl_w is None:
            tbl_w = OxmlElement('w:tblW')
            tbl_pr.append(tbl_w)
        tbl_w.set(qn('w:type'), 'dxa')
        tbl_w.set(qn('w:w'), str(int(round(table_width / 635))))

        grid = table._tbl.tblGrid
        for col_idx, width in enumerate(widths):
            if col_idx < len(grid.gridCol_lst):
                grid_col = grid.gridCol_lst[col_idx]
            else:
                grid_col = OxmlElement('w:gridCol')
                grid.append(grid_col)
            grid_col.set(qn('w:w'), str(int(round(width / 635))))

        for row in table.rows:
            for col_idx, cell in enumerate(row.cells):
                if col_idx >= len(widths):
                    continue

                cell.width = Emu(widths[col_idx])
                tc_pr = cell._tc.get_or_add_tcPr()
                tc_w = tc_pr.tcW
                if tc_w is None:
                    tc_w = OxmlElement('w:tcW')
                    tc_pr.append(tc_w)
                tc_w.set(qn('w:type'), 'dxa')
                tc_w.set(qn('w:w'), str(int(round(widths[col_idx] / 635))))
```

- [ ] **Step 3: Call the helper from `table()`**

In `DocxRenderer.table()`, immediately after table creation:

```python
        # Create table
        table = self.doc.add_table(rows=row_count, cols=col_count)
        column_widths = self._calculate_table_column_widths(
            table_head,
            table_body,
            col_count,
            table_style,
        )
        self._set_table_column_widths(table, column_widths)
```

- [ ] **Step 4: Run the focused table tests**

Run:

```bash
uv run pytest tests/test_tables.py::test_default_table_column_widths_are_content_weighted tests/test_tables.py::test_balanced_table_column_widths_are_more_even_than_default -v
```

Expected: both tests pass.

---

### Task 3: Add Defaults And Documentation

**Files:**
- Modify: `md2docx/styles.py`
- Modify: `md2docx/templates/default.yaml`
- Modify: `docs/STYLES_CONFIG.md`
- Modify: `docs/TABLE_FEATURES.md`

- [ ] **Step 1: Add the hardcoded default fallback**

In `StyleManager.DEFAULT_CONFIG["table"]`, add:

```python
            "column_width_strategy": "content-weighted",
```

Place it near the other table layout keys, after `"header_vertical_alignment": "center",`.

- [ ] **Step 2: Add the packaged template default**

In `md2docx/templates/default.yaml`, add:

```yaml
  column_width_strategy: content-weighted  # content-weighted=按内容自动分配；balanced=更均衡保守
```

Place it in the `table:` section after `header_vertical_alignment: center`.

- [ ] **Step 3: Update `docs/STYLES_CONFIG.md` table examples**

In the `### 6️⃣ table - 表格样式` YAML block, add:

```yaml
  column_width_strategy: content-weighted  # 列宽策略：content-weighted 或 balanced
```

In the parameter table, add this row:

```markdown
| `column_width_strategy` | 字符串 | `content-weighted` | `content-weighted`, `balanced` | 列宽策略：默认按内容分配，可切换为更均衡的保守分配 |
```

After the table alignment explanation, add:

```markdown
**列宽策略说明**：
- `content-weighted` - 默认策略。根据每列内容长度分配宽度，短列更窄，长文本列更宽。
- `balanced` - 均衡策略。仍参考内容长度，但更接近等宽，适合希望表格整体更规整的文档。
```

- [ ] **Step 4: Update `docs/TABLE_FEATURES.md`**

In the table configuration block, add:

```yaml
  column_width_strategy: content-weighted  # 列宽策略：content-weighted 或 balanced
```

In the completed feature list, add:

```markdown
### 4. 内容感知列宽 ✨ **NEW**

默认按内容长度分配 Word 表格列宽，让短列少占空间、长文本列获得更多空间。可在 YAML 中切换为更均衡的 `balanced` 策略。

**配置：**
```yaml
table:
  column_width_strategy: balanced
```
```

- [ ] **Step 5: Run documentation and table tests**

Run:

```bash
uv run pytest tests/test_tables.py tests/test_table_alignment.py -v
```

Expected: all tests in both files pass.

---

### Task 4: Full Verification

**Files:**
- No new edits unless verification exposes a bug.

- [ ] **Step 1: Run the full test suite**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run GitNexus change detection**

Run GitNexus detect changes:

```text
gitnexus_detect_changes(scope="all", repo="md2docx")
```

Expected: changed symbols are limited to table rendering/configuration/docs/tests, with no unexpected high-risk execution flows.

- [ ] **Step 3: Review git diff**

Run:

```bash
git diff -- md2docx/renderer.py md2docx/styles.py md2docx/templates/default.yaml tests/test_tables.py docs/STYLES_CONFIG.md docs/TABLE_FEATURES.md
```

Expected: diff only contains the column-width feature, tests, and documentation.

- [ ] **Step 4: Report results**

Report:

```text
Implemented default content-weighted table column widths and YAML-selectable balanced widths.
Verification:
- uv run pytest tests/test_tables.py tests/test_table_alignment.py -v
- uv run pytest
- GitNexus detect_changes
```

Mention any unrelated dirty files that were left untouched.
