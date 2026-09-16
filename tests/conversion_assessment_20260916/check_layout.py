"""Detect an inline picture clipped by an inherited fixed paragraph line height."""
import json
from pathlib import Path
import sys

from docx import Document

filename = Path(sys.argv[1])
rows = []
for paragraph in Document(filename).paragraphs:
    for extent in paragraph._p.xpath('.//wp:inline/wp:extent'):
        rules = paragraph._p.xpath('./w:pPr/w:spacing/@w:lineRule')
        lines = paragraph._p.xpath('./w:pPr/w:spacing/@w:line')
        style = paragraph.style
        while style is not None and (not rules or not lines):
            rules = rules or style._element.xpath('./w:pPr/w:spacing/@w:lineRule')
            lines = lines or style._element.xpath('./w:pPr/w:spacing/@w:line')
            style = style.base_style
        rule = (rules or ['auto'])[0]
        line_pt = int(lines[0]) / 20 if lines and rule == 'exact' else None
        height_pt = int(extent.get('cy')) / 12700
        rows.append({'image_height_pt': height_pt, 'line_rule': rule, 'fixed_line_pt': line_pt,
                     'clipped': rule == 'exact' and line_pt is not None and height_pt > line_pt})
print(json.dumps({'file': str(filename), 'pictures': rows}, ensure_ascii=False, indent=2))
assert rows, 'Expected the real Mermaid image'
assert not any(row['clipped'] for row in rows), 'Inline image exceeds inherited fixed line height'
