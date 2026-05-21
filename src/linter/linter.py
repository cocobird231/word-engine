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
    Lint check for Mermaid diagram blocks.

    Step 1 – Heuristic rules:
      - Raw \\n inside node labels → should use <br/>

    Step 2 – Tool validation (if mmdc is available):
      - Attempt to render the block; if mmdc exits non-zero, report as error.
    """
    import json, shutil, subprocess, tempfile

    lines = block_content.split("\n")
    for i, line in enumerate(lines, start=start_line + 1):
        # Raw \n inside node labels is invalid in Mermaid
        if r'\n' in line:
            errors.append(
                f"Line {i}: Mermaid: raw '\\n' inside node label "
                f"(use '<br/>' for line breaks instead)"
            )

    # Tool validation via mmdc
    mmdc = shutil.which("mmdc")
    if mmdc is None:
        warnings.append(f"Line {start_line}: Mermaid lint: mmdc not found, skipping render validation")
        return

    tmp_in = tmp_out = tmp_cfg = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False, encoding="utf-8") as f:
            f.write(block_content)
            tmp_in = f.name
        tmp_out = tmp_in.replace(".mmd", "_lint.png")
        puppeteer_cfg = {"args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as pf:
            json.dump(puppeteer_cfg, pf)
            tmp_cfg = pf.name

        result = subprocess.run(
            [mmdc, "-i", tmp_in, "-o", tmp_out, "-p", tmp_cfg],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0 or not __import__("os").path.isfile(tmp_out):
            # Summarise the mmdc error (trim to avoid flooding the report)
            stderr_summary = (result.stderr.decode("utf-8", errors="replace")
                              .strip().splitlines())
            reason = next((l for l in stderr_summary if "Error" in l or "error" in l), "")
            errors.append(
                f"Line {start_line}: Mermaid: block fails to render "
                f"(mmdc exit {result.returncode}){': ' + reason[:120] if reason else ''}"
            )
    except subprocess.TimeoutExpired:
        warnings.append(f"Line {start_line}: Mermaid lint: mmdc timed out, skipping")
    except Exception as exc:
        warnings.append(f"Line {start_line}: Mermaid lint: tool error ({exc})")
    finally:
        for p in filter(None, [tmp_in, tmp_out, tmp_cfg]):
            try:
                __import__("os").unlink(p)
            except Exception:
                pass


def _check_graphviz_block(block_content: str, start_line: int, errors: list, warnings: list):
    """
    Lint check for Graphviz/dot diagram blocks.

    Step 1 – Heuristic rules:
      - Must start with graph/digraph declaration
      - Balanced braces

    Step 2 – Tool validation (if dot is available):
      - Run dot -Tsvg and check exit code; stderr indicates parse errors.
    """
    import shutil, subprocess

    stripped = block_content.strip()

    # Heuristic: valid declaration
    if not re.match(r'^\s*(strict\s+)?(di)?graph\b', stripped, re.IGNORECASE):
        errors.append(
            f"Line {start_line}: Graphviz: block does not start with "
            f"'graph', 'digraph', or 'strict graph/digraph'"
        )

    # Heuristic: balanced braces
    opens = stripped.count('{')
    closes = stripped.count('}')
    if opens != closes:
        errors.append(
            f"Line {start_line}: Graphviz: unbalanced braces "
            f"({{ = {opens}, }} = {closes})"
        )

    # Tool validation via dot
    dot = shutil.which("dot")
    if dot is None:
        warnings.append(f"Line {start_line}: Graphviz lint: dot not found, skipping parse validation")
        return

    try:
        result = subprocess.run(
            [dot, "-Tsvg"],
            input=block_content.encode("utf-8"),
            capture_output=True, timeout=15,
        )
        if result.returncode != 0:
            stderr_msg = result.stderr.decode("utf-8", errors="replace").strip().splitlines()
            reason = next((l for l in stderr_msg if "error" in l.lower()), "")
            errors.append(
                f"Line {start_line}: Graphviz: dot parse error "
                f"(exit {result.returncode}){': ' + reason[:120] if reason else ''}"
            )
    except subprocess.TimeoutExpired:
        warnings.append(f"Line {start_line}: Graphviz lint: dot timed out, skipping")
    except Exception as exc:
        warnings.append(f"Line {start_line}: Graphviz lint: tool error ({exc})")


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
