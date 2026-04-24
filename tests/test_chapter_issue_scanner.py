"""
Tests for chapter layout issue scanning.
"""
import tomllib
from pathlib import Path

from md2docx.chapter_issue_scanner import (
    main,
    resolve_scan_settings,
    scan_directory,
    scan_markdown_file,
)


def test_scan_markdown_file_detects_isolated_outline_markers(tmp_path: Path):
    """Separated outline markers should be reported with their next content line."""
    chapter_path = tmp_path / "chapter-1.md"
    chapter_path.write_text(
        "# 示例章节\n\n"
        "一、\n\n"
        "信息完整性核验机制\n\n"
        "（一）\n\n"
        "核验范围\n\n"
        "1.\n\n"
        "本机制执行中重点把握以下要求：\n\n"
        "（1）\n\n"
        "覆盖完整。\n",
        encoding="utf-8",
    )

    findings = scan_markdown_file(chapter_path)

    assert [(item.line_number, item.marker, item.next_line_number) for item in findings] == [
        (3, "一、", 5),
        (7, "（一）", 9),
        (11, "1.", 13),
        (15, "（1）", 17),
    ]


def test_scan_markdown_file_treats_zero_width_lines_as_blank(tmp_path: Path):
    """Invisible separator lines should still count as the broken-layout pattern."""
    chapter_path = tmp_path / "chapter-hidden.md"
    chapter_path.write_text(
        "一、\n"
        "\u200b\u200b\n"
        "信息完整性核验机制\n",
        encoding="utf-8",
    )

    findings = scan_markdown_file(chapter_path)

    assert len(findings) == 1
    assert findings[0].line_number == 1
    assert findings[0].next_line_number == 3


def test_scan_directory_returns_only_files_with_findings(tmp_path: Path):
    """Directory scanning should group findings by Markdown chapter file."""
    output_dir = tmp_path / "chapters"
    output_dir.mkdir()

    (output_dir / "clean.md").write_text("# 正常章节\n\n内容正常。\n", encoding="utf-8")
    (output_dir / "broken.md").write_text("1.\n\n章节说明\n", encoding="utf-8")

    results = scan_directory(output_dir)

    assert list(results.keys()) == [output_dir / "broken.md"]
    assert results[output_dir / "broken.md"][0].marker == "1."


def test_main_reads_default_target_dir_from_current_config(
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    """The standalone scanner should print only the problematic Markdown file list."""
    output_dir = tmp_path / "generated-chapters"
    output_dir.mkdir()
    (output_dir / "chapter-a.md").write_text("（一）\n\n核验范围\n", encoding="utf-8")

    (tmp_path / "default.yaml").write_text(
        "chapter_scan:\n"
        "  target_dir: generated-chapters\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out.strip().splitlines() == ["chapter-a.md"]


def test_resolve_scan_settings_uses_root_dir_plus_output_dir_from_config(tmp_path: Path):
    """Business config files should resolve output_dir relative to the configured root_dir."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()

    root_dir = tmp_path / "project-root"
    target_dir = root_dir / "output"
    target_dir.mkdir(parents=True)

    config_path = config_dir / "config_统计台账.yaml"
    config_path.write_text(
        "root_dir: ../project-root\n"
        "output_dir: ./output\n",
        encoding="utf-8",
    )

    resolved_target_dir, pattern, recursive, resolved_config_path = resolve_scan_settings(
        config_path=str(config_path)
    )

    assert resolved_target_dir == target_dir.resolve()
    assert pattern == "*.md"
    assert recursive is True
    assert resolved_config_path == config_path.resolve()


def test_pyproject_registers_scan_chapter_console_script():
    """Packaging should expose the scanner as a real console command."""
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["md2docx-scan-chapters"] == (
        "md2docx.chapter_issue_scanner:main"
    )
