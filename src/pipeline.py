from src.loader.loader import load_project
from src.linter.linter import lint_markdown
from src.validator.validator import validate_params
from src.normalizer.normalizer import normalize_markdown
from src.renderer.renderer import render_docx
from src.exporter.exporter import export_pdf
from src.reporter.reporter import generate_qc_report
from src.post_processor_uno.post_processor import run_post_process
from src.syncer.syncer import sync_to_cloud

def run_qc(md_path, params_path):
    print(f"Running QC on {md_path} with {params_path}...")
    project_data = load_project(md_path, params_path)
    
    lint_results = lint_markdown(project_data['markdown'])
    val_results = validate_params(project_data['params'])
    
    normalized_md = normalize_markdown(project_data['markdown'])
    
    report = generate_qc_report(lint_results, val_results)
    print("QC Report:", report)
    return normalized_md, project_data['params']

def run_render(md_path, params_path, output_docx):
    print(f"Rendering {md_path} to {output_docx}...")
    normalized_md, params = run_qc(md_path, params_path)
    
    docx_path = render_docx(normalized_md, params, output_docx)
    
    # Phase 1 stub call
    final_docx = run_post_process(docx_path, params)
    print(f"Successfully rendered: {final_docx}")
    return final_docx

def run_export(docx_path, output_pdf):
    print(f"Exporting {docx_path} to {output_pdf}...")
    pdf_path = export_pdf(docx_path, output_pdf)
    
    # Phase 1 stub call
    sync_to_cloud([docx_path, pdf_path], config={})
    print(f"Successfully exported: {pdf_path}")
    return pdf_path

def run_all(md_path, params_path):
    print("Running full pipeline...")
    output_docx = "output.docx"
    output_pdf = "output.pdf"
    
    docx_path = run_render(md_path, params_path, output_docx)
    pdf_path = run_export(docx_path, output_pdf)
    
    print("Full pipeline complete.")
