"""
Tests for Chinese document outline heading handling.
"""
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zipfile import ZipFile

from docx import Document

from md2docx import Converter


WORD_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def _read_paragraph_numbering(docx_path: str) -> List[Tuple[str, Optional[str]]]:
    """Return each paragraph's text with its explicit numbering id if present."""
    with ZipFile(docx_path) as archive:
        document_xml = archive.read('word/document.xml')

    root = ET.fromstring(document_xml)
    paragraphs: List[Tuple[str, Optional[str]]] = []

    for paragraph in root.findall('.//w:body/w:p', WORD_NS):
        text = ''.join(node.text or '' for node in paragraph.findall('.//w:t', WORD_NS)).strip()
        num_id = paragraph.find('./w:pPr/w:numPr/w:numId', WORD_NS)
        paragraphs.append(
            (
                text,
                num_id.get(f'{{{WORD_NS["w"]}}}val') if num_id is not None else None,
            )
        )

    return paragraphs


def test_chinese_outline_numeric_headings_render_as_plain_paragraphs():
    """`1.` headings inside Chinese outlines should not be emitted as Word lists."""
    converter = Converter()

    md_content = """# 分析示例

（二）区域差异的分析口径

区域差异分析以“横向比较、纵向辨识、结构拆解、类型归纳”为主线。

1. 比较单位口径

一是设区市之间的横向比较，用于识别市域层面公共文化服务统筹推进能力。

2. 比较指标口径

综合得分之外，更重视一级指标和关键观测点的分项比较。

（1）补充判断

进一步结合样本规模和误差区间审慎研判。
"""

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name

    try:
        converter.convert_string(md_content, output_path)
        doc = Document(output_path)
        texts = [p.text for p in doc.paragraphs]

        assert '（二）区域差异的分析口径' in texts
        assert '1. 比较单位口径' in texts
        assert '2. 比较指标口径' in texts
        assert '（1）补充判断' in texts

        numbering = {
            text: num_id for text, num_id in _read_paragraph_numbering(output_path)
        }
        assert numbering['1. 比较单位口径'] is None
        assert numbering['2. 比较指标口径'] is None
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_standard_markdown_ordered_lists_still_use_word_numbering():
    """Normal Markdown ordered lists should keep list numbering behavior."""
    converter = Converter()

    md_content = """# 标准列表

1. 第一项
2. 第二项
3. 第三项
"""

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        output_path = f.name

    try:
        converter.convert_string(md_content, output_path)
        numbering = {
            text: num_id for text, num_id in _read_paragraph_numbering(output_path)
        }

        assert numbering['第一项'] is not None
        assert numbering['第二项'] == numbering['第一项']
        assert numbering['第三项'] == numbering['第一项']
    finally:
        Path(output_path).unlink(missing_ok=True)
