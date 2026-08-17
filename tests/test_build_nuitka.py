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


def test_preflight_rejects_non_macos(monkeypatch):
    monkeypatch.setattr(build_nuitka.sys, "platform", "linux")

    with pytest.raises(RuntimeError, match="requires macOS"):
        build_nuitka.preflight_macos_app(launch=False)


def test_preflight_rejects_non_arm64_python(monkeypatch):
    monkeypatch.setattr(build_nuitka.sys, "platform", "darwin")
    monkeypatch.setattr(build_nuitka.platform, "machine", lambda: "x86_64")

    with pytest.raises(RuntimeError, match="requires an arm64 Python"):
        build_nuitka.preflight_macos_app(launch=False)


def test_run_logged_streams_and_retains_output(tmp_path, capsys):
    log_path = tmp_path / "build.log"

    build_nuitka.run_logged(
        [sys.executable, "-c", "print('compiler output')"],
        log_path,
    )

    assert "compiler output" in capsys.readouterr().out
    assert "compiler output" in log_path.read_text(encoding="utf-8")


def test_run_logged_propagates_nonzero_exit(tmp_path):
    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        build_nuitka.run_logged(
            [sys.executable, "-c", "raise SystemExit(7)"],
            tmp_path / "build.log",
        )

    assert exc_info.value.returncode == 7


def test_run_test_suite_uses_active_python(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        build_nuitka,
        "run_logged",
        lambda command, log_path, env=None: calls.append((command, log_path)),
    )

    build_nuitka.run_test_suite(tmp_path / "build.log")

    assert calls == [([sys.executable, "-m", "pytest"], tmp_path / "build.log")]


def test_report_worktree_state_does_not_block_when_git_is_unavailable(
    monkeypatch, tmp_path, capsys
):
    def fail_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(build_nuitka.subprocess, "run", fail_git)
    log_path = tmp_path / "build.log"
    log_path.write_text("build\n", encoding="utf-8")

    build_nuitka.report_worktree_state(log_path)

    assert "unable to inspect Git worktree state" in capsys.readouterr().out
    assert "unable to inspect Git worktree state" in log_path.read_text(encoding="utf-8")


def test_build_target_uses_logged_runner_and_returns_app(monkeypatch, tmp_path):
    monkeypatch.setattr(build_nuitka, "OUTPUT_DIR", tmp_path / "nuitka")
    monkeypatch.setattr(build_nuitka.sys, "platform", "darwin")
    expected = build_nuitka.OUTPUT_DIR / build_nuitka.MACOS_APP_NAME
    calls = []

    def fake_run(command, log_path, env=None):
        calls.append((command, log_path, env))
        expected.mkdir(parents=True)

    monkeypatch.setattr(build_nuitka, "run_logged", fake_run)

    result = build_nuitka.build_target("gui", "app", tmp_path / "build.log")

    assert result == expected
    assert calls[0][1] == tmp_path / "build.log"
    assert "-Wl,-headerpad_max_install_names" in calls[0][2]["LDFLAGS"]


def test_main_preserves_legacy_build_flow(monkeypatch, tmp_path):
    executable = tmp_path / "md2docx-gui"
    config = tmp_path / "default.yaml"
    events = []
    args = argparse.Namespace(
        entry="gui",
        mode="onefile",
        clean=True,
        skip_tests=False,
        launch=False,
    )
    monkeypatch.setattr(build_nuitka, "parse_args", lambda argv=None: args)
    monkeypatch.setattr(
        build_nuitka,
        "prepare_build",
        lambda clean, app_mode: events.append(("prepare", clean, app_mode)),
    )
    monkeypatch.setattr(
        build_nuitka,
        "build_target",
        lambda entry, mode, log_path=None: events.append(("build", entry, mode))
        or executable,
    )
    monkeypatch.setattr(
        build_nuitka,
        "copy_editable_default_config",
        lambda path: events.append(("config", path)) or config,
    )

    result = build_nuitka.main([])

    assert result == 0
    assert events == [
        ("prepare", True, False),
        ("build", "gui", "onefile"),
        ("config", executable),
    ]


def make_fake_app(root: Path) -> Path:
    app_path = root / build_nuitka.MACOS_APP_NAME
    contents = app_path / "Contents"
    executable = contents / "MacOS" / build_nuitka.MACOS_PRODUCT_NAME
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"fake Mach-O")
    executable.chmod(0o755)
    resources = contents / "Resources"
    (resources / "md2docx" / "templates").mkdir(parents=True)
    (resources / "md2docx" / "templates" / "default.yaml").write_text(
        "paragraph: {}\n", encoding="utf-8"
    )
    (resources / "tcl8.6").mkdir()
    (resources / "tcl8.6" / "init.tcl").write_text("# tcl\n", encoding="utf-8")
    (resources / "tk8.6").mkdir()
    (resources / "tk8.6" / "tk.tcl").write_text("# tk\n", encoding="utf-8")
    with (contents / "Info.plist").open("wb") as plist_file:
        plistlib.dump({"CFBundleExecutable": build_nuitka.MACOS_PRODUCT_NAME}, plist_file)
    return app_path


def test_stage_macos_app_copies_bundle_and_editable_config(tmp_path):
    built_app = make_fake_app(tmp_path / "build")
    template = tmp_path / "default.yaml"
    template.write_text("paragraph: {}\n", encoding="utf-8")
    staging = tmp_path / "macos.staging"

    staged_app = build_nuitka.stage_macos_app(built_app, staging, template)

    assert staged_app == staging / build_nuitka.MACOS_APP_NAME
    assert (staged_app / "Contents" / "Info.plist").is_file()
    assert (staging / "default.yaml").read_text(encoding="utf-8") == "paragraph: {}\n"


def test_verify_macos_app_accepts_complete_arm64_bundle(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)

    def fake_run(command, **kwargs):
        if command[0] == "file":
            return subprocess.CompletedProcess(command, 0, "Mach-O 64-bit executable arm64\n", "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(build_nuitka.subprocess, "run", fake_run)

    executable = build_nuitka.verify_macos_app(app_path)

    assert executable == app_path / "Contents" / "MacOS" / "Md2docx"


def test_verify_macos_app_rejects_missing_info_plist(tmp_path):
    app_path = tmp_path / build_nuitka.MACOS_APP_NAME
    app_path.mkdir()

    with pytest.raises(RuntimeError, match="Info.plist"):
        build_nuitka.verify_macos_app(app_path)


def test_verify_macos_app_rejects_wrong_architecture(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)
    monkeypatch.setattr(
        build_nuitka.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "Mach-O 64-bit executable x86_64\n", ""
        ),
    )

    with pytest.raises(RuntimeError, match="does not contain arm64"):
        build_nuitka.verify_macos_app(app_path)


def test_verify_macos_app_rejects_missing_packaged_template(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)
    (app_path / "Contents" / "Resources" / "md2docx" / "templates" / "default.yaml").unlink()
    monkeypatch.setattr(
        build_nuitka.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "Mach-O 64-bit executable arm64\n", ""
        ),
    )

    with pytest.raises(RuntimeError, match="packaged md2docx template"):
        build_nuitka.verify_macos_app(app_path)


def test_verify_macos_app_rejects_missing_tk_resources(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)
    (app_path / "Contents" / "Resources" / "tk8.6" / "tk.tcl").unlink()
    monkeypatch.setattr(
        build_nuitka.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "Mach-O 64-bit executable arm64\n", ""
        ),
    )

    with pytest.raises(RuntimeError, match="Tk runtime"):
        build_nuitka.verify_macos_app(app_path)


def test_verify_macos_app_propagates_invalid_signature(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)

    def fake_run(command, **kwargs):
        if command[0] == "file":
            return subprocess.CompletedProcess(command, 0, "Mach-O 64-bit executable arm64\n", "")
        raise subprocess.CalledProcessError(1, command, stderr="invalid signature")

    monkeypatch.setattr(build_nuitka.subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        build_nuitka.verify_macos_app(app_path)


def test_sign_macos_app_uses_ad_hoc_identity(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)
    calls = []
    monkeypatch.setattr(
        build_nuitka.subprocess,
        "run",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )

    build_nuitka.sign_macos_app(app_path)

    assert calls[0][0] == [
        "codesign", "--force", "--deep", "--sign", "-", str(app_path)
    ]
    assert calls[0][1]["check"] is True


def test_promote_macos_app_replaces_verified_release(tmp_path, monkeypatch):
    final_dir = tmp_path / "macos"
    staging_dir = tmp_path / "macos.staging"
    backup_dir = tmp_path / "macos.backup"
    final_dir.mkdir()
    (final_dir / "old.txt").write_text("old", encoding="utf-8")
    make_fake_app(staging_dir)
    (staging_dir / "default.yaml").write_text("new\n", encoding="utf-8")
    monkeypatch.setattr(
        build_nuitka,
        "KNOWN_REMOVABLE_DIRS",
        frozenset({backup_dir.resolve()}),
    )

    app_path = build_nuitka.promote_macos_app(staging_dir, final_dir, backup_dir)

    assert app_path == final_dir / build_nuitka.MACOS_APP_NAME
    assert app_path.is_dir()
    assert not (final_dir / "old.txt").exists()
    assert not backup_dir.exists()


def test_promote_macos_app_restores_previous_release_on_rename_failure(
    tmp_path, monkeypatch
):
    final_dir = tmp_path / "macos"
    staging_dir = tmp_path / "macos.staging"
    backup_dir = tmp_path / "macos.backup"
    final_dir.mkdir()
    (final_dir / "old.txt").write_text("keep", encoding="utf-8")
    make_fake_app(staging_dir)
    monkeypatch.setattr(
        build_nuitka,
        "KNOWN_REMOVABLE_DIRS",
        frozenset({backup_dir.resolve()}),
    )
    real_replace = os.replace

    def fail_candidate_move(source, destination):
        if Path(source) == staging_dir:
            raise OSError("simulated promotion failure")
        real_replace(source, destination)

    monkeypatch.setattr(build_nuitka.os, "replace", fail_candidate_move)

    with pytest.raises(OSError, match="simulated promotion failure"):
        build_nuitka.promote_macos_app(staging_dir, final_dir, backup_dir)

    assert (final_dir / "old.txt").read_text(encoding="utf-8") == "keep"
