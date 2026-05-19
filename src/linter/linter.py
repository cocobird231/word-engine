"""
Word Engine - Linter Module (Phase 1 + Phase 3)
Checks markdown structure for common issues.

Phase 3 additions:
- Unclosed inline bold (**text without closing **)
- Unclosed inline italic (*text without closing *)
- Unclosed inline code (`text without closing `)
"""
import re


def _check_mermaid_block(block_content: str, start_line: int, errors: list, warnings: list):
    """
    Heuristic lint check for Mermaid diagram blocks.

    Detects known invalid patterns that cause mmdc rendering to fail.
    """
    lines = block_content.split("\n")
    for i, line in enumerate(lines, start=start_line + 1):
        # Raw \n inside node labels is invalid in Mermaid (must use <br/> instead)
        if r'\n' in line:
            errors.append(
                f"Line {i}: Mermaid: raw backslash-n '\\n' inside node label "
                f"(use '<br/>' for line breaks instead)"
            )
        # Unclosed subgraph
        if line.strip().startswith("subgraph") and not re.search(r'subgraph\s*\[', line):
            pass  # simple check, not conclusive


def _check_graphviz_block(block_content: str, start_line: int, errors: list, warnings: list):
    """
    Heuristic lint check for Graphviz/dot diagram blocks.

    Checks for common structural issues that prevent rendering.
    """
    stripped = block_content.strip()

    # Must start with a valid graph declaration
    if not re.match(r'^\s*(strict\s+)?(di)?graph\s', stripped, re.IGNORECASE):
        errors.append(
            f"Line {start_line}: Graphviz: block does not start with "
            f"'graph', 'digraph', or 'strict graph/digraph'"
        )

    # Count braces
    opens = stripped.count('{')
    closes = stripped.count('}')
    if opens != closes:
        errors.append(
            f"Line {start_line}: Graphviz: unbalanced braces "
            f"({{ = {opens}, }} = {closes})"
        )


def _check_inline_markers(line_number, text, errors, warnings):
    """
    Check for unclosed inline markers on a single line.

    Checks:
    - Backtick inline code: odd number of backticks (unclosed `code`)
    - Bold (**): odd number of ** markers (unclosed **bold)
    - Italic (*): unmatched single * markers (excluding **)

    Note: This is a heuristic line-level check. It catches common cases but
    does not do full markdown AST analysis (e.g., multi-line spans).
    """
    # ── Inline code backtick check ──
    # Count unescaped single backticks (not double backticks for literal `)
    backtick_count = len(re.findall(r'(?<!`)`(?!`)', text))
    if backtick_count % 2 != 0:
        errors.append(f"Line {line_number}: Unclosed inline code (odd number of backticks)")

    # ── Bold ** check ──
    # Count ** markers (simplified: just count occurrences of **)
    bold_markers = len(re.findall(r'\*\*', text))
    if bold_markers % 2 != 0:
        errors.append(f"Line {line_number}: Unclosed bold marker (**)")

    # ── Italic * check (excluding ** and content inside backtick code spans) ──
    # First remove inline code spans and {{ref:*}} patterns to avoid false positives
    text_no_code = re.sub(r'`[^`]*`', '', text)  # remove backtick spans
    text_no_code = re.sub(r'\{\{ref:[^}]*\}\}', '', text_no_code)  # remove {{ref:...}}
    # Remove all ** to isolate single * markers
    text_no_bold = re.sub(r'\*\*', '', text_no_code)
    italic_markers = len(re.findall(r'(?<!\*)\*(?!\*)', text_no_bold))
    if italic_markers % 2 != 0:
        warnings.append(f"Line {line_number}: Possible unclosed italic marker (*)")


def lint_markdown(md_text):
    """
    Lint markdown text and return errors/warnings.

    Checks (Phase 1):
    - Heading level jumps (e.g. H1 -> H3 without H2)
    - Empty headings
    - Unclosed code fences
    - Consecutive blank lines (> 3)

    Checks (Phase 3 additions):
    - Unclosed inline code backtick
    - Unclosed inline bold (**)
    - Possible unclosed inline italic (*)

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

        # Skip inline checks inside code blocks
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

            # Check inline markers in heading text
            _check_inline_markers(i, title, errors, warnings)
            prev_heading_level = level
            consecutive_blanks = 0
            continue

        # ── Blank line tracking ──
        if stripped == "":
            consecutive_blanks += 1
            if consecutive_blanks == 4:
                warnings.append(f"Line {i}: More than 3 consecutive blank lines")
            continue
        else:
            consecutive_blanks = 0

        # ── Inline marker checks (non-empty, non-heading, non-fence lines) ──
        # Skip table separator rows (--- | --- etc.)
        if re.match(r'^[\s\|:\-]+$', stripped):
            continue
        # Skip pure link/image lines
        if re.match(r'^!?\[', stripped):
            continue

        _check_inline_markers(i, stripped, errors, warnings)

    # ── Unclosed code fence ──
    if in_code_fence:
        errors.append(f"Line {code_fence_line}: Unclosed code fence (``` not closed)")

    # ── Diagram block lint (Mermaid / Graphviz) ──────────────────────────────
    # Second pass: extract fenced diagram blocks and run specialized checks
    fence_pattern = re.compile(r"^```(mermaid|graphviz|dot)\s*$", re.MULTILINE)
    all_lines = md_text.split("\n")
    in_diag = False
    diag_lang = ""
    diag_start = 0
    diag_buf = []
    for lineno, line in enumerate(all_lines, start=1):
        if not in_diag:
            m = fence_pattern.match(line)
            if m:
                in_diag = True
                diag_lang = m.group(1).lower()
                diag_start = lineno
                diag_buf = []
        else:
            if line.strip() == "```":
                block = "\n".join(diag_buf)
                if diag_lang == "mermaid":
                    _check_mermaid_block(block, diag_start, errors, warnings)
                elif diag_lang in ("graphviz", "dot"):
                    _check_graphviz_block(block, diag_start, errors, warnings)
                in_diag = False
                diag_buf = []
            else:
                diag_buf.append(line)

    if in_diag:
        errors.append(f"Line {diag_start}: Unclosed diagram fence ({diag_lang})")

    return {"errors": errors, "warnings": warnings}
