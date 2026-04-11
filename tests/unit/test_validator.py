"""Unit tests for the validator module."""
import pytest
from src.validator.validator import validate_params, ValidationResult


def _minimal_valid_params():
    """Return a minimal params dict that should pass validation."""
    return {
        "meta": {
            "schema_version": "1.0.0",
            "spec_name": "test",
            "language": "zh-TW",
        },
        "project": {
            "project_id": "TEST001",
            "document_title": "Test Doc",
            "version": "v1.0",
            "status": "draft",
            "confidentiality": "internal",
        },
        "paths": {
            "source_md": "./source.md",
            "output_docx": "./output.docx",
            "output_pdf": "./output.pdf",
        },
        "page": {"size": "A4", "orientation": "portrait"},
        "fonts": {},
        "headings": {},
        "paragraphs": {},
        "colors": {
            "text_primary": "#000000",
            "accent_primary": "#1F4E79",
        },
    }


class TestTopLevel:
    def test_valid_params_pass(self):
        result = validate_params(_minimal_valid_params())
        assert result.is_valid

    def test_missing_meta(self):
        params = _minimal_valid_params()
        del params["meta"]
        result = validate_params(params)
        assert not result.is_valid
        assert any("meta" in e for e in result.errors)

    def test_missing_project(self):
        params = _minimal_valid_params()
        del params["project"]
        result = validate_params(params)
        assert not result.is_valid
        assert any("project" in e for e in result.errors)

    def test_missing_paths(self):
        params = _minimal_valid_params()
        del params["paths"]
        result = validate_params(params)
        assert not result.is_valid
        assert any("paths" in e for e in result.errors)


class TestRequiredFields:
    def test_missing_project_id(self):
        params = _minimal_valid_params()
        del params["project"]["project_id"]
        result = validate_params(params)
        assert not result.is_valid
        assert any("project.project_id" in e for e in result.errors)

    def test_empty_field_warning(self):
        params = _minimal_valid_params()
        params["project"]["document_title"] = ""
        result = validate_params(params)
        assert any("document_title" in w for w in result.warnings)


class TestEnumChecks:
    def test_valid_page_size(self):
        params = _minimal_valid_params()
        result = validate_params(params)
        assert result.is_valid

    def test_invalid_page_size(self):
        params = _minimal_valid_params()
        params["page"]["size"] = "B5"
        result = validate_params(params)
        assert not result.is_valid
        assert any("page.size" in e for e in result.errors)

    def test_invalid_orientation(self):
        params = _minimal_valid_params()
        params["page"]["orientation"] = "diagonal"
        result = validate_params(params)
        assert not result.is_valid
        assert any("page.orientation" in e for e in result.errors)

    def test_invalid_status(self):
        params = _minimal_valid_params()
        params["project"]["status"] = "archived"
        result = validate_params(params)
        assert not result.is_valid
        assert any("project.status" in e for e in result.errors)


class TestColorChecks:
    def test_valid_colors(self):
        params = _minimal_valid_params()
        result = validate_params(params)
        assert result.is_valid

    def test_invalid_hex_color(self):
        params = _minimal_valid_params()
        params["colors"]["text_primary"] = "red"
        result = validate_params(params)
        assert not result.is_valid
        assert any("colors.text_primary" in e for e in result.errors)

    def test_short_hex_color(self):
        params = _minimal_valid_params()
        params["colors"]["text_primary"] = "#FFF"
        result = validate_params(params)
        assert not result.is_valid


class TestEdgeCases:
    def test_non_dict_input(self):
        result = validate_params("not a dict")
        assert not result.is_valid

    def test_none_input(self):
        result = validate_params(None)
        assert not result.is_valid
