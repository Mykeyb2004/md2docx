"""
Test list rendering functionality.
"""
import pytest
from pathlib import Path
import tempfile
from md2docx import Converter
from docx import Document


def test_unordered_list():
    """Test unordered list conversion."""
    converter = Converter()
    
    md_content = """# Lists Test

* Item 1
* Item 2
* Item 3
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = Document(output_path)
        # Should have heading + 3 list items
        assert len(doc.paragraphs) >= 4
        
        # Check list items exist
        list_items = [p for p in doc.paragraphs if 'List' in p.style.name]
        assert len(list_items) >= 3
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_ordered_list():
    """Test ordered list conversion."""
    converter = Converter()
    
    md_content = """# Ordered List

1. First item
2. Second item
3. Third item
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = Document(output_path)
        list_items = [p for p in doc.paragraphs if 'List' in p.style.name]
        assert len(list_items) >= 3
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_mixed_lists():
    """Test document with both ordered and unordered lists."""
    converter = Converter()
    
    md_content = """# Mixed Lists

Unordered:
* Apple
* Banana

Ordered:
1. First
2. Second
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = Document(output_path)
        list_items = [p for p in doc.paragraphs if 'List' in p.style.name]
        assert len(list_items) >= 4
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_real_document_with_lists():
    """Test converting a more complete document with lists."""
    converter = Converter()
    
    md_content = """# 项目文档

## 功能列表

项目具有以下功能：

1. Markdown 转换
2. 样式定制
3. 多种格式支持

## 主要特性

- 快速转换
- 高质量输出
- 易于使用
"""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        assert Path(output_path).exists()
        
        doc = Document(output_path)
        assert len(doc.paragraphs) > 5
    finally:
        Path(output_path).unlink(missing_ok=True)
