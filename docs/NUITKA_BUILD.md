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

## 说明

- `gui` 入口会启用 Nuitka 的 `tk-inter` 插件。
- 构建命令会把包内模板一起编进程序，保证外部 `default.yaml` 被删掉时仍可运行。
- 分发给用户时，建议把可执行文件和旁边那份 `default.yaml` 一起提供。
