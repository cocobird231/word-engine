"""Unit tests for the reporter module."""
import pytest
from src.reporter.reporter import generate_qc_report
from src.validator.validator import ValidationResult


class TestReportGeneration:
    def test_passed_report(self):
        lint = {"errors": [], "warnings": []}
        val = ValidationResult()
        report = generate_qc_report(lint, val)
        assert "PASSED" in report
        assert "No lint errors" in report
        assert "No validation errors" in report

    def test_failed_report_lint_error(self):
        lint = {"errors": ["Line 5: Heading jump from H1 to H3"], "warnings": []}
        val = ValidationResult()
        report = generate_qc_report(lint, val)
        assert "FAILED" in report
        assert "Heading jump" in report

    def test_failed_report_val_error(self):
        lint = {"errors": [], "warnings": []}
        val = ValidationResult()
        val.add_error("Missing required field: 'meta.language'")
        report = generate_qc_report(lint, val)
        assert "FAILED" in report
        assert "meta.language" in report

    def test_warnings_shown(self):
        lint = {"errors": [], "warnings": ["Line 10: More than 3 consecutive blank lines"]}
        val = ValidationResult()
        val.add_warning("Field 'project.subtitle' is empty")
        report = generate_qc_report(lint, val)
        assert "PASSED" in report  # warnings don't fail
        assert "consecutive blank" in report
        assert "subtitle" in report

    def test_combined_errors(self):
        lint = {"errors": ["Line 1: Empty heading"], "warnings": []}
        val = ValidationResult()
        val.add_error("Invalid HEX color")
        report = generate_qc_report(lint, val)
        assert "FAILED" in report
        assert "Errors:   2" in report
