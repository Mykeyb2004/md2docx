"""
Command-line interface for md2docx.
"""
import argparse
import sys
from pathlib import Path
from md2docx import Converter


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='md2docx',
        description='Convert Markdown files to Word documents with precise style control',
        epilog='Examples:\n'
               '  md2docx input.md                    # Convert to input.docx\n'
               '  md2docx input.md -o output.docx     # Specify output file\n'
               '  md2docx input.md -t chinese_academic  # Use template\n'
               '  md2docx input.md -s custom.yaml     # Use custom styles',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='Input Markdown file path'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output Word document path (default: same as input with .docx extension)'
    )
    
    parser.add_argument(
        '-t', '--template',
        type=str,
        default=None,
        help='Style template name (e.g., default, chinese_academic)'
    )
    
    parser.add_argument(
        '-s', '--style-config',
        type=str,
        default=None,
        metavar='FILE',
        help='Path to custom YAML style configuration file'
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
    if args.output:
        output_path = args.output
    else:
        output_path = input_path.with_suffix('.docx')
    
    # Check for conflicts
    if args.template and args.style_config:
        print("Error: Cannot use both --template and --style-config", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Create converter
        converter = Converter(
            template=args.template,
            style_config=args.style_config
        )
        
        # Convert
        print(f"Converting {args.input} to {output_path}...")
        converter.convert(args.input, str(output_path))
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

