"""Smoke tests for committed macOS app icon resources."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = REPO_ROOT / "assets" / "macos"


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS icon tools are platform-specific")
def test_committed_icon_assets_have_expected_format():
    svg = ICON_DIR / "AppIcon.svg"
    png = ICON_DIR / "AppIcon.png"
    icns = ICON_DIR / "AppIcon.icns"

    assert svg.is_file()
    assert png.is_file()
    assert icns.is_file()
    assert icns.stat().st_size > 0

    dimensions = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(png)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "pixelWidth: 1024" in dimensions
    assert "pixelHeight: 1024" in dimensions

    file_result = subprocess.run(
        ["file", str(icns)], check=True, capture_output=True, text=True
    ).stdout.lower()
    assert "icon" in file_result or "icns" in file_result
