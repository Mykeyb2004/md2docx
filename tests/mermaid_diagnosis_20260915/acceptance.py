"""Post-fix acceptance of the user's document with Finder's restricted PATH."""
import json
import os
from dataclasses import asdict
from pathlib import Path
from zipfile import ZipFile

import yaml
from lxml import etree

from md2docx import Converter


source = Path('/Users/zhangqijin/Documents/Field/项目数据库/2026/投标项目/武穴市社会救助联合体项目/output/武穴市社会救助联合体服务项目技术方案.md')
config = yaml.safe_load(Path('/Users/zhangqijin/Desktop/桌面文件/md2docx简单表格配置.yml').read_text())
template = '/Users/zhangqijin/Documents/Field/素材/word模板/Doc1.docx'
folder = Path(__file__).resolve().parent
os.environ['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
results = []
for name, markdown, expected in [
    ('original-fixed-runtime', source.read_text(), 82),
    ('corrected-fixed-runtime', (folder / 'source-corrected.md').read_text(), 90),
]:
    converter = Converter(config_data=config, word_template=template)
    output = folder / (name + '.docx')
    converter.convert_string(markdown, str(output), base_dir=source.parent)
    with ZipFile(output) as archive:
        root = etree.fromstring(archive.read('word/document.xml'))
    drawings = len(root.xpath('//*[local-name()="drawing"]'))
    report = converter.mermaid_report
    result = {
        'case': name, 'PATH': os.environ['PATH'], 'output': str(output),
        'drawings': drawings, 'mermaid': asdict(report),
        'formula': asdict(converter.formula_report),
    }
    results.append(result)
    (folder / (name + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'case': name, 'drawings': drawings, 'total': report.total,
                      'succeeded': report.succeeded, 'failures': len(report.failures)}, ensure_ascii=False), flush=True)
    assert report.total == 90 and report.succeeded == expected
    assert drawings == expected
    assert [f.index for f in report.failures] == ([21, 33, 42, 54, 65, 83, 84, 88] if expected == 82 else [])
print('Both full-document acceptance cases passed.', flush=True)
