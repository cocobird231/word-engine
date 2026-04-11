"""Unit tests for the renderer module."""
import os
import pytest
from docx import Document
from src.renderer.renderer import render_docx

def test_render_docx_basic(tmp_path):
    output_path = tmp_path / "test_render.docx"
    md_text = "# H1 Heading\n\nSome paragraph text.\n\n- Item 1\n- Item 2\n\n```python\nprint('hello')\n```\n"
    params = {}
    
    result = render_docx(md_text, params, str(output_path))
    assert result == str(output_path)
    assert os.path.exists(output_path)
    
    # Read back and verify basic content
    doc = Document(output_path)
    text = [p.text for p in doc.paragraphs]
    
    assert "H1 Heading" in text
    assert "Some paragraph text." in text
    assert "Item 1" in text
    assert "print('hello')" in text
