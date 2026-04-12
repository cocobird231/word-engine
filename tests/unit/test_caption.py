"""
Unit tests for the caption and numbering module.

Tests cover: flat mode, chapter mode, chapter separator, figure/table captions,
counter reset per chapter, prefix customisation, and disabled captions.
"""
import pytest
from docx import Document
from src.renderer.caption import CaptionCounter, add_figure_caption, add_table_caption


# ── CaptionCounter ────────────────────────────────────────────────────────

class TestCaptionCounterFlat:
    def test_flat_figure_increments(self):
        c = CaptionCounter()
        assert c.next_figure(mode="flat") == "1"
        assert c.next_figure(mode="flat") == "2"
        assert c.next_figure(mode="flat") == "3"

    def test_flat_table_increments(self):
        c = CaptionCounter()
        assert c.next_table(mode="flat") == "1"
        assert c.next_table(mode="flat") == "2"

    def test_flat_figure_and_table_independent(self):
        c = CaptionCounter()
        c.next_figure(mode="flat")
        assert c.next_table(mode="flat") == "1"

    def test_flat_figure_starts_at_1(self):
        c = CaptionCounter()
        assert c.next_figure(mode="flat") == "1"


class TestCaptionCounterChapter:
    def test_chapter_format(self):
        c = CaptionCounter()
        c.advance_chapter()  # ch = 1
        assert c.next_figure(mode="chapter") == "1-1"
        assert c.next_figure(mode="chapter") == "1-2"

    def test_chapter_resets_on_advance(self):
        c = CaptionCounter()
        c.advance_chapter()  # ch = 1
        c.next_figure(mode="chapter")  # 1-1
        c.advance_chapter()  # ch = 2, reset index
        assert c.next_figure(mode="chapter") == "2-1"

    def test_chapter_separator_custom(self):
        c = CaptionCounter()
        c.advance_chapter()
        assert c.next_figure(mode="chapter", separator=".") == "1.1"

    def test_table_chapter_mode(self):
        c = CaptionCounter()
        c.advance_chapter()
        assert c.next_table(mode="chapter") == "1-1"
        c.advance_chapter()
        assert c.next_table(mode="chapter") == "2-1"

    def test_no_chapter_advance_defaults_to_1(self):
        c = CaptionCounter()
        # If no H1 was seen, chapter defaults to 1
        result = c.next_figure(mode="chapter")
        assert result.startswith("1-")


# ── add_figure_caption ────────────────────────────────────────────────────

def _fig_params(**overrides):
    p = {
        "images": {
            "insert_caption": True,
            "caption_prefix": "圖",
            "numbering_mode": "flat",
            "chapter_separator": "-",
            "caption_position": "below",
        }
    }
    p["images"].update(overrides)
    return p


class TestAddFigureCaption:
    def test_caption_added_to_doc(self):
        doc = Document()
        c = CaptionCounter()
        add_figure_caption(doc, "測試圖片", c, _fig_params())
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert any("圖 1" in t for t in texts)

    def test_caption_includes_alt_text(self):
        doc = Document()
        c = CaptionCounter()
        add_figure_caption(doc, "系統架構圖", c, _fig_params())
        combined = " ".join(p.text for p in doc.paragraphs)
        assert "系統架構圖" in combined

    def test_caption_flat_numbering(self):
        doc = Document()
        c = CaptionCounter()
        add_figure_caption(doc, "A", c, _fig_params())
        add_figure_caption(doc, "B", c, _fig_params())
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert any("圖 1" in t for t in texts)
        assert any("圖 2" in t for t in texts)

    def test_caption_chapter_numbering(self):
        from docx.oxml.ns import qn
        doc = Document()
        c = CaptionCounter()
        c.advance_chapter()  # ch = 1
        p = add_figure_caption(doc, "A", c, _fig_params(numbering_mode="chapter"))
        # SEQ field uses instrText, so check XML directly
        full_text = p.text  # includes placeholder runs
        instr_texts = [e.text for e in p._p.iter() if e.tag == qn("w:instrText")]
        # Check: chapter prefix in text, SEQ field present, and chapter-specific seq name
        assert "圖 1-" in full_text
        assert any("SEQ" in (t or "") for t in instr_texts)

    def test_caption_disabled(self):
        doc = Document()
        c = CaptionCounter()
        add_figure_caption(doc, "X", c, _fig_params(insert_caption=False))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert not any("圖" in t for t in texts)

    def test_caption_custom_prefix(self):
        doc = Document()
        c = CaptionCounter()
        add_figure_caption(doc, "X", c, _fig_params(caption_prefix="Fig"))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert any("Fig 1" in t for t in texts)


# ── add_table_caption ─────────────────────────────────────────────────────

def _tbl_params(**overrides):
    p = {
        "tables": {
            "caption_enabled": True,
            "caption_prefix": "表",
            "numbering_mode": "flat",
            "chapter_separator": "-",
            "caption_position": "above",
        }
    }
    p["tables"].update(overrides)
    return p


class TestAddTableCaption:
    def test_table_caption_added(self):
        doc = Document()
        c = CaptionCounter()
        add_table_caption(doc, "測試表格", c, _tbl_params())
        combined = " ".join(p.text for p in doc.paragraphs if p.text.strip())
        assert "表 1" in combined

    def test_table_caption_flat_increments(self):
        doc = Document()
        c = CaptionCounter()
        add_table_caption(doc, "", c, _tbl_params())
        add_table_caption(doc, "", c, _tbl_params())
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert any("表 1" in t for t in texts)
        assert any("表 2" in t for t in texts)

    def test_table_caption_chapter_mode(self):
        from docx.oxml.ns import qn
        doc = Document()
        c = CaptionCounter()
        c.advance_chapter()
        p = add_table_caption(doc, "", c, _tbl_params(numbering_mode="chapter"))
        # SEQ field: check that chapter prefix and SEQ field are present
        assert "表 1-" in p.text
        instr_texts = [e.text for e in p._p.iter() if e.tag == qn("w:instrText")]
        assert any("SEQ" in (t or "") for t in instr_texts)

    def test_table_caption_disabled(self):
        doc = Document()
        c = CaptionCounter()
        add_table_caption(doc, "X", c, _tbl_params(caption_enabled=False))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert not any("表" in t for t in texts)
