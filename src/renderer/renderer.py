"""
Word Engine - Renderer Module (Phase 1 + Phase 2 + Phase 3)
Renders normalized markdown to docx using python-docx and markdown-it-py.

Phase 2 additions:
  - Cover page (src/renderer/cover.py)
  - TOC Word field (src/renderer/toc.py)
  - Image rendering with figure caption and numbering
  - Table rendering with table caption and numbering
  - H1 chapter tracking for 'chapter' numbering mode
  - Cross-reference: {{ref:fig-1}}, {{ref:tbl-1}}, {{ref:sec-1}} substitution
  - Bookmarks added to figure/table captions and headings

Phase 3 additions:
  - Graphviz / Mermaid fenced code blocks rendered to PNG and inserted as images
  - Image sources: file:// URI, relative path (resolved from md_dir), URL download
  - All fetched/generated images saved persistently under assets_dir
"""
import hashlib
import os
import re
import urllib.request
import urllib.parse
from docx import Document
from markdown_it import MarkdownIt
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from src.renderer.cover import render_cover
from src.renderer.seq_field import insert_ref_field
from src.renderer.toc import render_toc
from src.renderer.caption import CaptionCounter, add_figure_caption, add_table_caption
from src.renderer.cross_reference import (
    ReferenceRegistry, BookmarkManager, add_bookmark
)
from src.renderer.diagram import render_graphviz, render_mermaid


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
    Add a Word REF field cross-reference to a paragraph.

    Phase 3 upgrade: Uses REF field (Word-updatable reference) instead of
    static hyperlink. The REF field:
    - Points to the bookmark on the SEQ caption
    - Updates automatically when F9 / UNO field update runs
    - \\h flag makes it a clickable hyperlink in Word

    Falls back to plain text if cross_references.hyperlink_enabled is False.
    """
    xref_cfg = params.get("cross_references", {})
    hyperlink_enabled = xref_cfg.get("hyperlink_enabled", True)

    insert_ref_field(
        paragraph=paragraph,
        display_text=display_text,
        bookmark_name=bookmark_name,
        with_hyperlink=hyperlink_enabled,
    )



def _render_text_to_paragraph(paragraph, text, registry, params, bold_all=False):
    """
    Render a text string into a paragraph with full inline formatting support.

    Uses markdown-it to parse inline tokens, supporting:
    - **bold** (strong)
    - *italic* (em)
    - `inline code` (code_inline, with Consolas font + shading)
    - Plain text with {{ref:*}} substitution

    Args:
        paragraph: python-docx Paragraph object to add runs to.
        text: Raw text string possibly containing inline markdown.
        registry: ReferenceRegistry for {{ref:*}} substitution.
        params: Parsed params.yaml dict.
        bold_all: If True, all runs are additionally bolded (for table headers).
    """
    code_cfg = params.get("code", {}).get("inline", {})
    code_font = code_cfg.get("font_family", "Consolas")
    code_size_pt = code_cfg.get("font_size_pt", 10.5)
    code_bg = code_cfg.get("background_color", "#F2F2F2")

    from src.renderer.cross_reference import REF_PATTERN

    # Use markdown-it to parse inline tokens from the text string
    _md = MarkdownIt()
    tokens = _md.parse(text)
    # Get inline children from the first inline token
    children = []
    for t in tokens:
        if t.type == "inline" and t.children:
            children = t.children
            break

    if not children:
        # Fallback: add as plain text
        run = paragraph.add_run(registry.substitute(text))
        if bold_all:
            run.bold = True
        return

    i = 0
    while i < len(children):
        child = children[i]

        if child.type == "code_inline":
            run = paragraph.add_run(child.content)
            run.font.name = code_font
            run.font.size = Pt(code_size_pt)
            _add_run_shading(run, code_bg)
            if bold_all:
                run.bold = True

        elif child.type == "strong_open":
            i += 1
            bold_text = ""
            while i < len(children) and children[i].type != "strong_close":
                if children[i].type == "text":
                    bold_text += children[i].content
                elif children[i].type == "code_inline":
                    # code inside bold
                    run = paragraph.add_run(children[i].content)
                    run.bold = True
                    run.font.name = code_font
                    run.font.size = Pt(code_size_pt)
                    _add_run_shading(run, code_bg)
                    if bold_all:
                        run.bold = True
                    i += 1
                    continue
                i += 1
            if bold_text:
                run = paragraph.add_run(bold_text)
                run.bold = True
                if bold_all:
                    run.bold = True

        elif child.type == "em_open":
            i += 1
            em_text = ""
            while i < len(children) and children[i].type != "em_close":
                if children[i].type == "text":
                    em_text += children[i].content
                i += 1
            if em_text:
                run = paragraph.add_run(em_text)
                run.italic = True
                if bold_all:
                    run.bold = True

        elif child.type == "text":
            resolved = registry.substitute(child.content)
            if REF_PATTERN.search(child.content):
                # Render refs as anchor hyperlinks
                last_end = 0
                for m in REF_PATTERN.finditer(child.content):
                    if m.start() > last_end:
                        run = paragraph.add_run(registry.substitute(child.content[last_end:m.start()]))
                        if bold_all:
                            run.bold = True
                    ref_id = m.group(1)
                    display = registry.resolve(ref_id)
                    bm_name = ref_id.replace("-", "_")
                    _add_anchor_hyperlink(paragraph, display, bm_name, params)
                    last_end = m.end()
                if last_end < len(child.content):
                    run = paragraph.add_run(registry.substitute(child.content[last_end:]))
                    if bold_all:
                        run.bold = True
            else:
                run = paragraph.add_run(resolved)
                if bold_all:
                    run.bold = True

        elif child.type == "softbreak":
            paragraph.add_run(" ")

        i += 1

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


def _resolve_image_src(src: str, md_dir: str, assets_dir: str, images_cfg: dict) -> "str | None":
    """
    Resolve an image source string to a local file path.

    Handles four source types:
    - file:// URI       → decoded to a local path
    - http:// / https:// URL → downloaded to assets_dir (cached by URL hash)
    - Relative path     → resolved relative to md_dir, then cwd
    - Absolute path     → used directly

    Args:
        src: The image src attribute from Markdown.
        md_dir: Directory of the source Markdown file (for relative path resolution).
        assets_dir: Directory where downloaded images are persistently saved.
        images_cfg: The 'images' section of params.yaml.

    Returns:
        Local file path string, or None if the image cannot be resolved.
    """
    if not src:
        return None

    # ── file:// URI ──────────────────────────────────────────────────────────
    if src.startswith("file://"):
        parsed = urllib.parse.urlparse(src)
        local = urllib.parse.unquote(parsed.path)
        return local if os.path.isfile(local) else None

    # ── HTTP / HTTPS URL ─────────────────────────────────────────────────────
    if src.startswith("http://") or src.startswith("https://"):
        if not images_cfg.get("download_remote_images", True):
            return None
        try:
            url_hash = hashlib.md5(src.encode()).hexdigest()[:8]
            # Determine extension from URL path (before query string)
            url_path = urllib.parse.urlparse(src).path
            ext = os.path.splitext(url_path)[1].lower() or ".png"
            if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"):
                ext = ".png"
            os.makedirs(assets_dir, exist_ok=True)
            dest = os.path.join(assets_dir, f"image_{url_hash}{ext}")
            if not os.path.isfile(dest):
                urllib.request.urlretrieve(src, dest)
            return dest if os.path.isfile(dest) else None
        except Exception:
            return None

    # ── Relative path ────────────────────────────────────────────────────────
    if not os.path.isabs(src):
        if md_dir:
            candidate = os.path.join(md_dir, src)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
        if os.path.isfile(src):
            return os.path.abspath(src)
        return None

    # ── Absolute path ────────────────────────────────────────────────────────
    return src if os.path.isfile(src) else None


def _insert_image_paragraph(doc, local_path: str, max_width_cm: float):
    """Add a centered paragraph containing the image at local_path."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(local_path, width=Inches(max_width_cm / 2.54))
    return p


def _render_image(doc, token, counter, registry, bm_mgr, params, md_dir="", assets_dir="assets"):
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
        local_path = _resolve_image_src(src, md_dir, assets_dir, images_cfg)
        if local_path:
            try:
                _insert_image_paragraph(doc, local_path, max_width_cm)
                image_inserted = True
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
            # Clear default empty paragraph text, then render with inline code support
            cell.paragraphs[0].clear()
            _render_text_to_paragraph(
                cell.paragraphs[0], cell_text.strip(), registry, params,
                bold_all=is_header
            )

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


def _render_tokens(doc, tokens, params, counter, registry, bm_mgr, md_dir="", assets_dir="assets"):
    """Walk through markdown-it tokens and render to docx."""
    list_level = 0
    in_list = False
    list_type = "bullet"
    heading_path = [0, 0, 0, 0, 0, 0]  # H1–H6 counters
    _graphviz_count = 0
    _mermaid_count = 0

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
                                _render_image(doc, child, counter, registry, bm_mgr, params, md_dir=md_dir, assets_dir=assets_dir)
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
            style = "List Bullet" if list_type == "bullet" else "List Number"
            if list_level > 1:
                styled = f"{style} {list_level}"
                if styled not in doc.styles:
                    styled = style
                style = styled
            p = doc.add_paragraph()
            p.style = doc.styles[style]
            _render_text_to_paragraph(p, content, registry, params)

        # ── Tables ──
        elif token.type == "table_open":
            headers, rows, end_idx = _parse_table_tokens(tokens, i)
            _render_table(doc, {"headers": headers, "rows": rows}, counter, registry, bm_mgr, params)
            i = end_idx

        # ── Code Blocks / Diagrams ──
        elif token.type == "fence":
            lang = (token.info or "").strip().lower().split()[0] if token.info else ""

            # ── Graphviz diagram ──────────────────────────────────────────────
            if lang in ("graphviz", "dot"):
                _graphviz_count += 1
                img_path = render_graphviz(token.content, assets_dir, _graphviz_count)
                images_cfg = params.get("images", {})
                max_width_cm = images_cfg.get("max_width_cm", 15.5)
                if img_path and os.path.isfile(img_path):
                    try:
                        _insert_image_paragraph(doc, img_path, max_width_cm)
                    except Exception:
                        p = doc.add_paragraph()
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        run = p.add_run(f"[Graphviz 圖表 {_graphviz_count}: 無法嵌入]")
                        run.font.size = Pt(10)
                        run.italic = True
                else:
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run(f"[Graphviz 圖表 {_graphviz_count}: 需安裝 graphviz 或 dot CLI]")
                    run.font.size = Pt(10)
                    run.italic = True

            # ── Mermaid diagram ───────────────────────────────────────────────
            elif lang == "mermaid":
                _mermaid_count += 1
                img_path = render_mermaid(token.content, assets_dir, _mermaid_count)
                images_cfg = params.get("images", {})
                max_width_cm = images_cfg.get("max_width_cm", 15.5)
                if img_path and os.path.isfile(img_path):
                    try:
                        _insert_image_paragraph(doc, img_path, max_width_cm)
                    except Exception:
                        p = doc.add_paragraph()
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        run = p.add_run(f"[Mermaid 圖表 {_mermaid_count}: 無法嵌入]")
                        run.font.size = Pt(10)
                        run.italic = True
                else:
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run(f"[Mermaid 圖表 {_mermaid_count}: 需安裝 mmdc (npm i -g @mermaid-js/mermaid-cli)]")
                    run.font.size = Pt(10)
                    run.italic = True

            # ── Regular code block ────────────────────────────────────────────
            else:
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


def _extract_h1_title(tokens):
    """
    Extract the text of the first H1 heading from a markdown-it token list.

    This is used to set the document title on the cover page, so that the
    cover title reflects the actual document heading rather than params.yaml.

    Returns:
        The H1 text string, or None if no H1 is found.
    """
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "heading_open" and t.tag == "h1":
            i += 1
            while i < len(tokens) and tokens[i].type != "heading_close":
                if tokens[i].type == "inline":
                    return tokens[i].content.strip()
                i += 1
        i += 1
    return None


def render_docx(md_text, params, output_path, md_dir="", assets_dir=None):
    """
    Render normalized markdown text to a docx file.

    Uses a two-pass approach:
      Pass 1 (_pre_scan_references): scan all elements to build the reference map
      Pass 2 (_render_tokens): actual docx rendering with all {{ref:*}} resolved

    Args:
        md_text: Normalized markdown string.
        params: Parsed params.yaml dict.
        output_path: Destination path for the .docx file.
        md_dir: Directory of the source Markdown file, used to resolve relative
                image paths. Defaults to current working directory.
        assets_dir: Directory for saving downloaded images and rendered diagrams.
                    Defaults to 'assets/' next to output_path.

    Returns:
        output_path
    """
    if assets_dir is None:
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "assets")

    doc = Document()
    md = MarkdownIt().enable("table")
    tokens = md.parse(md_text)

    # Pass 1: pre-scan to build full reference map (enables forward references)
    registry = _pre_scan_references(tokens, params)

    # Pass 2: actual render with all references pre-resolved
    counter = CaptionCounter()
    bm_mgr = BookmarkManager(params)

    h1_title = _extract_h1_title(tokens)
    render_cover(doc, params, h1_title=h1_title)
    render_toc(doc, params)
    _render_tokens(doc, tokens, params, counter, registry, bm_mgr, md_dir=md_dir, assets_dir=assets_dir)

    doc.save(output_path)
    return output_path
