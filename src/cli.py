import argparse
from src.pipeline import run_qc, run_render, run_export, run_all

def main():
    parser = argparse.ArgumentParser(description="Word Engine CLI (Phase 1 MVP)")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Command: qc
    qc_parser = subparsers.add_parser("qc", help="Run QC process (lint, validate, normalize)")
    qc_parser.add_argument("--md", required=True, help="Path to markdown file (refine.md)")
    qc_parser.add_argument("--params", required=True, help="Path to params.yaml")

    # Command: render
    render_parser = subparsers.add_parser("render", help="Render markdown to docx")
    render_parser.add_argument("--md", required=True, help="Path to markdown file")
    render_parser.add_argument("--params", required=True, help="Path to params.yaml")
    render_parser.add_argument("--output", default="output.docx", help="Output docx path")

    # Command: export
    export_parser = subparsers.add_parser("export", help="Export docx to pdf")
    export_parser.add_argument("--docx", required=True, help="Path to docx file")
    export_parser.add_argument("--output", default="output.pdf", help="Output pdf path")

    # Command: run (all-in-one)
    run_parser = subparsers.add_parser("run", help="Run full pipeline (qc -> render -> export)")
    run_parser.add_argument("--md", required=True, help="Path to markdown file")
    run_parser.add_argument("--params", required=True, help="Path to params.yaml")

    args = parser.parse_args()

    if args.command == "qc":
        run_qc(args.md, args.params)
    elif args.command == "render":
        run_render(args.md, args.params, args.output)
    elif args.command == "export":
        run_export(args.docx, args.output)
    elif args.command == "run":
        run_all(args.md, args.params)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
