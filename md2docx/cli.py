"""
Command-line interface for md2docx.
"""
import argparse
import sys
from pathlib import Path

from md2docx import Converter


def _iter_markdown_files(root: Path) -> list[Path]:
    """Return Markdown files under a directory in deterministic order."""
    return sorted(
        (path for path in root.rglob("*.md") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def _flatten_output_name(md_file: Path, root: Path) -> str:
    """Flatten a Markdown path under root into a unique DOCX filename."""
    relative_path = md_file.relative_to(root).with_suffix("")
    return f"{'_'.join(relative_path.parts)}.docx"


def _ensure_output_available(
    output_path: Path,
    overwrite: bool,
    parser: argparse.ArgumentParser,
) -> None:
    """Reject an existing output path unless explicit overwrite is enabled."""
    if output_path.exists() and not overwrite:
        parser.error(f"output already exists: {output_path}. Use --overwrite to replace it.")


def _report_mermaid_failures(converter: Converter, output_path: Path) -> bool:
    """Report incomplete diagrams without discarding the saved document."""
    report = converter.mermaid_report
    if not report.failures:
        return False
    print(
        f"Warning: {output_path}: Mermaid images {report.succeeded}/{report.total}; "
        f"{len(report.failures)} failed and were preserved as source.",
        file=sys.stderr,
    )
    for failure in report.failures:
        print(f"  Diagram {failure.index}: {failure.error}", file=sys.stderr)
    return True


def _report_conversion_warnings(converter: Converter, output_path: Path) -> bool:
    """Report diagram failures and formula degradation after saving a document."""
    has_warning = _report_mermaid_failures(converter, output_path)
    report = converter.formula_report
    if report.fallbacks or report.failures:
        has_warning = True
        print(
            f"Warning: {output_path}: Native formulas {report.native}/{report.total}; "
            f"{len(report.fallbacks)} image fallback(s), {len(report.failures)} failure(s).",
            file=sys.stderr,
        )
        for kind, issues in [('image fallback', report.fallbacks), ('source preserved', report.failures)]:
            for issue in issues:
                print(f"  Formula {issue.index} ({kind}): {issue.latex[:120]}\n{issue.error}", file=sys.stderr)
    return has_warning


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='md2docx',
        description='Convert Markdown files to Word documents with precise style control',
        epilog='Examples:\n'
               '  md2docx input.md                    # Convert to input.docx\n'
               '  md2docx input.md --output-file output.docx  # Specify output file\n'
               '  md2docx input.md --output-dir out   # Save into a directory\n'
               '  md2docx docs --output-dir out       # Recursively convert all .md files\n'
               '  md2docx input.md -t chinese_academic  # Use template\n'
               '  md2docx input.md -s custom.yaml     # Use custom styles\n'
               '  md2docx input.md --word-template letterhead.docx  # Preserve Word header/footer',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='Input Markdown file path'
    )
    
    parser.add_argument(
        '-o', '--output-file',
        dest='output',
        type=str,
        default=None,
        metavar='FILE',
        help='Output Word document path (default: same as input with .docx extension)'
    )
    parser.add_argument(
        '--output',
        dest='output',
        type=str,
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        metavar='DIR',
        help='Directory to save converted Word documents (required when input is a directory)'
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Replace existing output DOCX files'
    )
    
    parser.add_argument(
        '-t', '--template',
        type=str,
        default=None,
        help='Style template name (e.g., default, chinese_academic)'
    )
    
    parser.add_argument(
        '-s', '--style-file', '--style-config',
        dest='style_config',
        type=str,
        default=None,
        metavar='FILE',
        help='Path to custom YAML style configuration file'
    )

    parser.add_argument(
        '--word-template',
        type=str,
        default=None,
        metavar='FILE',
        help='Path to a Word .docx template (preserves its headers and footers)',
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Determine output path
    if args.output and args.output_dir:
        parser.error("choose one: --output-file FILE or --output-dir DIR")

    if input_path.is_dir():
        if not args.output_dir:
            parser.error("directory input requires --output-dir DIR")
    elif args.output_dir:
        output_path = Path(args.output_dir) / input_path.with_suffix('.docx').name
    elif args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.docx')
    
    # Check for conflicts
    if args.template and args.style_config:
        parser.error("choose one: --template NAME or --style-file FILE")
    
    try:
        # Create converter
        converter = Converter(
            template=args.template,
            style_config=args.style_config,
            word_template=args.word_template,
        )

        if input_path.is_dir():
            markdown_files = _iter_markdown_files(input_path)
            if not markdown_files:
                print(f"Error: No Markdown files found under {args.input}", file=sys.stderr)
                sys.exit(1)

            output_dir = Path(args.output_dir)
            output_jobs = [
                (md_file, output_dir / _flatten_output_name(md_file, input_path))
                for md_file in markdown_files
            ]
            for _, output_path in output_jobs:
                _ensure_output_available(output_path, args.overwrite, parser)

            incomplete_files = 0
            for md_file, output_path in output_jobs:
                print(f"Converting {md_file} to {output_path}...")
                converter.convert(str(md_file), str(output_path))
                if _report_conversion_warnings(converter, output_path):
                    incomplete_files += 1

            if incomplete_files:
                print(f"Conversion completed with warnings in {incomplete_files} file(s).", file=sys.stderr)
                sys.exit(2)

            print(f"✓ Conversion successful! Converted {len(markdown_files)} file(s). Output dir: {output_dir}")
        else:
            # Convert
            _ensure_output_available(output_path, args.overwrite, parser)
            print(f"Converting {args.input} to {output_path}...")
            converter.convert(args.input, str(output_path))
            if _report_conversion_warnings(converter, output_path):
                sys.exit(2)
            print(f"✓ Conversion successful! Output: {output_path}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
