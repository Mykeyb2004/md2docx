cd /Users/zhangqijin/PycharmProjects/md2docx

rm -rf -- md2docx/__pycache__ scripts/__pycache__ .pytest_cache \
  "$HOME/.md2docx/mermaid_cache" "$HOME/.md2docx/math_cache"

uv run --group build python - <<'PY'
from scripts import build_nuitka as build

original_command = build.build_nuitka_command

def clean_command(entry, mode):
    return original_command(entry, mode) + [
        "--clean-cache=all",
        "--disable-cache=all",
    ]

build.build_nuitka_command = clean_command
raise SystemExit(build.main(["--entry", "gui", "--mode", "app", "--clean"]))
PY