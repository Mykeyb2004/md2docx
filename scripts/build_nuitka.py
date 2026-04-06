"""
Build md2docx executables with Nuitka.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "build" / "nuitka"
DEFAULT_TEMPLATE = REPO_ROOT / "md2docx" / "templates" / "default.yaml"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
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
        choices=("onefile", "standalone"),
        default="onefile",
        help="Nuitka build mode.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous build output before compiling.",
    )
    return parser.parse_args()


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

    if mode == "onefile":
        return OUTPUT_DIR / binary_name

    return OUTPUT_DIR / f"{binary_name}.dist" / binary_name


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
