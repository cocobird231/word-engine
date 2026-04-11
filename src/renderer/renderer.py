"""
Word Engine - Renderer Module (Phase 1 + Phase 2)
Renders normalized markdown to docx using python-docx and markdown-it-py.

Phase 2 additions:
  - Cover page (src/renderer/cover.py)
  - TOC Word field (src/renderer/toc.py)
  - Image rendering with figure caption and numbering
  - Table rendering with table caption and numbering
  - H1 chapter tracking for 'chapter' numbering mode
"""
import re
import os
import tempfile
import urllib.request
from docx import Document
from markdown_it import MarkdownIt
from docx.shared import Pt, Inches, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from src.renderer.cover import render_cover
from src.renderer.toc import render_toc
from src.renderer.caption import CaptionCounter, add_figure_caption, add_table_caption


def _apply_heading_style(run, level, params):
    """Apply basic heading styles from params."""
    run.font.bold = True
    if level == 1:
        run.font.size = Pt(18)
    elif level == 2:
        run.font.size = Pt(16)
    else:
        run.font.size = Pt(14)


def _render_image(doc, token, counter, params):
    """
    Render an image inline token and its caption.

    Tries to insert the image from local path or URL.
    Falls back to a placeholder paragraph if the image cannot be loaded.
    """
    images_cfg = params.get("images", {})
    max_width_cm = images_cfg.get("max_width_cm", 15.5)

    # Extract src and alt from token children
    src = ""
    alt = ""
    if token.children:
        for child in token.children:
            if child.type == "image":
                src = child.attrGet("src") or ""
                alt = child.content or ""
            elif child.type == "text":
                alt = child.content or alt

    # Determine src and alt from token attrs directly if children method didn't work
    if not src and hasattr(token, "attrs") and token.attrs:
        src = token.attrs.get("src", "")
        alt = token.attrs.get("alt", alt)

    # Add figure caption before image if caption_position is "above" (unusual but supported)
    caption_position = images_cfg.get("caption_position", "below")
    if caption_position == "above":
        add_figure_caption(doc, alt, counter, params)

    # Try to insert the image
    image_inserted = False
    if src:
        local_path = None
        tmp_file = None
        try:
            if src.startswith("http://") or src.startswith("https://"):
                # Download to temp file
                if images_cfg.get("download_remote_images", True):
                    tmp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                    urllib.request.urlretrieve(src, tmp_file.name)
                    local_path = tmp_file.name
            else:
                # Local file path
                if os.path.exists(src):
                    local_path = src

            if local_path:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.add_picture(local_path, width=Inches(max_width_cm / 2.54))
                image_inserted = True

        except Exception:
            # Image failed to load — fall through to placeholder
            pass
        finally:
            if tmp_file:
                try:
                    os.unlink(tmp_file.name)
                except Exception:
                    pass

    if not image_inserted:
        # Placeholder when image can't be loaded
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"[圖片: {src or alt or '無法載入'}]")
        run.font.size = Pt(10)
        run.italic = True

    # Add caption below image (default)
    if caption_position != "above":
        add_figure_caption(doc, alt, counter, params)


def _render_table(doc, token_group, counter, params):
    """
    Render a markdown table token group and its caption.

    Args:
        doc: python-docx Document.
        token_group: Dict with 'headers' (list[str]) and 'rows' (list[list[str]]).
        counter: CaptionCounter instance.
        params: Parsed params.yaml dict.
    """
    tables_cfg = params.get("tables", {})
    caption_position = tables_cfg.get("caption_position", "above")

    headers = token_group.get("headers", [])
    rows = token_group.get("rows", [])

    if not headers and not rows:
        return

    # Caption above (default for tables)
    if caption_position == "above":
        add_table_caption(doc, "", counter, params)

    # Build table
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

    # Caption below
    if caption_position != "above":
        add_table_caption(doc, "", counter, params)


def _parse_table_tokens(tokens, start_idx):
    """
    Parse markdown-it table tokens starting from table_open at start_idx.

    Returns:
        (headers, rows, end_idx)
    """
    headers = []
    rows = []
    current_row = []
    in_thead = False
    in_tbody = False

    i = start_idx + 1  # skip table_open
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
        elif t.type in ("th_open", "td_open"):
            pass
        elif t.type == "inline":
            current_row.append(t.content)
        i += 1
    return headers, rows, i  # i now points at table_close


def _render_tokens(doc, tokens, params, counter):
    """Walk through markdown-it tokens and render to docx."""
    list_level = 0
    in_list = False
    list_type = "bullet"

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
                    content = tokens[i].content
                i += 1

            # Track H1 for chapter numbering
            if level == 1:
                counter.advance_chapter()

            if level <= 3:
                p = doc.add_paragraph()
                p.style = doc.styles[f"Heading {level}"]
                run = p.add_run(content)
                _apply_heading_style(run, level, params)

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
                    # Check if this paragraph is just an image
                    children = inline_token.children or []
                    is_image_only = (
                        len(children) == 1 and children[0].type == "image"
                    ) or (
                        len(children) >= 1 and all(
                            c.type in ("image", "softbreak") for c in children
                        )
                    )
                    if is_image_only:
                        for child in children:
                            if child.type == "image":
                                # Build a synthetic token for image rendering
                                _render_image(doc, child, counter, params)
                    else:
                        doc.add_paragraph(inline_token.content)

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
            _render_table(doc, {"headers": headers, "rows": rows}, counter, params)
            i = end_idx  # skip to table_close

        # ── Code Blocks ──
        elif token.type == "fence":
            content = token.content
            if content.endswith("\n"):
                content = content[:-1]
            p = doc.add_paragraph()
            try:
                p.style = doc.styles["Macro Text"]
            except KeyError:
                p.style = doc.styles["Normal"]
            run = p.add_run(content)
            run.font.name = "Courier New"
            p.paragraph_format.left_indent = Inches(0.5)

        i += 1


def render_docx(md_text, params, output_path):
    """
    Render normalized markdown text to a docx file.

    Args:
        md_text: Normalized markdown string.
        params: Parsed params.yaml dict.
        output_path: Destination path for the .docx file.

    Returns:
        output_path
    """
    doc = Document()
    md = MarkdownIt().enable("table")
    counter = CaptionCounter()

    # Phase 2: cover page
    render_cover(doc, params)

    # Phase 2: TOC field
    render_toc(doc, params)

    tokens = md.parse(md_text)
    _render_tokens(doc, tokens, params, counter)

    doc.save(output_path)
    return output_path
