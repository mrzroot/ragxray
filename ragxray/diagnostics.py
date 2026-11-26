"""Zero-LLM chunk-boundary fracture and near-duplicate diagnostics."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set

from .chunker import Chunk, chunk_text, collect_documents

_HEADING_END_RE = re.compile(r"(?:^|\n)#{1,6}\s+[^\n]+\s*$")
_TABLE_ROW_RE = re.compile(r"^\|.*\|\s*$")


def _shingles(text: str, k: int = 5) -> Set[str]:
    norm = re.sub(r"\s+", " ", text.lower()).strip()
    if len(norm) < k:
        return {norm} if norm else set()
    return {norm[i : i + k] for i in range(len(norm) - k + 1)}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def diagnose_chunks(full_text: str, chunks: List[Chunk]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        t = ch.text
        # 1. Unclosed fenced code block inside chunk
        if t.count("```") % 2 == 1:
            issues.append({"chunk": ch.index, "source": ch.source, "kind": "split_code_block", "detail": "Fenced code block (```) cut across chunk boundary."})

        # 2. Markdown table split across consecutive chunks (either at row boundary or mid-row)
        lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
        if lines and i + 1 < len(chunks):
            next_lines = [ln.strip() for ln in chunks[i + 1].text.splitlines() if ln.strip()]
            tail_table = lines[-1].startswith("|") or (len(lines) >= 2 and _TABLE_ROW_RE.match(lines[-2]) and "|" in lines[-1])
            head_table = bool(next_lines and (next_lines[0].startswith("|") or next_lines[0].endswith("|")))
            has_real_row = any(_TABLE_ROW_RE.match(ln) for ln in (lines[-2:] + next_lines[:2]))
            if tail_table and head_table and has_real_row:
                issues.append({"chunk": ch.index, "source": ch.source, "kind": "split_markdown_table", "detail": "Markdown table rows split across chunk boundary."})

        # 3. Orphan heading at the end of a chunk
        if _HEADING_END_RE.search(t.rstrip()):
            issues.append({"chunk": ch.index, "source": ch.source, "kind": "orphan_heading", "detail": "Markdown heading sits at the end of the chunk without its body."})

        # 4. Mid-sentence cut (English or Persian/Arabic) when chunk does not end document
        if ch.end < len(full_text):
            tail = t.rstrip()
            if tail and tail[-1] not in ".!?\n؟۔»\"')]}":
                # Check if next char in document continues a word or sentence
                nxt = full_text[ch.end : ch.end + 1]
                if nxt and not nxt.isspace():
                    issues.append({"chunk": ch.index, "source": ch.source, "kind": "mid_word_split", "detail": "Chunk splits directly in the middle of a word."})
                else:
                    issues.append({"chunk": ch.index, "source": ch.source, "kind": "mid_sentence_split", "detail": "Chunk ends mid-sentence before punctuation."})

    # 5. Near-duplicate non-adjacent chunks
    sh_list = [_shingles(c.text) for c in chunks]
    for i in range(len(chunks)):
        for j in range(i + 2, len(chunks)):
            sim = _jaccard(sh_list[i], sh_list[j])
            if sim >= 0.8:
                issues.append({"chunk": chunks[i].index, "other_chunk": chunks[j].index, "source": chunks[i].source, "kind": "near_duplicate_chunk", "similarity": round(sim, 3), "detail": f"Chunks {chunks[i].index} and {chunks[j].index} are {sim:.0%} similar."})
    return issues


def inspect_path(target: str | Path, chunk_size: int = 800, overlap: int = 100) -> Dict[str, Any]:
    docs = collect_documents(target)
    all_chunks: List[Chunk] = []
    all_issues: List[Dict[str, Any]] = []

    for doc in docs:
        txt = doc.read_text(encoding="utf-8", errors="ignore")
        rel = doc.name if Path(target).is_file() else str(doc.relative_to(Path(target))).replace("\\", "/")
        chs = chunk_text(txt, source=rel, chunk_size=chunk_size, overlap=overlap)
        all_chunks.extend(chs)
        all_issues.extend(diagnose_chunks(txt, chs))

    by_kind: Dict[str, int] = {}
    for iss in all_issues:
        by_kind[iss["kind"]] = by_kind.get(iss["kind"], 0) + 1

    recommendation = "Chunks look structurally clean."
    if by_kind.get("split_code_block") or by_kind.get("split_markdown_table"):
        recommendation = "Switch to structure-aware splitting on Markdown headings/fences/tables before fixed-size chunking."
    elif by_kind.get("mid_word_split") or by_kind.get("mid_sentence_split"):
        recommendation = f"Use sentence-boundary snapping or increase overlap (current: chunk_size={chunk_size}, overlap={overlap})."

    return {
        "files": len(docs),
        "chunks": len(all_chunks),
        "chunk_size": chunk_size,
        "overlap": overlap,
        "issue_count": len(all_issues),
        "issues_by_kind": by_kind,
        "recommendation": recommendation,
        "issues": all_issues,
    }
