"""Verify original syntax failures and prepare a corrected test input."""
import json
import re
from pathlib import Path

import yaml

from md2docx.mermaid_converter import MermaidConverter

output_dir = Path(__file__).resolve().parent
source = Path('/Users/zhangqijin/Documents/Field/项目数据库/2026/投标项目/武穴市社会救助联合体项目/output/武穴市社会救助联合体服务项目技术方案.md')
markdown = source.read_text()
matches = list(re.finditer(r'^```mermaid\s*\n(.*?)^```', markdown, re.M | re.S))
config = yaml.safe_load(Path('/Users/zhangqijin/Desktop/桌面文件/md2docx简单表格配置.yml').read_text())['mermaid']
converter = MermaidConverter(cache_dir=output_dir / 'cache', command=config['command'], output_format=config['format'], theme=config['theme'], theme_variables=config['theme_variables'], background_color=config['background_color'])
changes = {
    21: [('E -- 政策保障 --F', 'E -->|政策保障| F'), ('E -- 服务需求 --G', 'E -->|服务需求| G')],
    33: [('B -- 政策咨询/宣介 -- C', 'B -->|政策咨询/宣介| C'), ('B -- 救助申请提交 -- D', 'B -->|救助申请提交| D'), ('B -- 帮办代办/特殊紧急 -- E', 'B -->|帮办代办/特殊紧急| E'), ('F -- 材料齐全 -- G', 'F -->|材料齐全| G'), ('F -- 材料不全 -- H', 'F -->|材料不全| H')],
    42: [('-- >', '-->')],
    54: [('\n]\n', '\n')],
    65: [('-- >', '-->')],
    83: [('B -- 不符合或无补位人 --|退回| A', 'B -->|不符合或无补位人：退回| A'), ('B -- 符合要求 -- C', 'B -->|符合要求| C')],
    84: [('B -- 请休假/疾病 --C', 'B -->|请休假/疾病| C'), ('B -- 离职 -- D', 'B -->|离职| D'), ('F -- 不合格 -- G', 'F -->|不合格| G'), ('F -- 合格 -- H', 'F -->|合格| H')],
    88: [('B -- 4小时以内 --|触发三级响应| C', 'B -->|4小时以内：触发三级响应| C'), ('B -- 4小时以上 --|触发二级响应| D', 'B -->|4小时以上：触发二级响应| D')],
}
failures = []
replacements = []
for number, edits in changes.items():
    match = matches[number - 1]
    code = match.group(1)
    try:
        converter.mermaid_to_image(code)
        raise AssertionError(f'Expected original diagram {number} to fail')
    except ValueError as exc:
        root = exc
        while root.__cause__ is not None:
            root = root.__cause__
        error = str(root)
        assert 'Parse error' in error or 'Lexical error' in error, error
        record = {'diagram': number, 'line': markdown[:match.start()].count('\n') + 1, 'error': error}
        failures.append(record)
        print(json.dumps({'diagram': number, 'line': record['line'], 'error': error[:650]}, ensure_ascii=False), flush=True)
    for old, new in edits:
        assert old in code, (number, old)
        code = code.replace(old, new)
    replacements.append((match.start(1), match.end(1), code))
for start, end, code in reversed(replacements):
    markdown = markdown[:start] + code + markdown[end:]
(output_dir / 'syntax-errors.json').write_text(json.dumps(failures, ensure_ascii=False, indent=2))
(output_dir / 'source-corrected.md').write_text(markdown)
print('Prepared corrected test copy; original input unchanged.', flush=True)
