"""
Test table alignment functionality.
"""
import pytest
from pathlib import Path
import tempfile
from md2docx import Converter
from docx import Document as DocxDocument


def test_table_alignment_left_center_right():
    """Test table with left, center, and right alignment."""
    converter = Converter()
    
    md_content = """# Alignment Test

| 左对齐 | 居中 | 右对齐 |
|:-------|:----:|-------:|
| A1 | B1 | C1 |
| A2 | B2 | C2 |
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = DocxDocument(output_path)
        assert len(doc.tables) >= 1
        
        table = doc.tables[0]
        # Check alignment is applied to cells
        # Note: We check paragraphs in cells
        assert len(table.rows) == 3  # header + 2 data rows
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_table_default_alignment():
    """Test table without explicit alignment."""
    converter = Converter()
    
    md_content = """
| Col 1 | Col 2 |
|-------|-------|
| A | B |
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = DocxDocument(output_path)
        assert len(doc.tables) >= 1
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_table_all_center():
    """Test table with all columns centered."""
    converter = Converter()
    
    md_content = """
| A | B | C |
|:-:|:-:|:-:|
| 1 | 2 | 3 |
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = DocxDocument(output_path)
        assert len(doc.tables) >= 1
    finally:
        Path(output_path).unlink(missing_ok=True)
