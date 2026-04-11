"""
Word Engine - Reporter Module (Phase 1)
Generates human-readable QC reports from lint and validation results.
"""
from datetime import datetime


def generate_qc_report(lint_results, val_results):
    """
    Generate a structured QC report string.

    Args:
        lint_results: dict with "errors" and "warnings" lists (from linter)
        val_results: ValidationResult object (from validator)

    Returns:
        str: formatted QC report
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  WORD ENGINE - QC REPORT")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)

    # ── Summary ──
    lint_errors = lint_results.get("errors", [])
    lint_warnings = lint_results.get("warnings", [])
    val_errors = val_results.errors if hasattr(val_results, "errors") else []
    val_warnings = val_results.warnings if hasattr(val_results, "warnings") else []

    total_errors = len(lint_errors) + len(val_errors)
    total_warnings = len(lint_warnings) + len(val_warnings)
    passed = total_errors == 0

    lines.append("")
    lines.append(f"  Result: {'✅ PASSED' if passed else '❌ FAILED'}")
    lines.append(f"  Errors:   {total_errors}")
    lines.append(f"  Warnings: {total_warnings}")

    # ── Lint Section ──
    lines.append("")
    lines.append("-" * 60)
    lines.append("  [LINT] Markdown Structure Check")
    lines.append("-" * 60)

    if lint_errors:
        for err in lint_errors:
            lines.append(f"  ❌ ERROR: {err}")
    else:
        lines.append("  ✅ No lint errors found.")

    if lint_warnings:
        for warn in lint_warnings:
            lines.append(f"  ⚠️  WARN: {warn}")

    # ── Validation Section ──
    lines.append("")
    lines.append("-" * 60)
    lines.append("  [VALIDATE] Params YAML Check")
    lines.append("-" * 60)

    if val_errors:
        for err in val_errors:
            lines.append(f"  ❌ ERROR: {err}")
    else:
        lines.append("  ✅ No validation errors found.")

    if val_warnings:
        for warn in val_warnings:
            lines.append(f"  ⚠️  WARN: {warn}")

    # ── Footer ──
    lines.append("")
    lines.append("=" * 60)
    if not passed:
        lines.append("  Please fix the errors above and re-run: word-engine qc")
    else:
        lines.append("  QC passed. You may proceed with: word-engine render")
    lines.append("=" * 60)

    return "\n".join(lines)
