# 测试实际转换功能
from md2docx import Converter

# 创建测试内容
md_content = """# md2docx 测试文档

这是一个使用 **md2docx** 转换的示例文档。

## 功能特性

1. 支持多级标题
2. 支持**粗体**和*斜体*文本
3. 支持有序和无序列表

## 示例段落

这是一个包含 **粗体文字** 和 *斜体文字* 的段落，展示了md2docx的文本格式化能力。

### 三级标题示例

- 无序列表项 1
- 无序列表项 2
- 无序列表项 3

#### 四级标题示例

转换测试成功！
"""

# 执行转换
converter = Converter()
converter.convert_string(md_content, "测试输出.docx")

print("✅ 转换成功！输出文件：测试输出.docx")
