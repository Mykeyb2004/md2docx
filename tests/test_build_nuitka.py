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
    assert "--output-filename=md2docx-app" in command
    assert "--enable-plugin=tk-inter" in command
    assert "--mode=onefile" not in command
    assert "--mode=app" not in command


def test_app_command_includes_committed_icon_path():
    command = build_nuitka.build_nuitka_command("gui", "app")

    assert f"--macos-app-icon={build_nuitka.MACOS_APP_ICON}" in command


def test_app_command_includes_header_icon_png():
    """The GUI header icon must be bundled alongside the macOS app icon."""
    command = build_nuitka.build_nuitka_command("gui", "app")

    assert (
        f"--include-data-file={build_nuitka.MACOS_HEADER_ICON}="
        "assets/macos/AppIcon.png"
    ) in command


def test_legacy_commands_do_not_include_macos_app_icon():
    for mode in ("onefile", "standalone"):
        command = build_nuitka.build_nuitka_command("gui", mode)

        assert not any(argument.startswith("--macos-app-icon=") for argument in command)


def test_project_pins_reproducible_macos_build_python():
    python_version = (build_nuitka.REPO_ROOT / ".python-version").read_text(
        encoding="utf-8"
    )

    assert python_version.strip() == "3.11.9"


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


def test_preflight_rejects_unpinned_python_version(monkeypatch):
    monkeypatch.setattr(build_nuitka.sys, "platform", "darwin")
    monkeypatch.setattr(build_nuitka.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(build_nuitka.sys, "version_info", (3, 12, 11))

    with pytest.raises(RuntimeError, match="requires Python 3.11.9"):
        build_nuitka.preflight_macos_app(launch=False)


def test_preflight_rejects_missing_app_icon(monkeypatch, tmp_path):
    monkeypatch.setattr(build_nuitka.sys, "platform", "darwin")
    monkeypatch.setattr(build_nuitka.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(build_nuitka.sys, "version_info", (3, 11, 9))
    monkeypatch.setattr(build_nuitka.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(build_nuitka.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(build_nuitka, "MACOS_APP_ICON", tmp_path / "missing.icns")
    monkeypatch.setattr(build_nuitka, "BUILD_ROOT", tmp_path / "build")
    monkeypatch.setattr(build_nuitka, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(build_nuitka, "DIST_ROOT", tmp_path / "dist")

    with pytest.raises(FileNotFoundError, match="AppIcon.icns|missing.icns"):
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
    icon_name = "AppIcon.icns"
    (resources / icon_name).write_bytes(b"fake icns")
    with (contents / "Info.plist").open("wb") as plist_file:
        plistlib.dump(
            {
                "CFBundleExecutable": build_nuitka.MACOS_PRODUCT_NAME,
                "CFBundleIconFile": icon_name,
            },
            plist_file,
        )
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


def test_verify_macos_app_rejects_missing_icon_declaration(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)
    plist_path = app_path / "Contents" / "Info.plist"
    with plist_path.open("rb") as plist_file:
        bundle_info = plistlib.load(plist_file)
    bundle_info.pop("CFBundleIconFile")
    with plist_path.open("wb") as plist_file:
        plistlib.dump(bundle_info, plist_file)
    monkeypatch.setattr(
        build_nuitka.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "Mach-O 64-bit executable arm64\n", ""
        ),
    )

    with pytest.raises(RuntimeError, match="CFBundleIconFile"):
        build_nuitka.verify_macos_app(app_path)


def test_verify_macos_app_rejects_missing_icon_resource(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)
    (app_path / "Contents" / "Resources" / "AppIcon.icns").unlink()
    monkeypatch.setattr(
        build_nuitka.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "Mach-O 64-bit executable arm64\n", ""
        ),
    )

    with pytest.raises(RuntimeError, match="icon"):
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


def app_args(**overrides):
    values = {
        "entry": "gui",
        "mode": "app",
        "clean": False,
        "skip_tests": False,
        "launch": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_app_pipeline_runs_stages_in_order_without_default_launch(tmp_path, monkeypatch):
    events = []
    built_app = tmp_path / "build" / build_nuitka.MACOS_APP_NAME
    staged_app = tmp_path / "staging" / build_nuitka.MACOS_APP_NAME
    final_app = tmp_path / "macos" / build_nuitka.MACOS_APP_NAME
    monkeypatch.setattr(build_nuitka, "BUILD_LOG", tmp_path / "build.log")
    monkeypatch.setattr(build_nuitka, "preflight_macos_app", lambda launch: events.append("preflight"))
    monkeypatch.setattr(build_nuitka, "initialize_build_log", lambda path: events.append("log"))
    monkeypatch.setattr(build_nuitka, "report_worktree_state", lambda path: events.append("git"))
    monkeypatch.setattr(build_nuitka, "run_test_suite", lambda path: events.append("tests"))
    monkeypatch.setattr(
        build_nuitka, "prepare_build", lambda clean, app_mode: events.append("prepare")
    )

    def fake_build(entry, mode, log_path):
        events.append("compile")
        return built_app

    def fake_stage(app):
        events.append("stage")
        return staged_app

    monkeypatch.setattr(build_nuitka, "build_target", fake_build)
    monkeypatch.setattr(build_nuitka, "stage_macos_app", fake_stage)
    monkeypatch.setattr(build_nuitka, "sign_macos_app", lambda app: events.append("sign"))
    monkeypatch.setattr(build_nuitka, "verify_macos_app", lambda app: events.append("verify"))
    monkeypatch.setattr(
        build_nuitka,
        "promote_macos_app",
        lambda: events.append("promote") or final_app,
    )
    monkeypatch.setattr(build_nuitka, "launch_macos_app", lambda app: events.append("launch"))

    result = build_nuitka.run_macos_app_pipeline(app_args())

    assert events == [
        "preflight", "log", "git", "tests", "prepare", "compile",
        "stage", "sign", "verify", "promote",
    ]
    assert result.app_path == final_app
    assert result.tests_ran is True
    assert result.launched is False


def test_app_pipeline_skips_tests_and_launches_only_after_promotion(tmp_path, monkeypatch):
    events = []
    candidate = tmp_path / "staging" / build_nuitka.MACOS_APP_NAME
    final_app = tmp_path / "macos" / build_nuitka.MACOS_APP_NAME
    monkeypatch.setattr(build_nuitka, "BUILD_LOG", tmp_path / "build.log")
    monkeypatch.setattr(build_nuitka, "preflight_macos_app", lambda launch: None)
    monkeypatch.setattr(build_nuitka, "initialize_build_log", lambda path: None)
    monkeypatch.setattr(build_nuitka, "report_worktree_state", lambda path: None)
    monkeypatch.setattr(
        build_nuitka,
        "run_test_suite",
        lambda path: pytest.fail("tests must be skipped"),
    )
    monkeypatch.setattr(build_nuitka, "prepare_build", lambda clean, app_mode: None)
    monkeypatch.setattr(build_nuitka, "build_target", lambda entry, mode, log: candidate)
    monkeypatch.setattr(build_nuitka, "stage_macos_app", lambda app: candidate)
    monkeypatch.setattr(build_nuitka, "sign_macos_app", lambda app: None)
    monkeypatch.setattr(build_nuitka, "verify_macos_app", lambda app: None)
    monkeypatch.setattr(
        build_nuitka,
        "promote_macos_app",
        lambda: events.append("promote") or final_app,
    )
    monkeypatch.setattr(
        build_nuitka,
        "launch_macos_app",
        lambda app: events.append("launch"),
    )

    result = build_nuitka.run_macos_app_pipeline(
        app_args(skip_tests=True, launch=True)
    )

    assert events == ["promote", "launch"]
    assert result.tests_ran is False
    assert result.launched is True


@pytest.mark.parametrize(
    ("failing_function", "expected_events", "expected_stage"),
    [
        ("stage_macos_app", [], "staging failed"),
        ("verify_macos_app", ["sign"], "verification failed"),
    ],
)
def test_app_pipeline_never_promotes_after_candidate_failure(
    tmp_path, monkeypatch, failing_function, expected_events, expected_stage
):
    events = []
    monkeypatch.setattr(build_nuitka, "BUILD_LOG", tmp_path / "build.log")
    monkeypatch.setattr(build_nuitka, "preflight_macos_app", lambda launch: None)
    monkeypatch.setattr(build_nuitka, "initialize_build_log", lambda path: None)
    monkeypatch.setattr(build_nuitka, "report_worktree_state", lambda path: None)
    monkeypatch.setattr(build_nuitka, "run_test_suite", lambda path: None)
    monkeypatch.setattr(build_nuitka, "prepare_build", lambda clean, app_mode: None)
    monkeypatch.setattr(
        build_nuitka,
        "build_target",
        lambda entry, mode, log: tmp_path / "built" / build_nuitka.MACOS_APP_NAME,
    )
    monkeypatch.setattr(
        build_nuitka,
        "stage_macos_app",
        lambda app: tmp_path / "staging" / build_nuitka.MACOS_APP_NAME,
    )
    monkeypatch.setattr(build_nuitka, "sign_macos_app", lambda app: events.append("sign"))
    monkeypatch.setattr(build_nuitka, "verify_macos_app", lambda app: None)

    def fail_candidate(app):
        raise RuntimeError("candidate is invalid")

    monkeypatch.setattr(build_nuitka, failing_function, fail_candidate)
    monkeypatch.setattr(
        build_nuitka,
        "promote_macos_app",
        lambda: events.append("promote"),
    )

    with pytest.raises(build_nuitka.BuildPipelineError, match=expected_stage):
        build_nuitka.run_macos_app_pipeline(app_args())

    assert events == expected_events


def test_run_stage_labels_failures():
    def fail():
        raise OSError("disk full")

    with pytest.raises(
        build_nuitka.BuildPipelineError,
        match="staging failed: disk full",
    ):
        build_nuitka.run_stage("staging", fail)


def test_launch_macos_app_uses_open(tmp_path, monkeypatch):
    app_path = tmp_path / build_nuitka.MACOS_APP_NAME
    calls = []
    monkeypatch.setattr(
        build_nuitka.subprocess,
        "run",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )

    build_nuitka.launch_macos_app(app_path)

    assert calls == [(["open", str(app_path)], {"cwd": build_nuitka.REPO_ROOT, "check": True})]


def test_print_app_summary_reports_paths_and_size(tmp_path, capsys):
    app_path = tmp_path / build_nuitka.MACOS_APP_NAME
    app_path.mkdir()
    (app_path / "payload.bin").write_bytes(b"x" * 1024)
    result = build_nuitka.BuildResult(
        app_path=app_path,
        config_path=tmp_path / "default.yaml",
        log_path=tmp_path / "build.log",
        elapsed_seconds=1.25,
        tests_ran=True,
        cleaned=True,
        launched=False,
    )

    build_nuitka.print_app_summary(result)

    output = capsys.readouterr().out
    assert "macOS app build succeeded" in output
    assert str(app_path) in output
    assert "0.0 MiB" in output
    assert "Elapsed time:     1.2s" in output


def test_main_returns_nonzero_and_names_failed_stage(monkeypatch, capsys):
    monkeypatch.setattr(build_nuitka, "parse_args", lambda argv=None: app_args())

    def fail_pipeline(args):
        raise build_nuitka.BuildPipelineError("tests", "pytest exited 1")

    monkeypatch.setattr(build_nuitka, "run_macos_app_pipeline", fail_pipeline)

    result = build_nuitka.main([])

    assert result == 1
    assert "Build failed: tests failed: pytest exited 1" in capsys.readouterr().err
