"""
Tests for Mermaid code block rendering.
"""
from io import BytesIO

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from PIL import Image

from md2docx.renderer import DocxRenderer
from md2docx.styles import StyleManager


def _sample_png_bytes() -> bytes:
    """Build a tiny in-memory PNG for image insertion tests."""
    return _sample_png_bytes_with_size(24, 24)


def _sample_png_bytes_with_size(width: int, height: int) -> bytes:
    """Build an in-memory PNG with a specific size."""
    image = Image.new("RGBA", (width, height), (0, 128, 255, 255))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class _MockState:
    """Minimal state object for renderer tests."""


def test_mermaid_block_renders_as_centered_image():
    """Mermaid fenced blocks should be rendered as centered images."""
    doc = Document()
    style_manager = StyleManager()
    renderer = DocxRenderer(doc, style_manager)

    class DummyMermaidConverter:
        def mermaid_to_image(self, code: str) -> bytes:
            assert "graph TD" in code
            return _sample_png_bytes()

    renderer.mermaid_converter = DummyMermaidConverter()

    token = {
        'type': 'block_code',
        'raw': 'graph TD\nA-->B\n',
        'attrs': {'info': 'mermaid'},
    }

    renderer.block_code(token, _MockState())

    assert len(doc.paragraphs) == 1
    assert doc.paragraphs[0].alignment == WD_PARAGRAPH_ALIGNMENT.CENTER
    assert doc.paragraphs[0].paragraph_format.keep_together is True
    assert doc.paragraphs[0].paragraph_format.page_break_before is False
    assert 'pic:pic' in doc.paragraphs[0]._p.xml
    assert len(doc.inline_shapes) == 1


def test_small_mermaid_block_stays_attached_to_previous_paragraph():
    """Compact Mermaid diagrams should stay with the previous text paragraph."""
    doc = Document()
    style_manager = StyleManager()
    style_manager.config.setdefault('mermaid', {}).update({
        'width': '5.5in',
        'page_break_threshold_ratio': 1.0,
        'follow_previous_trigger_height_ratio': 0.30,
        'follow_previous_width_ratio': 0.45,
        'follow_previous_space_before': '0pt',
        'oversized_strategy': 'shrink',
    })
    renderer = DocxRenderer(doc, style_manager)

    class DummyMermaidConverter:
        def mermaid_to_image(self, code: str) -> bytes:
            return _sample_png_bytes_with_size(800, 240)

    renderer.mermaid_converter = DummyMermaidConverter()

    doc.add_paragraph("上一段正文内容")

    token = {
        'type': 'block_code',
        'raw': 'graph TD\nA-->B\n',
        'attrs': {'info': 'mermaid'},
    }

    renderer.block_code(token, _MockState())

    assert len(doc.paragraphs) == 2
    assert doc.paragraphs[0].paragraph_format.keep_with_next is True
    assert doc.paragraphs[1].alignment == WD_PARAGRAPH_ALIGNMENT.CENTER
    assert int(doc.paragraphs[1].paragraph_format.space_before) == 0
    assert len(doc.inline_shapes) == 1
    shape = doc.inline_shapes[0]
    compact_width_limit = int(renderer._get_available_page_width()) * 0.45
    assert int(shape.width) <= int(compact_width_limit)
    assert int(shape.width) < int(renderer._parse_length('5.5in', default_unit='in'))


def test_mermaid_block_scales_tall_image_to_fit_page_height():
    """Tall Mermaid diagrams should be reduced to the configured height limit."""
    doc = Document()
    style_manager = StyleManager()
    style_manager.config.setdefault('mermaid', {}).update({
        'width': '5.5in',
        'hard_max_height_ratio': 0.5,
        'page_break_threshold_ratio': 2.0,
        'oversized_strategy': 'shrink',
        'min_readable_width': '0.1in',
    })
    renderer = DocxRenderer(doc, style_manager)

    class DummyMermaidConverter:
        def mermaid_to_image(self, code: str) -> bytes:
            return _sample_png_bytes_with_size(120, 1200)

    renderer.mermaid_converter = DummyMermaidConverter()

    token = {
        'type': 'block_code',
        'raw': 'graph TD\nA-->B\n',
        'attrs': {'info': 'mermaid'},
    }

    renderer.block_code(token, _MockState())

    assert len(doc.inline_shapes) == 1
    shape = doc.inline_shapes[0]
    max_height = int(renderer._get_available_page_height()) * 0.5
    assert int(shape.height) <= int(max_height)
    assert doc.paragraphs[0].paragraph_format.page_break_before is False


def test_large_mermaid_block_does_not_bind_previous_paragraph():
    """Large Mermaid diagrams should still stay bound to the previous paragraph."""
    doc = Document()
    style_manager = StyleManager()
    style_manager.config.setdefault('mermaid', {}).update({
        'width': '5.5in',
        'follow_previous_trigger_height_ratio': 0.10,
        'oversized_strategy': 'shrink',
    })
    renderer = DocxRenderer(doc, style_manager)

    class DummyMermaidConverter:
        def mermaid_to_image(self, code: str) -> bytes:
            return _sample_png_bytes_with_size(600, 420)

    renderer.mermaid_converter = DummyMermaidConverter()

    doc.add_paragraph("上一段正文内容")

    token = {
        'type': 'block_code',
        'raw': 'graph TD\nA-->B\n',
        'attrs': {'info': 'mermaid'},
    }

    renderer.block_code(token, _MockState())

    assert len(doc.paragraphs) == 2
    assert doc.paragraphs[0].paragraph_format.keep_with_next is True
    assert int(doc.paragraphs[1].paragraph_format.space_before) > 0


def test_mermaid_block_avoids_hard_page_break_for_oversized_diagram_by_default():
    """Oversized Mermaid diagrams should not force a new page by default."""
    doc = Document()
    style_manager = StyleManager()
    style_manager.config.setdefault('mermaid', {}).update({
        'width': '5.5in',
        'page_break_threshold_ratio': 0.5,
        'page_max_height_ratio': 0.9,
        'oversized_strategy': 'page',
        'min_readable_width': '3.2in',
    })
    renderer = DocxRenderer(doc, style_manager)

    class DummyMermaidConverter:
        def mermaid_to_image(self, code: str) -> bytes:
            return _sample_png_bytes_with_size(120, 1200)

    renderer.mermaid_converter = DummyMermaidConverter()

    doc.add_paragraph("上一段正文内容")

    token = {
        'type': 'block_code',
        'raw': 'graph TD\nA-->B\n',
        'attrs': {'info': 'mermaid'},
    }

    renderer.block_code(token, _MockState())

    assert len(doc.inline_shapes) == 1
    shape = doc.inline_shapes[0]
    max_height = int(renderer._get_available_page_height()) * 0.9
    assert int(shape.height) <= int(max_height)
    assert doc.paragraphs[0].paragraph_format.keep_with_next is True
    assert doc.paragraphs[1].paragraph_format.page_break_before is False


def test_mermaid_block_can_force_new_page_for_oversized_diagram_when_configured():
    """Oversized Mermaid diagrams can still request a hard page break explicitly."""
    doc = Document()
    style_manager = StyleManager()
    style_manager.config.setdefault('mermaid', {}).update({
        'width': '5.5in',
        'page_break_threshold_ratio': 0.5,
        'page_max_height_ratio': 0.9,
        'oversized_strategy': 'page',
        'force_page_break_before_oversized': True,
        'min_readable_width': '3.2in',
    })
    renderer = DocxRenderer(doc, style_manager)

    class DummyMermaidConverter:
        def mermaid_to_image(self, code: str) -> bytes:
            return _sample_png_bytes_with_size(120, 1200)

    renderer.mermaid_converter = DummyMermaidConverter()

    token = {
        'type': 'block_code',
        'raw': 'graph TD\nA-->B\n',
        'attrs': {'info': 'mermaid'},
    }

    renderer.block_code(token, _MockState())

    assert len(doc.inline_shapes) == 1
    assert doc.paragraphs[0].paragraph_format.page_break_before is True


def test_mermaid_block_falls_back_to_code_block_when_rendering_fails():
    """Mermaid blocks should remain readable when image rendering is unavailable."""
    doc = Document()
    style_manager = StyleManager()
    renderer = DocxRenderer(doc, style_manager)

    class FailingMermaidConverter:
        def mermaid_to_image(self, code: str) -> bytes:
            raise RuntimeError("mmdc not available")

    renderer.mermaid_converter = FailingMermaidConverter()

    token = {
        'type': 'block_code',
        'raw': 'graph TD\nA-->B\n',
        'attrs': {'info': 'mermaid'},
    }

    renderer.block_code(token, _MockState())

    assert len(doc.paragraphs) == 1
    assert 'graph TD' in doc.paragraphs[0].text
    assert 'A-->B' in doc.paragraphs[0].text
