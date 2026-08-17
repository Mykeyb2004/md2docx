# macOS 应用图标设计规格

## 背景

项目已经能够通过 Nuitka 重复构建 `dist/macos/Md2docx.app`，但应用包尚未包含专用图标。本次工作为应用增加可维护、可重复生成的 macOS 图标资源，并把图标接入现有构建和验证流程。

## 目标

- 为 `Md2docx.app` 提供专用的 macOS 应用图标。
- 图标在 Finder、Dock、启动台和应用切换器中正确显示。
- 日常应用构建直接使用仓库内的 `.icns` 成品，不增加不必要的生成耗时。
- 图标需要变更时，可以用单独命令从主图重新生成 `.icns`。
- 构建在缺少图标或图标未正确写入应用包时明确失败。
- 在现有 `编译管线.md` 中记录图标生成与应用构建命令。

## 非目标

- 不在 GUI 窗口内部增加 Logo 或品牌区域。
- 不更改当前界面布局、功能或启动流程。
- 不在每次构建应用时重新生成图标。
- 不使用 Microsoft Word 商标、仿制图形或 `W` 标志。
- 不接入 AI 图片生成服务；图标由可编辑的矢量源文件和确定性的本地转换流程维护。

## 视觉设计

### 方向

图标采用“文档转换”方向，以两张错位文档和一条弧形箭头表达从源文档到排版后文档的过程。图形本身传达转换语义，不出现 `MD`、`DOCX`、`W` 等文字。

### 构图

- 使用符合现代 macOS 风格的圆角方形底板，并在 1024×1024 画布内保留安全边距。
- 左侧为带简化文本行的源文档。
- 右侧为文本行排列更规整的目标文档。
- 两张文档适度错位，形成从左到右、从后到前的方向感。
- 文档之间使用清晰的弧形箭头，作为转换动作的视觉中心。
- 小尺寸下优先保留文档轮廓、箭头和少量粗线条，避免细碎装饰。

### 配色

- 底板使用经典蓝渐变，主色从较明亮的天蓝过渡到较深的文档蓝。
- 文档主体使用白色或轻微偏蓝的白色。
- 箭头使用与底板有充分明度差的深蓝色。
- 图标必须在浅色和深色 Dock 背景下保持清晰。

### 尺寸要求

- 主 PNG 为 1024×1024 像素。
- `.icns` 包含 macOS 常用的 16、32、128、256、512 像素及对应 Retina 2× 资源。
- 16×16 和 32×32 输出中仍能辨认两张文档与转换箭头。

## 资源结构

新增以下文件：

```text
assets/macos/AppIcon.svg
assets/macos/AppIcon.png
assets/macos/AppIcon.icns
scripts/build_macos_icon.sh
```

各文件职责如下：

- `AppIcon.svg` 是可编辑的视觉源文件。
- `AppIcon.png` 是 1024×1024 的稳定转换输入，也是视觉检查基准。
- `AppIcon.icns` 是日常应用构建直接使用的成品。
- `build_macos_icon.sh` 从主 PNG 生成完整 iconset，再使用 `iconutil` 输出 `.icns`。

不提交生成过程中的临时 `.iconset` 目录。

## 图标生成流程

图标只在设计发生变化时重新生成：

```text
assets/macos/AppIcon.svg
  → 导出并目视确认 1024×1024 AppIcon.png
  → scripts/build_macos_icon.sh
  → 临时 AppIcon.iconset
  → assets/macos/AppIcon.icns
```

SVG 发生变化时，先使用支持 SVG 的图形编辑器导出 1024×1024 主 PNG，并确认外观无误；仓库脚本负责从已经确认的主 PNG 确定性地生成全部 macOS 图标尺寸。日常重新构建应用不执行以上步骤。

生成脚本执行以下步骤：

1. 确认当前系统为 macOS，并检查 `sips` 和 `iconutil` 可用。
2. 确认主 PNG 存在、格式可读取且尺寸为 1024×1024。
3. 使用临时目录创建标准命名的各尺寸 PNG。
4. 使用 `iconutil` 生成候选 `.icns`。
5. 确认候选文件存在且非空后，再更新仓库中的 `AppIcon.icns`。
6. 无论成功或失败，都清理临时目录。

中途失败时保留原有可用的 `.icns`，不留下部分生成的正式资源。

## 应用构建集成

现有构建入口保持不变：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode app --clean
```

`scripts/build_nuitka.py` 在构造 GUI app 的 Nuitka 命令时：

1. 解析仓库内 `assets/macos/AppIcon.icns` 的固定路径。
2. 在执行 Nuitka 前确认该文件存在且非空；否则显示明确错误并终止构建。
3. 通过 Nuitka 的 macOS app icon 参数把 `.icns` 写入应用包。
4. 保持现有应用名称、内部可执行文件名、Python 版本固定策略和输出目录不变。
5. 在图标已经进入应用包后执行现有 ad-hoc 签名，使签名覆盖最终资源。

## 构建后验证

GUI app 构建完成后，在现有验证基础上增加：

- 读取 `Md2docx.app/Contents/Info.plist`，确认存在有效的图标声明。
- 根据图标声明确认 `Contents/Resources` 中对应 `.icns` 文件存在且非空。
- 继续执行现有架构、Tcl/Tk、模板文件和代码签名验证。

若图标声明或资源缺失，构建命令返回失败，不把该应用包视为成功产物。

## 错误处理

- 缺少源 PNG：图标生成脚本说明缺少的绝对或仓库相对路径并退出。
- 主 PNG 尺寸错误：报告实际尺寸与要求尺寸，不开始转换。
- 缺少 `sips` 或 `iconutil`：说明该命令需要在带有 Xcode Command Line Tools 的 macOS 上运行。
- `.icns` 生成失败：不覆盖现有成品，并返回非零状态。
- 构建时缺少 `.icns`：在启动 Nuitka 前失败，并提示先运行图标生成命令。
- 应用包未声明或未包含图标：构建后验证失败。

## 测试与验收

### 自动测试

- 测试 GUI app 的 Nuitka 命令包含正确的 macOS 图标参数和资源路径。
- 测试 CLI 或其他非 app 构建模式不错误地接入 macOS app 图标。
- 测试图标缺失时构建前检查会产生明确错误。
- 测试 app 验证逻辑会拒绝缺少图标声明或图标资源的应用包。
- 运行完整测试套件：`uv run pytest`。

### 真实构建验收

- 运行一次完整的 GUI app 构建。
- 确认产物为 `dist/macos/Md2docx.app`。
- 确认应用包内存在图标资源，`Info.plist` 指向该资源。
- 确认 `codesign --verify --deep --strict` 通过。
- 在 Finder 或 Dock 中目视检查图标，并分别检查 16×16、32×32 和大尺寸预览的辨识度。
- 启动应用，确认接入图标没有改变原有启动和转换功能。

## 文档更新

在根目录的 `编译管线.md` 中补充两类命令：

```bash
# 图标设计变化后才需要执行
bash scripts/build_macos_icon.sh

# 日常构建命令保持不变
uv run --group build python scripts/build_nuitka.py --entry gui --mode app --clean
```

文档需要明确说明：`.icns` 已提交到仓库，正常重复编译无需先执行图标生成脚本。

## 完成标准

当以下条件全部满足时，本功能完成：

- 经典蓝“文档转换”图标源文件、主 PNG 和 `.icns` 均在仓库中。
- 图标生成脚本可以在 macOS 上重复生成有效 `.icns`。
- 现有构建命令无需增加参数即可生成带图标的 `Md2docx.app`。
- 自动测试和真实 app 构建验证全部通过。
- 图标在 Finder、Dock、启动台和应用切换器中正确显示。
- `编译管线.md` 已记录图标维护方法。
