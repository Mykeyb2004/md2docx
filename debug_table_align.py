"""
Debug script to see table alignment tokens.
"""
import mistune
import json

md_content = """
| 左对齐 | 居中 | 右对齐 |
|:-------|:----:|-------:|
| A1 | B1 | C1 |
| A2 | B2 | C2 |
"""

# Create markdown parser with table plugin
markdown = mistune.create_markdown(plugins=['table'], renderer=None)
state = mistune.BlockState()
tokens = markdown.parse(md_content, state)

print(f"Type of tokens: {type(tokens)}")
print(f"Tokens content: {tokens}")

if isinstance(tokens, list):
    for i, token in enumerate(tokens):
        print(f"\n=== Token {i} ===")
        print(f"Type: {type(token)}")
        if isinstance(token, dict):
            print(json.dumps(token, indent=2, default=str))
