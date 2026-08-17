# Nuitka 打包

## macOS Apple Silicon 推荐方式

要求：macOS Apple Silicon 和 `uv`。仓库通过 `.python-version` 固定使用 Python 3.11.9；第一次运行时，`uv` 会自动准备对应环境。不要改用 uv 的 Python 3.12.11 构建此 app：该分发版的动态 `_tkinter.so` 没有为 Nuitka 重写 Tcl/Tk 路径预留足够的 Mach-O 头空间，会导致 `install_name_tool` 编译失败。

在仓库根目录执行：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode app
```

该命令会依次检查环境、运行测试、编译、暂存、进行本地 ad-hoc 签名、验证并发布应用。最终产物为：

```text
dist/macos/
├── Md2docx.app
└── default.yaml
```

`Md2docx.app` 使用 Nuitka standalone app bundle，不是 onefile，因此启动时不需要先把运行环境解压到临时目录。`default.yaml` 是可编辑示例；应用内部仍包含 `md2docx/templates/default.yaml`，删除外部示例不会阻止启动。

直接启动已经生成的应用：

```bash
open dist/macos/Md2docx.app
```

常用选项：

- `--clean`：删除已知的 `build/nuitka` 中间产物后重新编译。
- `--skip-tests`：临时跳过构建前测试，适合本地快速迭代。
- `--launch`：仅在签名、验证和发布全部成功后打开应用。

例如，完整清理并在成功后启动：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode app --clean --launch
```

诊断日志保存在 `build/logs/macos-app-build.log`。构建候选位于 `dist/macos.staging`；只有验证成功后才会替换 `dist/macos`。测试、编译或验证失败时，上一次成功的 `dist/macos/Md2docx.app` 保持不变。

当前 app 管线仅支持 macOS arm64 本机构建，使用 ad-hoc 签名，不需要 Apple Developer 账号。Developer ID、notarization、DMG、universal binary 和 CI 构建不在当前版本范围内。

## 兼容的原有构建方式

GUI onefile：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode onefile --clean
```

CLI onefile：

```bash
uv run --group build python scripts/build_nuitka.py --entry cli --mode onefile --clean
```

GUI standalone：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode standalone --clean
```

原有产物仍位于 `build/nuitka`，可编辑配置与对应可执行文件放在同一目录。Windows onefile 文件名带 `.exe`。

## GitHub Actions 构建 Windows EXE

仓库已提供工作流文件：

- `.github/workflows/build-windows.yml`

使用方法：

1. 把当前项目推送到 GitHub 仓库。
2. 打开仓库页面的 `Actions`。
3. 选择 `Build Windows EXE`。
4. 点击 `Run workflow`。
5. 选择要打包的入口：
   - `gui`：桌面窗口版
   - `cli`：命令行版
6. 选择打包模式：
   - `onefile`：单文件，适合直接分发
   - `standalone`：目录模式，方便排查问题
7. 等待构建完成后，在该次运行页面下载 artifact。

artifact 名称格式：

- `md2docx-windows-gui-onefile`
- `md2docx-windows-cli-onefile`
- `md2docx-windows-gui-standalone`
- `md2docx-windows-cli-standalone`

默认推荐：

- `entry = gui`
- `mode = onefile`
