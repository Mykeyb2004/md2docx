# Nuitka 打包

## 目标

生成可独立分发的可执行文件，并在可执行文件同目录放置一份可编辑的 `default.yaml`。

程序运行时的配置优先级如下：

1. 可执行文件同目录下的 `default.yaml`
2. 包内置的 `md2docx/templates/default.yaml`
3. 代码中的硬编码兜底默认值

## 推荐命令

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

## 输出位置

- onefile: `build/nuitka/md2docx-gui` 或 `build/nuitka/md2docx-cli`
- standalone: `build/nuitka/md2docx-gui.dist/` 或 `build/nuitka/md2docx-cli.dist/`
- 可编辑配置: 与可执行文件同目录的 `default.yaml`

Windows 下的 onefile 产物文件名会带 `.exe`，例如 `build/nuitka/md2docx-gui.exe`。

## 说明

- `gui` 入口会启用 Nuitka 的 `tk-inter` 插件。
- 构建命令会把包内模板一起编进程序，保证外部 `default.yaml` 被删掉时仍可运行。
- 分发给用户时，建议把可执行文件和旁边那份 `default.yaml` 一起提供。

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
