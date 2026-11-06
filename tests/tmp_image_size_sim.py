"""临时脚本：模拟当前 Mermaid / 本地图片尺寸算法，计算图中文字的等效字号。

假设 Mermaid 默认字体 16px、mmdc scale=1（1 图像像素 = 1 CSS px）。
等效字号(pt) = 源字号(px) × 显示宽度(pt) / 图像宽度(px)
"""
from io import BytesIO

from docx import Document
from docx.shared import Cm
from PIL import Image

from md2docx.renderer import DocxRenderer
from md2docx.styles import StyleManager

EMU_PER_PT = 12700


def png(w, h, dpi=None):
    buf = BytesIO()
    kw = {"dpi": (dpi, dpi)} if dpi else {}
    Image.new("RGB", (w, h), "white").save(buf, "PNG", **kw)
    return buf.getvalue()


doc = Document()
s = doc.sections[0]
s.page_width, s.page_height = Cm(21), Cm(29.7)
s.left_margin = s.right_margin = Cm(3.17)
s.top_margin = s.bottom_margin = Cm(2.54)
sm = StyleManager()
r = DocxRenderer(doc, sm)
ms = sm.get_mermaid_style()
print(f"可用版心: {r._get_available_page_width()/914400:.2f}in x {r._get_available_page_height()/914400:.2f}in\n")

cases = [
    ("小 LR 3节点", 500, 120),
    ("宽 LR 长链", 1400, 150),
    ("中等 TD", 600, 700),
    ("高 TD 长流程", 400, 1600),
    ("大型复杂图", 1800, 1200),
    ("时序图", 900, 600),
]
print(f"{'case':<14}{'px':>12} | {'follow':>6} {'宽in':>6} {'高in':>6} {'等效字号pt':>10}")
for name, w, h in cases:
    for follow in (False, True):
        lay = r._calculate_mermaid_layout(png(w, h), ms, can_follow_previous=follow)
        wpt = int(lay["width"]) / EMU_PER_PT
        font = 16 * wpt / w
        print(f"{name:<14}{f'{w}x{h}':>12} | {str(lay['follow_previous_paragraph']):>6} "
              f"{wpt/72:6.2f} {int(lay['height'])/914400:6.2f} {font:10.1f}")

print("\n本地截图（Retina 2x，UI 字号 13px→26px 物理像素）")
for name, w, h, dpi in [("全屏截图", 2880, 1800, 144), ("窗口截图", 1600, 1000, 144),
                        ("无DPI截图", 1600, 1000, None), ("小图标", 200, 200, 72)]:
    wpx, hpx = w, h
    d = dpi or 96
    w_in, h_in = wpx / d, hpx / d
    aw, ah = r._get_available_page_width() / 914400, r._get_available_page_height() / 914400
    sc = min(1, aw / w_in, ah / h_in)
    disp = w_in * sc
    font = 26 * disp * 72 / wpx
    print(f"{name:<10}{f'{w}x{h}@{d}':>16}  显示宽 {disp:5.2f}in  等效字号 {font:4.1f}pt")
