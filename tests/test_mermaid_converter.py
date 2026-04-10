"""
Tests for Mermaid CLI command assembly and theme configuration.
"""
import json
from pathlib import Path
from types import SimpleNamespace

from docx import Document

import md2docx.mermaid_converter as mermaid_converter_module
from md2docx.mermaid_converter import MermaidConverter
from md2docx.renderer import DocxRenderer
from md2docx.styles import StyleManager


def _install_fake_mermaid_cli(monkeypatch, captured):
    """Stub subprocess.run so tests can inspect the generated CLI command."""

    def fake_run(command, check, capture_output, text):
        captured["command"] = command
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_bytes(b"png-bytes")

        if "-c" in command:
            config_path = Path(command[command.index("-c") + 1])
            captured["config"] = json.loads(config_path.read_text(encoding="utf-8"))

        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(mermaid_converter_module.subprocess, "run", fake_run)


def test_mermaid_converter_passes_theme_flag_without_custom_variables(monkeypatch, tmp_path):
    """Theme-only config should keep using Mermaid CLI's built-in theme flag."""
    captured = {}
    _install_fake_mermaid_cli(monkeypatch, captured)

    converter = MermaidConverter(
        cache_dir=tmp_path,
        command="mmdc",
        theme="forest",
        background_color="transparent",
    )

    image_bytes = converter._render_diagram("graph TD\nA-->B")

    assert image_bytes == b"png-bytes"
    assert captured["command"][0] == "mmdc"
    assert "-t" in captured["command"]
    assert captured["command"][captured["command"].index("-t") + 1] == "forest"
    assert "-c" not in captured["command"]


def test_mermaid_converter_uses_config_file_for_theme_variables(monkeypatch, tmp_path):
    """Theme variables should be passed to Mermaid CLI via a generated config file."""
    captured = {}
    _install_fake_mermaid_cli(monkeypatch, captured)

    converter = MermaidConverter(
        cache_dir=tmp_path,
        command="mmdc",
        theme_variables={
            "primaryColor": "#E8F1FF",
            "lineColor": "#2F6BFF",
        },
    )

    image_bytes = converter._render_diagram("graph TD\nA-->B")

    assert image_bytes == b"png-bytes"
    assert "-c" in captured["command"]
    assert "-t" not in captured["command"]
    assert captured["config"] == {
        "theme": "base",
        "themeVariables": {
            "lineColor": "#2F6BFF",
            "primaryColor": "#E8F1FF",
        },
    }


def test_mermaid_converter_forces_base_theme_when_theme_variables_are_present(monkeypatch, tmp_path):
    """Custom theme variables should force Mermaid's base theme so colors actually apply."""
    captured = {}
    _install_fake_mermaid_cli(monkeypatch, captured)

    converter = MermaidConverter(
        cache_dir=tmp_path,
        command="mmdc",
        theme="default",
        theme_variables={
            "primaryColor": "#E8F1FF",
            "lineColor": "#2F6BFF",
        },
    )

    converter._render_diagram("graph TD\nA-->B")

    assert captured["config"]["theme"] == "base"


def test_mermaid_cache_key_includes_theme_variables():
    """Theme variable differences should invalidate the Mermaid render cache."""
    converter_a = MermaidConverter(
        theme_variables={
            "lineColor": "#2F6BFF",
            "primaryColor": "#E8F1FF",
        }
    )
    converter_b = MermaidConverter(
        theme_variables={
            "primaryColor": "#E8F1FF",
            "lineColor": "#2F6BFF",
        }
    )
    converter_c = MermaidConverter(
        theme_variables={
            "lineColor": "#163A70",
            "primaryColor": "#E8F1FF",
        }
    )

    assert converter_a._get_cache_key("graph TD\nA-->B") == converter_b._get_cache_key("graph TD\nA-->B")
    assert converter_a._get_cache_key("graph TD\nA-->B") != converter_c._get_cache_key("graph TD\nA-->B")


def test_renderer_passes_theme_variables_to_mermaid_converter(monkeypatch):
    """Renderer should forward Mermaid theme config from the style manager."""
    captured = {}

    class DummyMermaidConverter:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(mermaid_converter_module, "MermaidConverter", DummyMermaidConverter)

    style_manager = StyleManager()
    style_manager.config.setdefault("mermaid", {}).update(
        {
            "theme": "base",
            "theme_variables": {
                "primaryColor": "#E8F1FF",
                "lineColor": "#2F6BFF",
            },
        }
    )

    DocxRenderer(Document(), style_manager)

    assert captured["theme"] == "base"
    assert captured["theme_variables"] == {
        "primaryColor": "#E8F1FF",
        "lineColor": "#2F6BFF",
    }
