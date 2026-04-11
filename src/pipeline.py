"""
Word Engine - Pipeline Module (Phase 1 + Phase 2)
Orchestrates the flow: load -> lint -> validate -> normalize -> render -> export.

Phase 2 additions:
- run_rerender(): versioned re-render with params snapshot
- run_postfix(): UNO post-processor stub (Phase 2 prep)
"""
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
    UNO post-processing step (Phase 2 stub, Phase 3 real implementation).

    Use when: render output needs manual fine-tuning that cannot be achieved
    via params.yaml changes alone (e.g. TOC update, page break adjustment).

    Currently a pass-through. Phase 3 will wire in LibreOffice UNO API.
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
