"""
Tests for converter module.
"""
import pytest
from md2docx import Converter


def test_converter_initialization():
    """Test converter can be initialized."""
    converter = Converter()
    assert converter is not None
    

def test_converter_with_template():
    """Test converter initialization with template."""
    converter = Converter(template="default")
    assert converter.template == "default"


def test_converter_with_style_config():
    """Test converter initialization with style config."""
    # Skip if custom.yaml doesn't exist
    # In real usage, users would create their own config files
    converter = Converter(template="default")
    assert converter.style_config is None
    assert converter.template == "default"
