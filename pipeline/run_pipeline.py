"""Orchestrate Extract -> Transform -> Load -> Analytics -> Dashboard."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from src.analytics import compute_kpis
from src.dashboard import render
from src.extract import extract
from src.load import load
from src.transform import transform

INPUT_CSV      = Path("data/synthetic/cases.csv")
WAREHOUSE_DB   = Path("data/warehouse.db")
QUALITY_REPORT = Path("output/quality_report.csv")
DASHBOARD_HTML = Path("output/dashboard.html")
KPI_SUMMARY    = Path("output/kpi_summary.csv")


def main() -> int:
    step = None
    try:
        step = "extract"
        raw = extract(INPUT_CSV)

        step = "transform"
        masked = transform(raw, QUALITY_REPORT)

        step = "load"
        load(masked, WAREHOUSE_DB)

        step = "analytics"
        kpis = compute_kpis(WAREHOUSE_DB)

        step = "dashboard"
        render(kpis, DASHBOARD_HTML, KPI_SUMMARY)

        print("[run_pipeline] all steps OK")
        return 0
    except Exception:
        print(f"[run_pipeline] step failed: {step}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
