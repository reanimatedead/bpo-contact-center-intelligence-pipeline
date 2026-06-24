"""Render KPI tables as HTML (plain) and CSV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CSS = """
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 900px; margin: 2rem auto; padding: 0 1rem;
         color: #1a1a1a; background: #fafafa; }
  h1 { margin-bottom: 0.5rem; }
  .note { color: #666; font-size: 0.9rem; }
  h2 { margin-top: 2rem; font-size: 1.1rem;
       border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; }
  table { border-collapse: collapse; margin: 0.5rem 0 1.5rem; width: 100%; }
  th, td { border: 1px solid #ddd; padding: 0.4rem 0.7rem;
           text-align: left; font-size: 0.95rem; }
  th { background: #f0f0f0; }
</style>
"""


def render(kpis: dict[str, pd.DataFrame], html_path: Path, csv_path: Path) -> None:
    html_path.parent.mkdir(parents=True, exist_ok=True)

    parts = [
        '<!doctype html>',
        '<html lang="en"><head><meta charset="utf-8">',
        '<title>BPO Contact Center KPI Dashboard</title>',
        CSS,
        '</head><body>',
        '<h1>BPO Contact Center KPI Dashboard</h1>',
        '<p class="note">Synthetic data only - no real client data is represented.</p>',
        '<h2>Summary</h2>',
        kpis["summary"].to_html(index=False, border=0),
        '<h2>Cases by symptom category</h2>',
        kpis["by_category"].to_html(index=False, border=0),
        '<h2>Cases by purchase source</h2>',
        kpis["by_source"].to_html(index=False, border=0),
        '<h2>Weekly trend</h2>',
        kpis["weekly"].to_html(index=False, border=0),
        '</body></html>',
    ]
    html_path.write_text("\n".join(parts), encoding="utf-8")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8") as f:
        for name, table in kpis.items():
            f.write(f"# {name}\n")
            table.to_csv(f, index=False)
            f.write("\n")

    print(f"[dashboard] rendered -> {html_path}, {csv_path}")
