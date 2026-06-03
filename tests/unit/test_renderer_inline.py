"""
Unit tests for Phase 3 bold/italic/inline code rendering.

Tests verify actual docx run properties, not just text content.
"""
import pytest
from docx import Document
from src.renderer.renderer import render_docx


def _params():
    return {
        "cover": {"enabled": False},
        "toc": {"enabled": False},
        "images": {"insert_caption": False, "download_remote_images": False},
        "tables": {"caption_enabled": False},
        "cross_references": {},
        "code": {
            "block": {"font_family": "Consolas", "font_size_pt": 10.5,
                      "background_color": "#F2F2F2", "indent_left_cm": 0.5},
            "inline": {"font_family": "Consolas", "font_size_pt": 10.5,
                       "background_color": "#F2F2F2"}
        }
    }


class TestBoldRendering:
    def test_bold_in_paragraph(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\nThis is **bold text** here.\n", _params(), out)
        doc = Document(out)
        for p in doc.paragraphs:
            if "bold text" in p.text:
                bold_runs = [r for r in p.runs if r.bold and "bold text" in r.text]
                assert bold_runs, "No bold run found for **bold text**"
                return
        pytest.fail("Paragraph with 'bold text' not found")

    def test_bold_in_list(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\n- **Bold list item**\n", _params(), out)
        doc = Document(out)
        for p in doc.paragraphs:
            if "Bold list item" in p.text:
                bold_runs = [r for r in p.runs if r.bold and r.text.strip()]
                assert bold_runs
                return
        pytest.fail("Bold list item not found")

    def test_bold_in_table_cell(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\n| **Header** | Normal |\n|---|---|\n| A | B |\n", _params(), out)
        doc = Document(out)
        assert len(doc.tables) > 0
        cell = doc.tables[0].rows[0].cells[0]
        has_bold = any(r.bold for p in cell.paragraphs for r in p.runs if r.text.strip())
        assert has_bold, "Bold not found in table cell with **Header**"


class TestItalicRendering:
    def test_italic_in_paragraph(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\nThis is *italic text* here.\n", _params(), out)
        doc = Document(out)
        for p in doc.paragraphs:
            if "italic text" in p.text:
                italic_runs = [r for r in p.runs if r.italic and "italic text" in r.text]
                assert italic_runs, "No italic run found for *italic text*"
                return
        pytest.fail("Paragraph with 'italic text' not found")

    def test_italic_in_list(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\n- *Italic list item*\n", _params(), out)
        doc = Document(out)
        for p in doc.paragraphs:
            if "Italic list item" in p.text:
                italic_runs = [r for r in p.runs if r.italic and r.text.strip()]
                assert italic_runs
                return
        pytest.fail("Italic list item not found")


class TestInlineCodeRendering:
    def test_inline_code_in_paragraph(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\nThis is `inline code` here.\n", _params(), out)
        doc = Document(out)
        for p in doc.paragraphs:
            if "inline code" in p.text:
                code_runs = [r for r in p.runs
                             if r.font.name == "Consolas" and "inline code" in r.text]
                assert code_runs, "No Consolas run for `inline code`"
                return
        pytest.fail("Paragraph with inline code not found")

    def test_inline_code_in_table_cell(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\n| `code_cell` | Normal |\n|---|---|\n| A | B |\n", _params(), out)
        doc = Document(out)
        assert len(doc.tables) > 0
        cell = doc.tables[0].rows[0].cells[0]
        has_code = any(r.font.name == "Consolas"
                       for p in cell.paragraphs for r in p.runs if r.text.strip())
        assert has_code, "Consolas not found in table cell with `code_cell`"


class TestNoRawMarkersInOutput:
    def test_no_bold_markers_in_output(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\n**bold** text\n\n- **list bold**\n", _params(), out)
        doc = Document(out)
        for p in doc.paragraphs:
            assert "**" not in p.text, f"Raw ** found in: {repr(p.text)}"

    def test_no_italic_markers_in_output(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\n*italic* text\n", _params(), out)
        doc = Document(out)
        for p in doc.paragraphs:
            assert "**" not in p.text

    def test_no_backtick_markers_in_output(self, tmp_path):
        out = str(tmp_path / "out.docx")
        render_docx("# T\n\n`code` text\n\n| `cell` | A |\n|---|---|\n", _params(), out)
        doc = Document(out)
        for p in doc.paragraphs:
            assert "`" not in p.text, f"Backtick found in: {repr(p.text)}"
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    assert "`" not in cell.text, f"Backtick found in table cell: {repr(cell.text)}"


class TestNestedListRendering:
    """Nested bullet list inside ordered list should render separately."""

    def test_sub_bullet_in_ordered_list(self, tmp_path):
        out = str(tmp_path / "out.docx")
        md = (
            "# T\n\n"
            "1. Outer item\n"
            "   - Sub bullet A\n"
            "   - Sub bullet B\n"
            "2. Second outer\n"
        )
        render_docx(md, _params(), out)
        doc = Document(out)
        styles = [(p.style.name, p.text) for p in doc.paragraphs if p.text.strip()]
        # Outer should be List Number, inner should be List Bullet
        list_number_items = [t for s, t in styles if s == "List Number"]
        list_bullet_items = [t for s, t in styles if s.startswith("List Bullet")]
        assert len(list_number_items) >= 2, f"Expected >=2 List Number items, got {list_number_items}"
        assert len(list_bullet_items) >= 2, f"Expected >=2 List Bullet items, got {list_bullet_items}"
        # Bullet items should NOT be numbered like "6.2" etc.
        for t in list_bullet_items:
            assert not any(c.isdigit() and '.' in t[:5] for c in t[:5]), \
                f"Bullet item looks numbered: {repr(t)}"
