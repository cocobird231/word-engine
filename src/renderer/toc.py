"""
Word Engine - Table of Contents Renderer (Phase 2)

Inserts a TOC field into the document using raw XML.
The generated TOC is a **Word-updatable field** (not static text):
- Word/LibreOffice will show "TOC field" until the document is opened and
  fields are updated (F9 in Word, or handled by UNO post-processor in Phase 3).
- The TOC will be populated with real headings after field update.

Phase 2 implementation:
  - Inserts `TOC \\o "1-N"` field code (standard Word TOC syntax)
  - Optionally with `\\h` for hyperlinks
  - Title paragraph inserted above the TOC field
  - Optional page break before TOC
  - Does NOT auto-update fields (requires UNO in Phase 3 or manual F9 in Word)

Params controlled by params.yaml toc section:
  enabled: bool
  title: str (TOC section title, e.g. "目錄")
  levels: int (heading levels to include, 1-6)
  use_hyperlinks: bool (add \\h flag for clickable TOC entries)
  page_break_before: bool
"""
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from lxml import etree


def _make_toc_field(levels=3, use_hyperlinks=True):
    """
    Build the raw OOXML for a TOC field instruction.

    The result is a <w:p> element containing a TOC field using
    the standard Word field code: `TOC \\o "1-{levels}" [\\h]`

    Args:
        levels: Number of heading levels to include (1–6).
        use_hyperlinks: Whether to add \\h flag for hyperlinked entries.

    Returns:
        An lxml element (w:p) containing the TOC field.
    """
    # Build field instruction string
    field_instr = f'TOC \\\\o "1-{levels}"'
    if use_hyperlinks:
        field_instr += " \\\\h"

    # <w:p>
    p = OxmlElement("w:p")

    # <w:pPr> — optional: set style to TOC 1 (Word style for TOC)
    pPr = OxmlElement("w:pPr")
    pStyle = OxmlElement("w:pStyle")
    pStyle.set(qn("w:val"), "TOC1")
    pPr.append(pStyle)
    p.append(pPr)

    # <w:r><w:fldChar type="begin"/>
    r_begin = OxmlElement("w:r")
    fldChar_begin = OxmlElement("w:fldChar")
    fldChar_begin.set(qn("w:fldCharType"), "begin")
    r_begin.append(fldChar_begin)
    p.append(r_begin)

    # <w:r><w:instrText> TOC ... </w:instrText>
    r_instr = OxmlElement("w:r")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = field_instr
    r_instr.append(instrText)
    p.append(r_instr)

    # <w:r><w:fldChar type="separate"/>
    r_sep = OxmlElement("w:r")
    fldChar_sep = OxmlElement("w:fldChar")
    fldChar_sep.set(qn("w:fldCharType"), "separate")
    r_sep.append(fldChar_sep)
    p.append(r_sep)

    # <w:r> placeholder text (shown before field is updated)
    r_placeholder = OxmlElement("w:r")
    rPr_placeholder = OxmlElement("w:rPr")
    noProof = OxmlElement("w:noProof")
    rPr_placeholder.append(noProof)
    r_placeholder.append(rPr_placeholder)
    t = OxmlElement("w:t")
    t.text = "[目錄將在更新欄位後顯示 (Word: F9 / LibreOffice: Ctrl+A, F9)]"
    r_placeholder.append(t)
    p.append(r_placeholder)

    # <w:r><w:fldChar type="end"/>
    r_end = OxmlElement("w:r")
    fldChar_end = OxmlElement("w:fldChar")
    fldChar_end.set(qn("w:fldCharType"), "end")
    r_end.append(fldChar_end)
    p.append(r_end)

    return p


def render_toc(doc, params):
    """
    Insert a TOC section into the document after the cover.

    Args:
        doc: python-docx Document object.
        params: Parsed params.yaml dict.
    """
    toc_cfg = params.get("toc", {})

    if not toc_cfg.get("enabled", True):
        return

    page_break_before = toc_cfg.get("page_break_before", True)
    title = toc_cfg.get("title", "目錄")
    levels = min(max(int(toc_cfg.get("levels", 3)), 1), 6)
    use_hyperlinks = toc_cfg.get("use_hyperlinks", True)

    # ── Optional page break ─────────────────────────────────────────────
    if page_break_before:
        doc.add_page_break()

    # ── TOC Title ────────────────────────────────────────────────────────
    if title:
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p_title.add_run(title)
        run.bold = True
        run.font.size = Pt(16)

    # ── TOC Field ────────────────────────────────────────────────────────
    toc_field = _make_toc_field(levels=levels, use_hyperlinks=use_hyperlinks)
    doc.element.body.append(toc_field)

    # ── Page break after TOC ─────────────────────────────────────────────
    doc.add_page_break()
