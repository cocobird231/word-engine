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
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from src.renderer.cover import render_cover
from src.renderer.toc import render_toc
from src.renderer.caption import CaptionCounter, add_figure_caption, add_table_caption
from src.renderer.cross_reference import (
    ReferenceRegistry, BookmarkManager, add_bookmark
)


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

            if level == 1:
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
                        text = registry.substitute(inline_token.content)
                        doc.add_paragraph(text)

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
            if level == 1:
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
