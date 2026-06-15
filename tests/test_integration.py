"""
Test the full conversion workflow.
"""
import pytest
from pathlib import Path
import tempfile
from zipfile import ZipFile
from md2docx import Converter
from docx.document import Document as DocxDocument
from PIL import Image


def _write_sample_png(path: Path) -> None:
    """Create a tiny PNG image for document embedding tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (32, 24), (40, 120, 200))
    image.save(path, format="PNG")


def _docx_media_files(path: Path) -> list[str]:
    with ZipFile(path) as archive:
        return [
            name
            for name in archive.namelist()
            if name.startswith("word/media/")
        ]


def test_convert_string_basic():
    """Test basic string conversion."""
    converter = Converter()
    
    md_content = """# Test Heading

This is a paragraph with **bold** and *italic* text.

## Second Heading

Another paragraph."""
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name
    
    try:
        converter.convert_string(md_content, output_path)
        
        # Verify file was created
        assert Path(output_path).exists()
        
        # Verify content
        from docx import Document
        doc = Document(output_path)
        assert len(doc.paragraphs) > 0
        
        # Check headings
        assert "Test Heading" in doc.paragraphs[0].text
        assert "Second Heading" in [p.text for p in doc.paragraphs]
    finally:
        # Cleanup
        Path(output_path).unlink(missing_ok=True)


def test_convert_file():
    """Test file conversion."""
    converter = Converter()
    
    # Create temporary Markdown file
    md_content = """# File Test

This is a test from a file."""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(md_content)
        md_path = f.name
    
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        docx_path = f.name
    
    try:
        converter.convert(md_path, docx_path)
        
        # Verify output file exists
        assert Path(docx_path).exists()
        
        # Verify content
        from docx import Document
        doc = Document(docx_path)
        assert "File Test" in doc.paragraphs[0].text
    finally:
        # Cleanup
        Path(md_path).unlink(missing_ok=True)
        Path(docx_path).unlink(missing_ok=True)


def test_convert_file_embeds_relative_markdown_image(tmp_path):
    """Relative Markdown image paths should resolve from the Markdown file directory."""
    image_path = tmp_path / "assets" / "png" / "chart.png"
    _write_sample_png(image_path)
    md_path = tmp_path / "report.md"
    docx_path = tmp_path / "report.docx"
    md_path.write_text(
        "# Report\n\nBefore image.\n\n![Chart](assets/png/chart.png)\n\nAfter image.",
        encoding="utf-8",
    )

    Converter().convert(str(md_path), str(docx_path))

    from docx import Document

    doc = Document(docx_path)
    assert len(doc.inline_shapes) == 1
    assert _docx_media_files(docx_path)


def test_convert_file_embeds_relative_image_with_chinese_filename(tmp_path):
    """Percent-encoded image URLs from Mistune should resolve to local Unicode paths."""
    image_path = tmp_path / "assets" / "png" / "图4-1_能力得分比较.png"
    _write_sample_png(image_path)
    md_path = tmp_path / "report.md"
    docx_path = tmp_path / "report.docx"
    md_path.write_text(
        "![图4-1 能力得分比较](assets/png/图4-1_能力得分比较.png)",
        encoding="utf-8",
    )

    Converter().convert(str(md_path), str(docx_path))

    from docx import Document

    doc = Document(docx_path)
    assert len(doc.inline_shapes) == 1
    assert _docx_media_files(docx_path)


def test_convert_string_embeds_absolute_markdown_image(tmp_path):
    """Absolute Markdown image paths should be embedded without a base directory."""
    image_path = tmp_path / "absolute.png"
    docx_path = tmp_path / "absolute.docx"
    _write_sample_png(image_path)

    Converter().convert_string(f"![Chart]({image_path})", str(docx_path))

    from docx import Document

    doc = Document(docx_path)
    assert len(doc.inline_shapes) == 1
    assert _docx_media_files(docx_path)


def test_missing_markdown_image_renders_placeholder(tmp_path):
    """Missing Markdown images should leave a visible placeholder instead of disappearing."""
    md_path = tmp_path / "report.md"
    docx_path = tmp_path / "report.docx"
    md_path.write_text("![Missing](assets/png/missing.png)", encoding="utf-8")

    Converter().convert(str(md_path), str(docx_path))

    from docx import Document

    doc = Document(docx_path)
    assert "[Missing image: assets/png/missing.png]" in [p.text for p in doc.paragraphs]
    assert _docx_media_files(docx_path) == []


def test_unsupported_markdown_image_format_renders_placeholder(tmp_path):
    """Unsupported image formats should be visible in the output document."""
    image_path = tmp_path / "assets" / "graphic.webp"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"webp")
    md_path = tmp_path / "report.md"
    docx_path = tmp_path / "report.docx"
    md_path.write_text("![Graphic](assets/graphic.webp)", encoding="utf-8")

    Converter().convert(str(md_path), str(docx_path))

    from docx import Document

    doc = Document(docx_path)
    assert "[Unsupported image format: assets/graphic.webp]" in [
        p.text for p in doc.paragraphs
    ]
    assert _docx_media_files(docx_path) == []


def test_convert_file_not_found():
    """Test error handling for missing file."""
    converter = Converter()
    
    with pytest.raises(FileNotFoundError):
        converter.convert("nonexistent.md", "output.docx")


def test_to_document():
    """Test to_document method."""
    converter = Converter()
    
    md_content = "# Test\n\nParagraph."
    doc = converter.to_document(md_content)
    
    assert isinstance(doc, DocxDocument)
    assert len(doc.paragraphs) > 0


def test_converter_with_template():
    """Test converter with template."""
    converter = Converter(template="default")
    
    md_content = "# Test"
    doc = converter.to_document(md_content)
    
    assert isinstance(doc, DocxDocument)
