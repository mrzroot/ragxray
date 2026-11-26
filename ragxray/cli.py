"""CLI entrypoint for ragxray."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .diagnostics import inspect_path
from .html_report import render_html_report
from .retriever import probe_path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ragxray", description="Zero-LLM chunk-boundary and retrieval debugger for RAG.")
    p.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("inspect", help="Inspect documents for structural chunking fractures.")
    pi.add_argument("path", help="File or directory to inspect")
    pi.add_argument("--chunk-size", type=int, default=800)
    pi.add_argument("--overlap", type=int, default=100)
    pi.add_argument("--html", help="Write self-contained HTML report")
    pi.add_argument("--json", action="store_true")

    pp = sub.add_parser("probe", help="Compare BM25 vs character-trigram retrieval blind spots.")
    pp.add_argument("path", help="File or directory to index")
    pp.add_argument("--query", required=True, help="Search query")
    pp.add_argument("--chunk-size", type=int, default=800)
    pp.add_argument("--overlap", type=int, default=100)
    pp.add_argument("--top-k", type=int, default=5)
    pp.add_argument("--json", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "inspect":
        rep = inspect_path(args.path, chunk_size=args.chunk_size, overlap=args.overlap)
        if args.html:
            Path(args.html).write_text(render_html_report(rep), encoding="utf-8")
        if args.json:
            sys.stdout.write(json.dumps(rep, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(f"ragxray v{__version__} · files={rep['files']} · chunks={rep['chunks']} · issues={rep['issue_count']}\n")
            for k, v in rep["issues_by_kind"].items():
                sys.stdout.write(f"  - {k}: {v}\n")
            sys.stdout.write(f"Recommendation: {rep['recommendation']}\n")
        return 0

    if args.command == "probe":
        rep = probe_path(args.path, query=args.query, chunk_size=args.chunk_size, overlap=args.overlap, top_k=args.top_k)
        if args.json:
            sys.stdout.write(json.dumps(rep, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(f"Query: {rep['query']} ({rep['chunks_total']} chunks)\n")
            sys.stdout.write(f"Missed by BM25, found by Trigram: {rep['blind_spots']['missed_by_bm25_found_by_trigram']}\n")
            sys.stdout.write(f"Missed by Trigram, found by BM25: {rep['blind_spots']['missed_by_trigram_found_by_bm25']}\n")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
