"""临时脚本：解析 PDF，输出每页图片位置和页面底部留白（相对版心高度）。"""
import sys

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTFigure, LTImage, LTTextContainer

PT_PER_CM = 72 / 2.54
TOP = 2.54 * PT_PER_CM
BOTTOM = 2.54 * PT_PER_CM

for pno, page in enumerate(extract_pages(sys.argv[1]), 1):
    h = page.height
    body_h = h - TOP - BOTTOM
    lowest = h  # pdf 坐标原点在左下
    items = []
    for el in page:
        if isinstance(el, (LTFigure, LTImage)):
            items.append(f"图 {(el.x1-el.x0)/72:.2f}x{(el.y1-el.y0)/72:.2f}in")
            lowest = min(lowest, el.y0)
        elif isinstance(el, LTTextContainer) and el.get_text().strip():
            lowest = min(lowest, el.y0)
    blank = (lowest - BOTTOM) / body_h
    print(f"P{pno:>2}: 底部留白 {blank*100:5.1f}%  {'; '.join(items)}")
