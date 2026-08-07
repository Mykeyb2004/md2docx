"""
Tests for configuration editor helpers.
"""
from pathlib import Path
import stat

import pytest

import md2docx.config_utils as config_utils_module
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


def test_save_yaml_config_preserves_existing_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch,
):
    """A failed atomic replace must leave the previous configuration readable."""
    config_path = tmp_path / "sample.yaml"
    original_text = "document:\n  page_size: A4\n"
    config_path.write_text(original_text, encoding="utf-8")

    def fail_replace(_source, _destination):
        raise OSError("replace blocked")

    monkeypatch.setattr(config_utils_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace blocked"):
        save_yaml_config(config_path, {"document": {"page_size": "Letter"}})

    assert config_path.read_text(encoding="utf-8") == original_text
    assert list(tmp_path.glob(".sample.yaml.*.tmp")) == []


def test_save_yaml_config_preserves_existing_file_mode(tmp_path: Path):
    """Atomic replacement should retain the mode of an existing config file."""
    config_path = tmp_path / "sample.yaml"
    config_path.write_text("document:\n  page_size: A4\n", encoding="utf-8")
    config_path.chmod(0o640)

    save_yaml_config(config_path, {"document": {"page_size": "Letter"}})

    assert stat.S_IMODE(config_path.stat().st_mode) == 0o640


def test_save_yaml_config_updates_symlink_target_without_replacing_link(tmp_path: Path):
    """Saving through a symlink should keep the link and update its target."""
    target_path = tmp_path / "actual.yaml"
    link_path = tmp_path / "alias.yaml"
    target_path.write_text("document:\n  page_size: A4\n", encoding="utf-8")
    link_path.symlink_to(target_path)

    save_yaml_config(link_path, {"document": {"page_size": "Letter"}})

    assert link_path.is_symlink()
    assert load_yaml_config(target_path)["document"]["page_size"] == "Letter"


def test_load_yaml_config_rejects_non_mapping(tmp_path: Path):
    """Top-level YAML must be a dict."""
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("- item\n- item2\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_yaml_config(config_path)
