"""
Word Engine - Validator Module (Phase 1)
Validates params.yaml structure, required fields, and basic enum values.
"""

# ── Required top-level sections ──────────────────────────────────────────
REQUIRED_TOP_LEVEL = ["meta", "project", "paths", "page", "fonts", "headings", "paragraphs"]

# ── Required fields within each section ──────────────────────────────────
REQUIRED_FIELDS = {
    "meta": ["schema_version", "spec_name", "language"],
    "project": ["project_id", "document_title", "version", "status"],
    "paths": ["source_md", "output_docx", "output_pdf"],
}

# ── Enum constraints ─────────────────────────────────────────────────────
ENUM_RULES = {
    ("page", "size"): ["A4", "Letter"],
    ("page", "orientation"): ["portrait", "landscape"],
    ("images", "numbering_mode"): ["flat", "chapter"],
    ("tables", "numbering_mode"): ["flat", "chapter"],
    ("cross_references", "style"): ["ieee", "apa"],
    ("references", "style"): ["ieee", "apa"],
    ("numbering", "heading_numbering_style"): ["decimal", "roman"],
    ("project", "status"): ["draft", "review", "final"],
    ("project", "confidentiality"): ["public", "internal", "confidential"],
}

# ── Color hex pattern ────────────────────────────────────────────────────
import re
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ValidationResult:
    """Container for validation errors and warnings."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    @property
    def is_valid(self):
        return len(self.errors) == 0

    def add_error(self, message):
        self.errors.append(message)

    def add_warning(self, message):
        self.warnings.append(message)

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }

    def __repr__(self):
        status = "PASS" if self.is_valid else "FAIL"
        return f"<ValidationResult {status} errors={len(self.errors)} warnings={len(self.warnings)}>"


def _check_top_level(params, result):
    """Check that required top-level sections exist."""
    for section in REQUIRED_TOP_LEVEL:
        if section not in params:
            result.add_error(f"Missing required top-level section: '{section}'")
        elif not isinstance(params[section], dict):
            result.add_error(f"Top-level section '{section}' must be a mapping (dict), got {type(params[section]).__name__}")


def _check_required_fields(params, result):
    """Check required fields within known sections."""
    for section, fields in REQUIRED_FIELDS.items():
        section_data = params.get(section)
        if not isinstance(section_data, dict):
            continue  # Already reported by _check_top_level
        for field in fields:
            if field not in section_data:
                result.add_error(f"Missing required field: '{section}.{field}'")
            elif section_data[field] is None or section_data[field] == "":
                result.add_warning(f"Field '{section}.{field}' is empty")


def _check_enums(params, result):
    """Check enum fields against allowed values."""
    for (section, field), allowed in ENUM_RULES.items():
        section_data = params.get(section)
        if not isinstance(section_data, dict):
            continue
        value = section_data.get(field)
        if value is not None and value not in allowed:
            result.add_error(
                f"Invalid value for '{section}.{field}': '{value}'. "
                f"Allowed: {allowed}"
            )


def _check_colors(params, result):
    """Spot-check color fields in the 'colors' section."""
    colors = params.get("colors")
    if not isinstance(colors, dict):
        return
    for key, value in colors.items():
        if isinstance(value, str) and not _HEX_COLOR.match(value):
            result.add_error(f"Invalid HEX color for 'colors.{key}': '{value}'")


def validate_params(params):
    """
    Run all Phase 1 validations on a params dict.

    Args:
        params: dict parsed from params.yaml

    Returns:
        ValidationResult with errors and warnings.
    """
    result = ValidationResult()

    if not isinstance(params, dict):
        result.add_error("Params must be a dict (YAML mapping).")
        return result

    _check_top_level(params, result)
    _check_required_fields(params, result)
    _check_enums(params, result)
    _check_colors(params, result)

    return result
