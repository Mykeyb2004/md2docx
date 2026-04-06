"""
Word document renderer module.
"""
from typing import Any, Dict, Optional, Tuple
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm, Mm, Emu
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import re
import mistune
from io import BytesIO


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
        self.math_formulas = {'inline': [], 'block': []}  # Will be set by parser
        
        # Initialize math converter for LaTeX formulas
        from md2docx.math_converter import MathConverter
        self.math_converter = MathConverter(dpi=300)

        # Initialize Mermaid converter for fenced mermaid blocks
        from md2docx.mermaid_converter import MermaidConverter
        mermaid_style = self.styles.get_mermaid_style()
        self.mermaid_converter = MermaidConverter(
            command=mermaid_style.get('command', 'mmdc'),
            output_format=mermaid_style.get('format', 'png'),
            theme=mermaid_style.get('theme'),
            background_color=mermaid_style.get('background_color', 'white'),
            scale=mermaid_style.get('scale'),
        )
    
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
            color_str: Color string like "#FF0000" or "FF0000" or "#D14" (short format)
            
        Returns:
            RGBColor object
        """
        color_str = color_str.strip()
        
        if color_str.startswith('#'):
            color_str = color_str[1:]
        
        # Support short format (#RGB -> #RRGGBB)
        if len(color_str) == 3:
            color_str = ''.join([c*2 for c in color_str])
        
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

    def _get_vertical_alignment(self, alignment_str: str) -> WD_CELL_VERTICAL_ALIGNMENT:
        """Get cell vertical alignment enum from string."""
        alignment_map = {
            'top': WD_CELL_VERTICAL_ALIGNMENT.TOP,
            'center': WD_CELL_VERTICAL_ALIGNMENT.CENTER,
            'bottom': WD_CELL_VERTICAL_ALIGNMENT.BOTTOM,
        }
        return alignment_map.get(alignment_str.lower(), WD_CELL_VERTICAL_ALIGNMENT.TOP)

    def _parse_length(self, length_value: Any, default_unit: str = 'pt'):
        """
        Parse a length value into a python-docx length object.

        Args:
            length_value: Length like "5.5in", "12pt", or a numeric value
            default_unit: Unit to assume for numeric values

        Returns:
            Parsed python-docx length object
        """
        if hasattr(length_value, 'emu'):
            return length_value

        if isinstance(length_value, (int, float)):
            value = float(length_value)
            if default_unit == 'in':
                return Inches(value)
            if default_unit == 'cm':
                return Cm(value)
            if default_unit == 'mm':
                return Mm(value)
            return Pt(value)

        length_str = str(length_value).lower().strip()

        if length_str.endswith('cm'):
            return Cm(float(length_str[:-2]))
        if length_str.endswith('in'):
            return Inches(float(length_str[:-2]))
        if length_str.endswith('mm'):
            return Mm(float(length_str[:-2]))
        if length_str.endswith('pt'):
            return Pt(float(length_str[:-2]))

        if default_unit == 'in':
            return Inches(float(length_str))
        if default_unit == 'cm':
            return Cm(float(length_str))
        if default_unit == 'mm':
            return Mm(float(length_str))
        return Pt(float(length_str))

    def _get_available_page_width(self):
        """Get the usable document width after subtracting page margins."""
        section = self.doc.sections[-1]
        return section.page_width - section.left_margin - section.right_margin

    def _get_available_page_height(self):
        """Get the usable document height after subtracting page margins."""
        section = self.doc.sections[-1]
        return section.page_height - section.top_margin - section.bottom_margin

    def _get_image_pixel_size(self, img_bytes: bytes) -> Tuple[int, int]:
        """Read image pixel dimensions from image bytes."""
        from PIL import Image

        with Image.open(BytesIO(img_bytes)) as image:
            width_px, height_px = image.size

        if width_px <= 0 or height_px <= 0:
            raise ValueError("Image has invalid dimensions")

        return width_px, height_px

    def _calculate_mermaid_layout(self, img_bytes: bytes, mermaid_style: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate a Mermaid image layout that fits the current page.

        The image keeps its aspect ratio and is constrained by both
        available page width and height. Very tall diagrams can be nudged
        onto a fresh page so Word has more room to place them cleanly.
        """
        img_width_px, img_height_px = self._get_image_pixel_size(img_bytes)
        aspect_ratio = img_height_px / img_width_px

        available_width = int(self._get_available_page_width())
        available_height = int(self._get_available_page_height())

        preferred_width_value = mermaid_style.get('width')
        preferred_width = (
            min(int(self._parse_length(preferred_width_value, default_unit='in')), available_width)
            if preferred_width_value
            else available_width
        )

        soft_max_height = int(
            available_height * float(mermaid_style.get('soft_max_height_ratio', 0.68))
        )
        hard_max_height = int(
            available_height * float(mermaid_style.get('hard_max_height_ratio', 0.82))
        )
        page_max_height = int(
            available_height * float(mermaid_style.get('page_max_height_ratio', 0.92))
        )
        page_break_threshold = int(
            available_height * float(mermaid_style.get('page_break_threshold_ratio', 0.9))
        )

        min_readable_width_value = mermaid_style.get('min_readable_width')
        min_readable_width = (
            int(self._parse_length(min_readable_width_value, default_unit='in'))
            if min_readable_width_value
            else None
        )

        preferred_height = int(round(preferred_width * aspect_ratio))
        oversized_strategy = str(mermaid_style.get('oversized_strategy', 'page')).lower()
        page_break_before = False

        target_width = preferred_width
        target_height = preferred_height

        if preferred_height > hard_max_height:
            target_height = hard_max_height
            target_width = int(round(target_height / aspect_ratio))

        if oversized_strategy == 'page' and (
            preferred_height > page_break_threshold
            or (min_readable_width is not None and target_width < min_readable_width)
        ):
            page_break_before = True
            target_height = min(preferred_height, page_max_height)
            target_width = int(round(target_height / aspect_ratio))

        # Respect the configured preferred width and current page width.
        target_width = min(target_width, preferred_width, available_width)

        max_target_height = page_max_height if page_break_before else hard_max_height
        target_height = int(round(target_width * aspect_ratio))
        if target_height > max_target_height:
            target_height = max_target_height
            target_width = int(round(target_height / aspect_ratio))

        target_width = max(1, min(target_width, available_width))
        target_height = max(1, int(round(target_width * aspect_ratio)))

        if target_height > max_target_height:
            target_height = max_target_height
            target_width = max(1, int(round(target_height / aspect_ratio)))

        return {
            'width': Emu(target_width),
            'height': Emu(target_height),
            'page_break_before': page_break_before,
            'soft_limit_exceeded': target_height > soft_max_height,
        }

    def _add_block_image(
        self,
        img_bytes: bytes,
        width: Optional[Any] = None,
        height: Optional[Any] = None,
        alignment: str = 'center',
        space_before: Optional[Any] = None,
        space_after: Optional[Any] = None,
        keep_together: Optional[bool] = None,
        keep_with_next: Optional[bool] = None,
        page_break_before: Optional[bool] = None,
        widow_control: Optional[bool] = None,
    ) -> Any:
        """
        Add a block image as its own paragraph.

        Args:
            img_bytes: Image bytes to embed
            width: Optional target width
            height: Optional target height
            alignment: Paragraph alignment
            space_before: Optional spacing before
            space_after: Optional spacing after
            keep_together: Optional paragraph keep-together flag
            keep_with_next: Optional keep-with-next flag
            page_break_before: Optional page-break-before flag
            widow_control: Optional widow control flag
        """
        p = self.doc.add_paragraph()
        p.alignment = self._get_alignment(alignment)

        run = p.add_run()
        image_kwargs = {}
        if width is not None:
            image_kwargs['width'] = width
        if height is not None:
            image_kwargs['height'] = height
        shape = run.add_picture(BytesIO(img_bytes), **image_kwargs)

        if space_before is not None:
            p.paragraph_format.space_before = self._parse_length(space_before)
        if space_after is not None:
            p.paragraph_format.space_after = self._parse_length(space_after)

        if keep_together is not None:
            p.paragraph_format.keep_together = keep_together
        if keep_with_next is not None:
            p.paragraph_format.keep_with_next = keep_with_next
        if page_break_before is not None:
            p.paragraph_format.page_break_before = page_break_before
        if widow_control is not None:
            p.paragraph_format.widow_control = widow_control

        return p, shape
    
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
        
        # Apply heading-level bold/italic from style configuration
        # These are SEPARATE from inline markdown formatting
        if 'bold' in style or 'italic' in style:
            for run in heading.runs:
                if 'bold' in style:
                    run.font.bold = style['bold']
                if 'italic' in style:
                    run.font.italic = style['italic']
        
        # Apply paragraph-level styles
        if 'alignment' in style:
            heading.alignment = self._get_alignment(style['alignment'])
        
        if 'space_before' in style:
            heading.paragraph_format.space_before = Pt(self._parse_font_size(style['space_before']))
        
        if 'space_after' in style:
            heading.paragraph_format.space_after = Pt(self._parse_font_size(style['space_after']))
        
        # Apply first line indent if specified
        if 'first_line_indent' in style and style['first_line_indent'] > 0:
            char_count = style['first_line_indent']
            font_size_pt = self._parse_font_size(style.get('font_size', '12pt'))
            heading.paragraph_format.first_line_indent = Pt(char_count * font_size_pt)
        
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
        
        # Handle block math formulas (they appear as their own paragraphs)
        # Unicode brackets: 〔BLOCK_MATH_N〕
        text_stripped = text.strip()
        if text_stripped.startswith('〔BLOCK_MATH_') and text_stripped.endswith('〕'):
            idx_str = text_stripped.replace('〔BLOCK_MATH_', '').replace('〕', '')
            try:
                idx = int(idx_str)
                if idx < len(self.math_formulas.get('block', [])):
                    latex = self.math_formulas['block'][idx]
                    try:
                        img_bytes = self.math_converter.latex_to_image(latex, inline=False)
                        
                        # Create a centered paragraph for the formula
                        p = self.doc.add_paragraph()
                        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                        
                        # Add image
                        run = p.add_run()
                        run.add_picture(BytesIO(img_bytes), width=Inches(4))
                        
                        # Apply spacing
                        p.paragraph_format.space_before = Pt(6)
                        p.paragraph_format.space_after = Pt(6)
                        
                        return ''
                    except Exception as e:
                        # Fallback: show LaTeX code
                        text = f'$$\\n{latex}\\n$$'
            except:
                pass
        
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
        
        # Apply space before (段前间距)
        if 'space_before' in style:
            p.paragraph_format.space_before = Pt(self._parse_font_size(style['space_before']))
        
        # Apply space after (段后间距)
        if 'space_after' in style:
            p.paragraph_format.space_after = Pt(self._parse_font_size(style['space_after']))
        
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
        # We need to parse <strong>, <em>, <code>, etc.
        
        # Replace HTML tags with markers
        text = text.replace('<strong>', '**START_BOLD**')
        text = text.replace('</strong>', '**END_BOLD**')
        text = text.replace('<em>', '**START_ITALIC**')
        text = text.replace('</em>', '**END_ITALIC**')
        text = text.replace('<code>', '**START_CODE**')
        text = text.replace('</code>', '**END_CODE**')
        
        # Split by markers and process (including math placeholders with Unicode brackets)
        parts = re.split(r'(\*\*START_BOLD\*\*|\*\*END_BOLD\*\*|\*\*START_ITALIC\*\*|\*\*END_ITALIC\*\*|\*\*START_CODE\*\*|\*\*END_CODE\*\*|〔INLINE_MATH_\d+〕|〔BLOCK_MATH_\d+〕)', text)
        
        bold = False
        italic = False
        code = False
        
        # Get inline styles configuration
        inline_bold_style = self.styles.get_inline_style('bold')
        inline_italic_style = self.styles.get_inline_style('italic')
        inline_code_style = self.styles.get_inline_style('code')
        
        for part in parts:
            if part == '**START_BOLD**':
                bold = True
            elif part == '**END_BOLD**':
                bold = False
            elif part == '**START_ITALIC**':
                italic = True
            elif part == '**END_ITALIC**':
                italic = False
            elif part == '**START_CODE**':
                code = True
            elif part == '**END_CODE**':
                code = False
            elif part.startswith('〔INLINE_MATH_') and part.endswith('〕'):
                # Handle inline math formulas with Unicode brackets
                idx_str = part.replace('〔INLINE_MATH_', '').replace('〕', '')
                try:
                    idx = int(idx_str)
                    formulas = getattr(self, 'math_formulas', {'inline': []})
                    if idx < len(formulas.get('inline', [])):
                        latex = formulas['inline'][idx]
                        try:
                            img_bytes = self.math_converter.latex_to_image(latex, inline=True)
                            run = paragraph.add_run()
                            run.add_picture(BytesIO(img_bytes), height=Inches(0.15))
                        except:
                            # Fallback: show LaTeX code
                            paragraph.add_run(f'${latex}$')
                except:
                    pass
            elif part.startswith('〔BLOCK_MATH_') and part.endswith('〕'):
                # Block math should not appear in inline text
                # This shouldn't happen with proper preprocessing
                pass
            elif part:  # Actual text content
                run = paragraph.add_run(part)
                
                # Apply code style if in code span
                if code:
                    # Apply code-specific styling
                    if inline_code_style.get('font_name'):
                        run.font.name = inline_code_style['font_name']
                        # Also set East Asian font
                        from docx.oxml import OxmlElement
                        from docx.oxml.ns import qn
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), inline_code_style['font_name'])
                    
                    if inline_code_style.get('font_size'):
                        run.font.size = Pt(self._parse_font_size(inline_code_style['font_size']))
                    
                    if inline_code_style.get('font_color'):
                        run.font.color.rgb = self._parse_color(inline_code_style['font_color'])
                    
                    # Apply background color/shading
                    if inline_code_style.get('background'):
                        try:
                            from docx.oxml.ns import nsdecls
                            from docx.oxml import parse_xml
                            shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(
                                nsdecls('w'), 
                                inline_code_style['background'].replace('#', '')
                            ))
                            run._element.get_or_add_rPr().append(shading_elm)
                        except:
                            pass  # Ignore if shading fails
                else:
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
                        # Apply bold color from inline config if specified
                        if inline_bold_style.get('font_color'):
                            run.font.color.rgb = self._parse_color(inline_bold_style['font_color'])
                    
                    if italic:
                        run.font.italic = True
                        # Apply italic color from inline config if specified
                        if inline_italic_style.get('font_color'):
                            run.font.color.rgb = self._parse_color(inline_italic_style['font_color'])
    
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
    
    def codespan(self, token: Dict[str, Any], state: Any) -> str:
        """Render inline code span."""
        text = token.get('raw', '')
        return f"<code>{text}</code>"
    
    def inline_math(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render inline LaTeX math formula.
        
        Args:
            token: Token with 'raw' containing LaTeX formula
            state: State object
            
        Returns:
            Marker string for later processing
        """
        latex = token.get('raw', '')
        if not latex:
            return ''
        
        try:
            # Render formula to image
            img_bytes = self.math_converter.latex_to_image(latex, inline=True)
            
            # Create a marker that will be replaced in paragraph processing
            # For now, add image to current paragraph immediately
            # Note: This is a simplified approach for inline formulas
            return f'**INLINE_MATH:{latex}**'
        except Exception as e:
            # If rendering fails, show the LaTeX code
            return f'${latex}$'
    
    def block_math(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render block LaTeX math formula.
        
        Args:
            token: Token with 'raw' containing LaTeX formula
            state: State object
            
        Returns:
            Empty string (content added to document)
        """
        latex = token.get('raw', '')
        if not latex:
            return ''
        
        try:
            # Render formula to image
            img_bytes = self.math_converter.latex_to_image(latex, inline=False)
            
            # Create a centered paragraph for the formula
            p = self.doc.add_paragraph()
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            
            # Add image to paragraph
            run = p.add_run()
            run.add_picture(BytesIO(img_bytes), width=Inches(4))
            
            # Apply spacing from math_block style if available
            math_style = self.styles.get_style('math_block', {})
            if 'space_before' in math_style:
                p.paragraph_format.space_before = Pt(self._parse_font_size(math_style['space_before']))
            if 'space_after' in math_style:
                p.paragraph_format.space_after = Pt(self._parse_font_size(math_style['space_after']))
            
            return ''
        except Exception as e:
            # If rendering fails, show the LaTeX code in a code block
            p = self.doc.add_paragraph(f'$$\n{latex}\n$$')
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            return ''
    
    def block_code(self, token: Dict[str, Any], state: Any) -> str:
        """
        Render code block.
        
        Args:
            token: Token dictionary with 'raw' (code content) and optional 'attrs' (language)
            state: State object
            
        Returns:
            Empty string (content added to document)
        """
        # Get code content
        code_text = token.get('raw', '')
        attrs = token.get('attrs') or {}
        language_info = attrs.get('info', '') or ''
        language = language_info.split(None, 1)[0].lower() if language_info else ''
        
        if not code_text:
            return ''

        if language == 'mermaid':
            mermaid_style = self.styles.get_mermaid_style()
            try:
                img_bytes = self.mermaid_converter.mermaid_to_image(code_text)
                layout = self._calculate_mermaid_layout(img_bytes, mermaid_style)

                self._add_block_image(
                    img_bytes,
                    width=layout['width'],
                    height=layout['height'],
                    alignment=mermaid_style.get('alignment', 'center'),
                    space_before=mermaid_style.get('space_before'),
                    space_after=mermaid_style.get('space_after'),
                    keep_together=mermaid_style.get('keep_together', True),
                    keep_with_next=mermaid_style.get('keep_with_next', False),
                    page_break_before=layout['page_break_before'],
                    widow_control=mermaid_style.get('widow_control', False),
                )
                return ''
            except Exception:
                # Fall back to the existing code block rendering if Mermaid render fails.
                pass
        
        # Get code block style
        code_style = self.styles.get_code_block_style()
        
        # Apply padding by adding spaces to each line
        if code_style.get('padding'):
            padding_pt = self._parse_font_size(code_style['padding'])
            # Approximate: 1 space ≈ 0.5em for monospace fonts
            # For 12pt padding with 10pt font: ~2-3 spaces
            font_size = self._parse_font_size(code_style.get('font_size', '10pt'))
            spaces_count = max(1, int(padding_pt / font_size * 2))
            padding_str = ' ' * spaces_count
            
            # Add padding to each line
            lines = code_text.split('\n')
            padded_lines = [padding_str + line for line in lines]
            code_text = '\n'.join(padded_lines)
        
        # Create paragraph for code block
        p = self.doc.add_paragraph()
        
        # Add code text
        run = p.add_run(code_text)
        
        # Apply font styling
        if code_style.get('font_name'):
            run.font.name = code_style['font_name']
            # Also set East Asian font
            from docx.oxml import OxmlElement
            from docx.oxml.ns import qn
            run._element.rPr.rFonts.set(qn('w:eastAsia'), code_style['font_name'])
        
        if code_style.get('font_size'):
            run.font.size = Pt(self._parse_font_size(code_style['font_size']))
        
        # Apply bold and italic if specified
        if code_style.get('bold'):
            run.font.bold = True
        
        if code_style.get('italic'):
            run.font.italic = True
        
        if code_style.get('font_color'):
            run.font.color.rgb = self._parse_color(code_style['font_color'])
        
        # Apply background shading
        if code_style.get('background'):
            try:
                from docx.oxml.ns import nsdecls
                from docx.oxml import parse_xml
                shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(
                    nsdecls('w'), 
                    code_style['background'].replace('#', '')
                ))
                p._element.get_or_add_pPr().append(shading_elm)
            except:
                pass  # Ignore if shading fails
        
        # Apply paragraph-level styling
        if code_style.get('line_spacing'):
            p.paragraph_format.line_spacing = code_style['line_spacing']
        
        if code_style.get('space_before'):
            p.paragraph_format.space_before = Pt(self._parse_font_size(code_style['space_before']))
        
        if code_style.get('space_after'):
            p.paragraph_format.space_after = Pt(self._parse_font_size(code_style['space_after']))
        
        return ''
    
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
        # Separate inline content from nested lists
        children = token.get('children', [])
        inline_children = []
        nested_lists = []
        
        for child in children:
            if child['type'] == 'list':
                nested_lists.append(child)
            else:
                inline_children.append(child)
        
        # Get text from inline children only
        text = ''.join([self.render_token(child, state) for child in inline_children])
        
        # Only skip if there's no inline text AND no nested lists
        if (not text or text.strip() == '') and not nested_lists:
            return
        
        # If there's inline text, render it as a list item
        if text and text.strip():
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
            
            # Apply custom list formatting
            if ordered:
                # Custom number format
                number_format = list_style.get('number_format', '1.')
                self._apply_numbered_list(p, number_format, depth)
            else:
                # Custom bullet character
                bullet_char = list_style.get('bullet_char', '•')
                self._apply_bulleted_list(p, bullet_char, depth)
            
            # Apply indentation for nested lists
            if depth > 0:
                from docx.shared import Inches
                indent_size = 0.5  # inches per level
                if 'indent_size' in list_style:
                    indent_str = list_style['indent_size']
                    if isinstance(indent_str, str) and indent_str.endswith('in'):
                        indent_size = float(indent_str[:-2])
                
                p.paragraph_format.left_indent = Inches(indent_size * (depth + 1))
            
            # Apply line spacing from list style
            if 'line_spacing' in list_style:
                p.paragraph_format.line_spacing = list_style['line_spacing']
            
            # Apply space after from list style
            if 'space_after' in list_style:
                p.paragraph_format.space_after = Pt(self._parse_font_size(list_style['space_after']))
        
        # Render nested lists with increased depth
        for nested_list in nested_lists:
            # Get list type from nested list
            nested_ordered = nested_list['attrs'].get('ordered', False)
            # Process each child of the nested list
            for child in nested_list.get('children', []):
                if child['type'] == 'list_item':
                    self._render_list_item(child, state, nested_ordered, depth + 1)
    
    def _apply_bulleted_list(self, paragraph, bullet_char: str, depth: int):
        """
        Apply custom bullet character to paragraph.
        
        Args:
            paragraph: Paragraph object
            bullet_char: Bullet character to use
            depth: Nesting depth
        """
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        
        # Get or create paragraph properties
        pPr = paragraph._element.get_or_add_pPr()
        
        # Create numbering properties
        numPr = OxmlElement('w:numPr')
        
        # Create indent level
        ilvl = OxmlElement('w:ilvl')
        ilvl.set(qn('w:val'), str(depth))
        numPr.append(ilvl)
        
        # Create numbering ID (use 1 for bullets)
        numId = OxmlElement('w:numId')
        numId.set(qn('w:val'), '1')
        numPr.append(numId)
        
        # Add to paragraph properties
        pPr.append(numPr)
        
        # Add custom bullet as text at the beginning (workaround)
        # This is a simpler approach than creating complex numbering definitions
        if bullet_char != '•':  # Only if not default
            # Remove the numbering and add bullet manually
            pPr.remove(numPr)
            
            # Insert bullet at the beginning of paragraph
            runs = paragraph.runs
            if runs:
                # Prepend bullet to first run
                first_run = runs[0]
                first_run.text = f"{bullet_char}\t{first_run.text}"
            else:
                # Add bullet run
                run = paragraph.add_run(f"{bullet_char}\t")
        else:
            # Use Word's default bullet style
            paragraph.style = 'List Bullet'
    
    def _apply_numbered_list(self, paragraph, number_format: str, depth: int):
        """
        Apply custom number format to paragraph.
        
        Args:
            paragraph: Paragraph object
            number_format: Number format string (e.g., "1.", "1)", "(1)")
            depth: Nesting depth
        """
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        
        # Determine format type and suffix
        if number_format.startswith('(') and number_format.endswith(')'):
            # Format: (1)
            prefix = '('
            suffix = ')'
        elif number_format.endswith(')'):
            # Format: 1)
            prefix = ''
            suffix = ')'
        elif number_format.endswith('.'):
            # Format: 1.
            prefix = ''
            suffix = '.'
        else:
            # Default
            prefix = ''
            suffix = '.'
        
        # If using default format "1.", use built-in style
        if number_format == '1.':
            paragraph.style = 'List Number'
        else:
            # For custom formats, we need to manually track numbering
            # This is a simplified approach - for production, you'd want
            # to implement proper numbering tracking
            
            # Get or create paragraph properties
            pPr = paragraph._element.get_or_add_pPr()
            
            # Create numbering properties
            numPr = OxmlElement('w:numPr')
            
            # Create indent level
            ilvl = OxmlElement('w:ilvl')
            ilvl.set(qn('w:val'), str(depth))
            numPr.append(ilvl)
            
            # Create numbering ID (use 2 for numbers)
            numId = OxmlElement('w:numId')
            numId.set(qn('w:val'), '2')
            numPr.append(numId)
            
            # Add to paragraph properties
            pPr.append(numPr)
            
            # Note: For true custom number formats, we'd need to:
            # 1. Create/modify the numbering.xml part
            # 2. Define custom abstract numbering definitions
            # 3. This is complex and beyond basic implementation
            # For now, we use the built-in numbering with custom display

    
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
        header_alignment = str(table_style.get('header_alignment', 'center')).lower()
        header_vertical_alignment = str(table_style.get('header_vertical_alignment', 'center')).lower()
        
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
                
                # Apply line spacing to table cell paragraph
                if 'line_spacing' in table_style:
                    p.paragraph_format.line_spacing = table_style['line_spacing']
                
                # Center header text by default, with an opt-in inherit mode.
                align = cell_token.get('attrs', {}).get('align') or table_style.get('alignment', 'left')
                if header_alignment == 'inherit':
                    p.alignment = self._get_alignment(str(align))
                else:
                    p.alignment = self._get_alignment(header_alignment)
                cell.vertical_alignment = self._get_vertical_alignment(header_vertical_alignment)
                
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
        
        # Check if alternating rows are enabled
        alternating_rows = table_style.get('alternating_rows', False)
        
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
                
                # Apply column alignment, falling back to the configured table default.
                align = cell_token.get('attrs', {}).get('align') or table_style.get('alignment', 'left')
                p.alignment = self._get_alignment(str(align))
                
                # Apply alternating row background (zebra striping)
                if alternating_rows:
                    # Row 0 is header, so data rows start from row 1
                    # Even rows: 2, 4, 6... Odd rows: 1, 3, 5...
                    is_even_row = (self._current_row_idx % 2) == 0
                    
                    if is_even_row and 'row_background_even' in table_style:
                        bg_color = table_style['row_background_even']
                    elif not is_even_row and 'row_background_odd' in table_style:
                        bg_color = table_style['row_background_odd']
                    else:
                        bg_color = None
                    
                    if bg_color:
                        try:
                            from docx.oxml.ns import nsdecls
                            from docx.oxml import parse_xml
                            shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(
                                nsdecls('w'), 
                                bg_color.replace('#', '')
                            ))
                            cell._element.get_or_add_tcPr().append(shading_elm)
                        except:
                            pass  # Ignore if shading fails
        
        self._current_row_idx += 1
        return ''
    
    def table_cell(self, token: Dict[str, Any], state: Any) -> str:
        """Render table cell (called by render_children)."""
        return ''.join(self.render_children(token, state))
