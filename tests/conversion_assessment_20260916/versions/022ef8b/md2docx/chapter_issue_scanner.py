"""
Scan chapter Markdown files for broken outline-marker line breaks.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from md2docx.config_utils import load_yaml_config
from md2docx.styles import StyleManager


CHINESE_NUMERALS = "零〇一二三四五六七八九十百千万"
INVISIBLE_CHARS = {
    "\u00a0",
    "\u200b",
    "\u200c",
    "\u200d",
    "\u2060",
    "\ufeff",
}
ISOLATED_OUTLINE_RE = re.compile(
    rf"^\s*(?:"
    rf"[{CHINESE_NUMERALS}]+、"
    rf"|[（(][{CHINESE_NUMERALS}]+[）)]"
    rf"|\d+\."
    rf"|[（(]\d+[）)]"
    rf")\s*$"
)
MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S")
MARKDOWN_ORDERED_LIST_RE = re.compile(r"^\s*\d+\.\s+\S")
MARKDOWN_UNORDERED_LIST_RE = re.compile(r"^\s*[*+-]\s+\S")
MARKDOWN_TABLE_RE = re.compile(r"^\s*\|")
THEMATIC_BREAK_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class ChapterLayoutIssue:
    """One suspicious isolated outline marker in a Markdown chapter."""

    file_path: Path
    line_number: int
    marker: str
    next_line_number: int
    next_line: str


def _remove_invisible_chars(text: str) -> str:
    """Drop invisible separator characters that often sneak into LLM output."""
    return "".join(ch for ch in text if ch not in INVISIBLE_CHARS)


def _is_blankish(line: str) -> bool:
    """Treat whitespace-only and invisible-only lines as blank."""
    return _remove_invisible_chars(line).strip() == ""


def _normalized_line(line: str) -> str:
    """Normalize invisible characters before matching Markdown patterns."""
    return _remove_invisible_chars(line)


def _is_plain_body_line(line: str) -> bool:
    """Return True when a line looks like body text rather than Markdown structure."""
    normalized = _normalized_line(line)
    stripped = normalized.strip()

    if not stripped:
        return False
    if (
        MARKDOWN_HEADING_RE.match(normalized)
        or MARKDOWN_ORDERED_LIST_RE.match(normalized)
        or MARKDOWN_UNORDERED_LIST_RE.match(normalized)
        or MARKDOWN_TABLE_RE.match(normalized)
        or FENCE_RE.match(normalized)
        or THEMATIC_BREAK_RE.match(normalized)
        or stripped.startswith(">")
    ):
        return False

    return True


def _find_next_meaningful_line(lines: List[str], start: int) -> Optional[Tuple[int, str]]:
    """Return the next non-blank line index and text, skipping invisible blank lines."""
    for idx in range(start, len(lines)):
        if not _is_blankish(lines[idx]):
            return idx, lines[idx]
    return None


def scan_markdown_file(path: Path) -> List[ChapterLayoutIssue]:
    """Scan one Markdown file and return all suspicious isolated outline markers."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: List[ChapterLayoutIssue] = []
    in_fenced_block = False

    for idx, line in enumerate(lines):
        normalized = _normalized_line(line)

        if FENCE_RE.match(normalized):
            in_fenced_block = not in_fenced_block
            continue

        if in_fenced_block:
            continue

        if not ISOLATED_OUTLINE_RE.match(normalized):
            continue

        next_line_info = _find_next_meaningful_line(lines, idx + 1)
        if next_line_info is None:
            continue

        next_idx, next_line = next_line_info
        if not _is_plain_body_line(next_line):
            continue

        findings.append(
            ChapterLayoutIssue(
                file_path=path,
                line_number=idx + 1,
                marker=normalized.strip(),
                next_line_number=next_idx + 1,
                next_line=_normalized_line(next_line).strip(),
            )
        )

    return findings


def scan_directory(
    directory: Path,
    pattern: str = "*.md",
    recursive: bool = True,
) -> Dict[Path, List[ChapterLayoutIssue]]:
    """Scan all matching Markdown files under a directory and group findings by file."""
    walker = directory.rglob(pattern) if recursive else directory.glob(pattern)
    results: Dict[Path, List[ChapterLayoutIssue]] = {}

    for path in sorted((item for item in walker if item.is_file()), key=lambda item: str(item)):
        findings = scan_markdown_file(path)
        if findings:
            results[path] = findings

    return results


def _resolve_existing_config_path(config_path: Optional[str]) -> Optional[Path]:
    """Resolve the on-disk YAML config file used by the scanner, if one exists."""
    if config_path:
        if "/" not in config_path and "\\" not in config_path and not config_path.endswith(".yaml"):
            candidate = StyleManager.get_editable_template_path(config_path)
            return candidate.resolve() if candidate.exists() else None

        candidate = Path(config_path)
        return candidate.resolve() if candidate.exists() else candidate

    default_path = StyleManager.get_editable_template_path("default")
    return default_path.resolve() if default_path.exists() else None


def _resolve_path_from_config_value(raw_path: str, base_dir: Path) -> Path:
    """Resolve a config path relative to a known base directory."""
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return base_dir / path


def _resolve_target_dir_from_root_output_config(
    raw_config: Dict[str, object],
    config_file_path: Optional[Path],
) -> Optional[Path]:
    """Resolve the scan target from business config fields `root_dir` and `output_dir`."""
    raw_output_dir = raw_config.get("output_dir")
    if not raw_output_dir:
        return None

    config_base_dir = Path.cwd() if config_file_path is None else config_file_path.parent
    raw_root_dir = raw_config.get("root_dir")

    if raw_root_dir:
        root_dir = _resolve_path_from_config_value(str(raw_root_dir), config_base_dir)
    else:
        root_dir = config_base_dir

    output_dir = Path(str(raw_output_dir))
    if output_dir.is_absolute():
        return output_dir

    return root_dir / output_dir


def resolve_scan_settings(
    config_path: Optional[str] = None,
    target_dir: Optional[str] = None,
    pattern: Optional[str] = None,
) -> Tuple[Path, str, bool, Optional[Path]]:
    """Resolve the target directory and file-matching settings for the scan."""
    style_manager = StyleManager(config_path=config_path) if config_path else StyleManager()
    scan_config = style_manager.get_style("chapter_scan", {})
    config_file_path = _resolve_existing_config_path(config_path)
    raw_config: Dict[str, object] = {}

    if config_file_path is not None and config_file_path.exists():
        raw_config = load_yaml_config(config_file_path)

    if target_dir:
        target_path = _resolve_path_from_config_value(target_dir, Path.cwd())
    else:
        target_path = _resolve_target_dir_from_root_output_config(raw_config, config_file_path)

    if target_path is None:
        raw_target_dir = scan_config.get("target_dir")
        if not raw_target_dir:
            raise ValueError("Missing output_dir or chapter_scan.target_dir in the active configuration")

        base_dir = Path.cwd() if config_file_path is None else config_file_path.parent
        target_path = _resolve_path_from_config_value(str(raw_target_dir), base_dir)

    raw_pattern = str(pattern or scan_config.get("glob", "*.md"))
    recursive = bool(scan_config.get("recursive", True))

    return target_path.resolve(), raw_pattern, recursive, config_file_path


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="scan_chapter_issues",
        description="Scan generated chapter Markdown files for isolated outline-marker line breaks.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to the YAML config file to read. Defaults to the active default.yaml.",
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        default=None,
        help="Override the target chapter directory from config.",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default=None,
        help="Override the Markdown filename glob from config.",
    )
    return parser


def _print_summary(
    target_dir: Path,
    results: Dict[Path, List[ChapterLayoutIssue]],
    config_file_path: Optional[Path],
) -> None:
    """Print only the problematic Markdown file list."""
    if not results:
        print("未发现异常章节。")
        return

    for file_path in results:
        try:
            display_path = file_path.relative_to(target_dir).as_posix()
        except ValueError:
            display_path = str(file_path)
        print(display_path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point for the standalone scanner."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        target_dir, pattern, recursive, config_file_path = resolve_scan_settings(
            config_path=args.config,
            target_dir=args.target_dir,
            pattern=args.pattern,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if not target_dir.exists():
        print(f"Error: Target directory not found: {target_dir}", file=sys.stderr)
        return 2
    if not target_dir.is_dir():
        print(f"Error: Target path is not a directory: {target_dir}", file=sys.stderr)
        return 2

    results = scan_directory(target_dir, pattern=pattern, recursive=recursive)
    _print_summary(target_dir, results, config_file_path)
    return 1 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())
