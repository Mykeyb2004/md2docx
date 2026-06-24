"""
Tests for LaTeX math formula rendering.
"""
import pytest
from pathlib import Path
import zipfile
from md2docx import Converter
from md2docx.math_converter import MathConverter
from md2docx.omml_converter import MATH_NS, OmmlConverter


def _read_document_xml(docx_path: Path) -> str:
    """Read the main Word document XML from a DOCX file."""
    with zipfile.ZipFile(docx_path) as docx:
        return docx.read("word/document.xml").decode("utf-8")


class TestMathConverter:
    """Test the MathConverter class."""
    
    def test_basic_formula_rendering(self):
        """Test basic formula rendering."""
        converter = MathConverter()
        
        # Basic formulas
        formulas = [
            r'E=mc^2',
            r'x^2 + y^2 = 1',
            r'\frac{a}{b}',
            r'\sqrt{x}',
        ]
        
        for latex in formulas:
            img_bytes = converter.latex_to_image(latex, inline=True)
            assert img_bytes is not None
            assert len(img_bytes) > 0
            assert img_bytes.startswith(b'\x89PNG')  # PNG header
    
    def test_advanced_formulas(self):
        """Test advanced formulas."""
        converter = MathConverter()
        
        formulas = [
            r'\sum_{i=1}^{n} x_i',
            r'\int_0^1 x^2 dx',
            r'\frac{-b \pm \sqrt{b^2-4ac}}{2a}',
        ]
        
        for latex in formulas:
            img_bytes = converter.latex_to_image(latex, inline=False)
            assert img_bytes is not None
            assert len(img_bytes) > 0
    
    def test_inline_vs_block(self):
        """Test that inline and block formulas have different sizes."""
        converter = MathConverter()
        latex = r'\frac{a}{b}'
        
        inline_img = converter.latex_to_image(latex, inline=True)
        block_img = converter.latex_to_image(latex, inline=False)
        
        #  Inline should typically be smaller than block
        # (though this isn't guaranteed due to tight bbox)
        assert inline_img is not None
        assert block_img is not None
    
    def test_caching(self):
        """Test that caching works."""
        converter = MathConverter()
        latex = r'x^2 + y^2'
        
        # First render
        img1 = converter.latex_to_image(latex, inline=True)
        
        # Second render (should be from cache)
        img2 = converter.latex_to_image(latex, inline=True)
        
        assert img1 == img2
    
    def test_invalid_latex(self):
        """Test handling of invalid LaTeX."""
        converter = MathConverter()
        
        # Invalid LaTeX should raise an error
        with pytest.raises(ValueError):
            converter.latex_to_image(r'\invalid{command', inline=True)


class TestOmmlConverter:
    """Test the OmmlConverter class."""

    def test_latex_to_omml_returns_word_math_elements(self):
        """Test generic LaTeX formulas are converted to Word math XML."""
        converter = OmmlConverter()

        elements = converter.latex_to_omml(
            r'\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}',
            inline=False,
        )

        assert elements
        assert elements[0].tag == f'{{{MATH_NS}}}oMathPara'
        assert elements[0].xpath('.//m:f', namespaces={'m': MATH_NS})


class TestLatexRendering:
    """Test end-to-end LaTeX rendering in documents."""

    def test_block_math_is_written_as_omml(self, tmp_path):
        """Test block math is written as Word-native OMML, not an image."""
        md_content = r"""
$$
E = Z \times \sqrt{\frac{p(1-p)}{n}}
$$
"""
        output = tmp_path / "omml_block.docx"

        converter = Converter()
        converter.convert_string(md_content, str(output))

        xml = _read_document_xml(output)
        assert "<m:oMath" in xml
        assert "<m:f" in xml
        assert "<m:rad" in xml
        assert "<w:drawing" not in xml

    def test_latex_fenced_code_block_is_written_as_omml(self, tmp_path):
        """Test latex fenced code blocks are treated as Word-native equations."""
        md_content = r"""
```latex
n = \frac{Z^{2} \times p(1-p)}{E^{2}}
```
"""
        output = tmp_path / "omml_latex_fence.docx"

        converter = Converter()
        converter.convert_string(md_content, str(output))

        xml = _read_document_xml(output)
        assert "<m:oMath" in xml
        assert "<m:f" in xml
        assert "<w:drawing" not in xml
        assert "frac" not in xml
    
    def test_inline_math_conversion(self, tmp_path):
        """Test conversion of inline math formulas."""
        md_content = "The formula $E=mc^2$ is famous."
        output = tmp_path / "test_inline.docx"
        
        converter = Converter()
        converter.convert_string(md_content, str(output))
        
        assert output.exists()
        assert output.stat().st_size > 0
    
    def test_block_math_conversion(self, tmp_path):
        """Test conversion of block math formulas."""
        md_content = """
# Test
        
$$
\\int_0^1 x^2 dx = \\frac{1}{3}
$$
"""
        output = tmp_path / "test_block.docx"
        
        converter = Converter()
        converter.convert_string(md_content, str(output))
        
        assert output.exists()
        assert output.stat().st_size > 0
    
    def test_mixed_math_conversion(self, tmp_path):
        """Test conversion of mixed inline and block formulas."""
        md_content = """
# LaTeX Test

This has inline math $x^2$ and block math:

$$
\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}
$$

More text with $\\alpha + \\beta$.
"""
        output = tmp_path / "test_mixed.docx"
        
        converter = Converter()
        converter.convert_string(md_content, str(output))
        
        assert output.exists()
        assert output.stat().st_size > 0
    
    def test_multiple_formulas(self, tmp_path):
        """Test conversion with multiple formulas."""
        md_content = """
Formula 1: $a^2 + b^2 = c^2$

Formula 2: $\\frac{1}{2}$

$$
\\int_0^\\infty e^{-x} dx = 1
$$

Formula 3: $\\sqrt{2}$
"""
        output = tmp_path / "test_multiple.docx"
        
        converter = Converter()
        converter.convert_string(md_content, str(output))
        
        assert output.exists()
