"""
Word Engine - Exporter Module (Phase 1)
Exports docx to pdf using LibreOffice CLI.
"""
import os
import subprocess
import shutil

class ExportError(Exception):
    """Raised when exporting to PDF fails."""
    pass

def export_pdf(docx_path, output_pdf_path):
    """
    Export a docx file to PDF using LibreOffice headless mode.
    
    Args:
        docx_path: Path to the source .docx file
        output_pdf_path: Path where the output .pdf should be saved
        
    Returns:
        output_pdf_path if successful
    """
    if not os.path.exists(docx_path):
        raise ExportError(f"Source docx file not found: {docx_path}")
        
    soffice_path = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice_path:
        raise ExportError("LibreOffice (soffice) is not installed or not in PATH.")

    # LibreOffice outputs to a directory, preserving the original filename
    # We will output to the directory of output_pdf_path, and then rename it
    output_dir = os.path.dirname(os.path.abspath(output_pdf_path))
    if not output_dir:
        output_dir = "."
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Run LibreOffice
    cmd = [
        soffice_path,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        docx_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise ExportError(f"LibreOffice conversion failed: {e.stderr}")
        
    # LibreOffice generates a file with the same basename as docx, but .pdf extension
    basename = os.path.basename(docx_path)
    generated_pdf_name = os.path.splitext(basename)[0] + ".pdf"
    generated_pdf_path = os.path.join(output_dir, generated_pdf_name)
    
    # Rename to the requested output_pdf_path if it's different
    if os.path.abspath(generated_pdf_path) != os.path.abspath(output_pdf_path):
        if os.path.exists(generated_pdf_path):
            if os.path.exists(output_pdf_path):
                os.remove(output_pdf_path)
            os.rename(generated_pdf_path, output_pdf_path)
        else:
            raise ExportError(f"Expected generated PDF not found at: {generated_pdf_path}")
            
    if not os.path.exists(output_pdf_path):
        raise ExportError("Conversion seemed to succeed, but output PDF was not found.")
        
    return output_pdf_path
