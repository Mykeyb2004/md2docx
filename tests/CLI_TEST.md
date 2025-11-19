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
uv run md2docx test.md -o my_output.docx
```

### 3. 使用模板
```bash
uv run md2docx test.md -t default -o output_with_template.docx
```

### 4. 查看帮助
```bash
uv run md2docx --help
```

### 5. 查看版本
```bash
uv run md2docx --version
```

### 6. 错误处理测试
```bash
# 文件不存在
uv run md2docx nonexistent.md

# 同时使用模板和配置文件（应该报错）
uv run md2docx test.md -t default -s custom.yaml
```
