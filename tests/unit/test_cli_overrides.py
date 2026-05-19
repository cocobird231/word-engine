"""Unit tests for CLI project metadata override logic (_apply_cli_overrides)."""
import pytest
from src.pipeline import _apply_cli_overrides


def _base_params(**project_fields):
    return {"project": {"project_id": "P001", "author": "Alice",
                        "organization": "Org", "created_date": "2026-01-01",
                        "updated_date": "2026-01-01", **project_fields}}


class TestApplyCliOverrides:
    def test_project_id_override(self):
        p = _apply_cli_overrides(_base_params(), project_id="NEW-ID")
        assert p["project"]["project_id"] == "NEW-ID"

    def test_project_name_override(self):
        p = _apply_cli_overrides(_base_params(), project_name="New Name")
        assert p["project"]["project_name"] == "New Name"

    def test_author_override(self):
        p = _apply_cli_overrides(_base_params(), author="Bob")
        assert p["project"]["author"] == "Bob"

    def test_organization_override(self):
        p = _apply_cli_overrides(_base_params(), organization="NewOrg")
        assert p["project"]["organization"] == "NewOrg"

    def test_date_overrides_both_dates(self):
        p = _apply_cli_overrides(_base_params(), date="2030-12-31")
        assert p["project"]["created_date"] == "2030-12-31"
        assert p["project"]["updated_date"] == "2030-12-31"

    def test_none_value_does_not_override(self):
        p = _apply_cli_overrides(_base_params(), project_id=None, author=None)
        assert p["project"]["project_id"] == "P001"
        assert p["project"]["author"] == "Alice"

    def test_multiple_overrides_at_once(self):
        p = _apply_cli_overrides(_base_params(),
                                  project_id="X", author="Y",
                                  organization="Z", date="2099-01-01")
        assert p["project"]["project_id"] == "X"
        assert p["project"]["author"] == "Y"
        assert p["project"]["organization"] == "Z"
        assert p["project"]["created_date"] == "2099-01-01"

    def test_missing_project_section_is_created(self):
        p = _apply_cli_overrides({}, project_id="BRAND-NEW")
        assert p["project"]["project_id"] == "BRAND-NEW"
