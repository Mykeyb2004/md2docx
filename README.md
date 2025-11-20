# md2docx

Convert Markdown to Word documents with precise style control.

## Features

- 🎨 Precise style control for Word documents
- 📝 Support for common Markdown syntax (headings, lists, tables, etc.)
- ⚙️ Configurable styles via YAML
- 🚀 Fast conversion powered by mistune and python-docx
- 🐍 Python API and CLI tool

## Installation

```bash
# Install with uv
uv add md2docx

# Or with pip
pip install md2docx
```

## Quick Start

### GUI Mode (Recommended) 🎨

Launch the graphical interface for easy file selection and history tracking:

```bash
uv run md2docx-gui
```

**Features:**
- 📂 Visual file selection
- 📜 Automatic history tracking
- ✅ Progress indication
- 🔄 Reload previous conversions

See [GUI Guide](docs/GUI_GUIDE.md) for detailed instructions.

---

### CLI Mode (Command Line)

#### Basic Usage

```bash
# Convert a Markdown file to Word
uv run md2docx input.md

# Specify output filename
uv run md2docx input.md -o output.docx

# Use custom style configuration
uv run md2docx input.md -s custom_styles.yaml
```

### Python API

```python
from md2docx import Converter

# Basic usage
converter = Converter()
converter.convert('input.md', 'output.docx')

# With custom style
converter = Converter(style_config='my_styles.yaml')
converter.convert('input.md', 'output.docx')
```

## Development

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=md2docx --cov-report=term-missing
```

## Documentation

- [PRD](PRD.md) - Product Requirements Document
- [Development Guide](docs/UV_GUIDE.md) - Using uv for development
- [Style Configuration](docs/STYLES.md) - Configure Word styles

## License

MIT

## Status

🚧 **In Development** - Currently implementing MVP (Milestone 1)
