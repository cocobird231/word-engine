"""
Word Engine - SEQ and REF Field Helpers (Phase 3)

Provides OOXML helper functions for Word SEQ fields (auto-numbering) and
REF fields (cross-references).

## SEQ field (used for figure/table captions)
A SEQ field creates an auto-incrementing counter within Word:
    { SEQ Figure \\* ARABIC }
This renders as "1", "2", etc., and updates when F9 / UNO field update runs.

The full caption paragraph structure:
    "圖 " + [SEQ field] + " Alt text"

With a bookmark wrapping the SEQ field:
    <w:bookmarkStart w:name="fig_1"/>
    [SEQ field]
    <w:bookmarkEnd/>

## REF field (used for cross-references)
A REF field creates a reference to a bookmark:
    { REF fig_1 \\h }
- \\h makes it a hyperlink to the target
- This replaces the Phase 2 static text substitution

## Chapter mode limitation
- SEQ flat mode: { SEQ Figure \\* ARABIC }
- SEQ chapter mode: requires { STYLEREF 1 \\n }-{ SEQ Figure \\* ARABIC }
  which depends on Word heading styles (Heading 1/2 etc.)
- Chapter mode SEQ is deferred to Phase 3 later; currently uses flat SEQ
  with a note that chapter numbering via STYLEREF requires UNO field update

## Field update
All SEQ and REF fields require F9 (Word) or UNO field update to show correct
values. The postfix step (post_processor_uno) triggers this update.
"""
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _make_field_run(instr_text, placeholder=""):
    """
    Build a complete Word field as a sequence of runs:
    fldChar(begin) + instrText + fldChar(separate) + [placeholder text] + fldChar(end)

    Args:
        instr_text: The field instruction, e.g. ' SEQ Figure \\* ARABIC '
        placeholder: Text shown before field update (e.g. "1")

    Returns:
        List of OOXML run elements that form the field.
    """
    runs = []

    # begin
    r_begin = OxmlElement("w:r")
    fc_begin = OxmlElement("w:fldChar")
    fc_begin.set(qn("w:fldCharType"), "begin")
    r_begin.append(fc_begin)
    runs.append(r_begin)

    # instrText
    r_instr = OxmlElement("w:r")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instr_text
    r_instr.append(instr)
    runs.append(r_instr)

    # separate
    r_sep = OxmlElement("w:r")
    fc_sep = OxmlElement("w:fldChar")
    fc_sep.set(qn("w:fldCharType"), "separate")
    r_sep.append(fc_sep)
    runs.append(r_sep)

    # placeholder text run
    if placeholder:
        r_text = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        no_proof = OxmlElement("w:noProof")
        rPr.append(no_proof)
        r_text.append(rPr)
        t = OxmlElement("w:t")
        t.text = str(placeholder)
        r_text.append(t)
        runs.append(r_text)

    # end
    r_end = OxmlElement("w:r")
    fc_end = OxmlElement("w:fldChar")
    fc_end.set(qn("w:fldCharType"), "end")
    r_end.append(fc_end)
    runs.append(r_end)

    return runs


def _wrap_with_bookmark(paragraph, runs, bookmark_id, bookmark_name):
    """
    Add bookmarkStart before the runs and bookmarkEnd after them.
    Used to make SEQ fields targetable by REF fields.

    Args:
        paragraph: python-docx Paragraph to modify.
        runs: List of already-appended run elements (their parent is paragraph._p).
        bookmark_id: Unique integer ID.
        bookmark_name: Bookmark name (no spaces, e.g. "fig_1").
    """
    if not runs:
        return

    first_run = runs[0]
    last_run = runs[-1]

    # bookmarkStart goes before the first run
    bm_start = OxmlElement("w:bookmarkStart")
    bm_start.set(qn("w:id"), str(bookmark_id))
    bm_start.set(qn("w:name"), bookmark_name)
    first_run.addprevious(bm_start)

    # bookmarkEnd goes after the last run
    bm_end = OxmlElement("w:bookmarkEnd")
    bm_end.set(qn("w:id"), str(bookmark_id))
    last_run.addnext(bm_end)


def insert_seq_caption(paragraph, prefix, alt_text, seq_name, display_num,
                       bookmark_id, bookmark_name):
    """
    Insert a caption paragraph with a Word SEQ field.

    Produces: "{prefix} {SEQ seq_name \\* ARABIC} {alt_text}"
    e.g.:     "圖 1 系統架構圖"

    The SEQ field is wrapped with a bookmark so REF fields can reference it.

    Args:
        paragraph: python-docx Paragraph to write into (should be empty).
        prefix: Caption prefix string, e.g. "圖" or "表".
        alt_text: Description text after the number.
        seq_name: SEQ identifier, e.g. "Figure" or "Table".
        display_num: Placeholder number (shown before field update), e.g. "1".
        bookmark_id: Unique bookmark ID (integer).
        bookmark_name: Bookmark name, e.g. "fig_1".
    """
    p = paragraph._p

    # Prefix run: "圖 "
    r_prefix = OxmlElement("w:r")
    t_prefix = OxmlElement("w:t")
    t_prefix.set(qn("xml:space"), "preserve")
    # If prefix ends with "-" (chapter mode like "圖 1-"), no extra space before SEQ number
    prefix_text = prefix if prefix.endswith("-") else f"{prefix} "
    t_prefix.text = prefix_text
    r_prefix.append(t_prefix)
    p.append(r_prefix)

    # SEQ field runs
    instr = f" SEQ {seq_name} \\* ARABIC "
    field_runs = _make_field_run(instr, placeholder=str(display_num))
    for run in field_runs:
        p.append(run)

    # Wrap field runs with bookmark
    _wrap_with_bookmark(paragraph, field_runs, bookmark_id, bookmark_name)

    # Alt text run (if any): " 系統架構圖"
    if alt_text:
        r_alt = OxmlElement("w:r")
        t_alt = OxmlElement("w:t")
        t_alt.set(qn("xml:space"), "preserve")
        t_alt.text = f" {alt_text}"
        r_alt.append(t_alt)
        p.append(r_alt)


def insert_ref_field(paragraph, display_text, bookmark_name, with_hyperlink=True):
    """
    Insert a REF field into a paragraph, pointing to a named bookmark.

    Produces: { REF bookmark_name \\h }
    This is the Word-updatable cross-reference, replacing the Phase 2 static substitution.

    Args:
        paragraph: python-docx Paragraph to append the field to.
        display_text: Placeholder text shown before field update, e.g. "圖 1".
        bookmark_name: The target bookmark name, e.g. "fig_1".
        with_hyperlink: If True, adds \\h flag for clickable hyperlink.
    """
    instr = f" REF {bookmark_name}"
    if with_hyperlink:
        instr += " \\h"
    instr += " "

    # Wrap in a hyperlink element for clickable behavior in Word
    if with_hyperlink:
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("w:anchor"), bookmark_name)
        field_runs = _make_field_run(instr, placeholder=display_text)
        for run in field_runs:
            hyperlink.append(run)
        paragraph._p.append(hyperlink)
    else:
        field_runs = _make_field_run(instr, placeholder=display_text)
        for run in field_runs:
            paragraph._p.append(run)
