"""
Word document renderer module.
"""
from typing import Any, Dict, Optional
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import re
import mistune


class DocxRenderer(mistune.BaseRenderer):
    """Custom mistune renderer that outputs to python-docx."""
    
    def __init__(self, doc: Document, style_manager: Any) -> None:
        """
        Initialize renderer.
        
        Args:
            doc: python-docx Document object
            style_manager: StyleManager instance for style configuration
        """
        super().__init__()
        self.doc = doc
        self.styles = style_manager
        self._current_paragraph = None
    
    def _parse_font_size(self, size_str: str) -> int:
        """
        Parse font size string to points.
        
        Args:
            size_str: Font size string like "12pt" or "14"
            
        Returns:
            Font size in points
        """
        if isinstance(size_str, int):
            return size_str
        
        size_str = str(size_str).lower().strip()
        
        if size_str.endswith('pt'):
            return int(size_str[:-2])
        
        return int(size_str)
    
    def _parse_color(self, color_str: str) -> RGBColor:
        """
        Parse color string to RGBColor.
        
        Args:
            color_str: Color string like "#FF0000" or "FF0000"
            
        Returns:
            RGBColor object
        """
        color_str = color_str.strip()
        
        if color_str.startswith('#'):
            color_str = color_str[1:]
        
        r = int(color_str[0:2], 16)
        g = int(color_str[2:4], 16)
        b = int(color_str[4:6], 16)
        
        return RGBColor(r, g, b)
    
    def _get_alignment(self, alignment_str: str) -> WD_PARAGRAPH_ALIGNMENT:
        """Get alignment enum from string."""
        alignment_map = {
            'left': WD_PARAGRAPH_ALIGNMENT.LEFT,
            'center': WD_PARAGRAPH_ALIGNMENT.CENTER,
            'right': WD_PARAGRAPH_ALIGNMENT.RIGHT,
            'justify': WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
        }
        return alignment_map.get(alignment_str.lower(), WD_PARAGRAPH_ALIGNMENT.LEFT)
    
    def _apply_paragraph_style(self, paragraph: Any, style: Dict[str, Any]) -> None:
        """Apply style to paragraph."""
        if 'font_name' in style:
            paragraph.style.font.name = style['font_name']
        
        if 'font_size' in style:
            paragraph.style.font.size = Pt(self._parse_font_size(style['font_size']))
        
        if 'font_color' in style:
            paragraph.style.font.color.rgb = self._parse_color(style['font_color'])
        
        if 'bold' in style and style['bold']:
            paragraph.style.font.bold = True
        
        if 'alignment' in style:
            paragraph.alignment = self._get_alignment(style['alignment'])
        
        # Spacing
        if 'space_before' in style:
            space_before = self._parse_font_size(style['space_before'])
            paragraph.paragraph_format.space_before = Pt(space_before)
        
        if 'space_after' in style:
            space_after = self._parse_font_size(style['space_after'])
            paragraph.paragraph_format.space_after = Pt(space_after)
    
    def render_children(self, token: Dict[str, Any], state: Any) -> list:
        """
        Render child tokens.
        
        Args:
            token: Token dictionary with 'children' key
            state: State object
            
        Returns:
            List of rendered strings
        """
        children = token.get('children', [])
        return [self.render_token(child, state) for child in children]
    
    def render_token(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render a single token.
        
        Args:
            token: Token dictionary
            state: State object
            
        Returns:
            Rendered string
        """
        token_type = token['type']
        method_name = token_type
        
        # Get the render method for this token type
        method = getattr(self, method_name, None)
        
        if method:
            return method(token, state)
        
        # Fallback for unknown token types
        return ''
    
    def heading(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render heading.
        
        Args:
            token: Token dictionary with 'children' and 'attrs' keys  
            state: BlockState object
            
        Returns:
            Empty string (content added to document)
        """
        # Extract level from token attributes
        level = token['attrs']['level']
        
        # Get text from children
        text = ''.join(self.render_children(token, state))
        
        # mistune uses levels 1-6, we support 1-4
        if level > 4:
            level = 4
        
        # Get style configuration
        style = self.styles.get_heading_style(level)
        
        # Add heading to document WITHOUT text first
        heading = self.doc.add_heading('', level=level)
        
        # Parse and add formatted text to heading
        self._add_formatted_text(heading, text, style)
        
        # Apply paragraph-level styles
        if 'alignment' in style:
            heading.alignment = self._get_alignment(style['alignment'])
        
        if 'space_before' in style:
            heading.paragraph_format.space_before = Pt(self._parse_font_size(style['space_before']))
        
        if 'space_after' in style:
            heading.paragraph_format.space_after = Pt(self._parse_font_size(style['space_after']))
        
        return ''

    
    def paragraph(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render paragraph.
        
        Args:
            token: Token dictionary with 'children' key
            state: BlockState object
            
        Returns:
            Empty string (content added to document)
        """
        # Get text from children
        text = ''.join(self.render_children(token, state))
        
        # Skip empty paragraphs
        if not text or text.strip() == '':
            return ''
        
        # Get style configuration
        style = self.styles.get_paragraph_style()
        
        # Add paragraph to document
        p = self.doc.add_paragraph()
        
        # Parse inline formatting (bold, italic)
        self._add_formatted_text(p, text, style)
        
        # Apply paragraph alignment
        if 'alignment' in style:
            p.alignment = self._get_alignment(style['alignment'])
        
        # Apply line spacing
        if 'line_spacing' in style:
            p.paragraph_format.line_spacing = style['line_spacing']
        
        # Apply first line indent (首行缩进)
        # 2个字符 = 2倍字体大小
        if 'first_line_indent' in style and style['first_line_indent'] > 0:
            char_count = style['first_line_indent']
            # Get font size from style
            font_size_pt = self._parse_font_size(style.get('font_size', '12pt'))
            # 1 character width ≈ 1 * font_size in points
            p.paragraph_format.first_line_indent = Pt(char_count * font_size_pt)
        
        return ''
    
    def _add_formatted_text(self, paragraph: Any, text: str, base_style: Dict[str, Any]) -> None:
        """
        Add text with inline formatting to paragraph.
        
        Args:
            paragraph: Paragraph object
            text: Text with HTML-like formatting tags
            base_style: Base style configuration
        """
        # mistune converts markdown to HTML tags in text
        # We need to parse <strong>, <em>, etc.
        
        # Replace HTML tags with markers
        text = text.replace('<strong>', '**START_BOLD**')
        text = text.replace('</strong>', '**END_BOLD**')
        text = text.replace('<em>', '**START_ITALIC**')
        text = text.replace('</em>', '**END_ITALIC**')
        
        # Split by markers and process
        parts = re.split(r'(\*\*START_BOLD\*\*|\*\*END_BOLD\*\*|\*\*START_ITALIC\*\*|\*\*END_ITALIC\*\*)', text)
        
        bold = False
        italic = False
        
        for part in parts:
            if part == '**START_BOLD**':
                bold = True
            elif part == '**END_BOLD**':
                bold = False
            elif part == '**START_ITALIC**':
                italic = True
            elif part == '**END_ITALIC**':
                italic = False
            elif part:  # Actual text content
                run = paragraph.add_run(part)
                
                # Apply base style - ALWAYS apply font settings
                if 'font_name' in base_style:
                    run.font.name = base_style['font_name']
                    # Also set East Asian font for Chinese characters
                    from docx.oxml import OxmlElement
                    from docx.oxml.ns import qn
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), base_style['font_name'])
                
                if 'font_size' in base_style:
                    run.font.size = Pt(self._parse_font_size(base_style['font_size']))
                
                if 'font_color' in base_style:
                    run.font.color.rgb = self._parse_color(base_style['font_color'])
                
                # Apply formatting on top of base style
                if bold:
                    run.font.bold = True
                if italic:
                    run.font.italic = True
    
    def text(self, token: Dict[str, Any], state: Any) -> str:
        """Render plain text."""
        return token.get('raw', '')
    
    def strong(self, token: Dict[str, Any], state: Any) -> str:
        """Render strong (bold) text."""
        text = ''.join(self.render_children(token, state))
        return f"<strong>{text}</strong>"
    
    def emphasis(self, token: Dict[str, Any], state: Any) -> str:
        """Render emphasis (italic) text."""
        text = ''.join(self.render_children(token, state))
        return f"<em>{text}</em>"
    
    def linebreak(self, token: Dict[str, Any], state: Any) -> str:
        """Render line break."""
        return '\n'
    
    def softbreak(self, token: Dict[str, Any], state: Any) -> str:
        """Render soft break."""
        return ' '
    
    def blank_line(self, token: Dict[str, Any], state: Any) -> str:
        """Render blank line."""
        return ''
    
    def thematic_break(self, token: Dict[str, Any], state: Any) -> str:
        """Render horizontal rule."""
        # Add a paragraph with a horizontal line
        p = self.doc.add_paragraph()
        p.add_run('_' * 50)
        return ''
    
    def list(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render list (ordered or unordered).
        
        Args:
            token: Token dictionary with 'children' and 'attrs' keys
            state: BlockState object
            
        Returns:
            Empty string (content added to document)
        """
        # Get list style configuration
        list_style = self.styles.get_list_style()
        
        # Get list type (ordered/unordered) and depth
        ordered = token['attrs'].get('ordered', False)
        depth = token.get('tight', 0)  # Use tight as depth indicator for now
        
        # Process each list item
        children = token.get('children', [])
        for child in children:
            if child['type'] == 'list_item':
                self._render_list_item(child, state, ordered, 0)
        
        return ''
    
    def _render_list_item(self, token: Dict[str, Any], state: Any, ordered: bool, depth: int) -> None:
        """
        Render a single list item.
        
        Args:
            token: List item token
            state: State object
            ordered: Whether this is an ordered list
            depth: Nesting depth (0-based)
        """
        # Get text from children
        text = ''.join(self.render_children(token, state))
        
        if not text or text.strip() == '':
            return
        
        # Get list style
        list_style = self.styles.get_list_style()
        
        # Add paragraph with appropriate style
        p = self.doc.add_paragraph()
        
        # Parse and add formatted text
        base_style = {
            'font_name': list_style.get('font_name', '宋体'),
            'font_size': list_style.get('font_size', '12pt')
        }
        self._add_formatted_text(p, text, base_style)
        
        # Set list style based on type
        if ordered:
            # Use built-in list number style
            p.style = 'List Number'
        else:
            # Use built-in list bullet style
            p.style = 'List Bullet'
        
        # Apply indentation for nested lists
        if depth > 0:
            from docx.shared import Inches
            indent_size = 0.5  # inches per level
            if 'indent_size' in list_style:
                indent_str = list_style['indent_size']
                if isinstance(indent_str, str) and indent_str.endswith('in'):
                    indent_size = float(indent_str[:-2])
            
            p.paragraph_format.left_indent = Inches(indent_size * (depth + 1))

    
    def list_item(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render list item.
        
        Note: This is called by list() method, but we need to provide it
        for the render_token dispatcher.
        
        Args:
            token: List item token
            state: State object
            
        Returns:
            Empty string
        """
        # When called directly, just render children and return text
        # The actual rendering is done by _render_list_item in list()
        return ''.join(self.render_children(token, state))
    
    def block_text(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render block text (used in list items).
        
        Args:
            token: Block text token
            state: State object
            
        Returns:
            Rendered text string
        """
        # Block text is just a container, render its children
        return ''.join(self.render_children(token, state))
    
    def table(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render table.
        
        Args:
            token: Table token with 'children' (table_head and table_body)
            state: State object
            
        Returns:
            Empty string (content added to document)
        """
        # Get table style
        table_style = self.styles.get_table_style()
        
        # Create table - we'll determine column count from header
        children = token.get('children', [])
        if not children:
            return ''
        
        # Find table_head to get column count
        col_count = 0
        table_head = None
        table_body = None
        
        for child in children:
            if child['type'] == 'table_head':
                table_head = child
                col_count = len(child.get('children', []))
            elif child['type'] == 'table_body':
                table_body = child
        
        if col_count == 0:
            return ''
        
        # Determine row count
        row_count = 1  # header row
        if table_body:
            row_count += len(table_body.get('children', []))
        
        # Create table
        table = self.doc.add_table(rows=row_count, cols=col_count)
        
        # Apply table style if specified
        if 'style' in table_style and table_style['style']:
            try:
                table.style = table_style['style']
            except KeyError:
                # Style doesn't exist, use default
                pass
        
        # Track current row index
        self._current_table = table
        self._current_row_idx = 0
        
        # Render table head
        if table_head:
            self.table_head(table_head, state)
        
        # Render table body
        if table_body:
            self.table_body(table_body, state)
        
        self._current_table = None
        self._current_row_idx = 0
        
        return ''
    
    def table_head(self, token: Dict[str, Any], state: Any) -> str:
        """Render table header."""
        cells = token.get('children', [])
        table_style = self.styles.get_table_style()
        
        if not self._current_table:
            return ''
        
        row = self._current_table.rows[self._current_row_idx]
        
        for col_idx, cell_token in enumerate(cells):
            if col_idx < len(row.cells):
                cell = row.cells[col_idx]
                text = ''.join(self.render_children(cell_token, state))
                
                # Clear existing paragraphs and add formatted text
                cell._element.clear_content()
                p = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
                
                # Parse and add formatted text
                base_style = {
                    'font_name': table_style.get('font_name', '宋体'),
                    'font_size': table_style.get('font_size', '11pt')
                }
                self._add_formatted_text(p, text, base_style)
                
                # Apply header styling - make all runs bold
                for run in p.runs:
                    run.font.bold = True
                
                # Apply header background if specified
                if 'header_background' in table_style:
                    try:
                        from docx.oxml.ns import nsdecls
                        from docx.oxml import parse_xml
                        shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(
                            nsdecls('w'), 
                            table_style['header_background'].replace('#', '')
                        ))
                        cell._element.get_or_add_tcPr().append(shading_elm)
                    except:
                        pass  # Ignore if shading fails
        
        self._current_row_idx += 1
        return ''
    
    def table_body(self, token: Dict[str, Any], state: Any) -> str:
        """Render table body."""
        rows = token.get('children', [])
        
        for row_token in rows:
            if row_token['type'] == 'table_row':
                self.table_row(row_token, state)
        
        return ''
    
    def table_row(self, token: Dict[str, Any], state: Any) -> str:
        """Render table row."""
        cells = token.get('children', [])
        table_style = self.styles.get_table_style()
        
        if not self._current_table or self._current_row_idx >= len(self._current_table.rows):
            return ''
        
        row = self._current_table.rows[self._current_row_idx]
        
        for col_idx, cell_token in enumerate(cells):
            if col_idx < len(row.cells):
                cell = row.cells[col_idx]
                text = ''.join(self.render_children(cell_token, state))
                
                # Clear existing paragraphs and add formatted text
                cell._element.clear_content()
                p = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
                
                # Parse and add formatted text
                base_style = {
                    'font_name': table_style.get('font_name', '宋体'),
                    'font_size': table_style.get('font_size', '11pt')
                }
                self._add_formatted_text(p, text, base_style)
        
        self._current_row_idx += 1
        return ''
    
    def table_cell(self, token: Dict[str, Any], state: Any) -> str:
        """Render table cell (called by render_children)."""
        return ''.join(self.render_children(token, state))



