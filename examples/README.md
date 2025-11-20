# Examples 目录说明

本目录包含 md2docx 的功能演示示例。

## 📊 表格功能示例

### 1. table_alignment_test.md

演示 Markdown 表格对齐功能：

- ✅ 左对齐 (`:---`)
- ✅ 居中对齐 (`:--:`)
- ✅ 右对齐 (`---:`)

**用法**：
```bash
uv run md2docx examples/table_alignment_test.md -o output.docx
```

---

### 2. table_zebra_test.md

演示表格斑马纹（交替行颜色）功能：

- ✅ 启用/禁用交替行颜色
- ✅ 自定义奇偶行背景色
- ✅ 提升表格可读性

**配置示例**：
```yaml
table:
  alternating_rows: true
  row_background_odd: "#FFFFFF"
  row_background_even: "#F9F9F9"
```

**用法**：
```bash
# 1. 修改 default.yaml 启用斑马纹
# 2. 运行转换
uv run md2docx examples/table_zebra_test.md -o output.docx
```

---

## 🎯 使用这些示例

### 查看效果

```bash
# 转换示例文件
cd /Users/zhangqijin/PycharmProjects/md2docx
uv run md2docx examples/table_alignment_test.md
uv run md2docx examples/table_zebra_test.md
```

### 作为模板

这些示例可以作为您自己文档的起点：

1. 复制示例文件
2. 修改内容
3. 运行转换

---

## 📚 更多信息

- [样式配置指南](../docs/STYLES_CONFIG.md)
- [表格功能文档](../docs/TABLE_FEATURES.md)
- [README](../README.md)
