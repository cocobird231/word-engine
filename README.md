# word-engine

A parameterizable Markdown → DOCX + PDF document engine with QC, versioned rerender, and review workflow support.

---

## Features (Phase 1~3)

### Phase 1 – Core Rendering Pipeline
- Markdown to DOCX conversion (heading, paragraph, list, code block, table, image)
- Inline formatting: **bold**, *italic*, `inline code` with monospace font and shading
- Code block rendering with background shading
- QC pipeline: lint + validate params.yaml + normalize
- Structured QC report with errors and warnings
- PDF export via LibreOffice CLI headless

### Phase 2 – Document Structure & Review Workflow
- Cover page with configurable fields (title, subtitle, project_id, version, author, etc.)
- Table of Contents (Word-updatable TOC field)
- Figure and table captions with configurable numbering (flat / chapter modes)
- Cross-references via `{{ref:fig-N}}`, `{{ref:tbl-N}}`, `{{ref:sec-N}}` syntax
- Versioned rerender with `render_state.json` for artifact tracking
- Review loop: QC → rerender → postfix → export with `review_state.json` tracking

### Phase 3 – Native Word Fields & Inline Completeness
- Caption upgrade: Word SEQ field (`{ SEQ Figure \* ARABIC }`) for auto-updatable numbering
- Cross-reference upgrade: Word REF field (`{ REF fig_1 \h }`) pointing to SEQ bookmarks
- UNO socket bridge for precise field updates (UpdateAllIndexes + UpdateFields)
- Inline lint: detects unclosed backtick, bold `**`, and italic `*` markers
- Review flow completion: `mark-reviewed` and `status` commands

---

## Installation

### Requirements
- Python 3.10+
- LibreOffice (with `soffice` in PATH)
- `python3-uno` (system package, for UNO socket bridge)

### Setup
```bash
# Clone and enter project
cd word-engine

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

### 1. Prepare your files
- `refine.md` — your Markdown source
- `params.yaml` — rendering parameters (use `examples/final/params_full.yaml` as a template)

### 2. Check for errors (QC)
```bash
python word_engine.py qc \
  --md refine.md \
  --params params.yaml
```

### 3. Render to DOCX
```bash
python word_engine.py render \
  --md refine.md \
  --params params.yaml \
  --output output.docx
```

### 4. Export to PDF
```bash
python word_engine.py export \
  --docx output.docx \
  --output output.pdf
```

### 5. One-shot (QC + Render + Export)
```bash
python word_engine.py run \
  --md refine.md \
  --params params.yaml
```

---

## CLI Examples

### QC Only
```bash
python word_engine.py qc --md refine.md --params params.yaml
```

### QC with metadata override
```bash
python word_engine.py qc \
  --md refine.md --params params.yaml \
  --project-id "PROJ-2026" --author "Alice" --date "2026-05-19"
```

### Render to DOCX
```bash
python word_engine.py render \
  --md refine.md --params params.yaml \
  --output report.docx \
  --author "Bob" --organization "AcmeCorp"
```

### Export DOCX to PDF
```bash
python word_engine.py export --docx report.docx --output report.pdf
```

### One-shot (QC + Render + Export)
```bash
python word_engine.py run \
  --md refine.md --params params.yaml \
  --project-id "PROJ-001" --date "2026-05-19"
```

---

## Production Workflow (Versioned)

For iterative document editing with version tracking:

```bash
# Full review loop: QC → versioned rerender → UNO postfix → export
python word_engine.py review \
  --md refine.md \
  --params params.yaml \
  --project-dir . \
  --label "revision-2"

# Check current status
python word_engine.py status --project-dir .

# After visual review in Word/LibreOffice, mark as reviewed
python word_engine.py mark-reviewed --project-dir .

# Confirm final status
python word_engine.py status --project-dir .
```

---

## All Commands

| Command | Description |
|---------|-------------|
| `qc` | Run lint + validate + normalize on markdown and params |
| `render` | Render markdown to docx (unversioned) |
| `rerender` | Versioned render with params snapshot and state tracking |
| `export` | Export docx to pdf via LibreOffice CLI |
| `postfix` | Run UNO post-processing (field update) on a docx |
| `review` | Full loop: QC → rerender → postfix → export |
| `status` | Show review loop status and render history |
| `mark-reviewed` | Mark current version as human-reviewed |
| `run` | All-in-one: QC → render → export (unversioned, for quick testing) |

Run `python word_engine.py --help` or `python word_engine.py <command> --help` for details.

---

## Cross-Reference Syntax

In your Markdown, use `{{ref:ID}}` to create cross-references:

```markdown
Figure 1 is shown in {{ref:fig-1}}.
Table 2 is listed in {{ref:tbl-2}}.
See section {{ref:sec-1}} for details.
```

IDs are auto-assigned during rendering (first figure = `fig-1`, first table = `tbl-1`, etc.).
References are rendered as Word REF fields (Phase 3) that update with F9 or UNO postfix.

---

## Configuration (params.yaml)

See `configs/params.schema.v1.0.yaml` for the full parameter schema.
See `examples/final/params_full.yaml` for a ready-to-use template with all features enabled.

Key sections:
- `meta` / `project` — document metadata
- `cover` — cover page layout and field visibility
- `toc` — table of contents configuration
- `images` / `tables` — caption and numbering settings
- `cross_references` — reference style (ieee / apa)
- `code` — code block and inline code styling
- `caption_chapter_level` — which heading level defines a "chapter" (default: 2)

---

## Testing

```bash
./.venv/bin/pytest -q tests/unit/
```

---

## Project Structure

```
word-engine/
├── word_engine.py          # Entry point
├── src/
│   ├── cli.py              # CLI command definitions
│   ├── pipeline.py         # Pipeline orchestration
│   ├── loader/             # Markdown + YAML loading
│   ├── linter/             # Markdown structure checks
│   ├── validator/          # params.yaml schema validation
│   ├── normalizer/         # Low-risk auto-correction (stub)
│   ├── renderer/           # DOCX rendering
│   │   ├── cover.py        # Cover page
│   │   ├── toc.py          # TOC field
│   │   ├── caption.py      # Figure/table captions (SEQ field)
│   │   ├── cross_reference.py  # Reference registry
│   │   ├── seq_field.py    # SEQ / REF field OOXML helpers
│   │   └── renderer.py     # Main renderer
│   ├── exporter/           # LibreOffice PDF export
│   ├── post_processor_uno/ # UNO field update post-processor
│   ├── syncer/             # Nextcloud sync (stub)
│   └── state_manager/      # render_state.json / review_state.json
├── docs/                   # Design specs and guides
├── specs/                  # Phase planning documents
├── examples/               # Example markdown and params files
├── tests/                  # Unit and integration tests
├── configs/                # params.schema.v1.0.yaml
└── requirements.txt
```
