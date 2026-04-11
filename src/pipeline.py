"""
Word Engine - Pipeline Module (Phase 1)
Orchestrates the flow: load -> lint -> validate -> normalize -> render -> export.
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


def run_qc(md_path, params_path):
    """Run QC pipeline: load → lint → validate → normalize → report."""
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
        "qc_passed": qc_passed,
        "report": report,
    }


def run_render(md_path, params_path, output_docx="output.docx"):
    """Run render pipeline: QC → render → post-process."""
    qc_result = run_qc(md_path, params_path)

    if not qc_result["qc_passed"]:
        print("[RENDER] QC failed. Please fix issues before rendering.")
        print(qc_result["report"])
        return None

    print(f"[RENDER] Rendering to {output_docx}...")
    docx_path = render_docx(qc_result["normalized_md"], qc_result["params"], output_docx)

    # Phase 1 stub: pass-through
    final_docx = run_post_process(docx_path, qc_result["params"])
    print(f"[RENDER] Successfully rendered: {final_docx}")
    return final_docx


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
    """Run full pipeline: QC → render → export."""
    print("[RUN] Starting full pipeline...")
    output_docx = "output.docx"
    output_pdf = "output.pdf"

    docx_path = run_render(md_path, params_path, output_docx)
    if docx_path is None:
        print("[RUN] Pipeline aborted due to QC failure.")
        return None

    pdf_path = run_export(docx_path, output_pdf)
    print("[RUN] Full pipeline complete.")
    return pdf_path
