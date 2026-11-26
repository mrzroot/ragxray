import json
from pathlib import Path

from ragxray.cli import main
from ragxray.diagnostics import inspect_path
from ragxray.retriever import probe_path


def test_detects_table_code_orphan_and_persian_splits(tmp_path: Path, capsys):
    doc = tmp_path / "guide.md"
    doc.write_text(
        "\n".join(
            [
                "# Introduction",
                "این یک متن فارسی برای بررسی مرز جمله‌ها در سیستم‌های بازیابی است و نباید وسط کلمه قطع شود.",
                "",
                "## Configuration Table",
                "| Key | Value | Description |",
                "|---|---|---|",
                "| timeout | 30 | request timeout seconds |",
                "| retries | 3 | max retry attempts |",
                "",
                "## Code Sample",
                "```python",
                "def hello_rag_debugger():",
                "    config = {'timeout': 30, 'retries': 3, 'mode': 'strict'}",
                "    return config['mode']",
                "```",
            ]
        ),
        encoding="utf-8",
    )

    rep = inspect_path(doc, chunk_size=80, overlap=10)
    kinds = set(rep["issues_by_kind"].keys())
    assert "split_markdown_table" in kinds and "split_code_block" in kinds
    assert rep["issue_count"] >= 2

    html_out = tmp_path / "rep.html"
    assert main(["inspect", str(doc), "--chunk-size", "80", "--html", str(html_out), "--json"]) == 0
    assert html_out.exists()
    capsys.readouterr()


def test_bm25_vs_trigram_probe_finds_persian_blind_spots(tmp_path: Path):
    doc = tmp_path / "notes.md"
    doc.write_text(
        "معماری میکروسرویس و مدیریت خطاهای شبکه در پایتون.\n\nپیکربندی پایگاه داده و کش ردیس.",
        encoding="utf-8",
    )
    # Slight morphological/typo variant "میکروسرویسها" misses exact BM25 word match, caught by trigram
    res = probe_path(doc, query="میکروسرویسها", chunk_size=70, overlap=10, top_k=3)
    assert len(res["trigram_top"]) >= 1
    assert len(res["blind_spots"]["missed_by_bm25_found_by_trigram"]) >= 1
