# 可删除的临时测试文件清单

生成时间: 2025-11-20

## 📋 分类清单

### 🧪 测试 Markdown 文件（可删除）

这些是为测试各种功能临时创建的 Markdown 文件：

| 文件名 | 用途 | 大小 | 是否可删除 |
|:------|:-----|:----:|:----------:|
| `test_custom_list.md` | 测试自定义列表格式 | - | ✅ 可删除 |
| `test_headings.md` | 测试标题样式 | - | ✅ 可删除 |
| `test_inline.md` | 测试行内样式 | - | ✅ 可删除 |
| `test_list_spacing.md` | 测试列表行距 | - | ✅ 可删除 |
| `test_paragraph_spacing.md` | 测试段落间距 | - | ✅ 可删除 |
| `cli_test.md` | CLI 测试文件 | - | ✅ 可删除 |
| `table_alignment_test.md` | 测试表格对齐 | - | ✅ 可删除 |
| `table_zebra_test.md` | 测试表格斑马纹 | - | ✅ 可删除 |

**总计**: 8 个 Markdown 测试文件

---

### 📄 生成的 Word 文档（可删除）

测试过程中生成的输出文件：

| 文件名 | 来源 | 是否可删除 |
|:------|:-----|:----------:|
| `test_custom_list.docx` | test_custom_list.md | ✅ 可删除 |
| `test_list_spacing.docx` | test_list_spacing.md | ✅ 可删除 |
| `test_headings.docx` | test_headings.md | ✅ 可删除 |
| `test_inline.docx` | test_inline.md | ✅ 可删除 |
| `test_paragraph_spacing.docx` | test_paragraph_spacing.md | ✅ 可删除 |
| `table_alignment_test.docx` | table_alignment_test.md | ✅ 可删除 |
| `研究报告*.docx` | 研究报告测试 | ✅ 可删除 |

**总计**: ~7+ 个 Word 文档

---

### 🐛 调试脚本（可删除）

用于开发过程中调试的 Python 脚本：

| 文件名 | 用途 | 是否可删除 |
|:------|:-----|:----------:|
| `debug_table_align.py` | 调试表格对齐 token | ✅ 可删除 |
| `debug_table.py` | 调试表格解析 | ✅ 可删除（如存在）|
| `debug_tokens.py` | 调试 mistune tokens | ✅ 可删除（如存在）|

**总计**: 1-3 个调试脚本

---

### 📝 临时文档文件（可删除）

开发过程中创建的临时或中间文档：

| 文件名 | 类型 | 是否可删除 |
|:------|:-----|:----------:|
| `CONFIG_IMPLEMENTATION_STATUS.md` | 实现状态检查 | ⚠️ 建议保留（参考） |
| `IMPLEMENTATION_COMPLETE.md` | 实现完成报告 | ⚠️ 建议保留（记录） |
| `LIST_COMPLETE.md` | 列表功能完成报告 | ⚠️ 建议保留（记录） |
| `TABLE_ENHANCEMENTS.md` | 表格功能说明 | ⚠️ 建议保留（参考） |
| `tests/CLI_TEST.md` | CLI 测试说明 | ⚠️ 建议保留（文档） |
| `markdown格式支持语法.md` | 语法规格文档 | ⚠️ 建议保留（参考） |
| `论文 v03.md` | 示例文档 | ⚠️ 视情况（如不需要可删） |

---

## 🗑️ 推荐删除清单

### 方案 A：删除所有临时测试文件

```bash
# 删除测试 Markdown 文件
rm test_*.md
rm cli_test.md
rm table_*_test.md

# 删除生成的 Word 文档
rm test_*.docx
rm table_*_test.docx
rm 研究报告*.docx

# 删除调试脚本
rm debug_*.py
```

**影响**: 删除约 15-20 个文件，释放磁盘空间

---

### 方案 B：选择性保留（推荐）

保留有文档价值的文件，删除纯测试文件：

```bash
# 删除纯测试文件
rm test_custom_list.md test_custom_list.docx
rm test_headings.md test_headings.docx
rm test_inline.md test_inline.docx
rm test_list_spacing.md test_list_spacing.docx
rm test_paragraph_spacing.md test_paragraph_spacing.docx

# 删除调试脚本
rm debug_table_align.py

# 删除 CLI 临时测试
rm cli_test.md

# 保留的文件（有参考价值）
# - table_alignment_test.md (演示对齐功能)
# - table_zebra_test.md (演示斑马纹功能)
# - CONFIG_IMPLEMENTATION_STATUS.md (实现状态记录)
# - IMPLEMENTATION_COMPLETE.md (完成记录)
# - LIST_COMPLETE.md (列表功能记录)
```

**影响**: 删除约 10-12 个文件，保留有文档价值的文件

---

### 方案 C：创建示例目录（最佳）

将有用的示例移动到专门目录：

```bash
# 创建示例目录
mkdir -p examples

# 移动有价值的示例
mv table_alignment_test.md examples/
mv table_zebra_test.md examples/

# 删除纯测试文件
rm test_*.md test_*.docx
rm cli_test.md
rm debug_*.py
rm 研究报告*.docx
```

**影响**: 
- 删除约 10 个临时文件
- 保留 2-3 个示例到 examples/ 目录
- 项目结构更清晰

---

## 📊 统计

### 可安全删除

| 类型 | 数量 | 总计 |
|:-----|:----:|:----:|
| 测试 Markdown | 8 | ~8KB |
| 测试 Word 文档 | 7 | ~100KB |
| 调试脚本 | 1-3 | ~2KB |
| **合计** | **16-18** | **~110KB** |

### 建议保留

| 类型 | 数量 | 原因 |
|:-----|:----:|:-----|
| 实现报告 | 3 | 开发记录 |
| 功能文档 | 2 | 功能演示 |
| 测试文档 | 1 | 测试指南 |
| **合计** | **6** | 参考价值 |

---

## ⚠️ 注意事项

1. **备份**: 删除前建议备份或提交到 git
2. **git 清理**: 删除后运行 `git clean -fd` 清理未跟踪文件
3. **.gitignore**: 建议添加以下规则：
   ```gitignore
   # 测试文件
   test_*.md
   test_*.docx
   debug_*.py
   *_test.md
   
   # 临时文档
   研究报告*.docx
   ```

4. **CI/CD**: 如果有自动化测试，确保不会影响

---

## 🎯 推荐操作

**推荐使用方案 C**：

1. 创建 `examples/` 目录
2. 移动有价值的示例文件
3. 删除纯测试临时文件
4. 更新 `.gitignore`
5. 提交清理后的代码

这样既保持了项目整洁，又保留了有用的示例！
