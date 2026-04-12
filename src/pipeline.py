"""
Word Engine - Pipeline Module (Phase 1 + Phase 2)
Orchestrates the flow: load -> lint -> validate -> normalize -> render -> export.

Phase 2 additions:
- run_rerender(): versioned re-render with params snapshot
- run_postfix(): UNO post-processor stub (Phase 2 prep)
"""
import os
from src.loader.loader import load_project
from src.linter.linter import lint_markdown
from src.validator.validator import validate_params
from src.normalizer.normalizer import normalize_markdown
from src.renderer.renderer import render_docx
from src.exporter.exporter import export_pdf, ExportError
from src.reporter.reporter import generate_qc_report
from src.post_processor_uno.post_processor import run_post_process
from src.syncer.syncer import sync_to_cloud
from src.state_manager.render_state import RenderState
from src.state_manager.review_state import ReviewState


def run_qc(md_path, params_path):
    """
    QC pipeline: load → lint → validate → normalize → report.

    Use when: you want to check the markdown and params before rendering.
    Does NOT produce a docx output.
    """
    print(f"[QC] Loading project: md={md_path}, params={params_path}")
    project_data = load_project(md_path, params_path)

    print("[QC] Linting markdown...")
    lint_results = lint_markdown(project_data["markdown"])

    print("[QC] Validating params...")
    val_results = validate_params(project_data["params"])

    print("[QC] Normalizing markdown...")
    normalized_md = normalize_markdown(project_data["markdown"])

    print("[QC] Generating QC report...")
    report = generate_qc_report(lint_results, val_results)

    qc_passed = val_results.is_valid and len(lint_results.get("errors", [])) == 0
    print()
    print(report)

    return {
        "normalized_md": normalized_md,
        "params": project_data["params"],
        "params_path": params_path,
        "qc_passed": qc_passed,
        "report": report,
    }


def run_render(md_path, params_path, output_docx="output.docx"):
    """
    First-time render pipeline: QC → render → post-process.

    Use when: starting a fresh render from a refine.md and params.yaml.
    Does NOT version the output — use run_rerender() for versioned output.
    """
    qc_result = run_qc(md_path, params_path)

    if not qc_result["qc_passed"]:
        print("[RENDER] QC failed. Please fix issues before rendering.")
        return None

    print(f"[RENDER] Rendering to {output_docx}...")
    docx_path = render_docx(qc_result["normalized_md"], qc_result["params"], output_docx)

    # Phase 1 stub: pass-through
    final_docx = run_post_process(docx_path, qc_result["params"])
    print(f"[RENDER] Successfully rendered: {final_docx}")
    return final_docx


def run_rerender(md_path, params_path, project_dir=".", label=None, force=False):
    """
    Versioned re-render pipeline (Phase 2).

    Use when: the markdown or params have been modified and a new versioned
    render is needed. Each call increments the version counter and archives
    the params snapshot and output docx separately.

    Semantic difference vs run_render():
        run_render()    → unversioned, outputs to a fixed path (e.g. output.docx)
        run_rerender()  → versioned, outputs to documents/report_vN.docx and
                          preserves params snapshot at documents/params/params_vN.yaml

    Args:
        md_path: Path to the markdown file (refine.md).
        params_path: Path to the current params.yaml to use for this render.
        project_dir: Root directory of the project (where render_state.json lives).
        label: Optional human-readable label for this version.
        force: If True, overwrite existing version artifacts without error.

    Returns:
        Path to the versioned docx, or None if QC failed.
    """
    qc_result = run_qc(md_path, params_path)

    if not qc_result["qc_passed"]:
        print("[RERENDER] QC failed. Please fix issues before re-rendering.")
        return None

    state = RenderState(project_dir)
    version = state.next_version()

    print(f"[RERENDER] Starting versioned render: v{version}")

    # Archive params snapshot
    try:
        if force:
            params_snapshot = state.snapshot_params_force(params_path, version)
        else:
            params_snapshot = state.snapshot_params(params_path, version)
        print(f"[RERENDER] Params snapshot saved: {params_snapshot}")
    except Exception as e:
        print(f"[RERENDER] Failed to snapshot params: {e}")
        return None

    # Render to versioned output path
    output_docx = state.versioned_docx_path(version)
    docx_path = render_docx(qc_result["normalized_md"], qc_result["params"], output_docx)

    # Phase 2 stub: pass-through UNO post-process
    final_docx = run_post_process(docx_path, qc_result["params"])

    # Register in state
    state.register_render(
        version=version,
        params_snapshot_path=params_snapshot,
        output_docx=final_docx,
        label=label,
    )

    print(f"[RERENDER] Version v{version} complete: {final_docx}")
    print(state.summary())
    return final_docx


def run_postfix(docx_path):
    """
    UNO post-processing step (Phase 2 implementation).

    Use when: render output needs field update (TOC, page numbers) after
    rendering. This version uses LibreOffice headless re-save to trigger
    LO's internal field update pipeline.

    Not a pass-through as of Phase 2. Phase 3 will add fine-grained
    Writer API control via UNO socket bridge.
    """
    print(f"[POSTFIX] Post-processing: {docx_path}")
    result = run_post_process(docx_path, params={})
    print(f"[POSTFIX] Done (stub): {result}")
    return result


def run_export(docx_path, output_pdf="output.pdf"):
    """Export docx to pdf."""
    print(f"[EXPORT] Exporting {docx_path} to {output_pdf}...")
    try:
        pdf_path = export_pdf(docx_path, output_pdf)
    except ExportError as e:
        print(f"[EXPORT] Failed: {e}")
        return None

    # Phase 1 stub: skip cloud sync
    sync_to_cloud([docx_path, pdf_path], config={})
    print(f"[EXPORT] Successfully exported: {pdf_path}")
    return pdf_path


def run_review(md_path, params_path, project_dir=".", label=None, skip_postfix=False):
    """
    Full review loop pipeline (Phase 2).

    Orchestrates the complete review cycle:
      QC → rerender (versioned) → postfix → export → status report

    Each step is recorded in review_state.json alongside render_state.json.
    The review loop can be run multiple times; each run increments both the
    render version and the review round counter.

    Args:
        md_path: Path to the markdown file (refine.md).
        params_path: Path to the current params.yaml.
        project_dir: Project root directory (where render_state.json lives).
        label: Optional label for this review version (e.g. 'fix-indent').
        skip_postfix: If True, skip the UNO postfix step (faster iteration).

    Returns:
        Dict with paths to produced artifacts, or None on failure.
    """
    print("[REVIEW] Starting review loop...")
    review = ReviewState(project_dir)

    # ── Step 1: QC ─────────────────────────────────────────────────────────
    print("[REVIEW] Step 1/4: QC check")
    qc_result = run_qc(md_path, params_path)
    if not qc_result["qc_passed"]:
        print("[REVIEW] QC failed — review loop aborted. Fix issues and retry.")
        return None
    print("[REVIEW] QC passed.")

    # ── Step 2: Rerender (versioned) ───────────────────────────────────────
    print("[REVIEW] Step 2/4: Versioned rerender")
    docx_path = run_rerender(
        md_path=md_path,
        params_path=params_path,
        project_dir=project_dir,
        label=label,
    )
    if not docx_path:
        print("[REVIEW] Rerender failed — review loop aborted.")
        return None

    # Start / advance review round using the current render version
    render_state = RenderState(project_dir)
    review.start_new_round(render_state.current_version)
    review.mark_step("qc_passed")
    review.mark_step("rendered", artifact_path=docx_path)
    print(f"[REVIEW] Rendered: {docx_path}")

    # ── Step 3: Postfix ────────────────────────────────────────────────────
    if not skip_postfix:
        print("[REVIEW] Step 3/4: UNO postfix")
        postfixed = run_postfix(docx_path)
        review.mark_step("postfixed")
        print(f"[REVIEW] Postfixed: {postfixed}")
    else:
        print("[REVIEW] Step 3/4: Postfix skipped (--skip-postfix)")
        review.mark_step("postfixed")

    # ── Step 4: Export PDF ─────────────────────────────────────────────────
    print("[REVIEW] Step 4/4: Export PDF")
    ver = render_state.current_version
    pdf_path = os.path.join(project_dir, "documents", f"report_v{ver}.pdf")
    pdf_result = run_export(docx_path, output_pdf=pdf_path)
    if pdf_result:
        review.mark_step("exported", artifact_path=pdf_result)
        print(f"[REVIEW] Exported: {pdf_result}")
    else:
        print("[REVIEW] PDF export failed. Check LibreOffice installation.")

    # ── Status Report ──────────────────────────────────────────────────────
    print()
    print(review.summary())

    return {
        "version": ver,
        "docx": docx_path,
        "pdf": pdf_result,
        "review_state_path": review.state_path,
    }


def run_status(project_dir=".", mark_reviewed=False):
    """
    Show current review loop status and render history, or mark current round as reviewed.

    This is the user-facing command for Task 6 (Review / Delivery Flow).

    Displays:
    - Current review version and round
    - Step-by-step completion status (qc_passed / rendered / postfixed / exported / review_checked)
    - Paths to produced artifacts (docx, pdf)
    - Render version history from render_state.json

    Args:
        project_dir: Project root directory.
        mark_reviewed: If True, mark review_checked=True in review_state.json.
    """
    from src.state_manager.review_state import ReviewState
    from src.state_manager.render_state import RenderState

    review = ReviewState(project_dir)
    render_state = RenderState(project_dir)

    if mark_reviewed:
        if review.current_version is None:
            print("[STATUS] No active review round found. Run 'word-engine review' first.")
            return
        review.mark_step("review_checked")
        print(f"[STATUS] Version v{review.current_version} marked as reviewed.")
        print()

    print(review.summary())

    # Also show render version history
    history = render_state.state.get("history", [])
    if history:
        print()
        print("=" * 50)
        print(f"  Render History ({len(history)} versions)")
        print("=" * 50)
        for entry in history[-5:]:  # Show last 5
            print(f"  v{entry['version']} [{entry.get('label', '')}] {entry.get('timestamp', '')[:16]}")
            if entry.get("output_docx"):
                print(f"    docx: {entry['output_docx']}")
        if len(history) > 5:
            print(f"  ... and {len(history) - 5} earlier versions")
        print("=" * 50)


def run_all(md_path, params_path):
    """
    All-in-one pipeline (unversioned): QC → render → export.

    Use when: you want a quick one-shot output without version tracking.
    For versioned production workflows, use run_rerender() + run_export() instead.
    """
    print("[RUN] Starting full pipeline (unversioned)...")
    output_docx = "output.docx"
    output_pdf = "output.pdf"

    docx_path = run_render(md_path, params_path, output_docx)
    if docx_path is None:
        print("[RUN] Pipeline aborted due to QC failure.")
        return None

    pdf_path = run_export(docx_path, output_pdf)
    print("[RUN] Full pipeline complete.")
    return pdf_path
