"""
Word Engine - Caption and Numbering Module (Phase 2)

Provides auto-numbering for figures and tables,
and renders their caption paragraphs below/above the element.

Supported numbering modes (controlled by params.yaml):
  flat:    Sequential within the document   → 圖 1, 圖 2, 表 1, 表 2
  chapter: Prefixed with H1 chapter number → 圖 2-1, 圖 2-2, 表 3-1

Phase 2 limitations:
  - chapter mode uses the count of H1 headings seen so far in the token stream
  - Does NOT produce Word SEQ fields (static caption text only)
  - Word SEQ field generation deferred to Phase 3 (requires UNO or OxmlElement)
  - No bookmark/anchor for cross-reference (next phase)

Params sections read:
  images.caption_enabled        bool
  images.caption_prefix         str   (e.g. "圖")
  images.numbering_mode         str   ("flat" or "chapter")
  images.chapter_separator      str   (e.g. "-")
  images.caption_position       str   ("below" or "above")

  tables.caption_enabled        bool
  tables.caption_prefix         str   (e.g. "表")
  tables.numbering_mode         str   ("flat" or "chapter")
  tables.chapter_separator      str   (e.g. "-")
  tables.caption_position       str   ("above" or "below")

  captions.figure_caption.*     style overrides (Phase 3)
  captions.table_caption.*      style overrides (Phase 3)
"""
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


class CaptionCounter:
    """
    Tracks auto-incrementing counters for figures and tables.

    Supports both 'flat' and 'chapter' numbering modes.

    In 'chapter' mode, the caller must call advance_chapter() each time
    an H1 heading is encountered in the document.
    """

    def __init__(self):
        self._chapter = 0       # Current H1 chapter number
        self._figure = 0        # Flat figure counter
        self._table = 0         # Flat table counter
        self._figure_in_ch = 0  # Per-chapter figure counter
        self._table_in_ch = 0   # Per-chapter table counter

    def advance_chapter(self):
        """Call when an H1 heading is rendered. Resets per-chapter counters."""
        self._chapter += 1
        self._figure_in_ch = 0
        self._table_in_ch = 0

    def next_figure(self, mode="flat", separator="-"):
        """
        Return the next figure number string (increments counter).

        Args:
            mode: "flat" → "1" / "2"; "chapter" → "2-1" / "2-2"
            separator: Character between chapter and index (default "-")

        Returns:
            str, e.g. "1" or "2-1"
        """
        self._figure += 1
        self._figure_in_ch += 1
        if mode == "chapter":
            ch = self._chapter if self._chapter > 0 else 1
            return f"{ch}{separator}{self._figure_in_ch}"
        return str(self._figure)

    def peek_next_figure(self, mode="flat", separator="-"):
        """
        Preview what the next figure number will be WITHOUT incrementing the counter.
        Used by the cross-reference registry to pre-register before caption renders.
        """
        next_fig = self._figure + 1
        next_fig_ch = self._figure_in_ch + 1
        if mode == "chapter":
            ch = self._chapter if self._chapter > 0 else 1
            return f"{ch}{separator}{next_fig_ch}"
        return str(next_fig)

    def next_table(self, mode="flat", separator="-"):
        """
        Return the next table number string (increments counter).

        Args:
            mode: "flat" → "1" / "2"; "chapter" → "3-1" / "3-2"
            separator: Character between chapter and index (default "-")

        Returns:
            str, e.g. "1" or "3-1"
        """
        self._table += 1
        self._table_in_ch += 1
        if mode == "chapter":
            ch = self._chapter if self._chapter > 0 else 1
            return f"{ch}{separator}{self._table_in_ch}"
        return str(self._table)

    def peek_next_table(self, mode="flat", separator="-"):
        """
        Preview what the next table number will be WITHOUT incrementing the counter.
        """
        next_tbl = self._table + 1
        next_tbl_ch = self._table_in_ch + 1
        if mode == "chapter":
            ch = self._chapter if self._chapter > 0 else 1
            return f"{ch}{separator}{next_tbl_ch}"
        return str(next_tbl)


def add_figure_caption(doc, alt_text, counter, params):
    """
    Add a figure caption paragraph to the document.

    Args:
        doc: python-docx Document.
        alt_text: Alt text or description for the figure (from Markdown image syntax).
        counter: CaptionCounter instance.
        params: Parsed params.yaml dict.

    Returns:
        The added caption paragraph.
    """
    images_cfg = params.get("images", {})
    if not images_cfg.get("insert_caption", True):
        return None

    prefix = images_cfg.get("caption_prefix", "圖")
    mode = images_cfg.get("numbering_mode", "flat")
    separator = images_cfg.get("chapter_separator", "-")

    num = counter.next_figure(mode=mode, separator=separator)
    caption_text = f"{prefix} {num}"
    if alt_text:
        caption_text += f" {alt_text}"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(caption_text)
    run.font.size = Pt(10.5)
    run.italic = True

    return p


def add_table_caption(doc, caption_text_raw, counter, params, position="above"):
    """
    Add a table caption paragraph to the document.

    Args:
        doc: python-docx Document.
        caption_text_raw: Raw caption description text (e.g. from Markdown table header comment).
        counter: CaptionCounter instance.
        params: Parsed params.yaml dict.
        position: "above" or "below" (only affects semantics; caller decides placement).

    Returns:
        The added caption paragraph, or None if captions disabled.
    """
    tables_cfg = params.get("tables", {})
    if not tables_cfg.get("caption_enabled", True):
        return None

    prefix = tables_cfg.get("caption_prefix", "表")
    mode = tables_cfg.get("numbering_mode", "flat")
    separator = tables_cfg.get("chapter_separator", "-")

    num = counter.next_table(mode=mode, separator=separator)
    caption_text = f"{prefix} {num}"
    if caption_text_raw:
        caption_text += f" {caption_text_raw}"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(caption_text)
    run.font.size = Pt(10.5)
    run.italic = True

    return p
