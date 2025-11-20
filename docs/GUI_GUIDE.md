# GUI 使用指南

## 启动 GUI 应用

### 方法1：命令行启动

```bash
# 使用 uv
uv run md2docx-gui

# 或直接运行 Python 模块
python -m md2docx.gui
```

### 方法2：Python 代码启动

```python
from md2docx.gui import main

main()
```

---

## 功能说明

### 📂 文件转换

1. **选择 Markdown 文件**
   - 点击 "Browse..." 按钮
   - 选择 `.md` 文件
   - 自动建议输出文件名

2. **指定输出文件**
   - 点击 "Save As..." 按钮
   - 或直接修改输出路径

3. **执行转换**
   - 点击 "🔄 Convert to Word" 按钮
   - 查看进度条和状态
   - 完成后显示成功提示

### 📜 历史记录

**自动保存**：
- 每次转换自动记录
- 保存位置：`~/.md2docx/history.json`
- 最多保留 100 条记录

**查看历史**：
- 表格显示转换时间、文件名、状态
- 成功记录显示为绿色
- 失败记录显示为红色

**重新使用**：
- 双击历史记录
- 或选中后点击 "🔄 Reload Selected"
- 自动填充输入和输出路径

**清空历史**：
- 点击 "🗑️ Clear History"
- 确认后清空所有记录

---

## 界面布局

```
┌─────────────────────────────────────────┐
│  📄 Markdown to Word Converter          │
├─────────────────────────────────────────┤
│ File Conversion                         │
│  Markdown File: [________] [Browse...]  │
│  Output File:   [________] [Save As...] │
│                    [🔄 Convert to Word] │
├─────────────────────────────────────────┤
│ Conversion History                      │
│  Time    | Input | Output | Status      │
│  ────────┼───────┼────────┼──────       │
│  2025... │ file  │ out    │ ✓ Success   │
│  2025... │ doc   │ word   │ ✓ Success   │
│                                          │
│  [🔄 Reload] [🗑️ Clear History]        │
├─────────────────────────────────────────┤
│ Status: Ready                            │
└─────────────────────────────────────────┘
```

---

## 快捷键

- **Ctrl+O** - 打开文件（未实现，可扩展）
- **Ctrl+S** - 转换文件（未实现，可扩展）
- **双击历史记录** - 重新加载

---

## 历史文件格式

历史记录保存为 JSON 格式：

```json
[
  {
    "time": "2025-11-20 12:00:00",
    "input": "/path/to/input.md",
    "output": "/path/to/output.docx",
    "status": "Success"
  }
]
```

**字段说明**：
- `time` - 转换时间
- `input` - 输入文件完整路径
- `output` - 输出文件完整路径
- `status` - 转换状态（Success 或 Failed: xxx）

---

## 常见问题

**Q: GUI 无法启动？**  
A: 确保安装了 tkinter（Python 3 通常自带）

**Q: 如何查看完整文件路径？**  
A: 将鼠标悬停在历史记录上（可扩展添加 tooltip）

**Q: 历史记录保存在哪里？**  
A: `~/.md2docx/history.json`

**Q: 可以同时转换多个文件吗？**  
A: 当前版本仅支持单文件转换，可扩展添加批量转换功能

---

## 技术特性

- ✅ 异步转换（不阻塞 UI）
- ✅ 进度指示
- ✅ 错误处理
- ✅ 历史记录持久化
- ✅ 跨平台支持（Mac/Windows/Linux）

---

## 未来扩展

可添加的功能：
- [ ] 拖拽文件支持
- [ ] 批量转换
- [ ] 自定义样式选择（GUI 中）
- [ ] 转换预览
- [ ] 导出历史报告
- [ ] 快捷键支持
- [ ] 深色主题
