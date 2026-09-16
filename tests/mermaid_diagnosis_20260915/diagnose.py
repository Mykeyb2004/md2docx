"""Manual, local reproduction of the September 15 Mermaid GUI issue."""
import json
import os
import re
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile

import yaml
from docx import Document
from lxml import etree

from md2docx import Converter
from md2docx.mermaid_converter import MermaidConverter

source = Path('/Users/zhangqijin/Documents/Field/项目数据库/2026/投标项目/武穴市社会救助联合体项目/output/武穴市社会救助联合体服务项目技术方案.md')
config_path = Path('/Users/zhangqijin/Desktop/桌面文件/md2docx简单表格配置.yml')
template = '/Users/zhangqijin/Documents/Field/素材/word模板/Doc1.docx'
output_dir = Path(__file__).resolve().parent
config = yaml.safe_load(config_path.read_text())
markdown = source.read_text()
blocks = list(re.finditer(r'^```mermaid\s*\n(.*?)^```', markdown, re.M | re.S))
mode = sys.argv[1] if len(sys.argv) > 1 else 'normal'
if mode == 'corrected':
    markdown = (output_dir / 'source-corrected.md').read_text()
    blocks = list(re.finditer(r'^```mermaid\s*\n(.*?)^```', markdown, re.M | re.S))
if mode in {'gui-path', 'absolute-command'}:
    if mode == 'absolute-command':
        config['mermaid']['command'] = shutil.which('mmdc')
    os.environ['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'

if mode == 'all-diagrams':
    selected_markdown = '\n\n'.join(match.group(0) for match in blocks)
    expected = len(blocks)
elif mode in {'full', 'corrected'}:
    selected_markdown = markdown
    expected = len(blocks)
else:
    selected_markdown = blocks[0].group(0)
    expected = 1

style = config['mermaid']
probe = MermaidConverter(
    cache_dir=output_dir / 'cache', command=style['command'],
    output_format=style['format'], theme=style['theme'],
    theme_variables=style['theme_variables'],
    background_color=style['background_color'],
)
print(json.dumps({'mode': mode, 'mmdc': shutil.which(style['command']), 'node': shutil.which('node')}, ensure_ascii=False), flush=True)
try:
    image_bytes = probe.mermaid_to_image(blocks[0].group(1))
    print('first_image_bytes:', len(image_bytes), flush=True)
except Exception as exc:
    causes = []
    while exc is not None:
        causes.append(str(exc))
        exc = exc.__cause__
    print('first_image_error:', ' <- '.join(causes), flush=True)

output = output_dir / (mode + '.docx')
Converter(config_data=config, word_template=template).convert_string(selected_markdown, str(output), base_dir=source.parent)
with ZipFile(output) as archive:
    root = etree.fromstring(archive.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    drawings = len(root.xpath('//w:drawing', namespaces=ns))
    paragraphs = [p.text for p in Document(output).paragraphs]
    leaked = [p for p in paragraphs if re.match(r'\s*(?:flowchart |graph |sequenceDiagram)', p)]
    failures = []
    for paragraph in leaked:
        normalized = '\n'.join(line.strip() for line in paragraph.strip().splitlines())
        for index, match in enumerate(blocks, 1):
            if normalized == '\n'.join(line.strip() for line in match.group(1).strip().splitlines()):
                failures.append({'diagram': index, 'line': markdown[:match.start()].count('\n') + 1})
    result = {'mode': mode, 'expected': expected, 'body_drawings': drawings, 'raw_code_paragraphs': len(leaked), 'failures': failures, 'output': str(output)}
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    (output_dir / (mode + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2))
assert drawings == expected and not leaked, 'Mermaid diagrams missing from Word body'
