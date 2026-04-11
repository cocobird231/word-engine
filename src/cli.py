"""
Word Engine CLI

Commands:
  qc          Run QC check (lint + validate + normalize). Does not produce output.
  render      First-time render (unversioned). Produces output.docx.
  rerender    Versioned re-render after params/content changes. Archives params
              snapshot and increments version counter in render_state.json.
  export      Export a .docx to .pdf via LibreOffice CLI.
  postfix     Run UNO post-processing on a docx (Phase 2 stub).
  run         All-in-one: QC → render → export (unversioned, for quick testing).

Semantic notes:
  - Use `render` for the first time you produce a docx from new content.
  - Use `rerender` every time you tweak params.yaml or refine.md and want a
    new versioned output. Each call increments the version and archives artifacts.
  - Use `run` for quick end-to-end checks without version tracking.
"""
import argparse
from src.pipeline import run_qc, run_render, run_rerender, run_export, run_postfix, run_review, run_all


def main():
    parser = argparse.ArgumentParser(
        description="Word Engine - Markdown to DOCX/PDF document pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── qc ──────────────────────────────────────────────────────────────────
    qc_parser = subparsers.add_parser(
        "qc",
        help="Run QC check (lint + validate + normalize). Does not produce output."
    )
    qc_parser.add_argument("--md", required=True, metavar="PATH", help="Path to refine.md")
    qc_parser.add_argument("--params", required=True, metavar="PATH", help="Path to params.yaml")

    # ── render ───────────────────────────────────────────────────────────────
    render_parser = subparsers.add_parser(
        "render",
        help="First-time render (unversioned). Produces a single output.docx."
    )
    render_parser.add_argument("--md", required=True, metavar="PATH", help="Path to refine.md")
    render_parser.add_argument("--params", required=True, metavar="PATH", help="Path to params.yaml")
    render_parser.add_argument("--output", default="output.docx", metavar="PATH", help="Output docx path")

    # ── rerender ─────────────────────────────────────────────────────────────
    rerender_parser = subparsers.add_parser(
        "rerender",
        help=(
            "Versioned re-render. Increments version counter, archives params "
            "snapshot, and saves output to documents/report_vN.docx."
        )
    )
    rerender_parser.add_argument("--md", required=True, metavar="PATH", help="Path to refine.md")
    rerender_parser.add_argument("--params", required=True, metavar="PATH", help="Path to params.yaml")
    rerender_parser.add_argument(
        "--project-dir", default=".", metavar="DIR",
        help="Project root directory where render_state.json is stored (default: .)"
    )
    rerender_parser.add_argument(
        "--label", default=None, metavar="LABEL",
        help="Optional human-readable label for this version (e.g. 'fix-heading-indent')"
    )
    rerender_parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing version artifacts without error"
    )

    # ── export ───────────────────────────────────────────────────────────────
    export_parser = subparsers.add_parser(
        "export",
        help="Export a .docx file to .pdf via LibreOffice CLI."
    )
    export_parser.add_argument("--docx", required=True, metavar="PATH", help="Path to input .docx")
    export_parser.add_argument("--output", default="output.pdf", metavar="PATH", help="Output pdf path")

    # ── postfix ──────────────────────────────────────────────────────────────
    postfix_parser = subparsers.add_parser(
        "postfix",
        help="Run UNO post-processing on a docx (Phase 2 stub, Phase 3 real impl)."
    )
    postfix_parser.add_argument("--docx", required=True, metavar="PATH", help="Path to .docx to post-process")

    # ── review ───────────────────────────────────────────────────────────────
    review_parser = subparsers.add_parser(
        "review",
        help=(
            "Full review loop: QC → rerender → postfix → export. "
            "Records status in review_state.json."
        )
    )
    review_parser.add_argument("--md", required=True, metavar="PATH", help="Path to refine.md")
    review_parser.add_argument("--params", required=True, metavar="PATH", help="Path to params.yaml")
    review_parser.add_argument(
        "--project-dir", default=".", metavar="DIR",
        help="Project root directory (default: .)"
    )
    review_parser.add_argument(
        "--label", default=None, metavar="LABEL",
        help="Optional label for this review version"
    )
    review_parser.add_argument(
        "--skip-postfix", action="store_true",
        help="Skip UNO postfix step for faster iteration"
    )

    # ── run ──────────────────────────────────────────────────────────────────
    run_parser = subparsers.add_parser(
        "run",
        help="All-in-one: QC → render → export. Unversioned, for quick testing."
    )
    run_parser.add_argument("--md", required=True, metavar="PATH", help="Path to refine.md")
    run_parser.add_argument("--params", required=True, metavar="PATH", help="Path to params.yaml")

    # ── dispatch ──────────────────────────────────────────────────────────────
    args = parser.parse_args()

    if args.command == "qc":
        run_qc(args.md, args.params)
    elif args.command == "render":
        run_render(args.md, args.params, args.output)
    elif args.command == "rerender":
        run_rerender(
            md_path=args.md,
            params_path=args.params,
            project_dir=args.project_dir,
            label=args.label,
            force=args.force,
        )
    elif args.command == "export":
        run_export(args.docx, args.output)
    elif args.command == "postfix":
        run_postfix(args.docx)
    elif args.command == "review":
        run_review(
            md_path=args.md,
            params_path=args.params,
            project_dir=args.project_dir,
            label=args.label,
            skip_postfix=args.skip_postfix,
        )
    elif args.command == "run":
        run_all(args.md, args.params)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
