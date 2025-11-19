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
        # Create renderer with the document and style manager
        self.renderer = DocxRenderer(doc, self.style_manager)
        
        # Create mistune Markdown instance with custom renderer and table plugin
        self.markdown = mistune.create_markdown(
            renderer=self.renderer,
            plugins=['table']  # Enable table support
        )
        
        # Parse and render
        self.markdown(md_text)


