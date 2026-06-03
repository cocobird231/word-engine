# word-engine Architecture

## Overview

word-engine is a CLI tool that converts Markdown documents into formatted Word (`.docx`) and PDF files. It follows a pipeline architecture with clear separation between QC, rendering, post-processing, and delivery.

```
Markdown (.md) + params.yaml
        │
        ▼
 ┌─────────────────┐
 │   CLI (cli.py)  │  ← User entry point
 └────────┬────────┘
          │
          ▼
 ┌────────────────────────────────────────────────────────┐
 │                   Pipeline (pipeline.py)               │
 │                                                        │
 │  run_qc()  →  run_render()  →  run_export()           │
 │  run_rerender()  →  run_review()  →  run_status()     │
 └────────────────────────────────────────────────────────┘
          │
     ┌────┴─────────────────┐
     │                      │
     ▼                      ▼
 ┌──────────┐         ┌──────────────┐
 │  Loader  │         │   Linter /   │
 │ (loader) │         │  Validator / │
 └──────────┘         │  Normalizer  │
                      └──────────────┘
                            │
                            ▼
               ┌────────────────────────┐
               │   Renderer Subsystem   │
               │                        │
               │  renderer.py           │
               │    ├── cover.py        │
               │    ├── toc.py          │
               │    ├── caption.py      │
               │    ├── cross_ref.py    │
               │    ├── seq_field.py    │
               │    └── diagram.py      │
               └────────────────────────┘
                            │
                            ▼
               ┌────────────────────────┐
               │   Post-Processor       │
               │  (post_processor_uno)  │
               └────────────────────────┘
                            │
                            ▼
               ┌────────────────────────┐
               │      Exporter          │
               │    (LibreOffice CLI)   │
               └────────────────────────┘
                            │
                            ▼
               ┌────────────────────────┐
               │   State Manager        │
               │  render_state.json     │
               │  review_state.json     │
               └────────────────────────┘
```

---

## Module Reference

### `src/cli.py`
**Purpose:** Command-line interface entry point.

**Commands:**
| Command | Description |
|---------|-------------|
| `qc` | Run QC check (lint + validate + normalize). No output produced. |
| `render` | First-time unversioned render → output.docx |
| `rerender` | Versioned re-render with params snapshot and state tracking |
| `export` | Export docx to pdf via LibreOffice CLI |
| `postfix` | Run UNO field update post-processing on a docx |
| `review` | Full loop: QC → rerender → postfix → export |
| `status` | Show review loop status and render history |
| `mark-reviewed` | Mark current version as human-reviewed |
| `run` | All-in-one: QC → render → export (unversioned) |

**Project metadata overrides** (available on all content commands):
```
--project-id   --project-name   --author   --organization   --date
```

---

### `src/pipeline.py`
**Purpose:** Orchestrates the rendering pipeline; connects all modules.

**Key functions:**
- `_apply_cli_overrides(params, **kwargs)` — applies CLI arg overrides to loaded params
- `run_qc(md_path, params_path)` — load → lint → validate → normalize → report
- `run_render(md_path, params_path, output_docx)` — QC + render (unversioned)
- `run_rerender(...)` — versioned render with `render_state.json` tracking
- `run_review(...)` — complete review loop with `review_state.json` tracking
- `run_status(project_dir, mark_reviewed)` — display current status

---

### `src/loader/loader.py`
**Purpose:** Loads markdown text and YAML params into structured data.

**Key functions:**
- `load_markdown(md_path)` → `str` — reads UTF-8 markdown
- `load_params(params_path)` → `dict` — parses YAML with schema validation
- `scan_assets(assets_dir)` → `list[str]` — lists asset files
- `load_project(md_path, params_path)` → `dict` — combined load

**Raises:** `LoadError` on missing file or malformed YAML.

---

### `src/linter/linter.py`
**Purpose:** Structural and syntax checking for markdown content.

**Checks:**
- Heading level jumps (H1 → H3 without H2)
- Empty headings
- Unclosed code fence (` ``` `)
- Excessive consecutive blank lines (warning)
- Unclosed inline code backtick (error)
- Unclosed bold `**` (error)
- Unclosed italic `*` (warning)
- **Mermaid blocks:** heuristic `\n` in node labels + mmdc render validation
- **Graphviz blocks:** graph/digraph declaration + dot parse validation

---

### `src/validator/validator.py`
**Purpose:** Validates params.yaml against the schema.

**Checks:**
- Required top-level sections: `meta`, `project`, `paths`, `page`, `fonts`, `headings`, `paragraphs`
- Required fields within each section
- Enum values (page size, orientation, numbering mode, citation style, etc.)
- HEX color format validation

**Returns:** `ValidationResult` with `.errors`, `.warnings`, `.is_valid`.

---

### `src/normalizer/normalizer.py`
**Status:** Stub — pass-through only.

**Intended functionality (not yet implemented):**
- Remove excessive blank lines
- Fix trailing whitespace
- Full-width → half-width character conversion (contextual)
- Punctuation normalization
- Default params fallback injection

---

### `src/renderer/renderer.py`
**Purpose:** Core rendering engine. Converts normalized markdown AST to DOCX.

**Architecture:**
1. `_pre_scan_references(tokens, params)` — Pass 1: build reference registry for `{{ref:*}}`
2. `render_docx(md_text, params, output_path, md_dir, assets_dir)` — Pass 2: render
3. `_render_tokens(doc, tokens, params, counter, registry, bm_mgr, md_dir, assets_dir)` — token walker

**Key behaviors:**
- Images: resolved via `_resolve_image_src()` relative to `md_dir` (not output path)
- Images inside list items: detected and rendered (not skipped)
- Ordered lists: each new list block restarts numbering counter
- Diagrams: `graphviz`/`dot`/`mermaid` fence blocks → PNG via `render_graphviz()`/`render_mermaid()`
- H1 title: extracted and passed to cover page (overrides `params.project.document_title`)

---

### `src/renderer/cover.py`
**Purpose:** Renders the cover page.

**Title priority:** H1 from markdown > `params.project.document_title` > "(No Title)"

**Configurable fields** (via `params.cover.show_*`):
subtitle, project_id, version, author, organization, date, confidentiality

---

### `src/renderer/toc.py`
**Purpose:** Inserts a Word-updatable TOC field.

**Implementation:** Raw OOXML `w:fldChar` + `w:instrText` with `TOC \o "1-N" \h`

**Note:** Requires F9 or UNO postfix to populate with actual headings.

---

### `src/renderer/caption.py`
**Purpose:** Auto-incrementing figure and table captions.

**Numbering modes:**
- `flat`: sequential whole-document (圖 1, 圖 2, 表 1, 表 2)
- `chapter`: per-chapter prefix (圖 2-1, 表 3-1), driven by `caption_chapter_level` (default: 2 = H2)

**Note:** Caption chapter level is based on encounter order of H-level headings, NOT the text content of headings (e.g., `## 1. Title` is H2 regardless of the `1.`).

**Classes:**
- `CaptionCounter` — tracks figure/table counts with `next_figure()`, `peek_next_figure()`, etc.
- `add_figure_caption(doc, alt_text, counter, params)` → inserts SEQ field caption
- `add_table_caption(doc, caption_text, counter, params)` → inserts SEQ field caption

---

### `src/renderer/cross_reference.py`
**Purpose:** Two-pass cross-reference resolution for `{{ref:*}}` syntax.

**Supported references:**
- `{{ref:fig-N}}` → 圖 N (figure)
- `{{ref:tbl-N}}` → 表 N (table)
- `{{ref:sec-N-M}}` → 第 N.M 節 (heading)

**Implementation:**
- Pass 1: pre-scan builds `ReferenceRegistry` with all fig/tbl/sec IDs
- Pass 2: `registry.substitute(text)` replaces markers with display labels
- Phase 3: renders as Word REF field (`{ REF bookmark \h }`) via `insert_ref_field()`

---

### `src/renderer/seq_field.py`
**Purpose:** OOXML helpers for Word SEQ and REF fields.

- `insert_seq_caption()` — inserts `{ SEQ Name \* ARABIC }` with bookmark
- `insert_ref_field()` — inserts `{ REF bookmark \h }` for cross-references
- Both require F9 or UNO postfix to display final values.

---

### `src/renderer/diagram.py`
**Purpose:** Renders diagram code blocks to PNG images.

- `render_graphviz(code, assets_dir, index)` — tries Python `graphviz` pkg, falls back to `dot` CLI
- `render_mermaid(code, assets_dir, index)` — uses `mmdc` CLI with puppeteer `--no-sandbox` config
- Returns path to generated PNG or `None` if tool unavailable (renderer shows placeholder)

---

### `src/post_processor_uno/post_processor.py`
**Purpose:** Post-processing via LibreOffice to update all Word fields.

**Strategy (Phase 3):**
1. Try UNO socket bridge: starts `soffice --accept=socket,...` then connects via python-uno
2. Dispatches `UpdateAllIndexes` + `UpdateFields` (updates TOC, SEQ captions, REF cross-references)
3. Falls back to headless re-save if socket bridge fails

---

### `src/exporter/exporter.py`
**Purpose:** Converts DOCX to PDF via LibreOffice CLI headless.

```bash
soffice --headless --convert-to pdf --outdir <dir> <docx>
```

---

### `src/state_manager/render_state.py`
**Purpose:** Tracks versioned render history in `render_state.json`.

Each `rerender` increments version and archives: params snapshot, docx path, timestamp.

---

### `src/state_manager/review_state.py`
**Purpose:** Tracks review loop state in `review_state.json`.

Steps: `qc_passed → rendered → postfixed → exported → review_checked`

---

### `src/syncer/syncer.py`
**Status:** Stub — returns skip. Nextcloud WebDAV upload not yet implemented.

---

## params.yaml Schema Reference

See `configs/params.schema.v1.0.yaml` for the full schema.

**Key sections:**
| Section | Description |
|---------|-------------|
| `meta` | Schema version, language |
| `project` | Project ID, title, author, organization, dates, confidentiality |
| `paths` | Input/output file paths, assets directory |
| `page` | Paper size, orientation, margins |
| `cover` | Cover page layout and field visibility flags |
| `toc` | Table of contents: levels, hyperlinks |
| `images` | Caption, numbering mode, max dimensions |
| `tables` | Caption, numbering mode |
| `cross_references` | Reference style (ieee/apa), format strings, hyperlinks |
| `code` | Block and inline code font and shading |
| `diagrams` | Diagram-specific caption prefix and enable flag |
| `caption_chapter_level` | Which heading level triggers chapter increment (default: 2) |

**Not yet implemented:** heading/paragraph styles, header/footer, list styles, color tokens, bibliography, appendix, equations, footnotes.

---

## Known Limitations

1. **Caption chapter numbering:** Based on encounter order of heading level (H2 by default), NOT text content. `## 3. Title` is still "chapter 1" if it's the first H2.
2. **SEQ/REF/TOC fields:** Require F9 or UNO postfix to display final values.
3. **Normalizer:** Not implemented (pass-through stub).
4. **Nextcloud sync:** Not implemented (stub).
5. **params.yaml heading/paragraph styles:** Defined in schema but not yet applied by renderer.
6. **Cross-reference:** REF field implementation; display text before F9 shows placeholder.

---

## Development Notes

### Running tests
```bash
./.venv/bin/pytest -q tests/unit/
```

### Adding a new renderer feature
1. Add token handling in `_render_tokens()` in `renderer.py`
2. If it involves captions, update `CaptionCounter` in `caption.py`
3. Add pre-scan logic in `_pre_scan_references()` if needed for forward refs
4. Write unit tests in `tests/unit/`

### params.yaml override priority
CLI args > params.yaml values > hardcoded defaults
