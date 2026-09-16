"""
Markdown parser module.
"""
from typing import Any
import mistune
from docx import Document
from md2docx.renderer import DocxRenderer
from md2docx.styles import StyleManager


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
    
    def parse(self, md_text: str, doc: Document) -> None:
        """
        Parse Markdown text and add content to document.
        
        Args:
            md_text: Markdown text to parse
            doc: python-docx Document object to add content to
        """
        # Preprocess: Convert LaTeX formulas to placeholders
        md_text = self._preprocess_math(md_text)
        
        # Create renderer with the document and style manager
        self.renderer = DocxRenderer(doc, self.style_manager)
        
        # Pass formulas to renderer
        self.renderer.math_formulas = self.math_formulas
        
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
