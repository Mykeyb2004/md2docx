# CLI 测试用例文档

## 手动测试步骤

### 1. 基础转换测试
```bash
# 创建测试 Markdown 文件
echo "# 测试标题\n\n这是测试内容。" > test.md

# 基础转换（自动输出为 test.docx）
uv run md2docx test.md

# 检查文件是否生成
ls -lh test.docx
```

### 2. 指定输出文件
```bash
uv run md2docx test.md --output-file my_output.docx
```

### 3. 指定输出目录
```bash
uv run md2docx test.md --output-dir converted

# 检查文件是否生成
ls -lh converted/test.docx
```

### 4. 递归转换目录
```bash
mkdir -p docs/a docs/b
echo "# A" > docs/a/report.md
echo "# B" > docs/b/report.md

uv run md2docx docs --output-dir converted

# 平铺输出，使用相对路径前缀避免同名覆盖
ls -lh converted/a_report.docx converted/b_report.docx
```

### 5. 使用模板
```bash
uv run md2docx test.md -t default --output-file output_with_template.docx
```

### 6. 查看帮助
```bash
uv run md2docx --help
```

### 7. 查看版本
```bash
uv run md2docx --version
```

### 8. 错误处理测试
```bash
# 文件不存在
uv run md2docx nonexistent.md

# 同时使用模板和配置文件（应该报错）
uv run md2docx test.md -t default -s custom.yaml

# 同时指定输出文件和输出目录（应该报错）
uv run md2docx test.md --output-file custom.docx --output-dir converted
```
