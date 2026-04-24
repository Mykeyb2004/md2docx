"""
Markdown parser module.
"""
import re
from typing import Any, Dict, List, Optional
import mistune
from docx import Document
from md2docx.renderer import DocxRenderer
from md2docx.styles import StyleManager


CHINESE_NUMERALS = '零〇一二三四五六七八九十百千万'
OUTLINE_LEVEL1_RE = re.compile(rf'^\s*[{CHINESE_NUMERALS}]+、\s*\S')
OUTLINE_LEVEL2_RE = re.compile(rf'^\s*[（(][{CHINESE_NUMERALS}]+[）)]\s*\S')
OUTLINE_LEVEL3_RE = re.compile(r'^\s*\d+\.\s+\S')
OUTLINE_LEVEL4_RE = re.compile(r'^\s*[（(]\d+[）)]\s*\S')
MARKDOWN_HEADING_RE = re.compile(r'^\s*#{1,6}\s+')
MARKDOWN_ORDERED_LIST_RE = re.compile(r'^\s*\d+\.\s+\S')
MARKDOWN_UNORDERED_LIST_RE = re.compile(r'^\s*[*+-]\s+\S')
FENCE_RE = re.compile(r'^\s*(```|~~~)')


class MarkdownParser:
    """Markdown parser using mistune."""
    
    def __init__(self, style_manager: StyleManager) -> None:
        """
        Initialize parser.
        
        Args:
            style_manager: StyleManager instance for style configuration
        """
        self.style_manager = style_manager
        self.markdown = None
        self.renderer = None
        self.outline_processing: Dict[str, Any] = {
            'mode': 'auto',
            'active': False,
        }
    
    def parse(self, md_text: str, doc: Document) -> None:
        """
        Parse Markdown text and add content to document.
        
        Args:
            md_text: Markdown text to parse
            doc: python-docx Document object to add content to
        """
        # Preprocess: Convert LaTeX formulas to placeholders
        md_text = self._preprocess_math(md_text)
        md_text = self._preprocess_outline(md_text)
        
        # Create renderer with the document and style manager
        self.renderer = DocxRenderer(doc, self.style_manager)
        
        # Pass formulas to renderer
        self.renderer.math_formulas = self.math_formulas
        self.renderer.outline_processing = self.outline_processing
        
        # Create mistune Markdown instance with custom renderer and plugins
        self.markdown = mistune.create_markdown(
            renderer=self.renderer,
            plugins=['table']  # Enable table support
        )
        
        # Parse and render
        self.markdown(md_text)
    
    def _preprocess_math(self, md_text: str) -> str:
        """
        Preprocess LaTeX math expressions to custom tokens.
        
        Convert $...$ and $$...$$ to special markers that will be handled
        by the renderer. Use Unicode brackets that won't conflict with Markdown.
        """
        import re
        
        # Store math formulas
        self.math_formulas = {'inline': [], 'block': []}
        
        # Replace block math first ($$...$$)
        # Support both single-line and multi-line formats
        def replace_block_math(m):
            idx = len(self.math_formulas['block'])
            latex = m.group(1).strip()
            self.math_formulas['block'].append(latex)
            # Use Unicode brackets that won't be parsed as markdown
            return f'\n\n〔BLOCK_MATH_{idx}〕\n\n'
        
        # Match both: $$ ... $$ (single line) and $$\n...\n$$ (multi-line)
        md_text = re.sub(r'\$\$\s*(.+?)\s*\$\$', 
                        replace_block_math, 
                        md_text, 
                        flags=re.DOTALL)
        
        # Replace inline math ($...$)
        # Make sure not to match $$ (block math)
        def replace_inline_math(m):
            idx = len(self.math_formulas['inline'])
            self.math_formulas['inline'].append(m.group(1).strip())
            # Use Unicode brackets
            return f'〔INLINE_MATH_{idx}〕'
        
        md_text = re.sub(r'\$(?!\$)([^\$\n]+?)\$', 
                        replace_inline_math, 
                        md_text)
        
        # Pass formulas to renderer (will be set later)
        return md_text

    def _preprocess_outline(self, md_text: str) -> str:
        """
        Convert Chinese document outline markers into paragraph-safe Markdown.

        In official-document style writing, `1.` often means a level-3 outline
        heading rather than a Markdown ordered list. We only escape those lines
        when the document looks like a Chinese outline document and the numeric
        item is isolated from normal Markdown list blocks.
        """
        mode = str(
            self.style_manager.get_document_style().get('outline_mode', 'auto')
        ).lower()
        if mode not in {'off', 'auto', 'on'}:
            mode = 'auto'

        lines = md_text.splitlines()
        has_outline_context = any(
            OUTLINE_LEVEL1_RE.match(line)
            or OUTLINE_LEVEL2_RE.match(line)
            or OUTLINE_LEVEL4_RE.match(line)
            for line in lines
        )

        self.outline_processing = {
            'mode': mode,
            'active': mode == 'on' or has_outline_context,
        }

        if mode == 'off' or not self.outline_processing['active']:
            return md_text

        processed_lines = []
        in_fenced_block = False

        for idx, line in enumerate(lines):
            if FENCE_RE.match(line):
                processed_lines.append(line)
                in_fenced_block = not in_fenced_block
                continue

            if in_fenced_block or line.startswith('    ') or line.startswith('\t'):
                processed_lines.append(line)
                continue

            is_outline_heading = self._is_outline_heading_line(lines, idx, mode)

            if OUTLINE_LEVEL3_RE.match(line) and is_outline_heading:
                line = re.sub(r'^(\s*\d+)\.', r'\1\\.', line, count=1)

            if is_outline_heading and processed_lines and processed_lines[-1].strip():
                processed_lines.append('')

            processed_lines.append(line)

            if is_outline_heading and idx + 1 < len(lines) and lines[idx + 1].strip():
                processed_lines.append('')

        return '\n'.join(processed_lines)

    def _is_outline_heading_line(self, lines: List[str], index: int, mode: str) -> bool:
        """Return True when a line should be treated as an isolated outline heading."""
        line = lines[index]

        if OUTLINE_LEVEL1_RE.match(line) or OUTLINE_LEVEL2_RE.match(line) or OUTLINE_LEVEL4_RE.match(line):
            return True

        if OUTLINE_LEVEL3_RE.match(line):
            return self._should_escape_outline_number(lines, index, mode)

        return False

    def _should_escape_outline_number(self, lines: List[str], index: int, mode: str) -> bool:
        """Return True when an isolated `1.` line is more like an outline heading."""
        prev_idx = self._find_nonempty_line(lines, index - 1, -1)
        next_idx = self._find_nonempty_line(lines, index + 1, 1)

        if prev_idx is not None and MARKDOWN_ORDERED_LIST_RE.match(lines[prev_idx]):
            return False
        if next_idx is not None and MARKDOWN_ORDERED_LIST_RE.match(lines[next_idx]):
            return False

        if mode == 'on':
            return True

        if prev_idx is not None and (
            OUTLINE_LEVEL1_RE.match(lines[prev_idx])
            or OUTLINE_LEVEL2_RE.match(lines[prev_idx])
            or OUTLINE_LEVEL4_RE.match(lines[prev_idx])
            or self._is_plain_body_line(lines[prev_idx])
        ):
            return True

        if next_idx is not None and self._is_plain_body_line(lines[next_idx]):
            return True

        return False

    def _find_nonempty_line(self, lines: List[str], start: int, step: int) -> Optional[int]:
        """Find the nearest non-empty line index in the given direction."""
        idx = start
        while 0 <= idx < len(lines):
            if lines[idx].strip():
                return idx
            idx += step
        return None

    def _is_plain_body_line(self, line: str) -> bool:
        """Return True for normal paragraph-like lines, excluding Markdown blocks."""
        stripped = line.strip()
        if not stripped:
            return False
        if (
            MARKDOWN_HEADING_RE.match(line)
            or MARKDOWN_ORDERED_LIST_RE.match(line)
            or MARKDOWN_UNORDERED_LIST_RE.match(line)
            or FENCE_RE.match(line)
            or stripped.startswith('>')
            or stripped.startswith('|')
        ):
            return False
        return True
