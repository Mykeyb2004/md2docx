# OMML Math Conversion Design

## Goal

Convert Markdown LaTeX math formulas into Word-native editable equations, not images, without hardcoding specific formulas.

## Architecture

Add a focused OMML conversion unit that delegates LaTeX parsing to Pandoc. The renderer will prefer OMML insertion for inline math, block math, and `latex` fenced code blocks, then fall back to the existing PNG renderer when Pandoc is unavailable or conversion fails.

## Components

- `md2docx/omml_converter.py`: Converts a LaTeX string to one or more OMML XML elements by creating a temporary Pandoc DOCX and extracting `m:oMath` or `m:oMathPara` nodes.
- `md2docx/renderer.py`: Owns Word document insertion. It will use `OmmlConverter` before `MathConverter`.
- `tests/test_math_rendering.py`: Verifies generated DOCX files contain OMML equation nodes and no picture drawing nodes for formulas that should convert.

## Data Flow

1. `MarkdownParser._preprocess_math()` stores `$...$` and `$$...$$` formulas as existing placeholders.
2. `DocxRenderer` sees a formula placeholder or a `latex` fenced code block.
3. `DocxRenderer` asks `OmmlConverter` for OMML elements.
4. If OMML conversion succeeds, the renderer appends the elements to the current Word paragraph.
5. If OMML conversion fails, the renderer uses the existing PNG formula rendering path.

## Error Handling

Pandoc failures, missing Pandoc executables, malformed LaTeX, and missing OMML output must not abort document conversion. They should trigger the existing LaTeX source or PNG fallback behavior.

## Testing

Tests will inspect `word/document.xml` inside generated DOCX files. Passing behavior requires `m:oMath` or `m:oMathPara` nodes, expected OMML structure such as `m:f` and `m:rad`, and no formula image drawing node for successful OMML conversions.
