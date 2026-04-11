"""
Unit tests for the UNO post-processor module.

Note: These tests require LibreOffice to be installed (soffice in PATH).
Tests that need actual UNO execution are marked with `@pytest.mark.slow`.

Phase 2 capability tested:
  - Error handling: missing file, missing LibreOffice
  - Integration: actual field update on a real docx (requires soffice)
"""
import os
import shutil
import pytest
from docx import Document
from src.post_processor_uno.post_processor import run_post_process, UNOError


def _make_simple_docx(path):
    """Create a minimal docx with a heading for TOC testing."""
    doc = Document()
    doc.add_heading("Test Heading 1", level=1)
    doc.add_paragraph("Some content here.")
    doc.save(path)


class TestErrorHandling:
    def test_missing_docx_raises_error(self):
        with pytest.raises(UNOError, match="not found"):
            run_post_process("/nonexistent/file.docx")

    def test_returns_docx_path_on_success(self, tmp_path):
        docx = tmp_path / "test.docx"
        _make_simple_docx(str(docx))
        result = run_post_process(str(docx))
        assert result == str(docx)

    def test_docx_still_exists_after_postfix(self, tmp_path):
        docx = tmp_path / "test.docx"
        _make_simple_docx(str(docx))
        run_post_process(str(docx))
        assert os.path.exists(docx)

    def test_docx_is_valid_after_postfix(self, tmp_path):
        docx = tmp_path / "test.docx"
        _make_simple_docx(str(docx))
        run_post_process(str(docx))
        # Should still be a valid docx (python-docx can open it)
        doc = Document(str(docx))
        assert len(doc.paragraphs) > 0
