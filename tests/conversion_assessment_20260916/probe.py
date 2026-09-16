"""Manual real-tool differential probe; run from project root with uv run.

Usage: probe.py <source-tree> <label> <template|plain> [gui-path]
Writes isolated assessment artifacts, never changes application source.
"""
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
label, mode = sys.argv[2:4]
case = OUT / f"{label}-{mode}"
case.mkdir(exist_ok=True)
os.environ['MPLCONFIGDIR'] = str(OUT / 'mpl-cache')

from docx import Document
from docx.oxml.ns import qn
from lxml import etree
from md2docx import Converter
from md2docx.mermaid_converter import MermaidConverter

calls = []
original_run = subprocess.run


def traced_run(command, *args, **kwargs):
    calls.append([str(item) for item in command])
    return original_run(command, *args, **kwargs)


subprocess.run = traced_run
original_init = MermaidConverter.__init__


def isolated_mermaid(self, *args, **kwargs):
    kwargs['cache_dir'] = case / 'mermaid-cache'
    original_init(self, *args, **kwargs)


MermaidConverter.__init__ = isolated_mermaid
if 'gui-path' in sys.argv[4:]:
    os.environ['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'

config = '/Users/zhangqijin/Desktop/桌面文件/md2docx简单表格配置.yml'
template = '/Users/zhangqijin/Documents/Field/素材/word模板/Doc1.docx'
kwargs = {'style_config': config}
if mode == 'template':
    kwargs['word_template'] = template

formula_md = r'''# 可编辑公式验收

行内公式 $E=mc^2$ 与行内分式 $\frac{a}{b}$。

$$
E = Z \times \sqrt{\frac{p(1-p)}{n}}
$$

$$
\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}
$$

$$
\int_0^1 x^2 dx = \frac{1}{3}
$$

```latex
n = \frac{Z^2 p(1-p)}{E^2}
```
'''
(OUT / 'formulas.md').write_text(formula_md)
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
      'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}
result = {'version': label, 'source': sys.path[0], 'mode': mode, 'cases': {}}
for name, md in [('mermaid', (OUT / 'screenshot-excerpt.md').read_text()), ('formulas', formula_md)]:
    filename = case / f'{name}.docx'
    try:
        converter = Converter(**kwargs)
        converter.convert_string(md, str(filename))
        with ZipFile(filename) as archive:
            root = etree.fromstring(archive.read('word/document.xml'))
            settings = etree.fromstring(archive.read('word/settings.xml'))
        doc = Document(filename)
        pictures = []
        for paragraph in doc.paragraphs:
            extents = paragraph._p.xpath('.//wp:inline/wp:extent')
            if not extents:
                continue
            direct = paragraph._p.xpath('./w:pPr/w:spacing/@w:lineRule')
            inherited = paragraph.style._element.xpath('./w:pPr/w:spacing/@w:lineRule')
            rule = (direct or inherited or ['auto'])[0]
            pictures.append({'height_pt': int(extents[0].get('cy')) / 12700,
                             'line_rule': rule,
                             'style': paragraph.style.name,
                             'direct_line': paragraph._p.xpath('./w:pPr/w:spacing/@w:line'),
                             'style_line': paragraph.style._element.xpath('./w:pPr/w:spacing/@w:line')})
        data = {
            'file': str(filename),
            'drawings': len(root.xpath('//w:drawing', namespaces=ns)),
            'inline_pictures': len(root.xpath('//wp:inline', namespaces=ns)),
            'floating_pictures': len(root.xpath('//wp:anchor', namespaces=ns)),
            'pictures': pictures,
            'equations': len(root.xpath('//m:oMath', namespaces=ns)),
            'display_equations': len(root.xpath('//m:oMathPara', namespaces=ns)),
            'fractions': len(root.xpath('//m:f', namespaces=ns)),
            'radicals': len(root.xpath('//m:rad', namespaces=ns)),
            'nary': len(root.xpath('//m:nary', namespaces=ns)),
            'document_protection': len(settings.xpath('//w:documentProtection', namespaces=ns)),
        }
        if hasattr(converter, 'mermaid_report') and converter.mermaid_report:
            report = converter.mermaid_report
            data['mermaid_report'] = {'total': report.total, 'succeeded': report.succeeded,
                                      'failures': [vars(f) for f in report.failures]}
        data['pass'] = (data['drawings'] == 1 and all(p['line_rule'] != 'exact' for p in pictures)) if name == 'mermaid' else (data['equations'] == 6 and data['drawings'] == 0 and data['fractions'] >= 4 and data['radicals'] >= 1 and data['nary'] >= 2 and not data['document_protection'])
        result['cases'][name] = data
    except Exception as exc:
        result['cases'][name] = {'error': f'{type(exc).__name__}: {exc}', 'pass': False}
result['external_commands'] = calls
(case / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
