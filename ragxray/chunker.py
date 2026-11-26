"""Deterministic character-window chunker with file discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Chunk:
    index: int
    source: str
    start: int
    end: int
    text: str


def chunk_text(text: str, source: str, chunk_size: int = 800, overlap: int = 100) -> List[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    step = max(1, chunk_size - max(0, min(overlap, chunk_size - 1)))
    chunks: List[Chunk] = []
    pos = 0
    idx = 0
    while pos < len(text):
        end = min(len(text), pos + chunk_size)
        chunks.append(Chunk(index=idx, source=source, start=pos, end=end, text=text[pos:end]))
        if end >= len(text):
            break
        pos += step
        idx += 1
    return chunks


def collect_documents(target: str | Path) -> List[Path]:
    p = Path(target)
    if p.is_file():
        return [p]
    exts = {".md", ".txt", ".py", ".ts", ".js", ".rst"}
    skip = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}
    docs: List[Path] = []
    for child in sorted(p.rglob("*")):
        if any(part in skip for part in child.parts):
            continue
        if child.is_file() and child.suffix.lower() in exts:
            docs.append(child)
    return docs
