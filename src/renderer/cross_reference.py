"""
Word Engine - Cross-Reference Module (Phase 2)

Provides a two-pass reference resolution system for figures, tables, and headings.

## In-Text Reference Syntax
Use `{{ref:ID}}` in Markdown to reference a figure, table, or heading:

    {{ref:fig-1}}   → "圖 1"    (or "圖 2-1" in chapter mode)
    {{ref:tbl-1}}   → "表 1"
    {{ref:sec-1}}   → "第 1 節"
    {{ref:sec-1-2}} → "第 1.2 節"

## Auto-ID Assignment (done by ReferenceRegistry during first pass)
Elements get auto-assigned IDs based on their encounter order:
    Figure  1 → fig-1
    Figure  2 → fig-2
    Table   1 → tbl-1
    Heading H1 #1 → sec-1
    Heading H2 #1.1 → sec-1-1

## Phase 2 Implementation
- Static text substitution: {{ref:ID}} is replaced with display label text
- Bookmarks added to caption/heading paragraphs (for future Word REF fields)
- Does NOT produce Word REF fields (Phase 3 upgrade)
- Text substitution happens at paragraph render time

## Capability Boundary
  DONE:    Two-pass reference map, static label substitution, bookmark stubs
  NOT YET: Word-updatable REF fields (Phase 3 requires UNO or raw OOXML)
"""
import re
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ── Reference marker pattern ──────────────────────────────────────────────
REF_PATTERN = re.compile(r"\{\{ref:([a-zA-Z0-9\-_]+)\}\}")


class ReferenceRegistry:
    """
    Maintains a mapping of reference IDs to their display labels.

    Usage:
        registry = ReferenceRegistry(params)
        # During first pass:
        registry.register_figure(counter_num, chapter=None)  → returns "fig-1"
        registry.register_table(counter_num)  → returns "tbl-1"
        registry.register_heading(level, heading_path)  → returns "sec-1-2"
        # During render:
        label = registry.resolve("fig-1")  → "圖 1"
        text = registry.substitute("請見 {{ref:fig-1}}")  → "請見 圖 1"
    """

    def __init__(self, params):
        self.params = params
        self._map = {}  # id → display_label
        self._fig_seq = 0
        self._tbl_seq = 0
        self._heading_counters = [0] * 7  # index 1–6 for H1–H6

        xref_cfg = params.get("cross_references", {})
        style = xref_cfg.get("style", "ieee")
        fig_fmt = xref_cfg.get("figure_reference_format", {}).get(style, "圖 {number}")
        tbl_fmt = xref_cfg.get("table_reference_format", {}).get(style, "表 {number}")
        sec_fmt = xref_cfg.get("heading_reference_format", {}).get(style, "第 {number} 節")

        self._fig_fmt = fig_fmt
        self._tbl_fmt = tbl_fmt
        self._sec_fmt = sec_fmt

    def _fig_id(self, seq):
        return f"fig-{seq}"

    def _tbl_id(self, seq):
        return f"tbl-{seq}"

    def _sec_id(self, path):
        """Convert heading path (e.g. [1,2,0,0,0,0]) to sec-1-2."""
        parts = [str(n) for n in path if n > 0]
        return "sec-" + "-".join(parts) if parts else "sec-0"

    def register_figure(self, display_number):
        """
        Register a figure with its display number string.

        Args:
            display_number: String like "1" or "2-1"

        Returns:
            The auto-assigned ID string (e.g. "fig-1")
        """
        self._fig_seq += 1
        ref_id = self._fig_id(self._fig_seq)
        label = self._fig_fmt.replace("{number}", display_number)
        self._map[ref_id] = label
        return ref_id

    def register_table(self, display_number):
        """
        Register a table with its display number string.

        Returns:
            The auto-assigned ID string (e.g. "tbl-1")
        """
        self._tbl_seq += 1
        ref_id = self._tbl_id(self._tbl_seq)
        label = self._tbl_fmt.replace("{number}", display_number)
        self._map[ref_id] = label
        return ref_id

    def register_heading(self, level, heading_path):
        """
        Register a heading with its hierarchical path.

        Args:
            level: H level (1–6)
            heading_path: List[int] of counters, e.g. [2, 1, 0, 0, 0, 0] → 2.1

        Returns:
            The auto-assigned ID string (e.g. "sec-2-1")
        """
        ref_id = self._sec_id(heading_path)
        number = ".".join(str(n) for n in heading_path if n > 0)
        label = self._sec_fmt.replace("{number}", number)
        self._map[ref_id] = label
        return ref_id

    def resolve(self, ref_id):
        """
        Look up a reference ID and return its display label.

        Returns:
            Display label string, or the original {{ref:ID}} if not found.
        """
        return self._map.get(ref_id, f"{{{{ref:{ref_id}}}}}")

    def substitute(self, text):
        """
        Replace all {{ref:ID}} markers in text with their resolved labels.

        Args:
            text: Input string possibly containing {{ref:ID}} markers.

        Returns:
            String with all resolvable markers substituted.
        """
        def _replace(m):
            return self.resolve(m.group(1))
        return REF_PATTERN.sub(_replace, text)

    def has_references(self, text):
        """Return True if text contains any {{ref:*}} markers."""
        return bool(REF_PATTERN.search(text))


# ── Bookmark helpers ──────────────────────────────────────────────────────

def add_bookmark(paragraph, bookmark_id, bookmark_name):
    """
    Add a Word bookmark to a paragraph element.

    Bookmarks are used as anchor targets for future Word REF fields (Phase 3).

    Args:
        paragraph: python-docx Paragraph object.
        bookmark_id: Unique integer ID for the bookmark (within the document).
        bookmark_name: Bookmark name string (must be unique, no spaces).
    """
    # <w:bookmarkStart w:id="N" w:name="NAME"/>
    bookmark_start = OxmlElement("w:bookmarkStart")
    bookmark_start.set(qn("w:id"), str(bookmark_id))
    bookmark_start.set(qn("w:name"), bookmark_name)
    paragraph._p.insert(0, bookmark_start)

    # <w:bookmarkEnd w:id="N"/>
    bookmark_end = OxmlElement("w:bookmarkEnd")
    bookmark_end.set(qn("w:id"), str(bookmark_id))
    paragraph._p.append(bookmark_end)


class BookmarkManager:
    """
    Generates unique bookmark IDs and names for the document.

    Bookmark naming convention:
        fig_1, fig_2     → figures
        tbl_1, tbl_2     → tables
        sec_1, sec_1_2   → headings
    """

    def __init__(self, params):
        self._counter = 0
        xref_cfg = params.get("cross_references", {})
        self._fig_prefix = xref_cfg.get("bookmark_prefix_figure", "fig_")
        self._tbl_prefix = xref_cfg.get("bookmark_prefix_table", "tbl_")
        self._sec_prefix = xref_cfg.get("bookmark_prefix_heading", "sec_")

    def _next_id(self):
        self._counter += 1
        return self._counter

    def figure_bookmark(self, seq):
        """Return (id, name) for a figure bookmark."""
        return self._next_id(), f"{self._fig_prefix}{seq}"

    def table_bookmark(self, seq):
        """Return (id, name) for a table bookmark."""
        return self._next_id(), f"{self._tbl_prefix}{seq}"

    def heading_bookmark(self, heading_path):
        """Return (id, name) for a heading bookmark."""
        path_str = "_".join(str(n) for n in heading_path if n > 0)
        return self._next_id(), f"{self._sec_prefix}{path_str}"
