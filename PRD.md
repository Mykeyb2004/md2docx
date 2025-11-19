# md2docx 产品需求文档（PRD）

**项目名称**：md2docx - Markdown 到 Word 文档转换工具  
**文档版本**：v1.0  
**编写日期**：2025-11-20  
**技术栈**：python-docx + mistune  
**目标用户**：需要将 Markdown 文档转换为专业 Word 文档的用户

---

## 一、项目背景与目标

### 1.1 项目背景

在日常工作中，特别是编写研究报告、技术文档、项目文档时，Markdown 格式因其简洁易用而广受欢迎。但在正式提交、汇报或归档时，通常需要标准的 Word 文档格式。现有的转换工具（如 Pandoc）存在以下问题：

- ❌ **样式控制不精确**：难以自定义标题、表格、列表等元素的具体样式
- ❌ **配置复杂**：需要学习模板语法或外部配置
- ❌ **中文支持不佳**：字体、排版等不符合中文文档习惯
- ❌ **扩展性差**：难以针对特定业务场景定制

### 1.2 项目目标

开发一个**轻量级、高度可定制**的 Markdown 到 Word 转换工具，满足以下核心目标：

#### 核心目标
1. ✅ **精确样式控制**：支持细粒度的 Word 样式定制（字体、字号、颜色、间距等）
2. ✅ **高频语法支持**：优先支持研究报告等业务文档的高频 Markdown 语法
3. ✅ **中文友好**：默认配置适配中文文档排版习惯
4. ✅ **易于扩展**：架构清晰，便于添加新的 Markdown 语法支持

#### 次要目标
- 🎯 提供命令行工具和 Python API 两种使用方式
- 🎯 支持样式配置文件，实现样式与代码分离
- 🎯 生成符合国标或企业规范的文档格式

---

## 二、用户角色与使用场景

### 2.1 用户角色

| 用户角色 | 技术能力 | 主要需求 |
| :------ | :------ | :------ |
| **业务人员** | 无编程基础 | 快速将 Markdown 文档转为 Word，用于汇报或提交 |
| **技术人员** | 熟悉 Python | 需要定制化样式，集成到自动化流程中 |
| **文档管理员** | 熟悉 Word 排版 | 统一团队文档格式，批量转换历史文档 |

### 2.2 典型使用场景

#### 场景一：研究报告转换
**用户**：业务分析师  
**需求**：将用 Markdown 编写的 320 行研究报告转换为 Word，保持：
- 多级标题层级清晰
- 表格样式美观（含对齐）
- 列表缩进正确
- 粗体强调保留

**操作**：
```bash
python md2docx.py 研究报告.md -o 研究报告.docx
```

#### 场景二：技术文档批量转换
**用户**：技术文档工程师  
**需求**：批量转换多个技术文档，统一使用公司文档模板样式

**操作**：
```python
from md2docx import Converter

converter = Converter(style_config='company_template.yaml')
converter.convert('tech_doc_1.md', 'output_1.docx')
converter.convert('tech_doc_2.md', 'output_2.docx')
```

#### 场景三：定制化样式需求
**用户**：高级用户  
**需求**：自定义一级标题为"华文中宋 18pt 蓝色"，表格使用特定样式

**操作**：修改 `styles.yaml` 配置文件，然后执行转换

---

## 三、功能需求

### 3.1 核心功能需求（MVP - 最小可行产品）

#### F1. Markdown 语法解析与转换

**优先级**：🔴 P0（最高）

支持以下 Markdown 语法元素的解析与转换：

##### F1.1 标题（Headings）
- **语法**：`#`、`##`、`###`、`####`
- **转换规则**：
  - 映射到 Word 的"标题1"到"标题4"样式
  - 支持自定义字体、字号、颜色、加粗
  - 支持段前段后间距设置
  - 自动生成文档目录（TOC）支持

**验收标准**：
```markdown
# 一级标题
## 二级标题
### 三级标题
#### 四级标题
```
转换后在 Word 中层级正确，样式符合配置。

---

##### F1.2 文本格式化
- **粗体**：`**文本**` → Word 粗体
- **斜体**：`*文本*` → Word 斜体
- **粗斜体**：`***文本***` → Word 粗斜体

**验收标准**：
- 单一格式正确转换
- 支持嵌套（如标题中的粗体）
- 支持段落内多处格式混用

---

##### F1.3 列表

**有序列表**：
```markdown
1. 第一项
2. 第二项
3. 第三项
```

**无序列表**：
```markdown
* 项目一
- 项目二
```

**多级嵌套列表**：
```markdown
1. 一级列表
    * 二级列表
        1. 三级列表
```

**转换规则**：
- 正确识别列表层级（支持 4 个空格或 1 个 Tab 缩进）
- 编号格式可配置（1. a. i. 等）
- 项目符号可配置（●、○、■ 等）
- 缩进量可配置

**验收标准**：
- 最多支持 4 级嵌套
- 层级关系正确
- 有序/无序混合嵌套正确

---

##### F1.4 表格

**语法示例**：
```markdown
| 列标题1 | 列标题2 | 列标题3 |
| :------ | :-----: | ------: |
| 左对齐  | 居中    | 右对齐  |
| 内容    | 内容    | 内容    |
```

**转换规则**：
- 支持左对齐 `:------`、居中 `:-----:`、右对齐 `------:`
- 表格样式可配置（边框、背景色、标题行样式）
- 支持表格内的粗体、斜体等格式
- 自动调整列宽（或支持固定列宽配置）

**验收标准**：
- 对齐方式正确
- 表格样式美观
- 表格内格式保留
- 处理跨多行的表格内容

---

##### F1.5 段落与换行

**规则**：
- 空行分隔段落 → Word 段落分隔
- 无空行连续文本 → Word 同一段落
- 支持段落首行缩进配置

**验收标准**：
- 段落间距正确
- 无多余空段落

---

##### F1.6 水平分隔线

**语法**：`---`

**转换规则**：
- 转换为 Word 水平线
- 支持线条样式、粗细、颜色配置

---

#### F2. 样式配置系统

**优先级**：🔴 P0

##### F2.1 样式配置文件

使用 YAML 格式定义样式规则：

```yaml
# styles.yaml 示例
document:
  page_size: A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.17cm
  margin_right: 3.17cm
  line_spacing: 1.5

heading1:
  font_name: 微软雅黑
  font_size: 18pt
  font_color: "#000080"  # 深蓝色
  bold: true
  space_before: 12pt
  space_after: 6pt
  alignment: left

heading2:
  font_name: 微软雅黑
  font_size: 16pt
  font_color: "#000000"
  bold: true
  space_before: 10pt
  space_after: 5pt

paragraph:
  font_name: 宋体
  font_size: 12pt
  line_spacing: 1.5
  first_line_indent: 2  # 2个字符
  alignment: justify  # 两端对齐

table:
  style: Light Grid Accent 1
  font_size: 11pt
  header_bold: true
  header_background: "#F2F2F2"
  border_color: "#CCCCCC"

list:
  bullet_char: "•"
  number_format: "1."
  indent_size: 0.5in
```

##### F2.2 内置样式模板

提供以下预设模板：
- `default` - 默认样式
- `chinese_academic` - 中文学术论文样式
- `business_report` - 商务报告样式
- `simple` - 简约样式

**使用方式**：
```bash
md2docx input.md -t chinese_academic -o output.docx
```

---

#### F3. 命令行工具

**优先级**：🔴 P0

##### 基本用法
```bash
# 基本转换
md2docx input.md

# 指定输出文件
md2docx input.md -o output.docx

# 使用预设模板
md2docx input.md -t business_report

# 使用自定义样式配置
md2docx input.md -c my_styles.yaml

# 批量转换
md2docx *.md -o output_dir/
```

##### 参数说明
| 参数 | 简写 | 说明 | 默认值 |
| :-- | :-- | :-- | :-- |
| `--output` | `-o` | 输出文件路径 | 同名 .docx |
| `--template` | `-t` | 样式模板名称 | default |
| `--config` | `-c` | 自定义配置文件 | - |
| `--verbose` | `-v` | 显示详细日志 | False |
| `--version` | - | 显示版本信息 | - |

---

#### F4. Python API

**优先级**：🔴 P0

```python
from md2docx import Converter

# 方式一：基本用法
converter = Converter()
converter.convert('input.md', 'output.docx')

# 方式二：使用预设模板
converter = Converter(template='chinese_academic')
converter.convert('input.md', 'output.docx')

# 方式三：自定义样式配置
converter = Converter(style_config='my_styles.yaml')
converter.convert('input.md', 'output.docx')

# 方式四：从字符串转换
md_content = "# 标题\n\n这是段落"
converter.convert_string(md_content, 'output.docx')

# 方式五：获取 Document 对象（不保存）
doc = converter.to_document('input.md')
# 可以进一步处理 doc 对象
doc.save('output.docx')
```

---

### 3.2 进阶功能需求（Phase 2）

**优先级**：🟡 P1（中）

#### F5. 扩展语法支持

##### F5.1 行内代码
**语法**：`` `code` ``  
**转换**：等宽字体（Consolas）+ 灰色背景

##### F5.2 代码块
**语法**：
````markdown
```python
def hello():
    print("Hello")
```
````
**转换**：等宽字体 + 边框 + 可选的语法高亮颜色

##### F5.3 引用块
**语法**：
```markdown
> 这是引用文本
> 可以多行
```
**转换**：左侧竖线 + 灰色背景 + 斜体

---

#### F6. 高级特性

##### F6.1 自动目录生成
- 根据标题自动生成 Word 目录（TOC）
- 支持目录样式自定义
- 支持多级目录

##### F6.2 图片支持
**语法**：`![描述](图片路径)`  
**转换**：
- 嵌入图片到 Word
- 支持调整图片大小
- 支持图片标题

##### F6.3 链接支持
**语法**：`[文本](URL)`  
**转换**：Word 超链接（蓝色 + 下划线）

---

### 3.3 可选功能需求（Future）

**优先级**：🟢 P2（低）

- 📌 脚注/尾注支持
- 📌 数学公式支持（通过 MathML）
- 📌 页眉页脚自定义
- 📌 多列布局
- 📌 Word 模板文件支持（基于现有 .docx 文件）

---

## 四、技术架构设计

### 4.1 技术栈

| 组件 | 技术选型 | 版本要求 | 用途 |
| :-- | :------ | :------ | :--- |
| **包管理器** | uv | ≥ 0.1.0 | 快速的 Python 包管理器和项目管理 |
| **Markdown 解析** | mistune | ≥ 3.0 | 解析 Markdown 为 AST |
| **Word 生成** | python-docx | ≥ 1.0 | 创建和样式化 Word 文档 |
| **配置管理** | PyYAML | ≥ 6.0 | 解析 YAML 样式配置 |
| **命令行** | argparse | 标准库 | CLI 参数解析 |
| **单元测试** | pytest | ≥ 7.0 | 测试框架 |
| **类型检查** | mypy | ≥ 1.0 | 静态类型检查 |

### 4.2 系统架构

```
┌─────────────────────────────────────────────────┐
│                  用户层                          │
│  ┌──────────────┐         ┌──────────────┐     │
│  │  命令行工具   │         │  Python API  │     │
│  └──────┬───────┘         └──────┬───────┘     │
└─────────┼─────────────────────────┼─────────────┘
          │                         │
          ▼                         ▼
┌─────────────────────────────────────────────────┐
│                 核心转换层                       │
│  ┌──────────────────────────────────────────┐  │
│  │         Converter (转换器)                │  │
│  │  - convert(md_path, docx_path)           │  │
│  │  - convert_string(md_string, docx_path)  │  │
│  │  - to_document(md_path) → Document       │  │
│  └──────────────┬───────────────────────────┘  │
└─────────────────┼─────────────────────────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
      ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Markdown │ │  样式     │ │  Word    │
│ 解析层   │ │  管理层   │ │  渲染层  │
└──────────┘ └──────────┘ └──────────┘
     │            │            │
     ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ mistune  │ │ styles.  │ │ python-  │
│ Renderer │ │ yaml     │ │ docx     │
└──────────┘ └──────────┘ └──────────┘
```

### 4.3 核心模块设计

#### 模块一：Markdown 解析层 (`parser.py`)

```python
class MarkdownParser:
    """Markdown 解析器，基于 mistune"""
    
    def __init__(self):
        self.markdown = mistune.create_markdown(
            renderer=DocxRenderer()
        )
    
    def parse(self, md_text: str) -> List[Element]:
        """解析 Markdown 文本为元素列表"""
        pass
```

#### 模块二：样式管理层 (`styles.py`)

```python
class StyleManager:
    """样式管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self.load_config(config_path)
    
    def get_heading_style(self, level: int) -> Dict:
        """获取标题样式"""
        pass
    
    def get_paragraph_style(self) -> Dict:
        """获取段落样式"""
        pass
    
    def get_table_style(self) -> Dict:
        """获取表格样式"""
        pass
```

#### 模块三：Word 渲染层 (`renderer.py`)

```python
class DocxRenderer(mistune.HTMLRenderer):
    """自定义 Mistune 渲染器，输出到 python-docx"""
    
    def __init__(self, doc: Document, style_manager: StyleManager):
        super().__init__()
        self.doc = doc
        self.styles = style_manager
    
    def heading(self, text: str, level: int) -> str:
        """渲染标题"""
        heading = self.doc.add_heading(text, level=level)
        style = self.styles.get_heading_style(level)
        self._apply_style(heading, style)
        return ''
    
    def paragraph(self, text: str) -> str:
        """渲染段落"""
        p = self.doc.add_paragraph(text)
        style = self.styles.get_paragraph_style()
        self._apply_style(p, style)
        return ''
    
    def table(self, header, body) -> str:
        """渲染表格"""
        # 表格渲染逻辑
        pass
```

#### 模块四：转换器 (`converter.py`)

```python
class Converter:
    """主转换器"""
    
    def __init__(
        self,
        template: Optional[str] = None,
        style_config: Optional[str] = None
    ):
        self.style_manager = StyleManager(style_config or template)
        self.parser = MarkdownParser()
    
    def convert(self, md_path: str, docx_path: str) -> None:
        """转换文件"""
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        doc = self.to_document(md_content)
        doc.save(docx_path)
    
    def to_document(self, md_content: str) -> Document:
        """转换为 Document 对象"""
        doc = Document()
        renderer = DocxRenderer(doc, self.style_manager)
        # ... 解析和渲染逻辑
        return doc
```

### 4.4 项目目录结构

```
md2docx/
├── md2docx/
│   ├── __init__.py
│   ├── converter.py          # 主转换器
│   ├── parser.py             # Markdown 解析器
│   ├── renderer.py           # Word 渲染器
│   ├── styles.py             # 样式管理器
│   ├── cli.py                # 命令行接口
│   ├── templates/            # 预设样式模板
│   │   ├── default.yaml
│   │   ├── chinese_academic.yaml
│   │   └── business_report.yaml
│   └── utils.py              # 工具函数
├── tests/
│   ├── test_converter.py
│   ├── test_parser.py
│   ├── test_renderer.py
│   ├── test_styles.py
│   └── fixtures/             # 测试用例文件
│       ├── sample.md
│       └── expected.docx
├── docs/
│   ├── README.md
│   ├── API.md
│   └── DEVELOPMENT.md
├── examples/
│   ├── basic_usage.py
│   └── custom_styles.yaml
├── pyproject.toml            # uv 项目配置文件
├── uv.lock                   # uv 锁文件（自动生成）
└── README.md
```

---

## 五、实现优先级与里程碑

### 5.1 开发阶段划分

#### 🏁 Milestone 1: MVP（最小可行产品）- 2-3 周

**目标**：完成核心功能，满足基本转换需求

**功能清单**：
- [x] 标题解析与转换（1-4 级）
- [x] 段落与换行
- [x] 粗体、斜体文本
- [x] 有序列表、无序列表
- [x] 多级嵌套列表（最多 4 级）
- [x] 表格（含对齐方式）
- [x] 水平分隔线
- [x] 基本样式配置系统（YAML）
- [x] 命令行工具（基本参数）
- [x] Python API（基本接口）

**验收标准**：
- ✅ 能够正确转换 `研究报告 v01.md`
- ✅ 所有元素样式符合配置
- ✅ 通过基本单元测试

---

#### 🏁 Milestone 2: 增强版 - 2 周

**目标**：提升易用性和灵活性

**功能清单**：
- [ ] 3 个预设样式模板（default, chinese_academic, business_report）
- [ ] 行内代码支持
- [ ] 代码块支持
- [ ] 引用块支持
- [ ] 批量转换功能
- [ ] 详细的错误提示和日志
- [ ] 配置文件验证

**验收标准**：
- ✅ 模板切换正常
- ✅ 支持技术文档转换
- ✅ 错误信息清晰友好

---

#### 🏁 Milestone 3: 完整版 - 2 周

**目标**：添加高级特性

**功能清单**：
- [ ] 自动目录生成（TOC）
- [ ] 图片支持
- [ ] 链接支持
- [ ] 更丰富的样式配置选项
- [ ] 性能优化（大文件处理）
- [ ] 完整的文档和示例

**验收标准**：
- ✅ 支持完整的业务文档转换
- ✅ 性能满足要求（1000 行文档 < 5 秒）
- ✅ 文档完善

---

### 5.2 开发优先级矩阵

| 功能 | 优先级 | 复杂度 | 预计工时 |
| :-- | :----: | :----: | :------: |
| 标题解析 | P0 | 低 | 0.5 天 |
| 文本格式化 | P0 | 低 | 0.5 天 |
| 列表（基础） | P0 | 中 | 1 天 |
| 列表（嵌套） | P0 | 高 | 2 天 |
| 表格 | P0 | 高 | 3 天 |
| 样式配置系统 | P0 | 中 | 2 天 |
| CLI 工具 | P0 | 低 | 1 天 |
| Python API | P0 | 低 | 0.5 天 |
| 预设模板 | P1 | 低 | 1 天 |
| 代码块 | P1 | 中 | 1 天 |
| 目录生成 | P1 | 中 | 2 天 |
| 图片支持 | P1 | 中 | 1.5 天 |

---

## 六、验收标准

### 6.1 功能验收

#### 测试用例一：基础语法转换
**输入**：包含所有基础语法的 Markdown 文件  
**预期**：所有元素正确转换，样式符合配置  
**测试文件**：`研究报告 v01.md`

#### 测试用例二：复杂嵌套列表
**输入**：4 层嵌套的混合列表  
**预期**：层级关系正确，缩进和编号符合规范

#### 测试用例三：表格对齐
**输入**：包含左对齐、居中、右对齐的表格  
**预期**：Word 中对齐方式正确

#### 测试用例四：样式配置
**输入**：自定义样式配置文件  
**预期**：生成的 Word 严格遵循配置的样式

#### 测试用例五：批量转换
**输入**：10 个 Markdown 文件  
**预期**：全部成功转换，无错误

### 6.2 性能验收

| 指标 | 目标值 |
| :-- | :---- |
| 100 行文档转换时间 | < 1 秒 |
| 1000 行文档转换时间 | < 5 秒 |
| 内存占用 | < 100MB |
| 支持最大文件大小 | ≥ 10MB |

### 6.3 质量验收

- ✅ 单元测试覆盖率 ≥ 80%
- ✅ 通过 mypy 类型检查
- ✅ 通过 flake8 代码规范检查
- ✅ 无 P0/P1 级别 bug
- ✅ 文档完整（README, API 文档，使用示例）

---

## 七、非功能性需求

### 7.1 性能要求

- 转换速度：100 行/秒（普通配置硬件）
- 内存控制：单次转换内存占用 < 100MB
- 支持文件大小：≥ 10MB Markdown 文件

### 7.2 兼容性要求

- **Python 版本**：≥ 3.8
- **操作系统**：Windows, macOS, Linux
- **Word 版本**：生成的 .docx 兼容 Word 2010 及以上版本

### 7.3 可维护性要求

- 模块化设计，职责清晰
- 代码注释覆盖率 ≥ 60%
- 遵循 PEP 8 编码规范
- 使用类型注解（Type Hints）
- 提供完整的单元测试

### 7.4 可扩展性要求

- 支持自定义渲染器（扩展新的 Markdown 语法）
- 支持插件机制（未来）
- 配置文件格式可扩展

### 7.5 安全性要求

- 输入验证：防止恶意 Markdown 注入
- 文件路径安全：防止路径遍历攻击
- 依赖安全：定期更新依赖库，修复安全漏洞

---

## 八、风险与挑战

### 8.1 技术风险

| 风险 | 影响 | 概率 | 应对策略 |
| :-- | :--: | :--: | :------ |
| mistune 解析复杂嵌套失败 | 高 | 中 | 编写自定义解析逻辑，或使用 markdown-it-py 备选 |
| python-docx 样式控制有限 | 中 | 低 | 深度研究文档，必要时操作底层 XML |
| 表格对齐渲染不准确 | 中 | 中 | 使用固定列宽或手动计算列宽 |
| 大文件性能问题 | 中 | 中 | 分段处理，优化内存占用 |

### 8.2 业务风险

| 风险 | 应对策略 |
| :-- | :------ |
| 用户需求变化 | 采用模块化架构，易于调整 |
| 竞品出现 | 重点打磨样式定制和中文支持的差异化优势 |

---

## 九、交付物清单

### 9.1 代码交付物

- [ ] 完整的源代码（符合 PEP 8）
- [ ] 单元测试代码（覆盖率 ≥ 80%）
- [ ] 3 个预设样式模板
- [ ] 示例代码和配置文件

### 9.2 文档交付物

- [ ] README.md（项目介绍、快速开始）
- [ ] API.md（Python API 文档）
- [ ] CLI.md（命令行工具文档）
- [ ] STYLES.md（样式配置文档）
- [ ] DEVELOPMENT.md（开发者指南）

### 9.3 测试交付物

- [ ] 单元测试报告
- [ ] 集成测试用例
- [ ] 性能测试报告
- [ ] 测试覆盖率报告

---

## 十、后续规划

### 10.1 版本规划

- **v1.0**：MVP 版本（基础功能）
- **v1.1**：增强版（预设模板、代码块）
- **v1.2**：完整版（目录、图片、链接）
- **v2.0**：高级版（插件系统、Word 模板支持）

### 10.2 潜在扩展方向

- 🔮 Web 在线转换服务
- 🔮 VS Code / JetBrains 插件
- 🔮 支持 docx → markdown 反向转换
- 🔮 支持 PDF 导出
- 🔮 AI 辅助样式推荐

---

## 附录

### A. 参考文档

- [python-docx 官方文档](https://python-docx.readthedocs.io/)
- [mistune 官方文档](https://mistune.lepture.com/)
- [Markdown 规范](https://commonmark.org/)
- [Word OOXML 规范](https://docs.microsoft.com/en-us/openspecs/office_standards/)

### B. 相关资源

- 测试文档：`研究报告 v01.md`
- 语法规范：`markdown格式支持语法.md`
- 样式配置示例：`examples/custom_styles.yaml`

---

**文档状态**：✅ 初稿完成  
**审核人**：待定  
**批准人**：待定  
**最后更新**：2025-11-20
