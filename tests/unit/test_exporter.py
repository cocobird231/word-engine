"""Unit tests for the exporter module."""
import os
import pytest
from src.exporter.exporter import export_pdf, ExportError
from docx import Document

def test_export_pdf_success(tmp_path):
    docx_file = tmp_path / "test_doc.docx"
    pdf_file = tmp_path / "test_doc.pdf"
    
    # Create a minimal docx to export
    doc = Document()
    doc.add_paragraph("Test Export Content")
    doc.save(str(docx_file))
    
    result = export_pdf(str(docx_file), str(pdf_file))
    assert result == str(pdf_file)
    assert os.path.exists(pdf_file)
    assert os.path.getsize(pdf_file) > 0
    
def test_export_nonexistent_docx():
    with pytest.raises(ExportError, match="Source docx file not found"):
        export_pdf("/tmp/nonexistent.docx", "/tmp/out.pdf")
