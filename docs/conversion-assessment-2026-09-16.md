# Mermaid 图片排版与 Word 可编辑公式版本评估

## 后续修复与验收

2026-09-16 后续已修复源码：在 `md2docx/renderer.py` 的 `_add_block_image()` 中为图片段落显式设置 `paragraph_format.line_spacing = 1.0`。这会写入自动单倍行距，让 Word 根据嵌入图片的实际高度排版。正文继续使用自身的段落格式；无需调整正在使用的 YAML 或 Word 模板。

新增 `tests/test_image_template_layout.py`，覆盖 Mermaid 与普通 Markdown 图片加载固定 28 磅 Normal 样式模板的完整转换。两个用例修复前均因固定行距断言失败，修复后通过；连同 Mermaid、公式和转换集成测试，**59 passed**。

使用用户正在使用的 YAML、Doc1.docx 和截图对应片段，并以 Finder 精简 PATH 实际调用 Mermaid CLI/Chromium 和 Pandoc，再次验证：

- 图片 1/1 成功，约 418.22 磅高；图片段落写入 `w:line="240" w:lineRule="auto"`，模板 Normal 样式仍为固定 28 磅。
- 六个公式全部生成 OMML，正文公式图片为 0。
- 新输出的 Mermaid 与公式文档各渲染为一页，已逐页目视确认流程图完整、下一标题位于图下方、六个公式显示完整。
- GitNexus 变更检测仅定位到 `_add_block_image` 及其所属类，符合预期。上游 impact 风险为 LOW，detect_changes 整体汇总为 medium；图片和普通图像相关流程已覆盖。

修复后验收材料位于 `tests/conversion_assessment_20260916/fixed-gui-template/`。本次完成源码修复与验收，尚未重新打包或替换已安装桌面应用；以下内容保留修复前的历史评估结果。

## 原评估结论

评估日期：2026-09-16。结论：截图中的 Mermaid 已正确生成 PNG，但图片段落继承 Word 模板的固定 28 磅行距，导致约 418 磅高的图片被裁切、看起来与前文重叠。6 月及 8 月不使用 Word 模板的版本正常；支持该模板的旧版也有相同问题。当前工作区的可编辑公式转换通过本次测试。

原评估阶段只新增评估脚本、测试副本和此文档，没有修改产品代码，没有创建提交或回退工作区已有修改。评估开始时 HEAD 为 `022ef8b`，昨日运行环境修复尚未提交；评估期间工作区经其他操作出现提交 `d2d6262`（“优化了打包”）。原评估收尾时产品代码相对 `d2d6262` 无未提交差异，下方历史表中的“当前工作区”结果对应修复前的这份代码。

## 输入与验证方法

- 从原始武穴项目 Markdown 中找到截图原文“同时，建立案例库……”和紧随其后的流程图，保留至“四、分类分层帮扶的落地执行策略”。抽取副本见 `tests/conversion_assessment_20260916/screenshot-excerpt.md`。
- 配置：`/Users/zhangqijin/Desktop/桌面文件/md2docx简单表格配置.yml`。
- 模板：`/Users/zhangqijin/Documents/Field/素材/word模板/Doc1.docx`。
- Git 历史通过 `git archive` 提取到测试目录，各版本在独立 Python 进程中导入；使用相同输入、配置和当前已安装依赖，避免修改当前检出。
- 实际调用 Mermaid CLI 和 Pandoc，检查生成的 DOCX XML、嵌入图片、OMML 结构，并使用 Codex 随附的 LibreOffice 渲染当前故障样本、旧版样本、单变量对照样本和公式样本。
- 环境：Node v26.4.0、Mermaid CLI 11.12.0、Pandoc 3.5。历史比较反映旧代码在当前依赖下的行为，不等同于重建当年的二进制和依赖环境。

## 版本测试结果

“正常”指截图样本能生成完整的嵌入图片，且图片段落没有小于图片高度的固定行高。“公式通过”指六个公式全部为原生 OMML、零公式图片，并具备预期的分式、根式、上下标和大型运算符结构。

| 版本 | 无 Word 模板的 Mermaid | 使用 Doc1.docx 的 Mermaid | 可编辑公式（常规 PATH） |
|---|---|---|---|
| `cd04fc8`，2026-06-15 | 正常 | 尚不支持模板参数 | 尚未实现；0 个 OMML，生成图片/源码 |
| `d14566d`，2026-06-24 | 正常 | 尚不支持模板参数 | 6/6 通过 |
| `446fd59`，2026-08-18 | 正常 | 尚不支持模板参数 | 6/6 通过 |
| `80fd050`，2026-08-20，引入模板 | 正常 | 此模板触发 `NotImplementedError` | 无模板 6/6；带模板也被初始化错误阻断 |
| `1eeb7e7`，2026-08-20，模板修复 | 正常 | 图片继承固定 28 磅行距，异常 | 无模板/带模板均 6/6 |
| `022ef8b`，评估开始时 HEAD | 正常 | 同上 | 无模板/带模板均 6/6 |
| 当前工作区，后提交为 `d2d6262`，含昨日运行环境修复 | 正常 | 同上 | 无模板/带模板均 6/6 |

因此不能通过简单回退到 `1eeb7e7` 或 `022ef8b` 来解决此图片问题。更早的正常版本尚未支持加载 Word 模板，不能把它们的无模板通过结果解释成“相同模板下也正常”。

另外，`022ef8b` 虽然提交说明是“完全重构,第1版”，实际只改变 `.DS_Store` 和 `编译命令.md`，没有修改图片或公式实现。

## 图片根因与单变量验证

模板的 Normal 样式（styleId 为 `a`）具有：

```xml
<w:spacing w:after="0" w:line="560" w:lineRule="exact"/>
```

560 twips = 28 pt。`DocxRenderer._add_block_image()` 新建默认段落，只设置居中、段前段后距离和分页相关属性，没有覆盖行距。图片采用 `wp:inline`，因此继承模板的固定行距。截图流程图的 `wp:extent/@cy` 对应高度约 418.22 pt，远超段落为它保留的 28 pt。

用户已确认测试所用 YAML 就是正在使用的配置。其中 `document.line_spacing: 1.5` 和 `paragraph.line_spacing: 1.5` 不会覆盖这个图片段落的模板继承值；正文有单独的段落格式处理，而图片帮助函数没有同样设置行距。因此本次不建议修改 YAML 中的图片宽度、分页阈值或正文行距来绕过问题。

验证结果：

1. PNG 本身完整；图形数量为 1，正文浮动锚点 `wp:anchor` 为 0，排除了“图片生成残缺”和“意外浮动定位”作为本次根因。
2. 当前版和 `1eeb7e7` 使用模板时都出现裁切；旧版无模板输出完整。
3. 仅在测试 DOCX 中将图片段落设为 `w:line="240" w:lineRule="auto"`，不改正文、模板样式、图片、尺寸、边距或分页，流程图即完整显示，下一标题自然排到图下方。
4. 对照文件和原始文件的 ZIP 包仅 `word/document.xml` 不同，所有媒体字节及其余包内容保持相同。
5. 对八个历史点的 `_add_block_image()` 做 AST 比较，从 `8989494` 到 `022ef8b` 函数一致。4 月和 6 月确实有图片缩放、分页、与前段绑定的改进，但没有解决后来引入的模板固定行距继承问题。

可重复的失败检查：

```sh
UV_CACHE_DIR=/private/tmp/md2docx-uv-cache uv run --no-sync python tests/conversion_assessment_20260916/check_layout.py tests/conversion_assessment_20260916/current-template.docx
```

输出图片高度约 418.22、固定行高 28、`clipped: true`，并以断言失败结束。将文件参数替换为 `tests/conversion_assessment_20260916/spacing-only-control.docx`，输出 `line_rule: auto`、`clipped: false`，检查通过。此文件只是验证根因的对照副本，产品代码尚未修复。

## 公式功能验证

实际链路是 LaTeX → Pandoc → DOCX → 提取 OMML → 写入最终 Word。Mermaid 的链路是 Mermaid 源码 → Node/Mermaid CLI → PNG → python-docx 嵌入。

六个公式覆盖两个行内公式、三个双美元块公式和一个 `latex` 围栏公式：上标、分式、嵌套根式、求和、积分与样本量公式。当前输出具有：

- `m:oMath`：6 个；其中 `m:oMathPara`：4 个。
- `m:f`：5 个；`m:rad`：1 个；`m:nary`：2 个。
- 公式文档正文 `w:drawing`：0 个；文档编辑保护：0 个。
- 渲染后六个公式显示完整。这支持“输出为 Word 原生可编辑公式”的判断，并非以图片外观代替验证。

## 精简 PATH 与昨日修复

在 Python 进程内设置 `PATH=/usr/bin:/bin:/usr/sbin:/sbin`，模拟 Finder 启动应用的依赖查找环境：

| 版本 | Mermaid 渲染 | 可编辑公式 |
|---|---|---|
| `022ef8b` | 0/1；找不到 CLI，退回源码 | 0/6 OMML，6 张图片 |
| 当前工作区 | 1/1；实际调用本机 Mermaid CLI | 6/6 OMML，0 张图片 |

当前工作区在精简 PATH 下仍有模板固定行距问题，但昨日“外部工具找不到”的修复有效。运行环境问题和这次图片段落排版问题需要分别处理。

## 测试覆盖与影响评估

本次原有测试命令：

```sh
UV_CACHE_DIR=/private/tmp/md2docx-uv-cache uv run --no-sync pytest -q tests/test_mermaid_rendering.py tests/test_mermaid_converter.py tests/test_mermaid_runtime.py tests/test_math_rendering.py tests/test_formula_runtime.py
```

结果：**38 passed**。它们没有覆盖“Word 模板 Normal 样式为固定行距”场景，因此通过并不能证明此次排版正确。另完成 13 个版本/模板/环境组合，共 26 个图片或公式转换用例（包括预期不支持和故障用例），详细结果见 `tests/conversion_assessment_20260916/matrix.json`。

已更新代码图谱和 GitNexus 索引，并交叉核对调用链。GitNexus 对 `_add_block_image` 的上游影响评估为 **LOW**，直接调用者为 `block_code` 与 `_embed_local_image`，间接涉及普通 Markdown 图片入口 `image`。结果汇总的受影响入口为 2 类：代码块图形和普通图片。公式原生 OMML 通过 `_append_omml`，不经过此图片帮助函数。

建议后续在 `_add_block_image` 显式设置可容纳图片的非固定行距，并补充“固定行距模板 + 真实 Mermaid/普通图片”的回归覆盖。应保留正文样式和昨日工具定位修复。此变更会影响普通图片，验收时也应覆盖普通图片、无模板、短图、长图及分页。

## 验证边界

- 本次用截图对应片段做精确定位和对照，没有重新逐页审核全文 90 张图。
- 可编辑性通过原生 OMML、结构、无图片和无保护验证；没有在 Microsoft Word 中逐个点击修改公式。
- 页面目视检查使用随附 LibreOffice，已配置本机中文字体。Word 与 LibreOffice 的裁切位置可有差异，不声称像素级一致。
- 精简 PATH 测试是源码级真实转换，不是本次重新打包后点击 GUI 的验收。

评估脚本、历史副本、命令日志、输入样本、DOCX 和渲染材料统一保留于 `tests/conversion_assessment_20260916/`。
