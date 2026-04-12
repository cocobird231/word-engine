"""
Word Engine - Caption and Numbering Module (Phase 2 + Phase 3)

Generates figure and table caption paragraphs with:

Phase 2: Static text numbering (e.g., "圖 1 描述")
Phase 3: Word SEQ field numbering (e.g., "圖 {SEQ Figure} 描述")
  - SEQ fields auto-update when F9 / UNO field update runs
  - Each caption is wrapped with a bookmark for REF field targeting

Numbering modes (controlled by params.yaml):
  flat:    Sequential within the document   → 圖 1, 圖 2, 表 1, 表 2
  chapter: Prefixed with H2 chapter number → 圖 1-1, 圖 2-1

Chapter mode with SEQ fields:
  - Full chapter-aware SEQ requires STYLEREF + SEQ combination which relies
    on Word heading styles being correctly mapped
  - Phase 3 MVP: flat SEQ field (chapter number prefix is static text)
  - e.g., chapter mode output: "圖 2-{SEQ Figure_Ch2}"
"""
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from src.renderer.seq_field import insert_seq_caption


# ── SEQ identifier names ─────────────────────────────────────────────────
SEQ_FIGURE = "Figure"
SEQ_TABLE = "Table"


class CaptionCounter:
    """
    Tracks display numbers for figures and tables.

    Used alongside SEQ fields: CaptionCounter tracks the preview number
    shown as placeholder in the SEQ field (displayed before field update),
    and as the bookmark suffix for REF targeting.
    """

    def __init__(self):
        self._chapter = 0
        self._figure = 0
        self._table = 0
        self._figure_in_ch = 0
        self._table_in_ch = 0

    def advance_chapter(self):
        """Call when a heading at caption_chapter_level is encountered."""
        self._chapter += 1
        self._figure_in_ch = 0
        self._table_in_ch = 0

    def next_figure(self, mode="flat", separator="-"):
        """Increment and return the next figure display number string."""
        self._figure += 1
        self._figure_in_ch += 1
        if mode == "chapter":
            ch = self._chapter if self._chapter > 0 else 1
            return f"{ch}{separator}{self._figure_in_ch}"
        return str(self._figure)

    def peek_next_figure(self, mode="flat", separator="-"):
        """Preview next figure number without incrementing."""
        next_fig = self._figure + 1
        next_fig_ch = self._figure_in_ch + 1
        if mode == "chapter":
            ch = self._chapter if self._chapter > 0 else 1
            return f"{ch}{separator}{next_fig_ch}"
        return str(next_fig)

    def next_table(self, mode="flat", separator="-"):
        """Increment and return the next table display number string."""
        self._table += 1
        self._table_in_ch += 1
        if mode == "chapter":
            ch = self._chapter if self._chapter > 0 else 1
            return f"{ch}{separator}{self._table_in_ch}"
        return str(self._table)

    def peek_next_table(self, mode="flat", separator="-"):
        """Preview next table number without incrementing."""
        next_tbl = self._table + 1
        next_tbl_ch = self._table_in_ch + 1
        if mode == "chapter":
            ch = self._chapter if self._chapter > 0 else 1
            return f"{ch}{separator}{next_tbl_ch}"
        return str(next_tbl)


def add_figure_caption(doc, alt_text, counter, params, bookmark_id=None, bookmark_name=None):
    """
    Add a figure caption paragraph with a Word SEQ field.

    Phase 3: Uses SEQ field for auto-updatable numbering.
    Falls back to static text if insert_caption is disabled.

    Args:
        doc: python-docx Document.
        alt_text: Alt text or description for the figure.
        counter: CaptionCounter instance.
        params: Parsed params.yaml dict.
        bookmark_id: Unique bookmark ID for REF targeting (optional).
        bookmark_name: Bookmark name for REF targeting (optional).

    Returns:
        The added caption paragraph, or None if disabled.
    """
    images_cfg = params.get("images", {})
    if not images_cfg.get("insert_caption", True):
        return None

    prefix = images_cfg.get("caption_prefix", "圖")
    mode = images_cfg.get("numbering_mode", "flat")
    separator = images_cfg.get("chapter_separator", "-")

    display_num = counter.next_figure(mode=mode, separator=separator)

    # For chapter mode, prefix the chapter number as static text before SEQ field
    if mode == "chapter" and "-" in display_num:
        ch_num, seq_num = display_num.split("-", 1)
        # Use chapter-specific SEQ name to get per-chapter numbering
        seq_name = f"Figure_Ch{ch_num}"
        display_placeholder = seq_num
        full_prefix = f"{prefix} {ch_num}-"
    else:
        seq_name = SEQ_FIGURE
        display_placeholder = display_num
        full_prefix = prefix

    # Generate bookmark name if not provided
    if bookmark_name is None:
        bookmark_name = f"fig_{display_num.replace('-', '_')}"
    if bookmark_id is None:
        bookmark_id = abs(hash(bookmark_name)) % 100000

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Apply caption style
    from docx.shared import Pt
    insert_seq_caption(
        paragraph=p,
        prefix=full_prefix,
        alt_text=alt_text or "",
        seq_name=seq_name,
        display_num=display_placeholder,
        bookmark_id=bookmark_id,
        bookmark_name=bookmark_name,
    )

    # Apply font sizing to all runs in paragraph
    for run in p.runs:
        if run.font.size is None:
            run.font.size = Pt(10.5)

    return p


def add_table_caption(doc, caption_text_raw, counter, params,
                      bookmark_id=None, bookmark_name=None, position="above"):
    """
    Add a table caption paragraph with a Word SEQ field.

    Phase 3: Uses SEQ field for auto-updatable numbering.

    Args:
        doc: python-docx Document.
        caption_text_raw: Raw description text for the table.
        counter: CaptionCounter instance.
        params: Parsed params.yaml dict.
        bookmark_id: Unique bookmark ID for REF targeting (optional).
        bookmark_name: Bookmark name for REF targeting (optional).
        position: "above" or "below" (semantics only, caller decides placement).

    Returns:
        The added caption paragraph, or None if disabled.
    """
    tables_cfg = params.get("tables", {})
    if not tables_cfg.get("caption_enabled", True):
        return None

    prefix = tables_cfg.get("caption_prefix", "表")
    mode = tables_cfg.get("numbering_mode", "flat")
    separator = tables_cfg.get("chapter_separator", "-")

    display_num = counter.next_table(mode=mode, separator=separator)

    if mode == "chapter" and "-" in display_num:
        ch_num, seq_num = display_num.split("-", 1)
        seq_name = f"Table_Ch{ch_num}"
        display_placeholder = seq_num
        full_prefix = f"{prefix} {ch_num}-"
    else:
        seq_name = SEQ_TABLE
        display_placeholder = display_num
        full_prefix = prefix

    if bookmark_name is None:
        bookmark_name = f"tbl_{display_num.replace('-', '_')}"
    if bookmark_id is None:
        bookmark_id = abs(hash(bookmark_name)) % 100000

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    insert_seq_caption(
        paragraph=p,
        prefix=full_prefix,
        alt_text=caption_text_raw or "",
        seq_name=seq_name,
        display_num=display_placeholder,
        bookmark_id=bookmark_id,
        bookmark_name=bookmark_name,
    )

    for run in p.runs:
        if run.font.size is None:
            run.font.size = Pt(10.5)

    return p
