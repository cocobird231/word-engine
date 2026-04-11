"""
Unit tests for the cross-reference module.

Tests cover: ReferenceRegistry (figure/table/heading registration + substitution),
BookmarkManager (ID generation, naming convention), and integration via renderer.
"""
import pytest
from docx import Document
from src.renderer.cross_reference import (
    ReferenceRegistry, BookmarkManager, add_bookmark, REF_PATTERN
)


def _xref_params(style="ieee"):
    return {
        "cross_references": {
            "enabled": True,
            "style": style,
            "figure_reference_format": {
                "ieee": "圖 {number}",
                "apa": "Figure {number}",
            },
            "table_reference_format": {
                "ieee": "表 {number}",
                "apa": "Table {number}",
            },
            "heading_reference_format": {
                "ieee": "第 {number} 節",
                "apa": "Section {number}",
            },
            "bookmark_prefix_figure": "fig_",
            "bookmark_prefix_table": "tbl_",
            "bookmark_prefix_heading": "sec_",
        }
    }


class TestRefPattern:
    def test_pattern_matches_ref(self):
        m = REF_PATTERN.search("如 {{ref:fig-1}} 所示")
        assert m is not None
        assert m.group(1) == "fig-1"

    def test_pattern_no_match(self):
        assert not REF_PATTERN.search("no reference here")

    def test_pattern_multiple_matches(self):
        matches = REF_PATTERN.findall("{{ref:fig-1}} and {{ref:tbl-2}}")
        assert matches == ["fig-1", "tbl-2"]


class TestReferenceRegistryFigure:
    def test_register_figure_flat(self):
        r = ReferenceRegistry(_xref_params())
        ref_id = r.register_figure("1")
        assert ref_id == "fig-1"
        assert r.resolve("fig-1") == "圖 1"

    def test_register_figure_chapter(self):
        r = ReferenceRegistry(_xref_params())
        ref_id = r.register_figure("2-1")
        assert r.resolve(ref_id) == "圖 2-1"

    def test_register_multiple_figures(self):
        r = ReferenceRegistry(_xref_params())
        r.register_figure("1")
        r.register_figure("2")
        assert r.resolve("fig-1") == "圖 1"
        assert r.resolve("fig-2") == "圖 2"

    def test_apa_style(self):
        r = ReferenceRegistry(_xref_params(style="apa"))
        r.register_figure("1")
        assert r.resolve("fig-1") == "Figure 1"


class TestReferenceRegistryTable:
    def test_register_table(self):
        r = ReferenceRegistry(_xref_params())
        ref_id = r.register_table("1")
        assert ref_id == "tbl-1"
        assert r.resolve("tbl-1") == "表 1"

    def test_register_multiple_tables(self):
        r = ReferenceRegistry(_xref_params())
        r.register_table("1")
        r.register_table("2")
        assert r.resolve("tbl-2") == "表 2"


class TestReferenceRegistryHeading:
    def test_register_h1(self):
        r = ReferenceRegistry(_xref_params())
        ref_id = r.register_heading(1, [1])
        assert ref_id == "sec-1"
        assert r.resolve("sec-1") == "第 1 節"

    def test_register_h2(self):
        r = ReferenceRegistry(_xref_params())
        ref_id = r.register_heading(2, [1, 2])
        assert ref_id == "sec-1-2"
        assert r.resolve("sec-1-2") == "第 1.2 節"


class TestSubstitution:
    def test_substitute_single(self):
        r = ReferenceRegistry(_xref_params())
        r.register_figure("1")
        result = r.substitute("如 {{ref:fig-1}} 所示")
        assert result == "如 圖 1 所示"

    def test_substitute_multiple(self):
        r = ReferenceRegistry(_xref_params())
        r.register_figure("1")
        r.register_table("2")
        result = r.substitute("{{ref:fig-1}} 和 {{ref:tbl-1}}")
        assert "圖 1" in result
        assert "表 2" in result

    def test_unresolved_ref_kept(self):
        r = ReferenceRegistry(_xref_params())
        result = r.substitute("{{ref:nonexistent}}")
        assert "{{ref:nonexistent}}" in result

    def test_has_references(self):
        r = ReferenceRegistry(_xref_params())
        assert r.has_references("see {{ref:fig-1}}")
        assert not r.has_references("no ref here")


class TestBookmarkManager:
    def test_figure_bookmark_name(self):
        bm = BookmarkManager(_xref_params())
        _, name = bm.figure_bookmark(1)
        assert name == "fig_1"

    def test_table_bookmark_name(self):
        bm = BookmarkManager(_xref_params())
        _, name = bm.table_bookmark(3)
        assert name == "tbl_3"

    def test_heading_bookmark_name(self):
        bm = BookmarkManager(_xref_params())
        _, name = bm.heading_bookmark([2, 1])
        assert name == "sec_2_1"

    def test_bookmark_ids_unique(self):
        bm = BookmarkManager(_xref_params())
        id1, _ = bm.figure_bookmark(1)
        id2, _ = bm.figure_bookmark(2)
        assert id1 != id2


class TestAddBookmark:
    def test_bookmark_added_to_paragraph(self):
        doc = Document()
        p = doc.add_paragraph("test")
        add_bookmark(p, 1, "fig_1")
        xml = p._p.xml
        assert "bookmarkStart" in xml
        assert "bookmarkEnd" in xml
        assert "fig_1" in xml


class TestForwardReference:
    """Test that {{ref:fig-1}} in a paragraph BEFORE the figure still resolves."""
    def test_forward_reference_via_renderer(self, tmp_path):
        from src.renderer.renderer import render_docx
        params = {
            "cover": {"enabled": False},
            "toc": {"enabled": False},
            "images": {"insert_caption": True, "caption_prefix": "圖", "numbering_mode": "flat",
                       "chapter_separator": "-", "caption_position": "below",
                       "max_width_cm": 15.5, "download_remote_images": False},
            "tables": {"caption_enabled": True, "caption_prefix": "表", "numbering_mode": "flat",
                       "chapter_separator": "-", "caption_position": "above"},
            **_xref_params(),
        }
        md = "# 章節\n如 {{ref:fig-1}} 所示。\n\n![圖片](fake.png)\n"
        out = str(tmp_path / "out.docx")
        render_docx(md, params, out)
        from docx import Document
        doc = Document(out)
        texts = [p.text for p in doc.paragraphs]
        assert any("圖 1" in t for t in texts)
        # Make sure the unresolved form is NOT in output
        assert not any("{{ref:fig-1}}" in t for t in texts)
