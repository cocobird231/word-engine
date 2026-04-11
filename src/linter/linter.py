"""
Word Engine - Linter Module (Phase 1)
Checks markdown structure for common issues.
"""
import re


def lint_markdown(md_text):
    """
    Lint markdown text and return errors/warnings.

    Checks (Phase 1):
    - Heading level jumps (e.g. H1 -> H3 without H2)
    - Empty headings
    - Unclosed code fences
    - Consecutive blank lines (> 3)

    Returns:
        {"errors": [...], "warnings": [...]}
    """
    errors = []
    warnings = []
    lines = md_text.split("\n")

    prev_heading_level = 0
    in_code_fence = False
    code_fence_line = 0
    consecutive_blanks = 0

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # ── Code fence tracking ──
        if stripped.startswith("```"):
            if in_code_fence:
                in_code_fence = False
            else:
                in_code_fence = True
                code_fence_line = i
            continue

        # Skip checks inside code blocks
        if in_code_fence:
            continue

        # ── Heading checks ──
        heading_match = re.match(r"^(#{1,6})\s*(.*)", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            # Empty heading
            if not title:
                errors.append(f"Line {i}: Empty heading (H{level})")

            # Heading jump
            if prev_heading_level > 0 and level > prev_heading_level + 1:
                errors.append(
                    f"Line {i}: Heading jump from H{prev_heading_level} to H{level}"
                )

            prev_heading_level = level
            consecutive_blanks = 0
            continue

        # ── Blank line tracking ──
        if stripped == "":
            consecutive_blanks += 1
            if consecutive_blanks == 4:
                warnings.append(f"Line {i}: More than 3 consecutive blank lines")
        else:
            consecutive_blanks = 0

    # ── Unclosed code fence ──
    if in_code_fence:
        errors.append(f"Line {code_fence_line}: Unclosed code fence (``` not closed)")

    return {"errors": errors, "warnings": warnings}
