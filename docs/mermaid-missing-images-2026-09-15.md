# 武穴项目 Mermaid 图片缺失诊断

## 修复状态（同日后续）

已修复并重新打包 macOS arm64 应用。以下原始诊断保留用于说明问题出现时的行为。

- 统一查找桌面应用需要的外部工具，支持本机 Homebrew、用户 bin、NVM、Volta 常用目录，并向 Mermaid 子进程传入可以找到 Node.js 的 PATH。不会读取或执行用户 shell 配置。
- 公式转换存在同类问题：Finder 环境无法找到 `/usr/local/bin/pandoc`，导致原生 Word 公式退化为 PNG。已通过同一工具定位机制修复；公式渲染失败时也会记录原因，并关闭 Matplotlib 图形以防资源泄漏。
- GUI 在图形失败、公式图片回退或公式失败时显示警告、数量和原因，历史记录标记为 Warning。CLI 保留输出并返回退出码 2。转换成功的原生公式仍可在 Word 中编辑。
- 277 项测试通过。全量测试通过后的打包因可选 ccache 下载证书校验失败而中断；使用 Nuitka 官方 `--disable-cache=ccache` 参数重试成功，没有关闭证书校验。新包通过深层签名验证。
- 修复后以 `/usr/bin:/bin:/usr/sbin:/sbin` 为 PATH，使用原 YAML 和 Word 模板再次转换全文：原始 Markdown 为 **82/90 张图，准确报告 8 个语法错误**；修正测试副本为 **90/90 张图，0 失败**。见 `tests/mermaid_diagnosis_20260915/acceptance.py` 及对应 `*-fixed-runtime.json`。

交付包位于 `dist/macos/Md2docx.app` 和 `dist/macos/Md2docx-macOS-arm64-20260915.zip`。已更新 `/Applications/Md2docx.app`，旧版备份为 `/Applications/Md2docx-before-20260915.app`。安装后深层签名校验通过，安装版与交付包主程序 SHA-256 一致。需要退出当前仍运行的旧进程并重新打开应用。

本次未修改用户原始 YAML、Markdown 或 Word；8 个图块的语法修正仅在测试副本中。打包应用仍依赖本机已安装的 Mermaid CLI、Node.js 和 Pandoc。

GUI 验证边界：新打包应用以精简 PATH 启动成功，并能读取原 YAML、Word 模板和历史记录。自动审批拒绝了未先核实字段内容就点击转换的组合操作（防止误覆盖文档）；改为仅填写并查看字段时，Tk 应用读取剪贴板超时，未开始转换。因此不将源码端验收或界面单元测试宣称为打包 GUI 的完整转换验收。测试启动的进程已关闭，用户原有进程保留。

## 原始诊断

2026-09-15。本次检查使用用户指定的 YAML、Markdown，以及 GUI 当前记忆的 Word 模板 Doc1.docx。结论：YAML 中的 Mermaid 样式设置可以正常工作；全部图片缺失的直接原因是打包版 GUI 找不到 Mermaid CLI 和 Node.js。此外，原文有 8 个图块存在语法错误，程序静默降级又掩盖了这两类问题。

## 实测结果

| 场景 | 预期图片 | Word 正文图片 | 残留 Mermaid 源码块 |
|---|---:|---:|---:|
| 用户 19:01:12 生成的原 Word | 90 | 0 | 90 |
| 第一张图，模拟 GUI 的 PATH | 1 | 0 | 1 |
| 第一张图，仅把 mmdc 改为绝对路径 | 1 | 0 | 1 |
| 原文全文，正确运行环境，原 YAML 和 Word 模板 | 90 | 82 | 8 |
| 修正 8 个图块的测试副本，正确运行环境，原 YAML 和 Word 模板 | 90 | 90 | 0 |

原 Word 包含 4 个媒体文件，但它们的 SHA-256 均与 Word 模板中的媒体匹配，不是正文流程图。不能仅用 DOCX 包内的图片文件数量判断 Mermaid 是否成功。

## 运行环境根因

正在运行的进程是 `/Applications/Md2docx.app/Contents/MacOS/md2docx-app`，PID 为 2411。只读获取到的 PATH 是：

```text
/usr/bin:/bin:/usr/sbin:/sbin
```

该 PATH 下 `shutil.which('mmdc')` 和 `shutil.which('node')` 都返回空。实际安装位置是：

```text
/Users/zhangqijin/.nvm/versions/node/v26.4.0/bin/mmdc
/Users/zhangqijin/.nvm/versions/node/v26.4.0/bin/node
```

本次使用的 Mermaid CLI 版本为 11.12.0。配置中的 `command: mmdc` 需要通过 PATH 查找命令。GUI 环境缺少 NVM 的 bin 目录，因此立即报找不到 Mermaid CLI；终端能执行 mmdc，并不代表桌面应用也能执行。

只将 `command` 改成 mmdc 的绝对路径也不足以修复：mmdc 的首行为 `#!/usr/bin/env node`，仍需要从 PATH 查找 node。对照测试得到 `env: node: No such file or directory`。

## 原文中另外 8 个错误图块

以下行号为原始合并 Markdown 中 Mermaid 围栏的起始行。8 个图均经真实 CLI 单独核验，返回 `Lexical error`。

| 图序号 | 起始行 | 所属章节 | 错误及修正方式 |
|---:|---:|---|---|
| 21 | 3150 | 3.1.2 政务环境下平台操作与运行记录 | `E -- 政策保障 --F` 等缺少完整箭头，改为 `E -->\|政策保障\| F` |
| 33 | 4456 | 4.1.1 窗口值守与统一受理 | 多条带标签连线以 `--` 结束，改为标准的 `-->\|标签\|` |
| 42 | 5444 | 4.5.2 超权限事项边界控制与应急协作 | `-- >` 中有空格，改为 `-->` |
| 54 | 6836 | 6.4.1 救助权益政策告知与协助 | 图块末尾多出一行单独的 `]`，删除该行 |
| 65 | 8363 | 7.3.2 多岗位复核与整改 | 多处 `-- >` 中有空格，改为 `-->` |
| 83 | 10619 | 9.1.5 日常管理制度与考勤纪律 | 混用了两种边标签写法且箭头不完整，合并标签并使用标准箭头 |
| 84 | 10752 | 9.2.1 请休假疾病离职补位 | 多条带标签连线箭头不完整，改为标准箭头 |
| 88 | 11170 | 9.4.1 服务连续性与应急值守 | `-- 4小时以内 --\|触发三级响应\|` 等混用标签语法，改为一个完整的带标签箭头 |

例如：

```text
错误：E -- 政策保障 --F[对接政府救助政策]
正确：E -->|政策保障| F[对接政府救助政策]

错误：B -- 属于辅助事务 -- > C[标准流程办理与反馈]
正确：B -- 属于辅助事务 --> C[标准流程办理与反馈]

错误：B -- 4小时以内 --|触发三级响应| C[现场B角人员直接兼任]
正确：B -->|4小时以内：触发三级响应| C[现场B角人员直接兼任]
```

## 为什么界面仍然显示“成功”

代码图谱和 GitNexus 确认了以下调用和异常处理：

1. [renderer.py](/Users/zhangqijin/PycharmProjects/md2docx/md2docx/renderer.py:68) 将 YAML 中的命令、格式、主题和颜色传给 MermaidConverter。
2. [mermaid_converter.py](/Users/zhangqijin/PycharmProjects/md2docx/md2docx/mermaid_converter.py:52) 通过 `shutil.which` 查找命令；找不到命令时抛出异常。
3. [renderer.py](/Users/zhangqijin/PycharmProjects/md2docx/md2docx/renderer.py:1510) 使用 `except Exception: pass` 吞掉图块转换异常，继续把图源码写成普通代码段。CLI 语法错误也走同一降级分支。
4. [gui.py](/Users/zhangqijin/PycharmProjects/md2docx/md2docx/gui.py:2127) 在文档保存完成后直接记为 Success，没有检查图块成功/失败数量。

因此，界面“成功”只说明 Word 保存成功，不能说明每张图都成功。GitNexus 对 MermaidConverter 的静态上游影响评估为 LOW；该结果仅辅助定位，修复时仍需覆盖 CLI、GUI 和普通代码块的行为。

## 配置评估与处理建议

`format: png` 可被 Word 正常嵌入；`theme: base` 与 `theme_variables` 配套正确；当前宽度、配色和分页比例能够完成全部 90 张图的转换，不是这次缺图原因。无需通过调整颜色、宽度、分页参数处理此故障。

临时处理方式：退出当前 GUI 后，从终端直接启动带有 NVM 路径的应用进程，并使用修正语法后的 Markdown。下面命令针对本机当前的 Node.js 安装路径：

```sh
PATH="/Users/zhangqijin/.nvm/versions/node/v26.4.0/bin:$PATH" /Applications/Md2docx.app/Contents/MacOS/md2docx-app
```

该启动命令未在本次检查中执行，避免另外打开一份 GUI；其对应的 PATH 修复已通过实际转换链路验证。若 Node.js 安装路径以后变更，启动路径也需要调整。

程序层面建议：为打包应用增加 mmdc、Node.js 的依赖定位和启动前检查；转换时记录每个失败图块的位置与具体错误；结束时显示“90 张图成功 82 张、失败 8 张”等统计，存在失败图时不能仅显示完整成功。保留源码作为降级内容仍可接受，但必须明确提示不完整转换。

原始诊断阶段仅完成诊断与测试副本验证；后续源码修复、打包与复验见文首“修复状态”。

## 验证材料

- [完整测试 Word：90 张图已嵌入](/Users/zhangqijin/PycharmProjects/md2docx/tests/mermaid_diagnosis_20260915/corrected.docx)
- [修正后的 Markdown 测试副本](/Users/zhangqijin/PycharmProjects/md2docx/tests/mermaid_diagnosis_20260915/source-corrected.md)
- [原文在正确环境下的核验结果：82/90](/Users/zhangqijin/PycharmProjects/md2docx/tests/mermaid_diagnosis_20260915/full.json)
- [修正副本核验结果：90/90](/Users/zhangqijin/PycharmProjects/md2docx/tests/mermaid_diagnosis_20260915/corrected.json)
- [8 张图的完整 CLI 错误](/Users/zhangqijin/PycharmProjects/md2docx/tests/mermaid_diagnosis_20260915/syntax-errors.json)
- [诊断脚本](/Users/zhangqijin/PycharmProjects/md2docx/tests/mermaid_diagnosis_20260915/diagnose.py)
- [语法核验与测试副本生成脚本](/Users/zhangqijin/PycharmProjects/md2docx/tests/mermaid_diagnosis_20260915/check_syntax.py)

已比对确认，仅第 21、33、42、54、65、83、84、88 个 Mermaid 图块发生修改，所有图块之外的文字一致。检查了 DOCX 正文图形数量与源码残留，并目视抽查了第一张渲染 PNG；本次未逐页审核整份 Word 的最终排版。

复验示例，从项目根目录执行：

```sh
uv run python tests/mermaid_diagnosis_20260915/diagnose.py gui-path
uv run python tests/mermaid_diagnosis_20260915/diagnose.py absolute-command
uv run python tests/mermaid_diagnosis_20260915/diagnose.py full
uv run python tests/mermaid_diagnosis_20260915/check_syntax.py
uv run python tests/mermaid_diagnosis_20260915/diagnose.py corrected
```

修复前，前两个场景断言失败；原文全文场景报告 82 张图并断言失败；修正场景报告 90 张图并通过。修复后，前两个场景应通过，也可运行 `uv run python tests/mermaid_diagnosis_20260915/acceptance.py` 验证两个全文场景。需要允许 Mermaid CLI 启动本机 Chromium。本次受限执行环境曾单独阻止 Chromium 启动，允许本机进程启动后已排除该诊断环境干扰，不将它归因于用户故障。
