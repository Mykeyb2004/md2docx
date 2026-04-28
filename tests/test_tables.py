"""
Test table rendering functionality.
"""
import pytest
from pathlib import Path
import tempfile
from md2docx import Converter
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


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


def test_table_header_is_centered_both_horizontally_and_vertically():
    """Test table headers default to centered alignment in both directions."""
    converter = Converter()

    md_content = """
| 类型 | 主要特征 |
|------|----------|
| A | B |
"""

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name

    try:
        converter.convert_string(md_content, output_path)
        doc = Document(output_path)
        table = doc.tables[0]
        header_cell = table.rows[0].cells[0]
        header_paragraph = header_cell.paragraphs[0]

        assert header_paragraph.alignment == WD_PARAGRAPH_ALIGNMENT.CENTER
        assert header_cell.vertical_alignment == WD_CELL_VERTICAL_ALIGNMENT.CENTER
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_missing_separator_table_is_not_auto_fixed_by_default():
    """Malformed pipe blocks should stay plain text unless auto-fix is enabled."""
    converter = Converter()

    md_content = """
表格标题
| 列1 | 列2 | 列3 |
| A | B | C |
| D | E | F |
"""

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name

    try:
        converter.convert_string(md_content, output_path)
        doc = Document(output_path)

        assert len(doc.tables) == 0
        assert any('|' in p.text for p in doc.paragraphs)
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_missing_separator_table_can_be_auto_fixed_when_enabled():
    """Auto-fix should insert a separator row for high-confidence malformed tables."""
    converter = Converter(config_override={"document": {"auto_fix_tables": True}})

    md_content = """
表格标题
| 列1 | 列2 | 列3 |
| A | B | C |
| D | E | F |
"""

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name

    try:
        converter.convert_string(md_content, output_path)
        doc = Document(output_path)

        assert len(doc.tables) == 1
        table = doc.tables[0]
        assert len(table.rows) == 3
        assert table.rows[0].cells[0].text == "列1"
        assert table.rows[1].cells[1].text == "B"
        assert not any('| 列1 | 列2 | 列3 |' in p.text for p in doc.paragraphs)
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_captioned_malformed_table_can_be_split_and_fixed():
    """Single-cell caption lines should be preserved as text before the repaired table."""
    converter = Converter(config_override={"document": {"auto_fix_tables": True}})

    md_content = """
| 名录库维护关键节点与交付对照表 |
| 维护阶段 | 核心任务 | 输出成果 |
| 数据采集与清洗 | 跨源提取 | 清洗后基础数据集 |
| 数据审核与逻辑校验 | 表内表间逻辑比对 | 审核报告与异常工单 |
"""

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name

    try:
        converter.convert_string(md_content, output_path)
        doc = Document(output_path)

        assert len(doc.tables) == 1
        assert any(p.text == "名录库维护关键节点与交付对照表" for p in doc.paragraphs)
        table = doc.tables[0]
        assert table.rows[0].cells[0].text == "维护阶段"
        assert table.rows[1].cells[2].text == "清洗后基础数据集"
    finally:
        Path(output_path).unlink(missing_ok=True)
