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


def build_target(entry: str, mode: str, clean: bool) -> Path:
    """Run Nuitka and return the built executable path."""
    source_file = REPO_ROOT / "md2docx" / f"{entry}.py"
    binary_name = f"md2docx-{entry}"

    if clean and OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "nuitka",
        f"--mode={mode}",
        "--assume-yes-for-downloads",
        "--include-package-data=md2docx",
        "--include-package=mistune.plugins",
        "--output-dir=" + str(OUTPUT_DIR),
        "--output-filename=" + binary_name,
        str(source_file),
    ]

    if entry == "gui":
        command.append("--enable-plugin=tk-inter")

    env = os.environ.copy()
    if sys.platform == "darwin":
        extra_flag = "-Wl,-headerpad_max_install_names"
        ldflags = env.get("LDFLAGS", "").strip()
        if extra_flag not in ldflags:
            env["LDFLAGS"] = f"{ldflags} {extra_flag}".strip()

    subprocess.run(command, check=True, cwd=REPO_ROOT, env=env)

    target_name = executable_name(binary_name)
    if mode == "onefile":
        return OUTPUT_DIR / target_name

    return OUTPUT_DIR / f"{binary_name}.dist" / target_name


def copy_editable_default_config(executable_path: Path) -> Path:
    """Copy the editable default config beside the built executable."""
    target_path = executable_path.parent / "default.yaml"
    shutil.copy2(DEFAULT_TEMPLATE, target_path)
    return target_path


def main() -> None:
    """Build the requested target and place editable config beside it."""
    args = parse_args()
    executable_path = build_target(args.entry, args.mode, args.clean)
    config_path = copy_editable_default_config(executable_path)

    print(f"Built executable: {executable_path}")
    print(f"Editable config:  {config_path}")


if __name__ == "__main__":
    main()
