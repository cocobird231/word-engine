"""
Word Engine - Renderer Module (Phase 1 + Phase 2)
Renders normalized markdown to docx using python-docx and markdown-it-py.

Phase 2 additions:
  - Cover page (src/renderer/cover.py)
  - TOC Word field (src/renderer/toc.py)
  - Image rendering with figure caption and numbering
  - Table rendering with table caption and numbering
  - H1 chapter tracking for 'chapter' numbering mode
  - Cross-reference: {{ref:fig-1}}, {{ref:tbl-1}}, {{ref:sec-1}} substitution
  - Bookmarks added to figure/table captions and headings
"""
import os
import tempfile
import urllib.request
from docx import Document
from markdown_it import MarkdownIt
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from src.renderer.cover import render_cover
from src.renderer.toc import render_toc
from src.renderer.caption import CaptionCounter, add_figure_caption, add_table_caption
from src.renderer.cross_reference import (
    ReferenceRegistry, BookmarkManager, add_bookmark
)


def _hex_to_rgb(hex_color):
    """Convert #RRGGBB to (R, G, B) tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _add_paragraph_shading(paragraph, bg_hex):
    """Add background shading to a paragraph via OOXML pPr/shd element."""
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    bg = bg_hex.lstrip("#")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), bg)
    pPr.append(shd)


def _add_run_shading(run, bg_hex):
    """Add background highlight shading to a run via OOXML rPr/shd element.
    
    Uses w:val='solid' which provides reliable character-level background shading
    in both Word and LibreOffice, unlike 'clear' which can be invisible in some
    rendering contexts.
    """
    rPr = run._r.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    bg = bg_hex.lstrip("#")
    shd.set(qn("w:val"), "solid")   # 'solid' not 'clear' for reliable run-level shading
    shd.set(qn("w:color"), bg)      # w:color is the pattern color (foreground of pattern)
    shd.set(qn("w:fill"), bg)       # w:fill is the background fill color
    rPr.append(shd)


def _add_anchor_hyperlink(paragraph, display_text, bookmark_name, params):
    """
    Add an internal anchor hyperlink to a paragraph that links to a Word bookmark.

    This creates a Word internal hyperlink (w:hyperlink w:anchor) pointing to
    the bookmark created by add_bookmark() for the referenced figure/table/heading.
    
    Falls back to plain text if cross_references.hyperlink_enabled is False.
    """
    xref_cfg = params.get("cross_references", {})
    hyperlink_enabled = xref_cfg.get("hyperlink_enabled", True)

    if not hyperlink_enabled:
        paragraph.add_run(display_text)
        return

    # Create <w:hyperlink w:anchor="bookmark_name">
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("w:anchor"), bookmark_name)

    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    # Apply Hyperlink style (blue + underline)
    rStyle = OxmlElement("w:rStyle")
    rStyle.set(qn("w:val"), "Hyperlink")
    rPr.append(rStyle)
    r.append(rPr)

    t = OxmlElement("w:t")
    t.text = display_text
    r.append(t)
    hyperlink.append(r)
    paragraph._p.append(hyperlink)


def _render_inline_content(paragraph, inline_token, registry, params):
    """
    Render an inline token's children into the paragraph with proper formatting.
    Handles: plain text, bold, italic, code_inline (monospace + shading), softbreak.
    Falls back to content string if children are not available.
    """
    code_cfg = params.get("code", {}).get("inline", {})
    code_font = code_cfg.get("font_family", "Consolas")
    code_size_pt = code_cfg.get("font_size_pt", 10.5)
    code_bg = code_cfg.get("background_color", "#F2F2F2")

    children = inline_token.children if inline_token.children else []

    if not children:
        # Fallback: substitute and add as plain text
        text = registry.substitute(inline_token.content)
        paragraph.add_run(text)
        return

    i = 0
    while i < len(children):
        child = children[i]

        if child.type == "code_inline":
            run = paragraph.add_run(child.content)
            run.font.name = code_font
            run.font.size = Pt(code_size_pt)
            _add_run_shading(run, code_bg)

        elif child.type == "text":
            # Check if text contains {{ref:*}} markers; if so, render as hyperlinks
            from src.renderer.cross_reference import REF_PATTERN, BookmarkManager
            raw = child.content
            if REF_PATTERN.search(raw):
                last_end = 0
                for m in REF_PATTERN.finditer(raw):
                    # Plain text before this ref
                    if m.start() > last_end:
                        paragraph.add_run(raw[last_end:m.start()])
                    ref_id = m.group(1)
                    display = registry.resolve(ref_id)
                    # Determine bookmark name from ref_id
                    bm_name = ref_id.replace("-", "_")
                    _add_anchor_hyperlink(paragraph, display, bm_name, params)
                    last_end = m.end()
                if last_end < len(raw):
                    paragraph.add_run(raw[last_end:])
            else:
                paragraph.add_run(raw)

        elif child.type == "softbreak":
            paragraph.add_run(" ")

        elif child.type == "hardbreak":
            paragraph.add_run("\n")

        elif child.type == "strong_open":
            # collect until strong_close
            i += 1
            bold_text = ""
            while i < len(children) and children[i].type != "strong_close":
                if children[i].type == "text":
                    bold_text += children[i].content
                i += 1
            run = paragraph.add_run(bold_text)
            run.bold = True

        elif child.type == "em_open":
            i += 1
            em_text = ""
            while i < len(children) and children[i].type != "em_close":
                if children[i].type == "text":
                    em_text += children[i].content
                i += 1
            run = paragraph.add_run(em_text)
            run.italic = True

        i += 1


def _apply_heading_style(run, level, params):
    """Apply basic heading styles from params."""
    run.font.bold = True
    if level == 1:
        run.font.size = Pt(18)
    elif level == 2:
        run.font.size = Pt(16)
    else:
        run.font.size = Pt(14)


def _heading_path_to_str(path):
    """Convert heading path list to display string, e.g. [2,1,0] → '2.1'."""
    return ".".join(str(n) for n in path if n > 0)


def _render_image(doc, token, counter, registry, bm_mgr, params):
    """Render an image inline token with figure caption and bookmark."""
    images_cfg = params.get("images", {})
    max_width_cm = images_cfg.get("max_width_cm", 15.5)

    src = ""
    alt = ""
    if hasattr(token, "attrs") and token.attrs:
        src = token.attrs.get("src", "")
        alt = token.attrs.get("alt", "")
    if not alt and token.children:
        for child in token.children:
            if child.type == "text":
                alt = child.content
                break

    caption_position = images_cfg.get("caption_position", "below")

    if caption_position == "above":
        mode = images_cfg.get("numbering_mode", "flat")
        sep = images_cfg.get("chapter_separator", "-")
        num = counter.peek_next_figure(mode=mode, separator=sep)
        ref_id = registry.register_figure(num)
        p_cap = add_figure_caption(doc, alt, counter, params)
        if p_cap:
            bm_id, bm_name = bm_mgr.figure_bookmark(counter._figure)
            add_bookmark(p_cap, bm_id, bm_name)

    # Insert image or placeholder
    image_inserted = False
    if src:
        local_path = None
        tmp_file = None
        try:
            if src.startswith("http://") or src.startswith("https://"):
                if images_cfg.get("download_remote_images", True):
                    tmp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                    urllib.request.urlretrieve(src, tmp_file.name)
                    local_path = tmp_file.name
            else:
                if os.path.exists(src):
                    local_path = src

            if local_path:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.add_picture(local_path, width=Inches(max_width_cm / 2.54))
                image_inserted = True
        except Exception:
            pass
        finally:
            if tmp_file:
                try:
                    os.unlink(tmp_file.name)
                except Exception:
                    pass

    if not image_inserted:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"[圖片: {src or alt or '無法載入'}]")
        run.font.size = Pt(10)
        run.italic = True

    if caption_position != "above":
        mode = images_cfg.get("numbering_mode", "flat")
        sep = images_cfg.get("chapter_separator", "-")
        num = counter.peek_next_figure(mode=mode, separator=sep)
        # Register BEFORE add_figure_caption so {{ref:fig-N}} in same doc resolves
        ref_id = registry.register_figure(num)
        p_cap = add_figure_caption(doc, alt, counter, params)
        if p_cap:
            bm_id, bm_name = bm_mgr.figure_bookmark(counter._figure)
            add_bookmark(p_cap, bm_id, bm_name)


def _render_table(doc, token_group, counter, registry, bm_mgr, params):
    """Render a markdown table with caption and bookmark."""
    tables_cfg = params.get("tables", {})
    caption_position = tables_cfg.get("caption_position", "above")

    headers = token_group.get("headers", [])
    rows = token_group.get("rows", [])

    if not headers and not rows:
        return

    mode = tables_cfg.get("numbering_mode", "flat")
    sep = tables_cfg.get("chapter_separator", "-")

    if caption_position == "above":
        num = counter.peek_next_table(mode=mode, separator=sep)
        ref_id = registry.register_table(num)
        p_cap = add_table_caption(doc, "", counter, params)
        if p_cap:
            bm_id, bm_name = bm_mgr.table_bookmark(counter._table)
            add_bookmark(p_cap, bm_id, bm_name)

    col_count = len(headers) if headers else (len(rows[0]) if rows else 1)
    all_rows = ([headers] if headers else []) + rows
    table = doc.add_table(rows=len(all_rows), cols=col_count)
    try:
        table.style = "Table Grid"
    except Exception:
        pass

    for r_idx, row_data in enumerate(all_rows):
        row = table.rows[r_idx]
        is_header = (r_idx == 0 and bool(headers))
        for c_idx, cell_text in enumerate(row_data[:col_count]):
            cell = row.cells[c_idx]
            cell.text = cell_text.strip()
            if is_header:
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.bold = True

    if caption_position != "above":
        num = counter.peek_next_table(mode=mode, separator=sep)
        ref_id = registry.register_table(num)
        p_cap = add_table_caption(doc, "", counter, params)
        if p_cap:
            bm_id, bm_name = bm_mgr.table_bookmark(counter._table)
            add_bookmark(p_cap, bm_id, bm_name)


def _parse_table_tokens(tokens, start_idx):
    """Parse markdown-it table tokens into headers and rows."""
    headers = []
    rows = []
    current_row = []
    in_thead = False
    in_tbody = False

    i = start_idx + 1
    while i < len(tokens) and tokens[i].type != "table_close":
        t = tokens[i]
        if t.type == "thead_open":
            in_thead = True
        elif t.type == "thead_close":
            in_thead = False
        elif t.type == "tbody_open":
            in_tbody = True
        elif t.type == "tbody_close":
            in_tbody = False
        elif t.type == "tr_open":
            current_row = []
        elif t.type == "tr_close":
            if in_thead:
                headers = current_row
            elif in_tbody:
                rows.append(current_row)
        elif t.type == "inline":
            current_row.append(t.content)
        i += 1
    return headers, rows, i


def _render_tokens(doc, tokens, params, counter, registry, bm_mgr):
    """Walk through markdown-it tokens and render to docx."""
    list_level = 0
    in_list = False
    list_type = "bullet"
    heading_path = [0, 0, 0, 0, 0, 0]  # H1–H6 counters

    i = 0
    while i < len(tokens):
        token = tokens[i]

        # ── Headings ──
        if token.type == "heading_open":
            level = int(token.tag[1:])
            i += 1
            content = ""
            while i < len(tokens) and tokens[i].type != "heading_close":
                if tokens[i].type == "inline":
                    content = tokens[i].type == "inline" and tokens[i].content or ""
                    content = tokens[i].content
                i += 1

            # Update heading path and chapter counter
            heading_path[level - 1] += 1
            for j in range(level, 6):
                heading_path[j] = 0

            chapter_level = int(params.get("caption_chapter_level", 2))
            if level == chapter_level:
                counter.advance_chapter()

            ref_id = registry.register_heading(level, heading_path[:level])

            if level <= 3:
                p = doc.add_paragraph()
                p.style = doc.styles[f"Heading {level}"]
                run = p.add_run(content)
                _apply_heading_style(run, level, params)
                # Add bookmark to heading
                bm_id, bm_name = bm_mgr.heading_bookmark(heading_path[:level])
                add_bookmark(p, bm_id, bm_name)

        # ── Paragraphs ──
        elif token.type == "paragraph_open":
            if not in_list:
                i += 1
                inline_token = None
                while i < len(tokens) and tokens[i].type != "paragraph_close":
                    if tokens[i].type == "inline":
                        inline_token = tokens[i]
                    i += 1

                if inline_token:
                    children = inline_token.children or []
                    is_image_only = (
                        len(children) >= 1 and all(
                            c.type in ("image", "softbreak") for c in children
                        )
                    )
                    if is_image_only:
                        for child in children:
                            if child.type == "image":
                                _render_image(doc, child, counter, registry, bm_mgr, params)
                    else:
                        p = doc.add_paragraph()
                        _render_inline_content(p, inline_token, registry, params)

        # ── Lists ──
        elif token.type == "bullet_list_open":
            in_list = True
            list_type = "bullet"
            list_level += 1
        elif token.type == "bullet_list_close":
            list_level -= 1
            if list_level == 0:
                in_list = False

        elif token.type == "ordered_list_open":
            in_list = True
            list_type = "ordered"
            list_level += 1
        elif token.type == "ordered_list_close":
            list_level -= 1
            if list_level == 0:
                in_list = False

        elif token.type == "list_item_open":
            i += 1
            content = ""
            while i < len(tokens) and tokens[i].type != "list_item_close":
                if tokens[i].type == "inline":
                    content = tokens[i].content
                i += 1
            content = registry.substitute(content)
            style = "List Bullet" if list_type == "bullet" else "List Number"
            if list_level > 1:
                styled = f"{style} {list_level}"
                if styled not in doc.styles:
                    styled = style
                style = styled
            doc.add_paragraph(content, style=style)

        # ── Tables ──
        elif token.type == "table_open":
            headers, rows, end_idx = _parse_table_tokens(tokens, i)
            _render_table(doc, {"headers": headers, "rows": rows}, counter, registry, bm_mgr, params)
            i = end_idx

        # ── Code Blocks ──
        elif token.type == "fence":
            code_content = token.content
            if code_content.endswith("\n"):
                code_content = code_content[:-1]
            code_cfg = params.get("code", {}).get("block", {})
            code_font = code_cfg.get("font_family", "Consolas")
            code_size_pt = code_cfg.get("font_size_pt", 10.5)
            code_bg = code_cfg.get("background_color", "#F2F2F2")
            indent_cm = code_cfg.get("indent_left_cm", 0.5)
            p = doc.add_paragraph()
            try:
                p.style = doc.styles["Macro Text"]
            except KeyError:
                p.style = doc.styles["Normal"]
            run = p.add_run(code_content)
            run.font.name = code_font
            run.font.size = Pt(code_size_pt)
            p.paragraph_format.left_indent = Inches(indent_cm)
            # Apply background shading from params
            _add_paragraph_shading(p, code_bg)

        i += 1


def _pre_scan_references(tokens, params):
    """
    First pass: scan all tokens to pre-register all figures, tables, and headings.
    Returns a fully populated ReferenceRegistry.

    This enables forward references ({{ref:fig-1}} before the figure).
    """
    counter = CaptionCounter()
    registry = ReferenceRegistry(params)
    heading_path = [0, 0, 0, 0, 0, 0]

    i = 0
    while i < len(tokens):
        t = tokens[i]

        if t.type == "heading_open":
            level = int(t.tag[1:])
            heading_path[level - 1] += 1
            for j in range(level, 6):
                heading_path[j] = 0
            chapter_level = int(params.get("caption_chapter_level", 2))
            if level == chapter_level:
                counter.advance_chapter()
            registry.register_heading(level, heading_path[:level])

        elif t.type == "paragraph_open":
            # Look ahead for image
            j = i + 1
            while j < len(tokens) and tokens[j].type != "paragraph_close":
                if tokens[j].type == "inline":
                    children = tokens[j].children or []
                    for child in children:
                        if child.type == "image":
                            images_cfg = params.get("images", {})
                            mode = images_cfg.get("numbering_mode", "flat")
                            sep = images_cfg.get("chapter_separator", "-")
                            num = counter.peek_next_figure(mode=mode, separator=sep)
                            registry.register_figure(num)
                            counter.next_figure(mode=mode, separator=sep)
                j += 1

        elif t.type == "table_open":
            tables_cfg = params.get("tables", {})
            mode = tables_cfg.get("numbering_mode", "flat")
            sep = tables_cfg.get("chapter_separator", "-")
            num = counter.peek_next_table(mode=mode, separator=sep)
            registry.register_table(num)
            counter.next_table(mode=mode, separator=sep)
            # Skip to table_close
            while i < len(tokens) and tokens[i].type != "table_close":
                i += 1

        i += 1

    return registry


def render_docx(md_text, params, output_path):
    """
    Render normalized markdown text to a docx file.

    Uses a two-pass approach:
      Pass 1 (_pre_scan_references): scan all elements to build the reference map
      Pass 2 (_render_tokens): actual docx rendering with all {{ref:*}} resolved

    Args:
        md_text: Normalized markdown string.
        params: Parsed params.yaml dict.
        output_path: Destination path for the .docx file.

    Returns:
        output_path
    """
    doc = Document()
    md = MarkdownIt().enable("table")
    tokens = md.parse(md_text)

    # Pass 1: pre-scan to build full reference map (enables forward references)
    registry = _pre_scan_references(tokens, params)

    # Pass 2: actual render with all references pre-resolved
    counter = CaptionCounter()
    bm_mgr = BookmarkManager(params)

    render_cover(doc, params)
    render_toc(doc, params)
    _render_tokens(doc, tokens, params, counter, registry, bm_mgr)

    doc.save(output_path)
    return output_path
