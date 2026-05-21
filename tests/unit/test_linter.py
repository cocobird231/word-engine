"""Unit tests for the linter module."""
import pytest
from src.linter.linter import lint_markdown


class TestHeadingChecks:
    def test_valid_headings(self):
        md = "# H1\n## H2\n### H3\n"
        result = lint_markdown(md)
        assert result["errors"] == []

    def test_heading_jump(self):
        md = "# H1\n### H3 skip H2\n"
        result = lint_markdown(md)
        assert any("Heading jump" in e for e in result["errors"])

    def test_empty_heading(self):
        md = "# \n## Valid\n"
        result = lint_markdown(md)
        assert any("Empty heading" in e for e in result["errors"])


class TestCodeFenceChecks:
    def test_closed_fence(self):
        md = "```python\ncode\n```\n"
        result = lint_markdown(md)
        assert result["errors"] == []

    def test_unclosed_fence(self):
        md = "```python\ncode\n"
        result = lint_markdown(md)
        assert any("Unclosed code fence" in e for e in result["errors"])


class TestBlankLines:
    def test_excessive_blanks(self):
        md = "# Title\n\n\n\n\nContent\n"
        result = lint_markdown(md)
        assert any("consecutive blank lines" in w for w in result["warnings"])

    def test_normal_blanks(self):
        md = "# Title\n\nContent\n"
        result = lint_markdown(md)
        assert result["warnings"] == []


class TestCleanMarkdown:
    def test_clean_inline_markdown(self):
        """Clean markdown with inline code and formatting should pass lint."""
        md = "# Title\n\n## Section\n\nParagraph with `code` and **bold** text.\n"
        result = lint_markdown(md)
        assert result["errors"] == []
