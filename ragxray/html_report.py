"""Self-contained HTML report generator for ragxray."""

from __future__ import annotations

import html
import json
from typing import Any, Dict


def render_html_report(report: Dict[str, Any]) -> str:
    payload = html.escape(json.dumps(report, ensure_ascii=False))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>ragxray Chunk Report</title>
<style>body{{margin:0;background:#120e0a;color:#f6ecd9;font-family:system-ui,sans-serif;padding:24px}}.wrap{{max-width:960px;margin:0 auto}}.card{{background:#1a1510;border:1px solid #3b2e20;border-radius:14px;padding:16px;margin:12px 0}}pre{{background:#241d16;padding:12px;border-radius:10px;overflow:auto}}</style>
</head><body><div class="wrap"><h1>ragxray Chunk-Boundary Diagnostics</h1><div class="card" id="summary"></div><pre id="raw"></pre></div>
<script>const R = JSON.parse(document.getElementById("raw").dataset.json || "{payload}");</script>
<script>
  const data = {json.dumps(report, ensure_ascii=False)};
  document.getElementById("summary").innerHTML = `<b>Files:</b> ${{data.files}} · <b>Chunks:</b> ${{data.chunks}} · <b>Issues:</b> ${{data.issue_count}}<br><b>Recommendation:</b> ${{data.recommendation}}`;
  document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
</script></body></html>"""
