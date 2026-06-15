"""
Markdown to Word converter.
"""
from typing import Any, Dict, Optional, Union
from pathlib import Path
from docx import Document

from md2docx.config_utils import merge_config
from md2docx.styles import StyleManager
from md2docx.parser import MarkdownParser


class Converter:
    """Main converter class for Markdown to Word conversion."""
    
    def __init__(
        self,
        template: Optional[str] = None,
        style_config: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize converter.
        
        Args:
            template: Name of predefined style template
            style_config: Path to custom YAML style configuration
            config_override: Runtime config overrides merged over the loaded style config
        """
        self.template = template
        self.style_config = style_config
        self.config_override = config_override or {}
        
        # Initialize style manager
        config_path = style_config or template
        self.style_manager = StyleManager(config_path)
        if self.config_override:
            self.style_manager.config = merge_config(
                self.style_manager.config,
                self.config_override,
            )
        
        # Initialize parser
        self.parser = MarkdownParser(self.style_manager)
    
    def convert(self, md_path: str, docx_path: str) -> None:
        """
        Convert Markdown file to Word document.
        
        Args:
            md_path: Path to input Markdown file
            docx_path: Path to output Word document
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            IOError: If there's an error reading/writing files
        """
        md_file = Path(md_path)
        
        if not md_file.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")
        
        # Read Markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Convert to Word
        self.convert_string(md_content, docx_path, base_dir=md_file.parent)
    
    def convert_string(
        self,
        md_content: str,
        docx_path: str,
        base_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        """
        Convert Markdown string to Word document.
        
        Args:
            md_content: Markdown content as string
            docx_path: Path to output Word document
            base_dir: Directory used to resolve relative image paths
            
        Raises:
            IOError: If there's an error writing the file
        """
        # Create document
        doc = self.to_document(md_content, base_dir=base_dir)
        
        # Save document
        output_path = Path(docx_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        doc.save(str(output_path))
    
    def to_document(
        self,
        md_content: str,
        base_dir: Optional[Union[str, Path]] = None,
    ) -> Document:
        """
        Convert Markdown string to Document object.
        
        Args:
            md_content: Markdown content as string
            base_dir: Directory used to resolve relative image paths
            
        Returns:
            python-docx Document object
        """
        # Create new document
        doc = Document()
        
        # Apply document-level styles
        doc_style = self.style_manager.get_document_style()
        
        # Apply document settings
        self._apply_document_settings(doc, doc_style)
        
        # Parse Markdown and add content to document
        self.parser.parse(md_content, doc, base_dir=base_dir)
        
        return doc
    
    def _apply_document_settings(self, doc: Document, style: dict) -> None:
        """
        Apply document-level settings like page size and margins.
        
        Args:
            doc: python-docx Document object
            style: Document style configuration
        """
        from docx.shared import Inches, Cm, Pt
        from docx.enum.section import WD_SECTION
        
        # Get the default section
        section = doc.sections[0]
        
        # Apply page size
        if 'page_size' in style:
            page_size = style['page_size'].upper()
            if page_size == 'A4':
                section.page_height = Cm(29.7)
                section.page_width = Cm(21.0)
            elif page_size == 'A3':
                section.page_height = Cm(42.0)
                section.page_width = Cm(29.7)
            elif page_size == 'LETTER':
                section.page_height = Inches(11)
                section.page_width = Inches(8.5)
        
        # Apply margins
        if 'margin_top' in style:
            section.top_margin = self._parse_length(style['margin_top'])
        
        if 'margin_bottom' in style:
            section.bottom_margin = self._parse_length(style['margin_bottom'])
        
        if 'margin_left' in style:
            section.left_margin = self._parse_length(style['margin_left'])
        
        if 'margin_right' in style:
            section.right_margin = self._parse_length(style['margin_right'])
    
    def _parse_length(self, length_str: str):
        """
        Parse length string to python-docx length object.
        
        Args:
            length_str: Length string like "2.54cm" or "1in"
            
        Returns:
            Length object (Inches, Cm, Pt, etc.)
        """
        from docx.shared import Inches, Cm, Pt, Mm
        
        length_str = str(length_str).lower().strip()
        
        if length_str.endswith('cm'):
            value = float(length_str[:-2])
            return Cm(value)
        elif length_str.endswith('in'):
            value = float(length_str[:-2])
            return Inches(value)
        elif length_str.endswith('mm'):
            value = float(length_str[:-2])
            return Mm(value)
        elif length_str.endswith('pt'):
            value = float(length_str[:-2])
            return Pt(value)
        else:
            # Default to cm
            return Cm(float(length_str))
