"""Zero-LLM BM25 vs character-trigram retrieval comparator for blind-spot detection."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from .chunker import Chunk, chunk_text, collect_documents

_TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+")


def _normalize(text: str) -> str:
    return text.lower().replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")


def _words(text: str) -> List[str]:
    return _TOKEN_RE.findall(_normalize(text))


def _trigrams(text: str) -> Counter[str]:
    norm = re.sub(r"\s+", " ", _normalize(text)).strip()
    if len(norm) < 3:
        return Counter([norm] if norm else [])
    return Counter(norm[i : i + 3] for i in range(len(norm) - 2))


def _bm25_scores(query: str, chunks: List[Chunk], k1: float = 1.5, b: float = 0.75) -> List[float]:
    q_terms = _words(query)
    docs = [_words(c.text) for c in chunks]
    n_docs = len(docs)
    if n_docs == 0 or not q_terms:
        return [0.0] * n_docs
    avgdl = sum(len(d) for d in docs) / max(1, n_docs)
    df = Counter()
    for d in docs:
        for term in set(d):
            df[term] += 1

    scores: List[float] = []
    for d in docs:
        tf = Counter(d)
        dl = len(d)
        s = 0.0
        for term in q_terms:
            if tf[term] == 0:
                continue
            idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + k1 * (1 - b + b * (dl / max(1.0, avgdl)))
            s += idf * ((tf[term] * (k1 + 1)) / denom)
        scores.append(round(s, 4))
    return scores


def _trigram_cosine_scores(query: str, chunks: List[Chunk]) -> List[float]:
    qv = _trigrams(query)
    q_norm = math.sqrt(sum(v * v for v in qv.values())) or 1.0
    scores: List[float] = []
    for ch in chunks:
        dv = _trigrams(ch.text)
        d_norm = math.sqrt(sum(v * v for v in dv.values())) or 1.0
        dot = sum(qv[k] * dv[k] for k in qv if k in dv)
        scores.append(round(dot / (q_norm * d_norm), 4))
    return scores


def probe_path(target: str | Path, query: str, chunk_size: int = 800, overlap: int = 100, top_k: int = 5) -> Dict[str, Any]:
    docs = collect_documents(target)
    chunks: List[Chunk] = []
    for doc in docs:
        txt = doc.read_text(encoding="utf-8", errors="ignore")
        rel = doc.name if Path(target).is_file() else str(doc.relative_to(Path(target))).replace("\\", "/")
        chunks.extend(chunk_text(txt, source=rel, chunk_size=chunk_size, overlap=overlap))

    bm25 = _bm25_scores(query, chunks)
    tri = _trigram_cosine_scores(query, chunks)

    bm25_top = sorted(range(len(chunks)), key=lambda i: bm25[i], reverse=True)[:top_k]
    tri_top = sorted(range(len(chunks)), key=lambda i: tri[i], reverse=True)[:top_k]

    bm25_ids = [f"{chunks[i].source}#{chunks[i].index}" for i in bm25_top if bm25[i] > 0]
    tri_ids = [f"{chunks[i].source}#{chunks[i].index}" for i in tri_top if tri[i] > 0]

    return {
        "query": query,
        "chunks_total": len(chunks),
        "bm25_top": [
            {"id": f"{chunks[i].source}#{chunks[i].index}", "score": bm25[i], "preview": chunks[i].text[:120].replace("\n", " ")}
            for i in bm25_top if bm25[i] > 0
        ],
        "trigram_top": [
            {"id": f"{chunks[i].source}#{chunks[i].index}", "score": tri[i], "preview": chunks[i].text[:120].replace("\n", " ")}
            for i in tri_top if tri[i] > 0
        ],
        "blind_spots": {
            "missed_by_bm25_found_by_trigram": [x for x in tri_ids if x not in bm25_ids],
            "missed_by_trigram_found_by_bm25": [x for x in bm25_ids if x not in tri_ids],
        },
    }
