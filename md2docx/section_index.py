"""Insert section-local heading indexes without changing the source headings."""
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Tuple

from docx.document import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Pt, RGBColor
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from md2docx.styles import StyleManager


Heading = Tuple[int, Paragraph]


def _points(value: Any) -> float:
    """Read the same numeric/pt values accepted by heading configuration."""
    text = str(value).strip().lower()
    return float(text[:-2] if text.endswith('pt') else text)


def _index_paragraph(
    paragraph: Paragraph, source: Paragraph, style: Dict[str, Any],
    line_spacing: float,
) -> Paragraph:
    """Copy heading content, applying its semantic level's configured style."""
    paragraph.style = 'Normal'
    for child in source._p:
        if child.tag not in {qn('w:pPr'), qn('w:bookmarkStart'), qn('w:bookmarkEnd')}:
            paragraph._p.append(deepcopy(child))

    # Include runs inside inline hyperlinks as well as ordinary text runs.
    for element in paragraph._p.xpath('.//w:r'):
        run = Run(element, paragraph)
        if 'font_name' in style:
            run.font.name = style['font_name']
            fonts = run._r.get_or_add_rPr().get_or_add_rFonts()
            for script in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
                fonts.set(qn(f'w:{script}'), style['font_name'])
                fonts.attrib.pop(qn(f'w:{script}Theme'), None)
        if 'font_size' in style:
            run.font.size = Pt(_points(style['font_size']))
        for attribute in ('bold', 'italic'):
            if attribute in style:
                setattr(run.font, attribute, style[attribute])
        if style.get('font_color'):
            color = style['font_color'].lstrip('#')
            if len(color) == 3:
                color = ''.join(character * 2 for character in color)
            run.font.color.rgb = RGBColor.from_string(color)

    formatting = paragraph.paragraph_format
    formatting.alignment = {
        'left': WD_ALIGN_PARAGRAPH.LEFT,
        'center': WD_ALIGN_PARAGRAPH.CENTER,
        'right': WD_ALIGN_PARAGRAPH.RIGHT,
        'justify': WD_ALIGN_PARAGRAPH.JUSTIFY,
    }.get(str(style.get('alignment', 'center')).lower(), WD_ALIGN_PARAGRAPH.LEFT)
    formatting.left_indent = Pt(0)
    formatting.right_indent = Pt(0)
    formatting.first_line_indent = Pt(
        float(style.get('first_line_indent', 0)) * _points(style.get('font_size', '12pt'))
    )
    formatting.space_before = Pt(_points(style.get('space_before', 0)))
    formatting.space_after = Pt(_points(style.get('space_after', 8)))
    formatting.line_spacing = style.get('line_spacing', line_spacing)
    formatting.page_break_before = False
    formatting.keep_with_next = False
    formatting.keep_together = True
    # Do not let an index duplicate participate in Word's navigation or TOC,
    # including templates whose Normal style has an outline level.
    outline = OxmlElement('w:outlineLvl')
    outline.set(qn('w:val'), '9')
    paragraph._p.get_or_add_pPr().append(outline)
    return paragraph


def _index_frame(doc: Document, heading: Paragraph):
    """Create a double-bordered frame that can expand/split for long indexes."""
    section = doc.sections[0]
    width = section.page_width - section.left_margin - section.right_margin
    height = section.page_height - section.top_margin - section.bottom_margin
    table = doc.add_table(rows=1, cols=1)
    table.style = 'Normal Table'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Emu(width)
    table.cell(0, 0).width = Emu(width)
    table._tbl.tblPr.find(qn('w:tblW')).set(qn('w:w'), str(Emu(width).twips))
    table._tbl.tblPr.find(qn('w:tblW')).set(qn('w:type'), 'dxa')
    borders = OxmlElement('w:tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border = OxmlElement(f'w:{side}')
        border.set(qn('w:val'), 'nil' if side.startswith('inside') else 'double')
        border.set(qn('w:sz'), '6')
        border.set(qn('w:color'), '000000')
        borders.append(border)
    table._tbl.tblPr.insert_element_before(
        borders, 'w:shd', 'w:tblLayout', 'w:tblCellMar', 'w:tblLook',
        'w:tblCaption', 'w:tblDescription', 'w:tblPrChange',
    )
    row = table.rows[0]
    row.height = Emu(int(height * 0.82))
    row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    cell = row.cells[0]
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    margins = OxmlElement('w:tcMar')
    for side in ('top', 'left', 'bottom', 'right'):
        margin = OxmlElement(f'w:{side}')
        margin.set(qn('w:w'), '200')
        margin.set(qn('w:type'), 'dxa')
        margins.append(margin)
    cell._tc.get_or_add_tcPr().insert_element_before(
        margins, 'w:textDirection', 'w:tcFitText', 'w:vAlign',
        'w:hideMark', 'w:headers', 'w:tcPrChange',
    )
    heading._p.addprevious(table._tbl)
    return cell


def add_section_indexes(
    doc: Document, headings: Iterable[Heading], styles: StyleManager,
) -> None:
    """Insert a standalone H2 title + H3/H4 index before each source H2.

    H1/H2 close the preceding section. H5/H6 are excluded even when their
    renderer uses the Heading 4 style. Indexes may flow onto further pages.
    """
    sections: List[Tuple[Paragraph, List[Heading]]] = []
    entries = None
    for level, paragraph in headings:
        if level <= 2:
            entries = None
            if level == 2:
                entries = []
                sections.append((paragraph, entries))
        elif level in (3, 4) and entries is not None:
            entries.append((level, paragraph))

    if not sections:
        return

    # Bookmarks in a supplied template's headers/footers also reserve names.
    bookmarks = []
    for part in doc.part.package.parts:
        element = getattr(part, 'element', None)
        if element is not None:
            bookmarks.extend(element.xpath('.//w:bookmarkStart'))
    used_names = {bookmark.get(qn('w:name')) for bookmark in bookmarks}
    used_ids = [bookmark.get(qn('w:id'), '') for bookmark in bookmarks]
    next_id = max((int(value) for value in used_ids if value.isdigit()), default=-1) + 1

    line_spacing = styles.get_document_style().get('line_spacing', 1.5)
    for heading, children in sections:
        title = _index_paragraph(
            heading.insert_paragraph_before(), heading,
            styles.get_heading_style(2), line_spacing,
        )
        title.paragraph_format.page_break_before = title._p.getprevious() is not None
        title.paragraph_format.keep_with_next = bool(children)
        cell = _index_frame(doc, heading) if children else None

        for index, (level, child) in enumerate(children):
            name = f'_md2docx_index_{next_id}'
            while name in used_names:
                next_id += 1
                name = f'_md2docx_index_{next_id}'
            used_names.add(name)
            bookmark = OxmlElement('w:bookmarkStart')
            bookmark.set(qn('w:id'), str(next_id))
            bookmark.set(qn('w:name'), name)
            child._p.insert(0 if child._p.pPr is None else 1, bookmark)
            end = OxmlElement('w:bookmarkEnd')
            end.set(qn('w:id'), str(next_id))
            child._p.append(end)
            next_id += 1

            entry = _index_paragraph(
                cell.paragraphs[0] if index == 0 else cell.add_paragraph(),
                child, styles.get_heading_style(level), line_spacing,
            )
            if level == 3 and index + 1 < len(children) and children[index + 1][0] == 4:
                entry.paragraph_format.keep_with_next = True
            link = OxmlElement('w:hyperlink')
            link.set(qn('w:anchor'), name)
            link.set(qn('w:history'), '1')
            for content in list(entry._p):
                if content.tag != qn('w:pPr'):
                    link.append(content)
            entry._p.append(link)

        # A paragraph-level break also handles a pre-existing heading break
        # without stacking explicit page-break runs and producing blank pages.
        heading.paragraph_format.page_break_before = True
