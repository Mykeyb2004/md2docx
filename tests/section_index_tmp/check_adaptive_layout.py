"""Build a focused pagination fixture with the user's saved template/styles."""
import json
import sys
from pathlib import Path

from md2docx import Converter


preferences = json.loads((Path.home() / '.md2docx/preferences.json').read_text())
short = '## 1. 简短章节\n\n### 1.1 项目背景\n\n#### 1.1.1 服务需求\n\n正文内容。'
wrapped = (
    '## 2. 长标题章节：社会救助联合体服务的项目理解、总体思路、实施安排与质量保障机制\n\n'
    '### 2.1 项目实施\n\n#### 2.1.1 服务保障\n\n正文内容。'
)
long = '## 3. 跨页索引章节\n\n' + '\n\n'.join(
    f'### 3.{i} 服务安排与实施计划\n\n#### 3.{i}.1 具体实施步骤\n\n正文内容。'
    for i in range(1, 17)
)
converter = Converter(
    style_config=preferences['last_config_path'],
    word_template=preferences['last_word_template_path'],
    config_override={
        'document': {'section_index': True},
        'heading2': {'font_size': '28pt', 'space_before': '12pt', 'space_after': '24pt'},
    },
)
converter.convert_string('\n\n'.join((short, wrapped, long)), sys.argv[1])
