"""
Tests for configuration editor helpers.
"""
from pathlib import Path

import pytest

from md2docx.config_utils import (
    build_config_schema,
    coerce_config_value,
    load_yaml_config,
    merge_config,
    save_yaml_config,
)


def test_merge_config_adds_defaults_and_preserves_overrides():
    """Merged config should contain defaults plus imported overrides."""
    base = {
        "document": {"page_size": "A4", "line_spacing": 1.5},
        "inline": {"bold": {"font_color": None}},
    }
    override = {
        "document": {"page_size": "Letter"},
        "extra": {"enabled": True},
    }

    merged = merge_config(base, override)

    assert merged["document"]["page_size"] == "Letter"
    assert merged["document"]["line_spacing"] == 1.5
    assert merged["inline"]["bold"]["font_color"] is None
    assert merged["extra"]["enabled"] is True


def test_build_config_schema_keeps_default_types_for_known_fields():
    """Schema should keep packaged default types while preserving unknown extras."""
    defaults = {
        "document": {"line_spacing": 1.5},
        "inline": {"bold": {"font_color": None}},
    }
    loaded = {
        "document": {"line_spacing": "custom-string"},
        "extra": {"threshold": 2},
    }

    schema = build_config_schema(defaults, loaded)

    assert schema["document"]["line_spacing"] == 1.5
    assert schema["inline"]["bold"]["font_color"] is None
    assert schema["extra"]["threshold"] == 2


@pytest.mark.parametrize(
    ("raw_value", "schema_value", "expected"),
    [
        ("2.0", 1.5, 2.0),
        ("3", 1, 3),
        ("A4", "Letter", "A4"),
        ("", None, None),
        ("#123456", None, "#123456"),
        (True, False, True),
    ],
)
def test_coerce_config_value(raw_value, schema_value, expected):
    """Widget values should be coerced back to schema types."""
    assert coerce_config_value(raw_value, schema_value) == expected


def test_save_and_load_yaml_config_roundtrip(tmp_path: Path):
    """Saved YAML should be readable again as a mapping."""
    config_path = tmp_path / "sample.yaml"
    config = {
        "document": {"page_size": "A4"},
        "inline": {"bold": {"font_color": None}},
    }

    save_yaml_config(config_path, config)
    loaded = load_yaml_config(config_path)

    assert loaded == config


def test_load_yaml_config_rejects_non_mapping(tmp_path: Path):
    """Top-level YAML must be a dict."""
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("- item\n- item2\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_yaml_config(config_path)
