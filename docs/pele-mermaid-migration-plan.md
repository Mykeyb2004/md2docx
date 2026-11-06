# Mermaid 转换模块替换开发计划（`obsidianmd/pele` 内置引擎方案）

- **日期**：2026-11-06
- **状态**：已完成 / 待验收确认（分支：`feat/pele-mermaid-engine`）
- **目标模块**：`md2docx/mermaid_converter.py` 及关联配置、GUI 选项、Nuitka 打包管线

---

## 一、背景与改造目标

### 1. 现状痛点
当前项目通过 [`MermaidConverter`](../md2docx/mermaid_converter.py) 调用外部 npm 包 `@mermaid-js/mermaid-cli`（`mmdc`）将 Mermaid 代码块转换为 PNG 图片插入 Word：
1. **外部环境强依赖**：无法打入 Nuitka 独立应用包，要求用户本机额外安装 Node.js 与 Puppeteer/Chromium（约 300MB+），在 macOS Finder 启动环境下还需维护复杂的 NVM/Volta 路径探测（[`external_tools.py`](../md2docx/external_tools.py)）。
2. **冷启动耗时长**：每张未命中缓存的流程图均需拉起一次独立 Node + Headless Chromium 子进程（单图约 1.5s～3.0s，90 张图的业务文档首次转换需 2～4 分钟）。

### 2. 改造目标
采用 **`obsidianmd/pele` + `quickjs-ng` + `resvg-py`** 构建**进程内、零外部依赖的高清 PNG 渲染管线**：
- **彻底去除外部依赖**：打包后的 macOS `Md2docx.app` 与 Windows `.exe` 开箱即用，用户电脑无需安装 Node.js、`mmdc` 或 Chromium。
- **百倍性能提升**：单图冷渲染耗时从秒级降至毫秒级（90 张中文流程图全量冷渲染目标 `< 2s`）。
- **100% 交付兼容**：继续输出高清 PNG 字节流（放弃 Word 原生纯 SVG 直插方案，规避 Word SVG 引擎不支持 `var()`/`dominant-baseline`/`<marker>` 导致的黑块、文字偏上、丢箭头及旧版 WPS/兼容模式白屏风险）。
- **平滑双引擎并存**：新增 `mermaid.engine: pele | mmdc`（默认 `pele`），完整保留原有 `mmdc` 分支作为可选兼容后端。

---

## 二、影响面评估（GitNexus 静态分析与源码核验）

基于 GitNexus 图谱检索与源码逐行核验，`MermaidConverter` 封装边界非常清晰，**上游影响风险为 LOW（改动高度收敛）**：

| 层级 | 涉及文件 / 符号 | 是否需要修改 | 说明 |
| :--- | :--- | :---: | :--- |
| **核心转换层** | `md2docx/pele_renderer.py`（新增） | **新增** | 封装 `pele` JS 执行、中文字宽测量、CSS 变量展开与 `resvg-py` 转 PNG |
| **核心转换层** | `md2docx/mermaid_converter.py` (`MermaidConverter`) | **修改** | 新增 `engine` 分发逻辑（`pele` / `mmdc`）、可用性检查与缓存键隔离 |
| **渲染调用方** | `md2docx/renderer.py` (`DocxRenderer.__init__`) | **微调** | 初始化 `MermaidConverter` 时透传 `engine=mermaid_style.get("engine", "pele")` |
| **排版与插图** | `md2docx/renderer.py` (`block_code`, `_calculate_mermaid_layout`, `_add_block_image`) | **零改动** | 继续消费 `mermaid_to_image(code) -> bytes` 返回的 PNG，宽高比与分页逻辑完全不变 |
| **错误统计层** | `md2docx/converter.py` (`Converter.mermaid_report`), `MermaidReport` | **零改动** | 保持异常链提取与 CLI 退出码 `2` / GUI `Warning` 汇总机制不变 |
| **默认配置层** | `md2docx/styles.py`, `md2docx/templates/default.yaml` | **微调** | `mermaid` 配置块补充 `engine: pele` |
| **桌面界面层** | `md2docx/gui.py` | **微调** | Mermaid 设置页新增“渲染引擎 (`engine`)”只读下拉框与提示文案 |
| **构建打包层** | `pyproject.toml`, `scripts/build_nuitka.py`, `docs/NUITKA_BUILD.md` | **修改** | 引入依赖、打包 `pele.global.js` 静态资源并在 `verify_macos_app` 中增加构建产物校验 |

---

## 三、核心技术方案设计

### 1. 渲染数据流架构

```mermaid
flowchart LR
    A["Mermaid 源码 + YAML 样式配置"] --> B["PeleRenderer (threading.local QuickJS)"]
    C["Pillow 真实中文字体测宽"] -. "RenderOptions.measurer" .-> B
    B --> D["原始 SVG (含 var(--pele-*))"]
    D --> E["主题映射 & CSS 变量静态内联器"]
    E --> F["标准静态 SVG (显式宽高 + 真实色值)"]
    F --> G["resvg_py.svg_to_bytes (zoom=1.0)"]
    G --> H["高清 PNG bytes -> DocxRenderer"]
```

### 2. 五个关键工程细节设计

1. **静态资源内嵌与版本锁定**
   - 下载并锁定 npm 官方发布的 `pele@1.x` 零依赖浏览器全局包 `dist/pele.global.js` 及其 MIT `LICENSE`，存放于 `md2docx/vendor/pele/`。
   - 运行时通过 `pkgutil.get_data("md2docx", "vendor/pele/pele.global.js")` 读取（与现有 `StyleManager._load_packaged_template` 完全一致），天然兼容源码运行、Nuitka `standalone/app` 与 `onefile` 模式。

2. **线程安全的嵌入式 JS 上下文（`quickjs-ng`）**
   - 桌面端 GUI 在后台 `threading.Thread` 中执行转换（`gui.py:_do_conversion`），而 QuickJS 的 `Context` 绑定创建线程、不可跨线程调用。
   - 采用 `threading.local()` 为每个工作线程懒加载并缓存独立的 QuickJS `Context`：`pele.global.js` 在单线程生命周期内仅初始化解析一次，同篇文档连续转换 90 张图直接复用该上下文，消除重复加载开销。

3. **中文字体定位与 `TextMeasurer` 精准对齐**
   - **字体定位（进程级缓存）**：按平台探测可用中文字体文件路径：
     - macOS：优先 `/System/Library/Fonts/PingFang.ttc`、`/Library/Fonts/Microsoft/Microsoft YaHei.ttf`、`/System/Library/Fonts/STHeiti Medium.ttc`；
     - Windows：优先 `C:\Windows\Fonts\msyh.ttc`（微软雅黑）、`C:\Windows\Fonts\simhei.ttf`（黑体）、`C:\Windows\Fonts\simsun.ttc`；
     - 兜底：若未命中固定路径，使用项目已有依赖 `matplotlib.font_manager` 查找或回退 `resvg_py` 系统字体扫描。
   - **字宽对齐**：利用 `Pillow` 的 `ImageFont.truetype(font_path, size)` 实现测量回调并通过 `ctx.add_callable` 注入 `pele` 的 `RenderOptions.measurer`（若字体加载失败则回退校准过全角 CJK 宽度的字符估算表），同时将同一 `font_files=[font_path]` 传给 `resvg_py.svg_to_bytes(..., skip_system_fonts=True)`：
     - 既保证 **节点框计算宽度 == 光栅化实际绘制中文字宽**（不溢出、不贴边）；
     - 又省去 `resvg` 每次调用重复扫描上百个系统字体的 I/O 开销。

4. **现有 YAML 主题与 `theme_variables` 无缝映射 + CSS 变量展开**
   - `resvg` 不解析 CSS `var(--...)`。在 Python 层建立内置主题调色板（`default` / `base` / `dark` / `forest` / `neutral`），并将现有 YAML 的 9 个 `theme_variables` 覆盖映射到 `--pele-*` 变量表：

   | 现有 `mermaid` 配置项 | 映射目标（`--pele-*` 及 SVG 处理） |
   | :--- | :--- |
   | `background_color` (`white` / `#RRGGBB` / `transparent`) | `--pele-bg`；非 `transparent` 时确保根 `<svg>` 底层绘制同色背景 `<rect width="100%" height="100%">`，避免透明底在深色预览器中反色 |
   | `theme_variables.primaryColor` | `--pele-surface`（主节点填充色） |
   | `theme_variables.primaryTextColor` | `--pele-fg`（主文字颜色） |
   | `theme_variables.primaryBorderColor` | `--pele-border`（主节点边框色） |
   | `theme_variables.lineColor` | `--pele-line`、`--pele-accent`（连线与箭头颜色） |
   | `theme_variables.secondaryColor` / `tertiaryColor` | `--pele-surface-alt` 及序列辅助色 |
   | `theme_variables.clusterBkg` | `--pele-surface-alt` 及 `.pele-cluster` 背景色 |
   | `theme_variables.clusterBorder` | `.pele-cluster` 边框色 |
   | `theme_variables.edgeLabelBackground` | 连线标签底色 |

   - 正则扫描生成的 SVG，将所有 `var(--pele-name[, fallback])` 静态替换为最终色值，并将 `width="100%"` 修正为 `pele.render()` 返回的精确像素 `width` / `height`，确保 `resvg` 按原始比例精准光栅化。

5. **缩放倍率与缓存隔离**
   - **默认渲染倍率**：默认设置 `scale = 1.0`（即 `zoom = 1.0`），与原默认比例一致；同时支持用户在 YAML 中按需配置 `scale`（如 `1.5` / `2.0`）。
   - **缓存键升级**：`_get_cache_key` 纳入 `self.engine`（及 `pele` 渲染器版本常量），与 `mmdc` 历史缓存互不污染。

---

## 四、分阶段开发任务拆解

### 阶段 1：依赖引入与 `pele` 资源准备
- **涉及文件**：
  - 修改：`pyproject.toml`、`uv.lock`
  - 新增：`md2docx/vendor/pele/pele.global.js`、`md2docx/vendor/pele/LICENSE`、`md2docx/vendor/pele/__init__.py`
- **执行步骤**：
  - [x] 使用 `uv add` 引入 `resvg-py` 与 `quickjs-ng`（配置环境标记 `python_full_version >= '3.10'`）。
  - [x] 从 npm 官方源拉取 `pele@1.13.0` 并提取 `dist/pele.global.js` 与 `LICENSE` 放入 `md2docx/vendor/pele/`，记录版本号与 SHA-1（`5a14f20b809a5ae61b04cd8825a4940550675d11`）。
  - [x] 验证 `pkgutil.get_data("md2docx", "vendor/pele/pele.global.js")` 成功读取 733,670 字节，QuickJS 加载及 resvg_py 转换正常闭环。

### 阶段 2：实现 `PeleRenderer` 核心模块与单元测试
- **涉及文件**：
  - 新增：`md2docx/pele_renderer.py`
  - 新增：`tests/test_pele_renderer.py`
- **执行步骤**：
  - [x] 编写单元测试 `tests/test_pele_renderer.py`（17 个用例）：
    1. 基础 `flowchart` / `graph` / `sequenceDiagram` / `mindmap` / `gantt` 渲染出合法 PNG；
    2. 中文长标签、多级子图与标点测宽无截断；
    3. `default`、`base`、`dark`、`forest`、`neutral` 五大预设主题及 `theme_variables` 自定义颜色生效；
    4. CSS 变量完全展开（展开后 SVG 中无未解析的 `var(--_` 或 `var(--pele-` 字符串，且 `<rect>` 的 `style="rx:..."` 均转为 `rx="..."` XML 属性以保证 `resvg` 圆角正常渲染）；
    5. 多线程并发调用 `PeleRenderer.render_png()` 验证 `threading.local()` 无跨线程崩溃；
    6. 非法 Mermaid 语法（如 `A -- > B`）抛出带可读错误摘要的 `PeleRenderError`。
  - [x] 实现 `md2docx/pele_renderer.py` 并运行 `uv run pytest tests/test_pele_renderer.py -v` 17 个用例 1.0s 全部通过。

### 阶段 3：集成 `MermaidConverter`、样式配置与 GUI 控件
- **涉及文件**：
  - 修改：`md2docx/mermaid_converter.py`
  - 修改：`md2docx/renderer.py`
  - 修改：`md2docx/styles.py`、`md2docx/templates/default.yaml`
  - 修改：`md2docx/gui.py`
  - 修改：`tests/test_mermaid_converter.py`、`tests/test_mermaid_runtime.py`、`tests/test_gui.py`
- **执行步骤**：
  - [x] `MermaidConverter.__init__` 增加 `engine: str = "pele"` 与 `scale: Optional[float] = 1.0`：
    - `engine == "pele"` 时，`is_available()` 检查内置 `PeleRenderer`，`_render_diagram()` 调用 `PeleRenderer`；
    - `engine == "mmdc"` 时，100% 保持现有 CLI 参数拼装、`mermaid-config.json` 生成及 `resolve_external_command` 逻辑；
    - `_get_cache_key()` 包含引擎标识与版本号，确保双引擎缓存隔离；
    - `cache_dir` 遇到权限受限时优雅回退至临时目录，不阻断文档渲染。
  - [x] 在 `styles.py` (`DEFAULT_CONFIG["mermaid"]`) 与 `templates/default.yaml` 中加入 `engine: pele` 与 `scale: 1.0`。
  - [x] 在 `renderer.py` 初始化 `MermaidConverter` 时传入 `engine=mermaid_style.get("engine", "pele")` 与 `scale=mermaid_style.get("scale", 1.0)`。
  - [x] 在 `gui.py` 中为 `("mermaid", "engine")` 注册只读下拉框映射（`内置极速引擎 (Pele)` / `外部 Mermaid CLI (mmdc)`）、`("mermaid", "scale")`，以及中文标签与说明。
  - [x] 更新 `tests/test_mermaid_converter.py` 与 `tests/test_mermaid_runtime.py`（验证模拟 Finder 精简 `PATH=/usr/bin:/bin` 且无 `node`/`mmdc` 时，默认 `pele` 引擎仍能成功将 Mermaid 渲染进 `.docx`；同时保留 `engine="mmdc"` 的原有测试）。

### 阶段 4：真实中文业务图全量回归测试
- **涉及文件**：
  - 新增验证脚本：`tests/pele_verification_20261106/verify_corpus.py`
- **执行步骤**：
  - [x] 验证 `tests/mermaid_diagnosis_20260915/source-corrected.md`（90 张中文图）：
    - 结果：**90/90 成功 (100%)**，生成 90 张 Word 嵌入图片；
  - [x] 验证 8 个 `failed-*.mmd` 语法错误图：
    - 结果：**8/8 均准确捕获并记录入 `MermaidReport`**，错误信息包含精确行号与代码片段，不崩溃；
  - [x] 验证 `tests/test_md/麻城市社会救助服务项目.md`（178 张中文图，涵盖 flowchart、sequenceDiagram、mindmap、gantt）：
    - 结果：**178/178 成功 (100%)**，总转换耗时仅 **7.19 秒（平均每张图 40 毫秒，即 25 张/秒）**！
  - [x] 导出 `flowchart_subgraph`、`sequence_diagram`、`mindmap_chinese`、`gantt_schedule` 4 份典型 PNG，人工核验中文排版、圆角边框、连线箭头与配色。

### 阶段 5：Nuitka 打包适配、构建验证与文档更新
- **涉及文件**：
  - 修改：`scripts/build_nuitka.py`
  - 修改：`tests/test_build_nuitka.py`
  - 修改：`docs/NUITKA_BUILD.md`、`docs/STYLES_CONFIG.md`
- **执行步骤**：
  - [x] 在 `scripts/build_nuitka.py` 的 `build_nuitka_command` 中显式补充 `--include-package=resvg_py` 与 `--include-package=quickjs`，并在 `verify_macos_app` 中增加 `pele.global.js` 静态资源存在性断言。
  - [x] 更新 `tests/test_build_nuitka.py`，44 个打包管线测试全部通过。
  - [x] 运行全量单元测试：329 passed, 0 failed。
  - [x] 更新 `/docs` 下相关技术文档（`NUITKA_BUILD.md`、`STYLES_CONFIG.md`）。

---

## 五、已确认的细节决策与落地结果

1. **旧 YAML 配置文件的升级行为**：未显式指定 `engine: mmdc` 时，一律默认启用新引擎 `pele`；仅当配置 `engine: mmdc` 时调用外部 `mmdc`。
2. **`pele` 渲染失败时的策略**：遇到非法 Mermaid 语法时直接记录失败并保留源码块，不自动回退调用 `mmdc`。
3. **默认缩放倍率**：默认设置 **`scale = 1.0`**（`zoom = 1.0`）。
4. **性能对比**：
   - 旧版 `mmdc`：单图冷启动 1.5s～3.0s，178 张图需 5～8 分钟，依赖 Node.js/Chromium；
   - 新版 `pele`：单图仅需 ~40ms，178 张图仅 7.19 秒（**提速约 50 倍**），零外部安装依赖！
