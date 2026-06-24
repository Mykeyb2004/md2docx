"""
Word-native math formula converter.

Converts LaTeX mathematical expressions to OMML by delegating parsing to
Pandoc and extracting the generated Office Math XML from a temporary DOCX.
"""
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, List
from zipfile import ZipFile

from lxml import etree


MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NSMAP = {"m": MATH_NS}


class OmmlConverter:
    """Convert LaTeX formulas to Word-native OMML elements."""

    def __init__(self, pandoc_command: str = "pandoc") -> None:
        """
        Initialize the OMML converter.

        Args:
            pandoc_command: Pandoc executable name or absolute path.
        """
        self.pandoc_command = pandoc_command

    def latex_to_omml(self, latex: str, inline: bool = False) -> List[Any]:
        """
        Convert a LaTeX formula to OMML XML elements.

        Args:
            latex: LaTeX formula string without math delimiters.
            inline: True for inline math, False for display math.

        Returns:
            Deep-copied lxml OMML elements suitable for insertion into a
            python-docx paragraph.

        Raises:
            ValueError: If Pandoc is unavailable or no OMML is produced.
        """
        latex = latex.strip()
        if not latex:
            return []

        command_path = shutil.which(self.pandoc_command) or self.pandoc_command
        if not Path(command_path).exists() and shutil.which(self.pandoc_command) is None:
            raise ValueError(f"Pandoc not found: {self.pandoc_command}")

        md_text = self._wrap_math(latex, inline=inline)

        try:
            with tempfile.TemporaryDirectory(prefix="md2docx-omml-") as tmpdir:
                docx_path = Path(tmpdir) / "math.docx"
                subprocess.run(
                    [
                        command_path,
                        "-f",
                        "markdown+tex_math_dollars",
                        "-t",
                        "docx",
                        "-o",
                        str(docx_path),
                    ],
                    input=md_text,
                    text=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                with ZipFile(docx_path) as docx:
                    document_xml = docx.read("word/document.xml")

            root = etree.fromstring(document_xml)
            xpath = ".//m:oMath" if inline else ".//m:oMathPara"
            nodes = root.xpath(xpath, namespaces=NSMAP)
            if not nodes and not inline:
                nodes = root.xpath(".//m:oMath", namespaces=NSMAP)

            if not nodes:
                raise ValueError(f"Pandoc produced no OMML for formula: {latex}")

            return [deepcopy(node) for node in nodes]
        except (OSError, subprocess.CalledProcessError, etree.XMLSyntaxError) as exc:
            raise ValueError(f"Failed to convert LaTeX to OMML: {latex}") from exc

    def _wrap_math(self, latex: str, inline: bool) -> str:
        """Wrap LaTeX in Markdown math delimiters for Pandoc."""
        if inline:
            return f"${latex}$\n"
        return f"$$\n{latex}\n$$\n"
