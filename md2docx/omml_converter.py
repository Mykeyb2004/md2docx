"""
Word-native math formula converter.

Converts LaTeX mathematical expressions to OMML by delegating parsing to
Pandoc and extracting the generated Office Math XML from a temporary DOCX.
"""
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import tempfile
from typing import Any, List
from zipfile import ZipFile

from lxml import etree

from md2docx.external_tools import resolve_external_command


MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NSMAP = {"m": MATH_NS}


def formula_error_detail(exc: BaseException) -> str:
    """Retain useful parser stderr from chained failures."""
    while exc.__cause__ is not None:
        exc = exc.__cause__
    detail = getattr(exc, 'stderr', None) or str(exc).strip() or type(exc).__name__
    return '\n'.join(str(detail).splitlines()[:4])[:600]


@dataclass(frozen=True)
class FormulaIssue:
    index: int
    latex: str
    error: str


@dataclass
class FormulaReport:
    """Distinguish editable formulas, image fallbacks, and preserved source."""

    total: int = 0
    native: int = 0
    fallbacks: List[FormulaIssue] = field(default_factory=list)
    failures: List[FormulaIssue] = field(default_factory=list)

    def record_fallback(self, latex: str, exc: BaseException) -> None:
        self.fallbacks.append(FormulaIssue(self.total, latex, formula_error_detail(exc)))

    def record_failure(self, latex: str, exc: BaseException, native_error: BaseException) -> None:
        detail = f"OMML: {formula_error_detail(native_error)}\nPNG: {formula_error_detail(exc)}"
        self.failures.append(FormulaIssue(self.total, latex, detail))


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

        command_path, env = resolve_external_command(self.pandoc_command)
        if command_path is None:
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
                    env=env,
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
