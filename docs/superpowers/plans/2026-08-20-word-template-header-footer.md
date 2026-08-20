# Word Template Header and Footer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional `.docx` template support that preserves template headers, footers, images, fields, and geometry while exposing the option in the CLI and GUI.

**Architecture:** Keep the existing no-template `Document()` path unchanged. Add a `word_template` input to `Converter`, load the template as the document package, clear only body blocks, and skip YAML page geometry when a template is active. Add an independent CLI flag and a GUI path selector whose value is snapshotted before background conversion.

**Tech Stack:** Python 3.11, `python-docx`, Tkinter, argparse, pytest, `uv run`.

---

### Task 1: Converter Template Loading

**Files:**
- Modify: `md2docx/converter.py:28-143`
- Test: `tests/test_integration.py`

- [x] **Step 1: Write failing template-preservation tests**

Add tests that create a one-section DOCX template with formatted primary, first-page, and even-page headers/footers and a PNG in the primary header. Convert Markdown with conflicting YAML page settings and assert the output preserves header/footer XML, relationships, media bytes, section flags, distances, and template geometry while removing the placeholder body.

Also add tests for missing template, non-DOCX suffix, and multi-section templates raising the documented exceptions.

- [x] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/test_integration.py -k 'word_template or multi_section_template' -q
```

Expected: FAIL because `Converter` does not accept `word_template` and still always creates a blank document.

- [x] **Step 3: Implement the minimal converter behavior**

Add `word_template: Optional[str] = None` to `Converter.__init__`. In `to_document()`, load `Document(word_template)` when set, validate existence, `.docx` suffix, and exactly one section, remove all body children except `w:sectPr`, skip `_apply_document_settings()`, then parse Markdown and apply metadata as before. Keep the existing `Document()` and settings path when the option is absent.

- [x] **Step 4: Run focused tests to verify they pass**

Run:

```bash
uv run pytest tests/test_integration.py -k 'word_template or multi_section_template' -q
```

Expected: PASS.

- [x] **Step 5: Run existing converter integration tests**

Run:

```bash
uv run pytest tests/test_integration.py -q
```

Expected: PASS with no-template behavior unchanged.

### Task 2: CLI Option

**Files:**
- Modify: `md2docx/cli.py:35-163`
- Test: `tests/test_cli.py`

- [x] **Step 1: Write a failing CLI integration test**

Create a DOCX template with a footer, invoke `main()` with `--word-template`, and assert the output contains the Markdown body and the template footer. Assert `--word-template` can coexist with `--template default`.

- [x] **Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest tests/test_cli.py -k word_template -q
```

Expected: FAIL because argparse does not recognize `--word-template`.

- [x] **Step 3: Implement CLI propagation**

Add `--word-template FILE` to the parser and pass `args.word_template` to `Converter` for both single-file and directory conversions. Leave existing YAML option conflict validation unchanged.

- [x] **Step 4: Run CLI tests**

Run:

```bash
uv run pytest tests/test_cli.py -q
```

Expected: PASS.

### Task 3: GUI Template Selector

**Files:**
- Modify: `md2docx/gui.py:1514-1591,1649-1680,1805-1893`
- Test: `tests/test_gui.py`

- [x] **Step 1: Write failing GUI state and conversion tests**

Test that the conversion panel creates a read-only Word-template entry, that choosing a `.docx` updates the variable, clearing it empties the variable, invalid paths are rejected before starting a worker, and `_do_conversion()` passes a selected path snapshot to `Converter` while retaining the existing no-template call shape.

- [x] **Step 2: Run the GUI tests to verify they fail**

Run:

```bash
uv run pytest tests/test_gui.py -k 'word_template or conversion_uses_saved_config' -q
```

Expected: FAIL because the GUI has no Word-template variable, selector, validation, or converter argument.

- [x] **Step 3: Implement the GUI controls and propagation**

Add a `word_template_var` row with a read-only entry, `Choose...` button, and `Clear` button. Add `browse_word_template()` and `clear_word_template()`. In `convert_file()`, validate an optional selected path exists and has a `.docx` suffix before starting the thread. Pass the string snapshot into `_do_conversion(input_file, output_file, word_template_file=None)`. Add the constructor keyword only when a non-empty template was selected, preserving existing test doubles and no-template behavior.

- [x] **Step 4: Run GUI tests**

Run:

```bash
uv run pytest tests/test_gui.py -q
```

Expected: PASS.

### Task 4: Documentation and Full Verification

**Files:**
- Modify: `README.md:50-100,120-140`
- Modify: `docs/STYLES_CONFIG.md` or a focused new usage section if needed

- [x] **Step 1: Document API, CLI, GUI, and template constraints**

Document `word_template`, `--word-template`, the GUI selector, `.docx`-only support, single-section limitation, template geometry precedence, and the requirement that template styles/numbering support the existing renderer.

- [x] **Step 2: Run the full test suite**

Run:

```bash
uv run pytest -q
```

Expected: PASS with zero failures.

- [x] **Step 3: Check formatting and affected scope**

Run:

```bash
git diff --check
```

Then run GitNexus `detect_changes({scope: "all", repo: "md2docx"})` and confirm only the converter, CLI, GUI, tests, and documentation symbols are affected.
