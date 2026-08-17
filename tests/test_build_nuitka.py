"""Tests for the repeatable Nuitka build pipeline."""
from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import build_nuitka


def test_parse_args_supports_macos_app_controls():
    args = build_nuitka.parse_args(
        ["--entry", "gui", "--mode", "app", "--clean", "--skip-tests", "--launch"]
    )

    assert args.entry == "gui"
    assert args.mode == "app"
    assert args.clean is True
    assert args.skip_tests is True
    assert args.launch is True


def test_parse_args_rejects_cli_app_mode(capsys):
    with pytest.raises(SystemExit) as exc_info:
        build_nuitka.parse_args(["--entry", "cli", "--mode", "app"])

    assert exc_info.value.code == 2
    assert "--mode app requires --entry gui" in capsys.readouterr().err


def test_parse_args_rejects_app_only_flags_for_legacy_modes(capsys):
    with pytest.raises(SystemExit) as exc_info:
        build_nuitka.parse_args(["--mode", "standalone", "--launch"])

    assert exc_info.value.code == 2
    assert "--skip-tests and --launch require --mode app" in capsys.readouterr().err


def test_app_command_creates_bundle_without_onefile():
    command = build_nuitka.build_nuitka_command("gui", "app")

    assert "--macos-create-app-bundle" in command
    assert "--macos-app-name=Md2docx" in command
    assert "--output-folder-name=Md2docx" in command
    assert "--output-filename=Md2docx" in command
    assert "--enable-plugin=tk-inter" in command
    assert "--mode=onefile" not in command
    assert "--mode=app" not in command


@pytest.mark.parametrize(
    ("entry", "mode", "relative_path"),
    [
        ("gui", "app", Path("Md2docx.app")),
        ("gui", "onefile", Path("md2docx-gui")),
        ("cli", "standalone", Path("md2docx-cli.dist/md2docx-cli")),
    ],
)
def test_expected_build_path_is_deterministic(entry, mode, relative_path):
    assert build_nuitka.expected_build_path(entry, mode) == (
        build_nuitka.OUTPUT_DIR / relative_path
    )


def test_remove_known_directory_rejects_unlisted_path(tmp_path):
    unsafe = tmp_path / "not-a-build-directory"
    unsafe.mkdir()

    with pytest.raises(ValueError, match="Refusing to remove unapproved directory"):
        build_nuitka.remove_known_directory(unsafe)

    assert unsafe.is_dir()


def test_remove_known_directory_removes_allowlisted_path(tmp_path, monkeypatch):
    removable = tmp_path / "macos.staging"
    removable.mkdir()
    (removable / "partial.txt").write_text("partial", encoding="utf-8")
    monkeypatch.setattr(
        build_nuitka,
        "KNOWN_REMOVABLE_DIRS",
        frozenset({removable.resolve()}),
    )

    build_nuitka.remove_known_directory(removable)

    assert not removable.exists()
