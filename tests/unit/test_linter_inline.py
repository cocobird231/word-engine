"""
Unit tests for Phase 3 inline marker lint checks.
"""
import pytest
from src.linter.linter import lint_markdown


class TestInlineCodeLint:
    def test_unclosed_backtick_error(self):
        md = "This has `unclosed code\n"
        result = lint_markdown(md)
        assert any("Unclosed inline code" in e for e in result["errors"])

    def test_closed_backtick_no_error(self):
        md = "This has `closed code` here\n"
        result = lint_markdown(md)
        assert not any("Unclosed inline code" in e for e in result["errors"])

    def test_multiple_closed_backticks(self):
        md = "First `one` and `two` code spans\n"
        result = lint_markdown(md)
        assert not any("Unclosed inline code" in e for e in result["errors"])


class TestBoldLint:
    def test_unclosed_bold_error(self):
        md = "This has **unclosed bold\n"
        result = lint_markdown(md)
        assert any("Unclosed bold marker" in e for e in result["errors"])

    def test_closed_bold_no_error(self):
        md = "This has **closed bold** here\n"
        result = lint_markdown(md)
        assert not any("Unclosed bold marker" in e for e in result["errors"])

    def test_multiple_bold_spans(self):
        md = "**First** and **second** bold\n"
        result = lint_markdown(md)
        assert not any("Unclosed bold marker" in e for e in result["errors"])


class TestItalicLint:
    def test_closed_italic_no_warning(self):
        md = "This has *closed italic* here\n"
        result = lint_markdown(md)
        # No italic warning for properly closed
        italic_warnings = [w for w in result["warnings"] if "italic" in w.lower()]
        assert len(italic_warnings) == 0

    def test_unclosed_italic_warning(self):
        md = "This has *unclosed italic text\n"
        result = lint_markdown(md)
        italic_warnings = [w for w in result["warnings"] if "italic" in w.lower()]
        assert len(italic_warnings) > 0


class TestInlineCheckNotInCodeFence:
    def test_backtick_inside_code_fence_not_flagged(self):
        md = "```python\n`inside fence`\n```\n"
        result = lint_markdown(md)
        # Content inside code fence should not be linted for inline markers
        assert not any("inline code" in e.lower() for e in result["errors"])

    def test_bold_inside_code_fence_not_flagged(self):
        md = "```python\n**not bold** in fence\n```\n"
        result = lint_markdown(md)
        assert not any("bold" in e.lower() for e in result["errors"])


class TestCombinedInlineLint:
    def test_clean_markdown_no_inline_errors(self):
        md = (
            "# Clean Document\n\n"
            "This is **bold** and *italic* and `code` all working.\n\n"
            "## Section\n\n"
            "- **Bold list item**\n"
            "- *Italic item*\n"
            "- `code item`\n"
        )
        result = lint_markdown(md)
        assert result["errors"] == []
        italic_warnings = [w for w in result["warnings"] if "italic" in w.lower()]
        assert len(italic_warnings) == 0
