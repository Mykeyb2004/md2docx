# macOS App Build Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Nuitka build script with one repeatable command that produces, verifies, ad-hoc signs, and safely publishes a fast-starting Apple Silicon `Md2docx.app`.

**Architecture:** Keep `scripts/build_nuitka.py` as the only public build entry point and preserve its existing onefile/standalone workflows. Add a macOS-only app pipeline whose stages are independently testable: argument validation, preflight, tests/logging, compilation, staging, signing/verification, atomic promotion, summary, and optional launch. Build into `build/nuitka`, validate a candidate in `dist/macos.staging`, and rename it to `dist/macos` only after every check passes so a failed build cannot replace the last successful app.

**Tech Stack:** Python 3.8+, uv, pytest, Nuitka 4.x, macOS `file`, `codesign`, and `open` tools, standard-library `argparse`, `plistlib`, `subprocess`, `shutil`, and `pathlib`.

---

## File map

- Create `tests/test_build_nuitka.py`: unit tests for CLI parsing, command generation, preflight, logging, staging, verification, promotion, and orchestration. Tests use temporary fake bundles and never invoke a real Nuitka build.
- Modify `scripts/build_nuitka.py`: retain the existing public entry point while adding the app-mode pipeline and small stage functions.
- Modify `docs/NUITKA_BUILD.md`: make the macOS app pipeline the recommended local macOS workflow and retain the existing Windows/legacy mode documentation.

Do not modify or stage the user's current changes in `md2docx/gui.py`, `tests/test_gui.py`, or the unrelated output-overwrite plan/spec files.

### Task 1: Define the app-mode CLI, deterministic paths, and safe preparation

**Files:**

- Create: `tests/test_build_nuitka.py`
- Modify: `scripts/build_nuitka.py:1-45`

- [ ] **Step 1: Write failing CLI, command, path, and deletion-safety tests**

Create `tests/test_build_nuitka.py` with these imports, helper, and tests:

```python
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
```

- [ ] **Step 2: Run the new tests and verify that they fail for missing app-mode behavior**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -v
```

Expected: collection succeeds, then tests fail because `parse_args()` does not accept an argument list and `build_nuitka_command`, `expected_build_path`, and `remove_known_directory` do not exist.

- [ ] **Step 3: Replace the old constants, add stage error/result types, and validate app-mode arguments**

In `scripts/build_nuitka.py`, keep the module docstring and `from __future__ import annotations`, then replace the remaining imports and constant block above `executable_name()` with this complete block:

```python
import argparse
import importlib.util
import os
import platform
import plistlib
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, FrozenSet, Mapping, Optional, Sequence, TypeVar


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_ROOT = REPO_ROOT / "build"
OUTPUT_DIR = BUILD_ROOT / "nuitka"
LOG_DIR = BUILD_ROOT / "logs"
BUILD_LOG = LOG_DIR / "macos-app-build.log"
DIST_ROOT = REPO_ROOT / "dist"
MACOS_DIST_DIR = DIST_ROOT / "macos"
MACOS_STAGING_DIR = DIST_ROOT / "macos.staging"
MACOS_BACKUP_DIR = DIST_ROOT / "macos.backup"
MACOS_PRODUCT_NAME = "Md2docx"
MACOS_APP_NAME = f"{MACOS_PRODUCT_NAME}.app"
DEFAULT_TEMPLATE = REPO_ROOT / "md2docx" / "templates" / "default.yaml"
KNOWN_REMOVABLE_DIRS: FrozenSet[Path] = frozenset(
    path.resolve()
    for path in (OUTPUT_DIR, MACOS_STAGING_DIR, MACOS_BACKUP_DIR)
)


class BuildPipelineError(RuntimeError):
    """Failure attributed to one named build pipeline stage."""

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(f"{stage} failed: {detail}")
        self.stage = stage


@dataclass(frozen=True)
class BuildResult:
    """Published macOS build metadata used by the final summary."""

    app_path: Path
    config_path: Path
    log_path: Path
    elapsed_seconds: float
    tests_ran: bool
    cleaned: bool
    launched: bool


T = TypeVar("T")
```

Replace `parse_args()` with:

```python
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse and validate command line arguments."""
    parser = argparse.ArgumentParser(
        description="Build md2docx executables with Nuitka.",
    )
    parser.add_argument(
        "--entry",
        choices=("gui", "cli"),
        default="gui",
        help="Application entry point to build.",
    )
    parser.add_argument(
        "--mode",
        choices=("onefile", "standalone", "app"),
        default="onefile",
        help="Nuitka build mode.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove known intermediate output before compiling.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip repository tests before a macOS app build.",
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Open the verified macOS app after promotion.",
    )
    args = parser.parse_args(argv)
    if args.mode == "app" and args.entry != "gui":
        parser.error("--mode app requires --entry gui")
    if args.mode != "app" and (args.skip_tests or args.launch):
        parser.error("--skip-tests and --launch require --mode app")
    return args
```

- [ ] **Step 4: Add deterministic command/path construction and allowlisted cleanup**

Add these functions before `build_target()`:

```python
def build_nuitka_command(entry: str, mode: str) -> list:
    """Return the Nuitka command for one supported target."""
    if mode == "app" and entry != "gui":
        raise ValueError("app mode supports only the gui entry point")

    source_file = REPO_ROOT / "md2docx" / f"{entry}.py"
    binary_name = MACOS_PRODUCT_NAME if mode == "app" else f"md2docx-{entry}"
    command = [sys.executable, "-m", "nuitka"]
    if mode == "app":
        command.extend(
            [
                "--macos-create-app-bundle",
                f"--macos-app-name={MACOS_PRODUCT_NAME}",
                f"--output-folder-name={MACOS_PRODUCT_NAME}",
            ]
        )
    else:
        command.append(f"--mode={mode}")
    command.extend(
        [
            "--assume-yes-for-downloads",
            "--include-package-data=md2docx",
            "--include-package=mistune.plugins",
            f"--output-dir={OUTPUT_DIR}",
            f"--output-filename={binary_name}",
            str(source_file),
        ]
    )
    if entry == "gui":
        command.append("--enable-plugin=tk-inter")
    return command


def expected_build_path(entry: str, mode: str) -> Path:
    """Return the exact artifact path produced by the configured command."""
    if mode == "app":
        return OUTPUT_DIR / MACOS_APP_NAME
    binary_name = f"md2docx-{entry}"
    target_name = executable_name(binary_name)
    if mode == "onefile":
        return OUTPUT_DIR / target_name
    return OUTPUT_DIR / f"{binary_name}.dist" / target_name


def remove_known_directory(path: Path) -> None:
    """Remove only an explicitly allowlisted build directory."""
    resolved = path.resolve()
    if resolved not in KNOWN_REMOVABLE_DIRS:
        raise ValueError(f"Refusing to remove unapproved directory: {path}")
    if path.exists():
        shutil.rmtree(path)


def prepare_build(clean: bool, app_mode: bool) -> None:
    """Prepare known build locations without touching promoted output."""
    if clean:
        remove_known_directory(OUTPUT_DIR)
    if app_mode:
        remove_known_directory(MACOS_STAGING_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
```

On Python 3.8, keep the return annotation of `build_nuitka_command()` as plain `list`; do not replace it with `list[str]`.

- [ ] **Step 5: Run the focused tests and verify that Task 1 passes**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -v
```

Expected: all Task 1 tests pass.

- [ ] **Step 6: Inspect scope and commit only Task 1 files**

Run GitNexus `detect_changes(scope="unstaged", repo="md2docx")`. Expected: only the build script symbols and the new build test module are reported; no GUI execution flow is affected.

Then run:

```bash
git diff -- scripts/build_nuitka.py tests/test_build_nuitka.py
git add scripts/build_nuitka.py tests/test_build_nuitka.py
git commit -m "feat: define macOS app build mode"
```

Expected: the commit contains no user-owned GUI or output-overwrite files.

### Task 2: Add macOS preflight, streamed logs, tests, and compilation

**Files:**

- Modify: `tests/test_build_nuitka.py`
- Modify: `scripts/build_nuitka.py`

- [ ] **Step 1: Append failing tests for preflight and logged commands**

Append to `tests/test_build_nuitka.py`:

```python
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
```

- [ ] **Step 2: Run the new tests and verify that they fail for missing functions/signature changes**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -k "preflight or logged or test_suite or build_target" -v
```

Expected: FAIL because `preflight_macos_app`, `run_logged`, and `run_test_suite` are absent and `build_target()` still has its old signature.

- [ ] **Step 3: Implement preflight and non-blocking dirty-worktree reporting**

Add before `build_target()`:

```python
def preflight_macos_app(launch: bool) -> None:
    """Validate requirements for a local Apple Silicon app build."""
    if sys.platform != "darwin":
        raise RuntimeError("macOS app mode requires macOS")
    if platform.machine() != "arm64":
        raise RuntimeError("macOS app mode requires an arm64 Python")
    for required in (REPO_ROOT / "md2docx" / "gui.py", DEFAULT_TEMPLATE):
        if not required.is_file():
            raise FileNotFoundError(f"required input is missing: {required}")
    if importlib.util.find_spec("nuitka") is None:
        raise RuntimeError("Nuitka is unavailable; run with --group build")
    required_tools = ["file", "codesign"]
    if launch:
        required_tools.append("open")
    missing_tools = [name for name in required_tools if shutil.which(name) is None]
    if missing_tools:
        raise RuntimeError(f"missing macOS tools: {', '.join(missing_tools)}")
    for location in (BUILD_ROOT, LOG_DIR, DIST_ROOT):
        if location.exists() and not location.is_dir():
            raise RuntimeError(f"output location is not a directory: {location}")


def initialize_build_log(log_path: Path) -> None:
    """Start a fresh diagnostic log for one app pipeline run."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("md2docx macOS app build\n", encoding="utf-8")


def report_worktree_state(log_path: Path) -> None:
    """Report a dirty tree without blocking a local build."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        message = "Warning: unable to inspect Git worktree state."
    else:
        if result.returncode != 0:
            message = "Warning: unable to inspect Git worktree state."
        elif result.stdout.strip():
            message = "Warning: Git worktree has uncommitted changes:\n" + result.stdout.rstrip()
        else:
            message = "Git worktree is clean."
    print(message)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")
```

- [ ] **Step 4: Implement streaming command logs and test execution**

Add:

```python
def run_logged(
    command: Sequence[str],
    log_path: Path,
    env: Optional[Mapping[str, str]] = None,
) -> None:
    """Stream combined command output to the terminal and append it to a log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        rendered = shlex.join(list(command))
        log_file.write(f"\n$ {rendered}\n")
        log_file.flush()
        process = subprocess.Popen(
            list(command),
            cwd=REPO_ROOT,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if process.stdout is None:
            process.kill()
            raise RuntimeError("unable to capture command output")
        for line in process.stdout:
            print(line, end="")
            log_file.write(line)
            log_file.flush()
        return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, list(command))


def run_test_suite(log_path: Path) -> None:
    """Run repository tests with the active uv-managed Python."""
    run_logged([sys.executable, "-m", "pytest"], log_path)
```

- [ ] **Step 5: Refactor compilation to use the deterministic command and optional log**

Replace `build_target()` with:

```python
def build_target(entry: str, mode: str, log_path: Optional[Path] = None) -> Path:
    """Run Nuitka and return the expected artifact path."""
    command = build_nuitka_command(entry, mode)
    env = os.environ.copy()
    if sys.platform == "darwin":
        extra_flag = "-Wl,-headerpad_max_install_names"
        ldflags = env.get("LDFLAGS", "").strip()
        if extra_flag not in ldflags:
            env["LDFLAGS"] = f"{ldflags} {extra_flag}".strip()

    if log_path is None:
        subprocess.run(command, check=True, cwd=REPO_ROOT, env=env)
    else:
        run_logged(command, log_path, env=env)

    target = expected_build_path(entry, mode)
    if not target.exists():
        raise FileNotFoundError(f"Nuitka did not create expected artifact: {target}")
    return target
```

- [ ] **Step 6: Run focused and existing build-mode tests**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -v
```

Expected: all tests pass. Confirm from the command-construction assertions that legacy onefile/standalone flags remain unchanged and app mode never contains `--mode=onefile`.

- [ ] **Step 7: Inspect scope and commit Task 2**

Run GitNexus `detect_changes(scope="unstaged", repo="md2docx")`, then:

```bash
git diff -- scripts/build_nuitka.py tests/test_build_nuitka.py
git add scripts/build_nuitka.py tests/test_build_nuitka.py
git commit -m "feat: add macOS build preflight and logs"
```

Expected: only the build script and its dedicated tests are committed.

### Task 3: Stage, ad-hoc sign, verify, and safely promote the app

**Files:**

- Modify: `tests/test_build_nuitka.py`
- Modify: `scripts/build_nuitka.py`

- [ ] **Step 1: Add a reusable fake app-bundle fixture**

Append this helper to `tests/test_build_nuitka.py`:

```python
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
```

- [ ] **Step 2: Append failing staging and bundle-verification tests**

Append:

```python
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
```

- [ ] **Step 3: Append failing signing and safe-promotion tests**

Append:

```python
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
```

- [ ] **Step 4: Run the Task 3 tests and verify that the new APIs are missing**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -k "stage_macos or verify_macos or sign_macos or promote_macos" -v
```

Expected: FAIL because the four app artifact functions are not defined.

- [ ] **Step 5: Implement staging and ad-hoc signing**

Add to `scripts/build_nuitka.py`:

```python
def stage_macos_app(
    built_app: Path,
    staging_dir: Path = MACOS_STAGING_DIR,
    template: Path = DEFAULT_TEMPLATE,
) -> Path:
    """Copy a built app and editable example config into candidate staging."""
    if staging_dir.exists():
        raise FileExistsError(f"staging directory already exists: {staging_dir}")
    staging_dir.mkdir(parents=True)
    staged_app = staging_dir / MACOS_APP_NAME
    shutil.copytree(built_app, staged_app, symlinks=True)
    shutil.copy2(template, staging_dir / "default.yaml")
    return staged_app


def sign_macos_app(app_path: Path) -> None:
    """Refresh the candidate bundle's local ad-hoc signature."""
    subprocess.run(
        ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
        cwd=REPO_ROOT,
        check=True,
    )
```

- [ ] **Step 6: Implement bundle, architecture, resource, and signature verification**

Add:

```python
def verify_macos_app(app_path: Path) -> Path:
    """Verify bundle structure, architecture, resources, and signature."""
    info_plist = app_path / "Contents" / "Info.plist"
    if not info_plist.is_file():
        raise RuntimeError(f"missing bundle Info.plist: {info_plist}")
    with info_plist.open("rb") as plist_file:
        bundle_info = plistlib.load(plist_file)
    executable_name_value = bundle_info.get("CFBundleExecutable")
    if not isinstance(executable_name_value, str) or not executable_name_value:
        raise RuntimeError("Info.plist has no valid CFBundleExecutable")
    executable = app_path / "Contents" / "MacOS" / executable_name_value
    if not executable.is_file():
        raise RuntimeError(f"bundle executable is missing: {executable}")

    file_result = subprocess.run(
        ["file", str(executable)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    architecture_text = f"{file_result.stdout}\n{file_result.stderr}"
    if "arm64" not in architecture_text:
        raise RuntimeError(f"bundle executable does not contain arm64: {architecture_text.strip()}")

    packaged_template = any(
        path.is_file()
        and tuple(path.parts[-3:]) == ("md2docx", "templates", "default.yaml")
        for path in app_path.rglob("default.yaml")
    )
    if not packaged_template:
        raise RuntimeError("bundle is missing packaged md2docx template")
    has_tcl = any(
        path.is_file() and path.parent.name.startswith("tcl")
        for path in app_path.rglob("init.tcl")
    )
    has_tk = any(
        path.is_file() and path.parent.name.startswith("tk")
        for path in app_path.rglob("tk.tcl")
    )
    if not has_tcl:
        raise RuntimeError("bundle is missing Tcl runtime")
    if not has_tk:
        raise RuntimeError("bundle is missing Tk runtime")

    subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(app_path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return executable
```

- [ ] **Step 7: Implement backup-aware promotion**

Add:

```python
def promote_macos_app(
    staging_dir: Path = MACOS_STAGING_DIR,
    final_dir: Path = MACOS_DIST_DIR,
    backup_dir: Path = MACOS_BACKUP_DIR,
) -> Path:
    """Atomically publish a verified candidate and preserve the old release on failure."""
    candidate_app = staging_dir / MACOS_APP_NAME
    if not candidate_app.is_dir():
        raise RuntimeError(f"verified candidate app is missing: {candidate_app}")
    final_dir.parent.mkdir(parents=True, exist_ok=True)

    if backup_dir.exists():
        if final_dir.exists():
            remove_known_directory(backup_dir)
        else:
            os.replace(backup_dir, final_dir)

    moved_previous = False
    if final_dir.exists():
        os.replace(final_dir, backup_dir)
        moved_previous = True
    try:
        os.replace(staging_dir, final_dir)
    except OSError:
        if moved_previous and backup_dir.exists() and not final_dir.exists():
            os.replace(backup_dir, final_dir)
        raise
    if backup_dir.exists():
        remove_known_directory(backup_dir)
    return final_dir / MACOS_APP_NAME
```

Because verification runs before this function, staging or verification failures do not call `promote_macos_app()` and leave the existing `dist/macos` directory untouched. A failed candidate remains under `dist/macos.staging` for inspection until the next build preparation.

- [ ] **Step 8: Run all build-script tests**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -v
```

Expected: all tests pass, including simulated promotion failure restoring `old.txt`.

- [ ] **Step 9: Inspect scope and commit Task 3**

Run GitNexus `detect_changes(scope="unstaged", repo="md2docx")`, then:

```bash
git diff -- scripts/build_nuitka.py tests/test_build_nuitka.py
git add scripts/build_nuitka.py tests/test_build_nuitka.py
git commit -m "feat: verify and safely publish macOS app"
```

Expected: only the app artifact pipeline and its unit tests are committed.

### Task 4: Wire ordered orchestration, summaries, legacy modes, and optional launch

**Files:**

- Modify: `tests/test_build_nuitka.py`
- Modify: `scripts/build_nuitka.py`

- [ ] **Step 1: Append failing orchestration and launch-order tests**

Append:

```python
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
```

- [ ] **Step 2: Run the orchestration tests and verify that they fail for missing functions**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -k "app_pipeline or run_stage" -v
```

Expected: FAIL because `run_macos_app_pipeline()` and `run_stage()` are absent.

- [ ] **Step 3: Implement stage attribution and optional launch**

Add:

```python
def run_stage(stage: str, action: Callable[[], T]) -> T:
    """Run one stage and attach its name to any failure."""
    try:
        return action()
    except BuildPipelineError:
        raise
    except Exception as exc:
        raise BuildPipelineError(stage, str(exc)) from exc


def launch_macos_app(app_path: Path) -> None:
    """Open a promoted app only when explicitly requested."""
    subprocess.run(["open", str(app_path)], cwd=REPO_ROOT, check=True)
```

- [ ] **Step 4: Implement ordered app orchestration**

Add:

```python
def run_macos_app_pipeline(args: argparse.Namespace) -> BuildResult:
    """Build, verify, publish, and optionally launch the macOS app."""
    started = time.monotonic()
    run_stage("preflight", lambda: preflight_macos_app(args.launch))
    run_stage("logging", lambda: initialize_build_log(BUILD_LOG))
    run_stage("logging", lambda: report_worktree_state(BUILD_LOG))
    if not args.skip_tests:
        run_stage("tests", lambda: run_test_suite(BUILD_LOG))
    run_stage("preparation", lambda: prepare_build(args.clean, app_mode=True))
    built_app = run_stage(
        "compilation",
        lambda: build_target("gui", "app", BUILD_LOG),
    )
    staged_app = run_stage("staging", lambda: stage_macos_app(built_app))

    def sign_and_verify() -> None:
        sign_macos_app(staged_app)
        verify_macos_app(staged_app)

    run_stage("verification", sign_and_verify)
    final_app = run_stage("promotion", promote_macos_app)
    if args.launch:
        run_stage("launch", lambda: launch_macos_app(final_app))
    return BuildResult(
        app_path=final_app,
        config_path=final_app.parent / "default.yaml",
        log_path=BUILD_LOG,
        elapsed_seconds=time.monotonic() - started,
        tests_ran=not args.skip_tests,
        cleaned=args.clean,
        launched=args.launch,
    )
```

- [ ] **Step 5: Add a concise success summary**

Add:

```python
def directory_size(path: Path) -> int:
    """Return the byte size of regular files inside a directory."""
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def format_megabytes(byte_count: int) -> str:
    """Format bytes for the human-readable build summary."""
    return f"{byte_count / (1024 * 1024):.1f} MiB"


def print_app_summary(result: BuildResult) -> None:
    """Print paths and choices for a successful pipeline run."""
    print("macOS app build succeeded")
    print(f"Application:      {result.app_path}")
    print(f"Editable config:  {result.config_path}")
    print(f"Diagnostics:      {result.log_path}")
    print(f"Application size: {format_megabytes(directory_size(result.app_path))}")
    print(f"Elapsed time:     {result.elapsed_seconds:.1f}s")
    print(f"Tests:            {'ran' if result.tests_ran else 'skipped'}")
    print(f"Clean build:      {'yes' if result.cleaned else 'no'}")
    print(f"Launched:         {'yes' if result.launched else 'no'}")
```

- [ ] **Step 6: Replace `main()` while preserving onefile/standalone behavior**

Replace the existing `main()` and module guard with:

```python
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build the requested target and return a process exit code."""
    args = parse_args(argv)
    try:
        if args.mode == "app":
            result = run_macos_app_pipeline(args)
            print_app_summary(result)
            return 0

        run_stage(
            "preparation",
            lambda: prepare_build(args.clean, app_mode=False),
        )
        executable_path = run_stage(
            "compilation",
            lambda: build_target(args.entry, args.mode),
        )
        config_path = run_stage(
            "staging",
            lambda: copy_editable_default_config(executable_path),
        )
    except BuildPipelineError as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built executable: {executable_path}")
    print(f"Editable config:  {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Run the build-script tests and confirm ordered behavior**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -v
```

Expected: all tests pass; the event assertions prove that tests precede compilation, promotion follows verification, and `open` runs only after successful promotion.

- [ ] **Step 8: Run the full repository test suite**

Run:

```bash
uv run pytest
```

Expected: all existing tests pass. If a failure comes from the user's already-modified `md2docx/gui.py` or `tests/test_gui.py`, record it separately and do not alter those files as part of this pipeline task.

- [ ] **Step 9: Inspect scope and commit Task 4**

Run GitNexus `detect_changes(scope="unstaged", repo="md2docx")`. Expected risk remains LOW because the build workflow is the only affected execution path.

Then run:

```bash
git diff -- scripts/build_nuitka.py tests/test_build_nuitka.py
git add scripts/build_nuitka.py tests/test_build_nuitka.py
git commit -m "feat: orchestrate repeatable macOS app builds"
```

### Task 5: Document the command and complete a real local acceptance build

**Files:**

- Modify: `docs/NUITKA_BUILD.md:1-58`
- Verify: `dist/macos/Md2docx.app`
- Verify: `build/logs/macos-app-build.log`

- [ ] **Step 1: Replace the macOS-facing portion of the build guide with exact usage**

At the start of `docs/NUITKA_BUILD.md`, replace the goal, recommended-command, output, and explanation sections before `## GitHub Actions 构建 Windows EXE` with:

````markdown
# Nuitka 打包

## macOS Apple Silicon 推荐方式

在仓库根目录执行：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode app
```

该命令会依次检查环境、运行测试、编译、暂存、进行本地 ad-hoc 签名、验证并发布应用。最终产物为：

```text
dist/macos/
├── Md2docx.app
└── default.yaml
```

`Md2docx.app` 使用 Nuitka standalone app bundle，不是 onefile，因此启动时不需要先把约 100 MB 的运行环境解压到临时目录。`default.yaml` 是可编辑示例；应用内部仍包含 `md2docx/templates/default.yaml`，删除外部示例不会阻止启动。

常用选项：

- `--clean`：删除已知的 `build/nuitka` 中间产物后重新编译。
- `--skip-tests`：临时跳过构建前测试，适合本地快速迭代。
- `--launch`：仅在签名、验证和发布全部成功后打开应用。

例如，完整清理并在成功后启动：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode app --clean --launch
```

诊断日志保存在 `build/logs/macos-app-build.log`。构建候选位于 `dist/macos.staging`；只有验证成功后才会替换 `dist/macos`。测试、编译或验证失败时，上一次成功的 `dist/macos/Md2docx.app` 保持不变。

当前 app 管线仅支持 macOS arm64 本机构建，使用 ad-hoc 签名，不需要 Apple Developer 账号。Developer ID、notarization、DMG、universal binary 和 CI 构建不在当前版本范围内。

## 兼容的原有构建方式

GUI onefile：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode onefile --clean
```

CLI onefile：

```bash
uv run --group build python scripts/build_nuitka.py --entry cli --mode onefile --clean
```

GUI standalone：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode standalone --clean
```

原有产物仍位于 `build/nuitka`，可编辑配置与对应可执行文件放在同一目录。Windows onefile 文件名带 `.exe`。
````

Keep the existing `## GitHub Actions 构建 Windows EXE` section unchanged below this content.

- [ ] **Step 2: Verify the documented help surface**

Run:

```bash
uv run --group build python scripts/build_nuitka.py --help
```

Expected: `--mode` lists `{onefile,standalone,app}`, and help lists `--clean`, `--skip-tests`, and `--launch`.

- [ ] **Step 3: Run the complete unit/regression suite before the expensive build**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 4: Run the exact repeatable acceptance command without launching the GUI**

Run:

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode app --clean
```

Expected: exit code 0 and a summary naming `dist/macos/Md2docx.app`, `dist/macos/default.yaml`, application size, elapsed time, test status, clean status, and the diagnostic log. Do not add `--launch` during automated verification because it creates a visible GUI side effect.

- [ ] **Step 5: Independently verify the real artifact**

Run:

```bash
test -f dist/macos/Md2docx.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' dist/macos/Md2docx.app/Contents/Info.plist
file dist/macos/Md2docx.app/Contents/MacOS/Md2docx
find dist/macos/Md2docx.app -path '*/md2docx/templates/default.yaml' -print
find dist/macos/Md2docx.app \( -name init.tcl -o -name tk.tcl \) -print
codesign --verify --deep --strict dist/macos/Md2docx.app
test -f dist/macos/default.yaml
test -s build/logs/macos-app-build.log
```

Expected:

- `PlistBuddy` prints the executable name.
- `file` output contains `arm64`.
- `find` prints the packaged template plus Tcl/Tk runtime files.
- `codesign` exits 0 without verification errors.
- The editable config and non-empty build log exist.

- [ ] **Step 6: Prove a second failed candidate cannot overwrite the accepted app**

Record the accepted app's plist checksum:

```bash
shasum -a 256 dist/macos/Md2docx.app/Contents/Info.plist
```

Run the focused unit test that simulates promotion failure:

```bash
uv run pytest tests/test_build_nuitka.py::test_promote_macos_app_restores_previous_release_on_rename_failure -v
```

Run the checksum command again:

```bash
shasum -a 256 dist/macos/Md2docx.app/Contents/Info.plist
```

Expected: the focused test passes and both real app checksums are identical.

- [ ] **Step 7: Run final change detection and commit documentation**

Run GitNexus `detect_changes(scope="compare", base_ref="main", repo="md2docx")`. Review that the final changes affect only the build workflow, its tests, and documentation.

Then run:

```bash
git diff -- docs/NUITKA_BUILD.md
git status --short
git add docs/NUITKA_BUILD.md
git commit -m "docs: document macOS app build pipeline"
```

Expected: user-owned `md2docx/gui.py`, `tests/test_gui.py`, and output-overwrite documents remain unstaged and unchanged by this work.

## Final acceptance checklist

- [ ] `uv run pytest` passes.
- [ ] The documented app command succeeds repeatedly on the local arm64 Mac.
- [ ] `dist/macos/Md2docx.app` is a bundle and contains no onefile extraction step.
- [ ] The bundle executable reports arm64.
- [ ] The packaged template and Tcl/Tk runtime are present.
- [ ] Ad-hoc signature verification succeeds.
- [ ] `dist/macos/default.yaml` exists but is not required for app startup.
- [ ] A failed test, compile, verification, or promotion cannot remove the previous successful app.
- [ ] `--launch` is opt-in and runs only after promotion.
- [ ] No Developer ID, notarization, DMG, Intel, universal-binary, or CI behavior was introduced.
