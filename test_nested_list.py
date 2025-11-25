#!/usr/bin/env python3
"""测试脚本：分析嵌套列表的token结构"""

import sys
sys.path.insert(0, '/Users/zhangqijin/PycharmProjects/md2docx')

import mistune
import json

# Test markdown with nested lists
md_text = '''1.  **用户需求与替代性调查（N=600样本）：**
    *   **对象：** 18岁以上市民及游客。
    *   **重点问卷设计：**
        *   "如果没有共享电单车，您会选择什么交通工具？"（测试替代率）
        *   "您选择共享电单车是否因为打不到车/公交太慢？"（测试溢出需求）'''

# Parse with mistune to AST
markdown = mistune.create_markdown(renderer='ast')
tokens = markdown(md_text)

# Print tokens
print(json.dumps(tokens, indent=2, ensure_ascii=False))
