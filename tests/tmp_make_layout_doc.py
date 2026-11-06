"""临时脚本：生成含多张图片的测试文档，用于检验 OfficeCLI 能否给出分页/图片位置信息。"""
from pathlib import Path

from PIL import Image, ImageDraw

out = Path(__file__).parent / "tmp_layout"
out.mkdir(exist_ok=True)

sizes = [(800, 500), (600, 900), (1200, 400), (500, 1100), (900, 700)]
for i, (w, h) in enumerate(sizes, 1):
    img = Image.new("RGB", (w, h), (232, 241, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([4, 4, w - 5, h - 5], outline=(47, 107, 255), width=6)
    d.text((20, 20), f"IMG{i} {w}x{h}", fill=(0, 0, 0))
    img.save(out / f"img{i}.png", dpi=(96, 96))

para = "这是用于测试分页位置的正文段落，包含若干中文字符以便占据多行空间。" * 6
lines = ["# 分页测试\n"]
for i in range(1, 6):
    for _ in range(i + 2):
        lines.append(para + "\n")
    lines.append("如下图所示：\n")
    lines.append(f"![图{i}](img{i}.png)\n")
(out / "layout_test.md").write_text("\n".join(lines), encoding="utf-8")
print(out / "layout_test.md")
