"""
Markdown to Word converter.
"""
from typing import Optional
from pathlib import Path
from docx import Document

from md2docx.styles import StyleManager
from md2docx.parser import MarkdownParser


class Converter:
    """Main converter class for Markdown to Word conversion."""
    
    def __init__(
        self,
        template: Optional[str] = None,
        style_config: Optional[str] = None
    ) -> None:
        """
        Initialize converter.
        
        Args:
            template: Name of predefined style template
            style_config: Path to custom YAML style configuration
        """
        self.template = template
        self.style_config = style_config
        
        # Initialize style manager
        config_path = style_config or template
        self.style_manager = StyleManager(config_path)
        
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
        self.convert_string(md_content, docx_path)
    
    def convert_string(self, md_content: str, docx_path: str) -> None:
        """
        Convert Markdown string to Word document.
        
        Args:
            md_content: Markdown content as string
            docx_path: Path to output Word document
            
        Raises:
            IOError: If there's an error writing the file
        """
        # Create document
        doc = self.to_document(md_content)
        
        # Save document
        output_path = Path(docx_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        doc.save(str(output_path))
    
    def to_document(self, md_content: str) -> Document:
        """
        Convert Markdown string to Document object.
        
        Args:
            md_content: Markdown content as string
            
        Returns:
            python-docx Document object
        """
        # Create new document
        doc = Document()
        
        # Apply document-level styles
        doc_style = self.style_manager.get_document_style()
        
        # TODO: Apply document margins, page size, etc.
        # This requires more advanced document manipulation
        
        # Parse Markdown and add content to document
        self.parser.parse(md_content, doc)
        
        return doc

