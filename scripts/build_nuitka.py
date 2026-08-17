"""
Build md2docx executables with Nuitka.
"""
from __future__ import annotations

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


def executable_name(binary_name: str) -> str:
    """Return the platform-specific executable filename."""
    if sys.platform == "win32":
        return f"{binary_name}.exe"
    return binary_name


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
        raise RuntimeError(
            f"bundle executable does not contain arm64: {architecture_text.strip()}"
        )

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


def promote_macos_app(
    staging_dir: Path = MACOS_STAGING_DIR,
    final_dir: Path = MACOS_DIST_DIR,
    backup_dir: Path = MACOS_BACKUP_DIR,
) -> Path:
    """Publish a verified candidate and preserve the old release on failure."""
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


def copy_editable_default_config(executable_path: Path) -> Path:
    """Copy the editable default config beside the built executable."""
    target_path = executable_path.parent / "default.yaml"
    shutil.copy2(DEFAULT_TEMPLATE, target_path)
    return target_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build the requested target and place editable config beside it."""
    args = parse_args(argv)
    prepare_build(args.clean, app_mode=False)
    executable_path = build_target(args.entry, args.mode)
    config_path = copy_editable_default_config(executable_path)

    print(f"Built executable: {executable_path}")
    print(f"Editable config:  {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
