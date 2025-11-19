"""
Tests for styles module.
"""
import pytest
from pathlib import Path
from md2docx.styles import StyleManager


def test_style_manager_initialization():
    """Test StyleManager can be initialized."""
    manager = StyleManager()
    assert manager is not None


def test_style_manager_loads_default_template():
    """Test StyleManager loads default template."""
    manager = StyleManager()
    assert manager.config is not None
    assert "heading1" in manager.config
    assert "paragraph" in manager.config


def test_get_heading_style():
    """Test getting heading styles for all levels."""
    manager = StyleManager()
    
    for level in range(1, 5):
        style = manager.get_heading_style(level)
        assert style is not None
        assert isinstance(style, dict)


def test_get_heading_style_invalid_level():
    """Test invalid heading level raises error."""
    manager = StyleManager()
    
    with pytest.raises(ValueError):
        manager.get_heading_style(0)
    
    with pytest.raises(ValueError):
        manager.get_heading_style(5)


def test_get_paragraph_style():
    """Test getting paragraph style."""
    manager = StyleManager()
    style = manager.get_paragraph_style()
    
    assert style is not None
    assert isinstance(style, dict)


def test_get_table_style():
    """Test getting table style."""
    manager = StyleManager()
    style = manager.get_table_style()
    
    assert style is not None
    assert isinstance(style, dict)


def test_get_list_style():
    """Test getting list style."""
    manager = StyleManager()
    style = manager.get_list_style()
    
    assert style is not None
    assert isinstance(style, dict)


def test_get_document_style():
    """Test getting document style."""
    manager = StyleManager()
    style = manager.get_document_style()
    
    assert style is not None
    assert isinstance(style, dict)


def test_load_template_by_name():
    """Test loading template by name."""
    manager = StyleManager(config_path="default")
    assert manager.config is not None
    assert "heading1" in manager.config
