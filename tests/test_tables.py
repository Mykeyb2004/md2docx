"""
Test table rendering functionality.
"""
import pytest
from pathlib import Path
import tempfile
from md2docx import Converter
from docx import Document


def test_simple_table():
    """Test simple table conversion."""
    converter = Converter()
    
    md_content = """# Table Test

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| A1       | B1       | C1       |
| A2       | B2       | C2       |
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = Document(output_path)
        # Should have 1 table
        assert len(doc.tables) >= 1
        
        # Check table dimensions
        table = doc.tables[0]
        assert len(table.rows) == 3  # header + 2 data rows
        assert len(table.columns) == 3
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_table_with_chinese():
    """Test table with Chinese content."""
    converter = Converter()
    
    md_content = """
| 姓名 | 年龄 | 城市 |
|------|------|------|
| 张三 | 25   | 北京 |
| 李四 | 30   | 上海 |
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = Document(output_path)
        assert len(doc.tables) >= 1
        
        table = doc.tables[0]
        # Check header
        assert "姓名" in table.rows[0].cells[0].text
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_mixed_content_with_table():
    """Test document with mixed content."""
    converter = Converter()
    
    md_content = """# Report

## Summary

This is a summary paragraph.

## Data Table

| Metric | Value | Change |
|--------|-------|--------|
| Users  | 1000  | +10%   |
| Revenue| $5000 | +15%   |

## Conclusion

End of report.
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = Document(output_path)
        assert len(doc.tables) >= 1
        assert len(doc.paragraphs) > 3
    finally:
        Path(output_path).unlink(missing_ok=True)
