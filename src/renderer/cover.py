"""
Word Engine - Cover Page Renderer (Phase 2)

Generates a basic formal cover page from params.yaml cover and project sections.

Title priority (as of Phase 3+):
  1. h1_title argument (extracted from the first H1 heading in the Markdown)
  2. params['project']['document_title'] as fallback
  3. "(No Title)" if both are absent

Supported fields (controlled by cover.show_* flags):
  - document_title  (H1 or params fallback, always shown)
  - subtitle
  - project_id
  - version
  - status
  - author
  - organization
  - date
  - confidentiality

Phase 2 scope: layout correctness, not final visual polish.
Logo support is deferred to Phase 3.
"""
from datetime import date
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ── Alignment helper ───────────────────────────────────────────────────────
_ALIGN_MAP = {
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}


def _align(name):
    return _ALIGN_MAP.get(str(name).lower(), WD_ALIGN_PARAGRAPH.CENTER)


def _add_blank(doc, count=1):
    for _ in range(count):
        doc.add_paragraph("")


def _add_text(doc, text, bold=False, size_pt=12, alignment="center"):
    p = doc.add_paragraph()
    p.alignment = _align(alignment)
    run = p.add_run(str(text))
    run.bold = bold
    run.font.size = Pt(size_pt)
    return p


def render_cover(doc, params, h1_title=None):
    """
    Insert a cover page at the current position in the document.

    Reads `params['cover']` for layout flags and `params['project']` for field values.
    Adds a page break after the cover.

    Args:
        doc: python-docx Document object.
        params: Parsed params.yaml dict.
    """
    cover_cfg = params.get("cover", {})
    project = params.get("project", {})

    # Skip entirely if cover is disabled
    if not cover_cfg.get("enabled", True):
        return

    title_alignment = cover_cfg.get("title_alignment", "center")

    # ── Top spacer ────────────────────────────────────────────────────────
    _add_blank(doc, 6)

    # ── Document Title ────────────────────────────────────────────────────
    # H1 from Markdown takes priority; fall back to params.project.document_title
    title = h1_title or project.get("document_title") or "(No Title)"
    _add_text(doc, title, bold=True, size_pt=24, alignment=title_alignment)

    # ── Subtitle ──────────────────────────────────────────────────────────
    if cover_cfg.get("show_subtitle", True):
        subtitle = project.get("subtitle", "")
        if subtitle:
            _add_text(doc, subtitle, bold=False, size_pt=16, alignment=title_alignment)

    _add_blank(doc, 3)

    # ── Meta fields table ─────────────────────────────────────────────────
    fields = []

    if cover_cfg.get("show_project_id", True):
        pid = project.get("project_id", "")
        if pid:
            fields.append(("專案編號", pid))

    if cover_cfg.get("show_version", True):
        ver = project.get("version", "")
        if ver:
            fields.append(("版本", ver))

    if cover_cfg.get("show_author", True):
        author = project.get("author", "")
        if author:
            fields.append(("撰寫者", author))

    if cover_cfg.get("show_organization", True):
        org = project.get("organization", "")
        if org:
            fields.append(("單位", org))

    if cover_cfg.get("show_date", True):
        doc_date = project.get("updated_date") or project.get("created_date") or str(date.today())
        fields.append(("日期", doc_date))

    if cover_cfg.get("show_confidentiality", True):
        conf = project.get("confidentiality", "")
        if conf:
            # Map to human-readable label
            conf_labels = {
                "public": "公開",
                "internal": "內部使用",
                "confidential": "機密",
            }
            fields.append(("機密等級", conf_labels.get(conf, conf)))

    # Render fields as simple label: value lines
    for label, value in fields:
        p = doc.add_paragraph()
        p.alignment = _align(title_alignment)
        run_label = p.add_run(f"{label}：")
        run_label.bold = True
        run_label.font.size = Pt(11)
        run_value = p.add_run(str(value))
        run_value.font.size = Pt(11)

    _add_blank(doc, 2)

    # ── Page break after cover ─────────────────────────────────────────────
    doc.add_page_break()
