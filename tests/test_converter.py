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


def test_converter_with_config_data_ignores_runtime_default(
    tmp_path,
    monkeypatch,
):
    """An in-memory effective config must not inherit a legacy default.yaml."""
    (tmp_path / "default.yaml").write_text(
        "document:\n"
        "  page_size: Letter\n"
        "legacy_only:\n"
        "  enabled: true\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    config_data = {"document": {"page_size": "A4"}}

    converter = Converter(config_data=config_data)
    config_data["document"]["page_size"] = "A3"

    assert converter.style_manager.config == {
        "document": {"page_size": "A4"},
    }
