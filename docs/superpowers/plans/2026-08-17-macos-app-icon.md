# macOS 应用图标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已批准的经典蓝“文档转换”图标接入现有 Nuitka macOS app 管线，并验证 `Md2docx.app` 在 Finder、Dock、启动台和应用切换器中使用该图标。

**Architecture:** 保留 `scripts/build_nuitka.py` 作为唯一公开构建入口；把可编辑 SVG、1024×1024 主 PNG 和提交到仓库的 `.icns` 放在 `assets/macos/`。图标变化时单独运行 `scripts/build_macos_icon.sh`，日常 app 编译只引用已经生成的 `.icns`，并在签名后由 `verify_macos_app()` 检查 `Info.plist` 和资源文件。

**Tech Stack:** macOS `sips`、`iconutil`、`file`、`codesign`，Nuitka macOS app bundle，Python 标准库 `pathlib`/`plistlib`/`subprocess`，`uv` 和 `pytest`。

---

## 文件地图

- Create: `assets/macos/AppIcon.svg` — 经典蓝文档转换图标的矢量源文件。
- Create: `assets/macos/AppIcon.png` — 从批准的 SVG 导出的 1024×1024 主 PNG。
- Create: `assets/macos/AppIcon.icns` — 由主 PNG 生成并提交的 macOS 成品资源。
- Create: `scripts/build_macos_icon.sh` — 校验主 PNG、生成各尺寸 iconset 并原子更新 `.icns`。
- Modify: `scripts/build_nuitka.py:18-150` — 增加图标路径、Nuitka 参数和 app 预检。
- Modify: `scripts/build_nuitka.py:314-368` — 验证 app 的图标声明和资源。
- Modify: `tests/test_build_nuitka.py` — 先写失败测试，再覆盖命令、预检、fake bundle 和验证逻辑。
- Create: `tests/test_macos_icon_assets.py` — 检查仓库资源存在、主 PNG 尺寸和 `.icns` 文件类型。
- Modify: `docs/编译管线.md` — 记录图标重新生成命令和日常构建命令的区别。

不要修改、暂存或提交用户已有的 `md2docx/gui.py`、`tests/test_gui.py`、`docs/superpowers/plans/2026-08-17-output-overwrite-confirmation.md` 和 `docs/superpowers/specs/2026-08-17-output-overwrite-confirmation-design.md`。

## Task 1: Add deterministic icon generator

**Files:**
- Create: `scripts/build_macos_icon.sh`

- [ ] **Step 1: Create the generator with fixed repository-relative paths and safe temporary output**

Add an executable script with this complete behavior:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_PNG="${REPO_ROOT}/assets/macos/AppIcon.png"
OUTPUT_ICNS="${REPO_ROOT}/assets/macos/AppIcon.icns"

die() {
  printf 'build_macos_icon: %s\n' "$1" >&2
  exit 1
}

command -v sips >/dev/null 2>&1 || die "sips is required on macOS"
command -v iconutil >/dev/null 2>&1 || die "iconutil is required on macOS"
[[ -f "$SOURCE_PNG" ]] || die "missing source PNG: $SOURCE_PNG"

read -r width height < <(
  sips -g pixelWidth -g pixelHeight "$SOURCE_PNG" |
    awk '/pixelWidth:/{width=$2} /pixelHeight:/{height=$2} END {print width, height}'
)
[[ "$width" == "1024" && "$height" == "1024" ]] ||
  die "source PNG must be 1024x1024 (got ${width}x${height})"

TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/md2docx-icon.XXXXXX")"
cleanup() {
  rm -rf "$TEMP_ROOT"
}
trap cleanup EXIT

ICONSET="${TEMP_ROOT}/AppIcon.iconset"
mkdir -p "$ICONSET"

for spec in \
  "16x16:16" "16x16@2x:32" \
  "32x32:32" "32x32@2x:64" \
  "128x128:128" "128x128@2x:256" \
  "256x256:256" "256x256@2x:512" \
  "512x512:512" "512x512@2x:1024"; do
  name="${spec%%:*}"
  size="${spec##*:}"
  sips -z "$size" "$size" "$SOURCE_PNG" \
    --out "${ICONSET}/icon_${name}.png" >/dev/null
done

CANDIDATE="${TEMP_ROOT}/AppIcon.icns"
iconutil --convert icns --output "$CANDIDATE" "$ICONSET"
[[ -s "$CANDIDATE" ]] || die "iconutil did not create a non-empty .icns"
mv "$CANDIDATE" "$OUTPUT_ICNS"
printf 'Generated %s\n' "$OUTPUT_ICNS"
```

- [ ] **Step 2: Make the script executable and verify its shell syntax**

Run:

```bash
chmod +x scripts/build_macos_icon.sh
bash -n scripts/build_macos_icon.sh
```

Expected: `bash -n` exits with status 0 and produces no output.

- [ ] **Step 3: Commit the isolated generator**

Run:

```bash
git add scripts/build_macos_icon.sh
git commit -m "build: add macOS icon generator"
```

## Task 2: Add the approved icon source and `.icns` asset

**Files:**
- Create: `assets/macos/AppIcon.svg`
- Create: `assets/macos/AppIcon.png`
- Create: `assets/macos/AppIcon.icns`

- [ ] **Step 1: Add the approved classic-blue SVG artwork**

Create an SVG with `viewBox="0 0 256 256"` and no text labels: a blue rounded-square background, a white source document with three blue lines, a dark-blue curved conversion arrow, and a white/blue target document with three aligned lines. Export it to a 1024×1024 PNG; keep the visual geometry equivalent to this exact compact source structure:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <defs>
    <linearGradient id="background" x1="32" y1="20" x2="224" y2="238" gradientUnits="userSpaceOnUse">
      <stop stop-color="#78C1FF"/>
      <stop offset=".52" stop-color="#398AF0"/>
      <stop offset="1" stop-color="#175FCB"/>
    </linearGradient>
    <linearGradient id="source" x1="54" y1="54" x2="173" y2="198" gradientUnits="userSpaceOnUse">
      <stop stop-color="#FFFFFF"/>
      <stop offset="1" stop-color="#DCEBFF"/>
    </linearGradient>
  </defs>
  <rect x="8" y="8" width="240" height="240" rx="56" fill="url(#background)"/>
  <path d="M48 63c0-9 7-16 16-16h66l30 30v73c0 9-7 16-16 16H64c-9 0-16-7-16-16V63Z" fill="url(#source)"/>
  <path d="M130 47v23c0 8 6 14 14 14h16" fill="#BAD8FF"/>
  <path d="M70 92h49M70 111h58M70 130h38" stroke="#397DD5" stroke-width="8" stroke-linecap="round" opacity=".68"/>
  <path d="M125 108c10-8 20-12 31-12" fill="none" stroke="#164B9C" stroke-width="11" stroke-linecap="round"/>
  <path d="m151 84 15 10-13 14" fill="none" stroke="#164B9C" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M119 112c0-9 7-16 16-16h48l26 26v69c0 9-7 16-16 16h-58c-9 0-16-7-16-16v-79Z" fill="#F8FBFF" stroke="#2F75D2" stroke-width="5"/>
  <path d="M183 96v19c0 8 6 14 14 14h12" fill="#B9D8FF"/>
  <path d="M142 145h42M142 163h42M142 181h29" stroke="#347BD6" stroke-width="8" stroke-linecap="round"/>
</svg>
```

The SVG is the editable design source; it must not include `MD`, `DOCX`, `W`, or Microsoft Word branding.

- [ ] **Step 2: Export and inspect the 1024×1024 master PNG**

Use macOS Quick Look to rasterize the SVG, then normalize and inspect the dimensions:

```bash
preview_dir="$(mktemp -d /tmp/md2docx-icon-preview.XXXXXX)"
qlmanage -t -s 1024 -o "$preview_dir" assets/macos/AppIcon.svg >/dev/null
mv "$preview_dir/AppIcon.svg.png" assets/macos/AppIcon.png
normalized_png="${preview_dir}/AppIcon-1024.png"
sips -z 1024 1024 assets/macos/AppIcon.png --out "$normalized_png" >/dev/null
mv "$normalized_png" assets/macos/AppIcon.png
rm -rf "$preview_dir"
sips -g pixelWidth -g pixelHeight assets/macos/AppIcon.png
```

Expected: `pixelWidth: 1024` and `pixelHeight: 1024`; visually inspect the PNG before generating the final asset.

- [ ] **Step 3: Generate and inspect the committed `.icns`**

Run:

```bash
bash scripts/build_macos_icon.sh
file assets/macos/AppIcon.icns
test -s assets/macos/AppIcon.icns
```

Expected: the script prints `Generated .../assets/macos/AppIcon.icns`, `file` identifies an Apple icon/ICNS resource, and the size check succeeds.

- [ ] **Step 4: Commit the icon assets**

Run:

```bash
git add assets/macos/AppIcon.svg assets/macos/AppIcon.png assets/macos/AppIcon.icns
git commit -m "assets: add Md2docx macOS app icon"
```

## Task 3: Attach the icon to app-mode Nuitka builds

**Files:**
- Modify: `scripts/build_nuitka.py:18-150`
- Modify: `tests/test_build_nuitka.py:1-125`

- [ ] **Step 1: Run GitNexus impact analysis before editing build symbols**

Call GitNexus for both modified functions before touching them:

```text
mcp__gitnexus__impact({"target":"build_nuitka_command","direction":"upstream","repo":"md2docx"})
mcp__gitnexus__impact({"target":"preflight_macos_app","direction":"upstream","repo":"md2docx"})
```

Review direct callers and risk. If either report is HIGH or CRITICAL, stop and report the blast radius before editing; otherwise continue with the focused tests below.

- [ ] **Step 2: Write failing command and preflight tests**

Add these tests to `tests/test_build_nuitka.py`:

```python
def test_app_command_includes_committed_icon_path():
    command = build_nuitka.build_nuitka_command("gui", "app")

    assert f"--macos-app-icon={build_nuitka.MACOS_APP_ICON}" in command


def test_legacy_commands_do_not_include_macos_app_icon():
    for mode in ("onefile", "standalone"):
        command = build_nuitka.build_nuitka_command("gui", mode)

        assert not any(argument.startswith("--macos-app-icon=") for argument in command)


def test_preflight_rejects_missing_app_icon(monkeypatch, tmp_path):
    monkeypatch.setattr(build_nuitka.sys, "platform", "darwin")
    monkeypatch.setattr(build_nuitka.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(build_nuitka.sys, "version_info", (3, 11, 9))
    monkeypatch.setattr(build_nuitka.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(build_nuitka.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(build_nuitka, "MACOS_APP_ICON", tmp_path / "missing.icns")
    monkeypatch.setattr(build_nuitka, "BUILD_ROOT", tmp_path / "build")
    monkeypatch.setattr(build_nuitka, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(build_nuitka, "DIST_ROOT", tmp_path / "dist")

    with pytest.raises(FileNotFoundError, match="AppIcon.icns|missing.icns"):
        build_nuitka.preflight_macos_app(launch=False)
```

- [ ] **Step 3: Run the focused tests and confirm the new tests fail**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -k "app_command_includes_committed_icon_path or legacy_commands_do_not_include_macos_app_icon or preflight_rejects_missing_app_icon" -v
```

Expected: failures report that `MACOS_APP_ICON` is undefined and that the app command/preflight do not yet handle the resource.

- [ ] **Step 4: Add the icon constant, app-only Nuitka flag, and preflight resource check**

Add this constant beside `DEFAULT_TEMPLATE`:

```python
MACOS_APP_ICON = REPO_ROOT / "assets" / "macos" / "AppIcon.icns"
```

In the `mode == "app"` command branch, append the fixed absolute resource path:

```python
f"--macos-app-icon={MACOS_APP_ICON}",
```

Include `MACOS_APP_ICON` in `preflight_macos_app()`'s existing required-file loop so missing or empty app icon input fails before Nuitka starts:

```python
for required in (
    REPO_ROOT / "md2docx" / "gui.py",
    DEFAULT_TEMPLATE,
    MACOS_APP_ICON,
):
    if not required.is_file() or required.stat().st_size == 0:
        raise FileNotFoundError(f"required input is missing or empty: {required}")
```

- [ ] **Step 5: Run the focused tests and the existing build-pipeline tests**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -k "app_command or legacy_commands_do_not_include_macos_app_icon or preflight" -v
uv run pytest tests/test_build_nuitka.py -v
```

Expected: all selected tests pass, including the pre-existing onefile/standalone command and preflight tests.

- [ ] **Step 6: Commit the build-command integration**

Before committing, run `git diff --check`, then:

```bash
git add scripts/build_nuitka.py tests/test_build_nuitka.py
git commit -m "build: attach icon to macOS app mode"
```

## Task 4: Verify the icon inside the signed app bundle

**Files:**
- Modify: `scripts/build_nuitka.py:314-368`
- Modify: `tests/test_build_nuitka.py:230-355`

- [ ] **Step 1: Run GitNexus impact analysis before editing the verifier**

Call:

```text
mcp__gitnexus__impact({"target":"verify_macos_app","direction":"upstream","repo":"md2docx"})
```

Review direct callers and affected app-pipeline tests. Continue only if the report is not HIGH or CRITICAL.

- [ ] **Step 2: Extend the fake app fixture and add failing bundle-icon tests**

Update `make_fake_app()` so every valid fixture contains a non-empty resource and matching plist entry:

```python
icon_name = "AppIcon.icns"
(resources / icon_name).write_bytes(b"fake icns")
with (contents / "Info.plist").open("wb") as plist_file:
    plistlib.dump(
        {
            "CFBundleExecutable": build_nuitka.MACOS_PRODUCT_NAME,
            "CFBundleIconFile": icon_name,
        },
        plist_file,
    )
```

Add a failing test for a missing resource:

```python
def test_verify_macos_app_rejects_missing_icon_resource(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)
    (app_path / "Contents" / "Resources" / "AppIcon.icns").unlink()
    monkeypatch.setattr(
        build_nuitka.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "Mach-O 64-bit executable arm64\n", ""
        ),
    )

    with pytest.raises(RuntimeError, match="icon"):
        build_nuitka.verify_macos_app(app_path)
```

Add this test for a missing plist declaration:

```python
def test_verify_macos_app_rejects_missing_icon_declaration(tmp_path, monkeypatch):
    app_path = make_fake_app(tmp_path)
    plist_path = app_path / "Contents" / "Info.plist"
    with plist_path.open("rb") as plist_file:
        bundle_info = plistlib.load(plist_file)
    bundle_info.pop("CFBundleIconFile")
    with plist_path.open("wb") as plist_file:
        plistlib.dump(bundle_info, plist_file)
    monkeypatch.setattr(
        build_nuitka.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "Mach-O 64-bit executable arm64\n", ""
        ),
    )

    with pytest.raises(RuntimeError, match="CFBundleIconFile"):
        build_nuitka.verify_macos_app(app_path)
```

- [ ] **Step 3: Run verifier tests and confirm the icon checks fail**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -k "verify_macos_app" -v
```

Expected: the complete-bundle fixture still exercises architecture/template/Tcl/Tk/signature checks, while the new missing-icon tests fail because the verifier does not inspect icon metadata yet.

- [ ] **Step 4: Add strict `Info.plist` and resource validation**

Immediately after loading `bundle_info` and before resolving the executable, add:

```python
icon_value = bundle_info.get("CFBundleIconFile")
if not isinstance(icon_value, str) or not icon_value:
    raise RuntimeError("Info.plist has no valid CFBundleIconFile")
icon_name = Path(icon_value).name
if not icon_name.endswith(".icns"):
    icon_name = f"{icon_name}.icns"
icon_resource = app_path / "Contents" / "Resources" / icon_name
if not icon_resource.is_file() or icon_resource.stat().st_size == 0:
    raise RuntimeError(f"bundle is missing app icon resource: {icon_resource}")
```

This accepts Nuitka's filename with or without the `.icns` suffix, rejects empty declarations, and limits the lookup to the bundle's `Resources` directory.

- [ ] **Step 5: Run all verifier and pipeline tests**

Run:

```bash
uv run pytest tests/test_build_nuitka.py -k "verify_macos_app or app_pipeline" -v
uv run pytest tests/test_build_nuitka.py -v
```

Expected: all tests pass, including invalid-signature propagation and the existing “never promote after candidate failure” orchestration test.

- [ ] **Step 6: Commit bundle verification**

Run:

```bash
git add scripts/build_nuitka.py tests/test_build_nuitka.py
git commit -m "build: verify macOS app icon bundle resource"
```

## Task 5: Add asset smoke tests and document the commands

**Files:**
- Create: `tests/test_macos_icon_assets.py`
- Modify: `docs/编译管线.md`

- [ ] **Step 1: Add resource smoke tests**

Create `tests/test_macos_icon_assets.py` with:

```python
"""Smoke tests for committed macOS app icon resources."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = REPO_ROOT / "assets" / "macos"


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS icon tools are platform-specific")
def test_committed_icon_assets_have_expected_format():
    svg = ICON_DIR / "AppIcon.svg"
    png = ICON_DIR / "AppIcon.png"
    icns = ICON_DIR / "AppIcon.icns"

    assert svg.is_file()
    assert png.is_file()
    assert icns.is_file()
    assert icns.stat().st_size > 0

    dimensions = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(png)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "pixelWidth: 1024" in dimensions
    assert "pixelHeight: 1024" in dimensions

    file_result = subprocess.run(
        ["file", str(icns)], check=True, capture_output=True, text=True
    ).stdout.lower()
    assert "icon" in file_result or "icns" in file_result
```

- [ ] **Step 2: Run the new smoke test before documentation changes**

Run:

```bash
uv run pytest tests/test_macos_icon_assets.py -v
```

Expected: one passing macOS asset test on the build machine; it is skipped on non-macOS hosts.

- [ ] **Step 3: Document icon maintenance in `docs/编译管线.md`**

Insert a section before “日常重复编译”:

````markdown
## 更新应用图标

正常重复编译不需要重新生成图标；仓库已经包含 `assets/macos/AppIcon.icns`。只有修改 `AppIcon.svg` 并重新导出 `AppIcon.png` 后，才运行：

```bash
bash scripts/build_macos_icon.sh
```

图标生成脚本会用 macOS 自带的 `sips` 和 `iconutil` 创建完整尺寸集合。生成成功后，再使用下面的普通 app 命令编译：

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode app
```

如果 `AppIcon.icns` 缺失或为空，app 管线会在 Nuitka 启动前失败并提示先生成图标。
````

- [ ] **Step 4: Run documentation and asset checks**

Run:

```bash
git diff --check
uv run pytest tests/test_build_nuitka.py tests/test_macos_icon_assets.py -v
```

Expected: no whitespace errors and all selected tests pass.

- [ ] **Step 5: Commit tests and documentation**

Run:

```bash
git add tests/test_macos_icon_assets.py docs/编译管线.md
git commit -m "docs: document macOS app icon maintenance"
```

## Task 6: Perform full verification and real macOS build

**Files:**
- No source changes expected; inspect `assets/macos/AppIcon.icns` and `dist/macos/Md2docx.app`.

- [ ] **Step 1: Regenerate the checked-in `.icns` from the approved PNG**

Run:

```bash
bash scripts/build_macos_icon.sh
git diff --exit-code -- assets/macos/AppIcon.icns
```

Expected: generation succeeds; if the deterministic output differs, inspect the binary change and stage the intentional regenerated asset before continuing.

- [ ] **Step 2: Run the complete test suite with uv**

Run:

```bash
uv run pytest
```

Expected: all existing tests and new icon tests pass, with no new warnings attributable to the icon changes.

- [ ] **Step 3: Build and validate the real app bundle**

Run:

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode app --clean
```

Expected: the command finishes successfully and publishes `dist/macos/Md2docx.app`. Then inspect the final bundle:

```bash
plutil -p dist/macos/Md2docx.app/Contents/Info.plist | rg "CFBundleIcon|CFBundleExecutable"
find dist/macos/Md2docx.app/Contents/Resources -name '*.icns' -type f -maxdepth 1 -print
codesign --verify --deep --strict dist/macos/Md2docx.app
```

Expected: `Info.plist` contains `CFBundleIconFile`, a non-empty `.icns` is present in `Resources`, and codesign verification exits 0.

- [ ] **Step 4: Check the actual visual result and launch behavior**

Open `dist/macos/Md2docx.app` in Finder, confirm the classic-blue document-conversion icon appears in Finder and Dock, and start the app once. Confirm the GUI starts and the existing conversion workflow is unchanged.

- [ ] **Step 5: Run the final GitNexus change-scope check**

Before the final commit or handoff, call:

```text
mcp__gitnexus__detect_changes({"scope":"all","repo":"md2docx"})
```

Review that only the planned icon assets, generator, build script, tests, and `docs/编译管线.md` are reported. Investigate any unrelated symbol or execution-flow change before committing.

- [ ] **Step 6: Record the final implementation commit**

Run:

```bash
git status --short
git diff --check
git add assets/macos scripts/build_macos_icon.sh scripts/build_nuitka.py tests/test_build_nuitka.py tests/test_macos_icon_assets.py docs/编译管线.md
git commit -m "feat: add macOS app icon to build pipeline"
```

Expected: the commit contains only the planned files and preserves the user's unrelated working changes.

## Self-review checklist

- [ ] The approved A direction, classic-blue palette, pure graphic treatment, app-only scope, and no Word branding are represented in `AppIcon.svg`.
- [ ] The resource path is shared by the generator, Nuitka command, preflight, tests, and documentation.
- [ ] onefile and standalone commands remain free of `--macos-app-icon`.
- [ ] Missing or empty `.icns` fails before compilation; missing plist/resource fails after compilation and before promotion.
- [ ] The existing ad-hoc signature check remains after icon inclusion.
- [ ] All Python commands use `uv run`; no new Python dependency or package manager is introduced.
- [ ] No placeholder marker or unresolved implementation choice remains in the plan.
