"""
Word Engine - UNO Post-Processor (Phase 2 + Phase 3)

Phase 2: LibreOffice headless re-save (triggers internal field update pipeline)
Phase 3: True UNO socket bridge with explicit dispatcher calls

## Field update capabilities
When run_post_process() is called, it updates:
  - TOC (Table of Contents) fields
  - SEQ fields (figure/table caption numbering)
  - REF fields (cross-references)
  - PAGE/NUMPAGES fields (page numbers)
  - All other document fields

## UNO socket bridge vs headless re-save
  Headless re-save (Phase 2):
    - Calls `soffice --convert-to docx` which re-saves through LO's filter
    - Indirectly triggers field update via filter pipeline
    - Less reliable for complex SEQ/REF fields; no explicit UpdateAllIndexes

  UNO socket bridge (Phase 3):
    - Starts LO with --accept socket listener
    - Connects via python-uno, opens the docx
    - Explicitly calls: UpdateAllIndexes + UpdateFields
    - Closes and saves
    - More reliable for SEQ/REF/TOC field updates
    - Falls back to headless re-save if socket bridge fails

## Usage
    result = run_post_process(docx_path)
    # docx is updated in-place with all fields resolved

## Known limitations
  - LibreOffice must be installed (soffice in PATH)
  - python3-uno must be available
  - UNO socket bridge starts a temporary LO instance; may not work in all envs
  - Field display depends on LO's interpretation of Word field codes
"""
import os
import subprocess
import shutil
import tempfile
import time

UNO_PORT = 2002
LO_STARTUP_TIMEOUT = 8  # seconds to wait for LO to start accepting connections


class UNOError(Exception):
    """Raised when UNO post-processing fails."""
    pass


def _try_uno_socket_bridge(docx_path):
    """
    Update all fields in a docx using the UNO socket bridge approach.

    Uses system python3 (which has the python-uno package) via subprocess
    to avoid venv/uno module conflicts.

    Process:
    1. Start LibreOffice headless with socket listener
    2. Connect via python-uno (system python3)
    3. Open the docx, run UpdateAllIndexes + UpdateFields
    4. Save and close, terminate LibreOffice

    Returns:
        True if successful, False if failed (caller should fallback).
    """
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return False

    docx_abs = os.path.abspath(docx_path)

    # UNO bridge script runs in system python3 (not venv) where python-uno is available
    script = f"""
import sys, os, time, subprocess

soffice = r"{soffice}"
docx_abs = r"{docx_abs}"
UNO_PORT = {UNO_PORT}
LO_STARTUP_TIMEOUT = {LO_STARTUP_TIMEOUT}

lo_proc = subprocess.Popen(
    [soffice, "--headless", "--norestore", "--nofirststartwizard",
     f"--accept=socket,host=localhost,port={{UNO_PORT}};urp;StarOffice.ServiceManager"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)

try:
    import uno
    from com.sun.star.beans import PropertyValue

    start = time.time()
    ctx = None
    while time.time() - start < LO_STARTUP_TIMEOUT:
        try:
            lctx = uno.getComponentContext()
            resolver = lctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver", lctx)
            ctx = resolver.resolve(
                f"uno:socket,host=localhost,port={{UNO_PORT}};urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(0.5)

    if ctx is None:
        sys.exit(1)

    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    file_url = uno.systemPathToFileUrl(docx_abs)

    p_hidden = PropertyValue()
    p_hidden.Name = "Hidden"
    p_hidden.Value = True

    doc = desktop.loadComponentFromURL(file_url, "_blank", 0, (p_hidden,))
    if doc is None:
        sys.exit(1)

    dispatcher = smgr.createInstanceWithContext(
        "com.sun.star.frame.DispatchHelper", ctx)
    frame = doc.getCurrentController().getFrame()

    dispatcher.executeDispatch(frame, ".uno:UpdateAllIndexes", "", 0, ())
    dispatcher.executeDispatch(frame, ".uno:UpdateFields", "", 0, ())

    doc.store()
    doc.close(True)
    print("UNO_OK")

except Exception as e:
    sys.stderr.write(str(e))
    sys.exit(1)

finally:
    try:
        lo_proc.terminate()
        lo_proc.wait(timeout=5)
    except Exception:
        pass
"""
    tmp = tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8")
    tmp.write(script)
    tmp.close()

    try:
        result = subprocess.run(
            ["python3", tmp.name],
            capture_output=True, text=True, timeout=LO_STARTUP_TIMEOUT + 30,
        )
        return result.returncode == 0 and "UNO_OK" in result.stdout
    except Exception:
        return False
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def _fallback_headless_resave(docx_path):
    """
    Fallback: use LibreOffice headless convert-to to re-save the docx.
    This indirectly triggers LO's field update pipeline.
    """
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise UNOError("LibreOffice (soffice) not found in PATH.")

    docx_path = os.path.abspath(docx_path)
    output_dir = os.path.dirname(docx_path)

    script = f"""
import sys, os, subprocess, shutil

soffice = "{soffice}"
docx_path = r"{docx_path}"
output_dir = r"{output_dir}"

result = subprocess.run(
    [soffice, "--headless", "--norestore",
     "--infilter=writer8",
     "--convert-to", "docx:MS Word 2007 XML",
     "--outdir", output_dir, docx_path],
    capture_output=True, text=True, timeout=60
)
if result.returncode != 0:
    sys.stderr.write(result.stderr)
    sys.exit(1)
basename = os.path.splitext(os.path.basename(docx_path))[0]
converted = os.path.join(output_dir, basename + ".docx")
if os.path.exists(converted) and os.path.abspath(converted) != docx_path:
    os.replace(converted, docx_path)
print("OK")
"""
    tmp = tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8")
    tmp.write(script)
    tmp.close()
    try:
        result = subprocess.run(
            ["python3", tmp.name],
            capture_output=True, text=True, timeout=90,
        )
        if result.returncode != 0:
            raise UNOError(f"Headless re-save failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise UNOError("Headless re-save timed out (>90s).")
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def run_post_process(docx_path, params=None):
    """
    Run UNO post-processing on a docx file.

    Phase 3 strategy:
    1. Try UNO socket bridge first (explicit UpdateAllIndexes + UpdateFields)
    2. Fall back to headless re-save if socket bridge fails

    Fields updated:
    - TOC (Table of Contents)
    - SEQ fields (figure/table caption numbering from Phase 3)
    - REF fields (cross-references from Phase 3)
    - PAGE/NUMPAGES and other document fields

    Args:
        docx_path: Path to the .docx file to post-process (updated in-place).
        params: (Optional) params dict for future extensions.

    Returns:
        docx_path if successful.

    Raises:
        UNOError if both approaches fail.
    """
    if params is None:
        params = {}

    docx_path = os.path.abspath(docx_path)

    if not os.path.exists(docx_path):
        raise UNOError(f"Input docx not found: {docx_path}")

    print(f"[UNO] Post-processing: {docx_path}")

    # Try Phase 3 UNO socket bridge first
    success = _try_uno_socket_bridge(docx_path)
    if success:
        print(f"[UNO] Fields updated via socket bridge: {docx_path}")
        return docx_path

    # Fallback to Phase 2 headless re-save
    print(f"[UNO] Socket bridge unavailable, falling back to headless re-save")
    _fallback_headless_resave(docx_path)
    print(f"[UNO] Fields updated via headless re-save: {docx_path}")
    return docx_path
