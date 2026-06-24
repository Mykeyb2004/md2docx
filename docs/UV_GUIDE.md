# md2docx 开发环境配置指南

## 使用 uv 作为包管理器

本项目使用 [uv](https://github.com/astral-sh/uv) 作为包管理器，它是一个极快的 Python 包和项目管理器，用 Rust 编写。

---

## 安装 uv

### macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 验证安装
```bash
uv --version
```

---

## 项目初始化

### 1. 初始化项目（首次设置）
```bash
cd /Users/zhangqijin/PycharmProjects/md2docx
uv init
```

### 2. 添加项目依赖
```bash
# 核心依赖
uv add python-docx mistune pyyaml

# 开发依赖
uv add --dev pytest mypy flake8 pytest-cov
```

### 3. 同步依赖（如果克隆项目）
```bash
uv sync
```

---

## 常用命令

### 运行 Python 脚本
```bash
# 运行转换工具
uv run md2docx input.md --output-file output.docx

# 覆盖已存在的输出文件
uv run md2docx input.md --output-file output.docx --overwrite

# 运行示例代码
uv run python examples/basic_usage.py
```

### 运行测试
```bash
# 运行所有测试
uv run pytest

# 运行指定测试文件
uv run pytest tests/test_converter.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=md2docx --cov-report=term-missing

# 运行测试（详细模式）
uv run pytest -v
```

### 代码质量检查
```bash
# 类型检查
uv run mypy md2docx/

# 代码规范检查
uv run flake8 md2docx/

# 格式化代码（可选）
uv run black md2docx/
```

### 依赖管理
```bash
# 添加新依赖
uv add <package-name>

# 添加开发依赖
uv add --dev <package-name>

# 移除依赖
uv remove <package-name>

# 更新所有依赖
uv sync --upgrade

# 查看依赖树
uv tree
```

### 进入虚拟环境
```bash
# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# 或者使用 uv 的 shell
uv run --with ipython ipython
```

---

## 项目结构

```
md2docx/
├── .venv/                    # 虚拟环境（由 uv 创建）
├── md2docx/                  # 源代码
├── tests/                    # 测试代码
├── examples/                 # 示例代码
├── docs/                     # 文档
├── pyproject.toml            # 项目配置和依赖
├── uv.lock                   # 依赖锁文件（自动生成）
└── README.md
```

---

## pyproject.toml 配置示例

```toml
[project]
name = "md2docx"
version = "0.1.0"
description = "Convert Markdown to Word documents with precise style control"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "python-docx>=1.0.0",
    "mistune>=3.0.0",
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.0.0",
    "flake8>=6.0.0",
]

[project.scripts]
md2docx = "md2docx.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]
```

---

## 开发工作流

### 1. 克隆项目并设置环境
```bash
git clone <repository-url>
cd md2docx
uv sync
```

### 2. 开发新功能
```bash
# 创建新分支
git checkout -b feature/new-feature

# 编写代码...
# 编写测试...

# 运行测试
uv run pytest

# 代码检查
uv run mypy md2docx/
uv run flake8 md2docx/
```

### 3. 测试转换功能
```bash
# 测试命令行工具
uv run md2docx 研究报告\ v01.md --output-file 测试报告.docx

# 测试 Python API
uv run python -c "
from md2docx import Converter
converter = Converter()
converter.convert('input.md', 'output.docx')
"
```

### 4. 提交代码
```bash
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
```

---

## 常见问题

### Q: uv 和 pip 有什么区别？
A: uv 是用 Rust 编写的，比 pip 快 10-100 倍，同时提供更好的依赖解析和锁文件支持。

### Q: 如何在 CI/CD 中使用 uv？
A: 
```yaml
# GitHub Actions 示例
- name: Install uv
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Install dependencies
  run: uv sync

- name: Run tests
  run: uv run pytest
```

### Q: 可以使用 pip 安装吗？
A: 可以，项目仍然兼容传统的 pip 安装：
```bash
pip install -e .
```

### Q: uv.lock 文件需要提交吗？
A: 是的，应该提交到版本控制，确保所有开发者使用相同的依赖版本。

---

## 参考资源

- [uv 官方文档](https://docs.astral.sh/uv/)
- [uv GitHub](https://github.com/astral-sh/uv)
- [pyproject.toml 规范](https://packaging.python.org/en/latest/specifications/pyproject-toml/)

---

**最后更新**：2025-11-20
