"""
Test the full conversion workflow.
"""
import pytest
from pathlib import Path
import tempfile
from md2docx import Converter
from docx.document import Document as DocxDocument


def test_convert_string_basic():
    """Test basic string conversion."""
    converter = Converter()
    
    md_content = """# Test Heading

This is a paragraph with **bold** and *italic* text.

## Second Heading

Another paragraph."""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        
        # Verify file was created
        assert Path(output_path).exists()
        
        # Verify content
        from docx import Document
        doc = Document(output_path)
        assert len(doc.paragraphs) > 0
        
        # Check headings
        assert "Test Heading" in doc.paragraphs[0].text
        assert "Second Heading" in [p.text for p in doc.paragraphs]
    finally:
        # Cleanup
        Path(output_path).unlink(missing_ok=True)


def test_convert_file():
    """Test file conversion."""
    converter = Converter()
    
    # Create temporary Markdown file
    md_content = """# File Test

This is a test from a file."""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(md_content)
        md_path = f.name
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        docx_path = f.name
    
    try:
        converter.convert(md_path, docx_path)
        
        # Verify output file exists
        assert Path(docx_path).exists()
        
        # Verify content
        from docx import Document
        doc = Document(docx_path)
        assert "File Test" in doc.paragraphs[0].text
    finally:
        # Cleanup
        Path(md_path).unlink(missing_ok=True)
        Path(docx_path).unlink(missing_ok=True)


def test_convert_file_not_found():
    """Test error handling for missing file."""
    converter = Converter()
    
    with pytest.raises(FileNotFoundError):
        converter.convert("nonexistent.md", "output.docx")


def test_to_document():
    """Test to_document method."""
    converter = Converter()
    
    md_content = "# Test\n\nParagraph."
    doc = converter.to_document(md_content)
    
    assert isinstance(doc, DocxDocument)
    assert len(doc.paragraphs) > 0


def test_converter_with_template():
    """Test converter with template."""
    converter = Converter(template="default")
    
    md_content = "# Test"
    doc = converter.to_document(md_content)
    
    assert isinstance(doc, DocxDocument)
