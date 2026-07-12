"""Orchestrate Extract -> Transform -> Quality gate -> Load -> Analytics -> Dashboard."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from src.analytics import compute_kpis
from src.dashboard import render
from src.extract import extract
from src.load import load
from src.quality_gate import evaluate_gate, load_gate_config
from src.transform import transform

INPUT_CSV      = Path("data/synthetic/cases.csv")
WAREHOUSE_DB   = Path("data/warehouse.db")
QUALITY_REPORT = Path("output/quality_report.csv")
DASHBOARD_HTML = Path("output/dashboard.html")
KPI_SUMMARY    = Path("output/kpi_summary.csv")
GATE_CONFIG    = Path("rules/quality_gate.yaml")

EXIT_OK           = 0
EXIT_STEP_FAILED  = 1
EXIT_QUALITY_GATE = 2


def main(
    input_csv: Path = INPUT_CSV,
    warehouse_db: Path = WAREHOUSE_DB,
    quality_report: Path = QUALITY_REPORT,
    dashboard_html: Path = DASHBOARD_HTML,
    kpi_summary: Path = KPI_SUMMARY,
    gate_config_path: Path = GATE_CONFIG,
) -> int:
    step = None
    try:
        step = "extract"
        raw = extract(input_csv)

        step = "transform"
        masked, report = transform(raw, quality_report)

        step = "quality_gate"
        gate_config = load_gate_config(gate_config_path)
        failures = evaluate_gate(report, gate_config)
        if failures:
            print(
                f"[run_pipeline] quality gate FAILED ({len(failures)} check(s) over threshold):",
                file=sys.stderr,
            )
            for f in failures:
                print(
                    f"  - column={f['column']} check={f['check']!r} "
                    f"violations={f['violation_count']} max_allowed={f['max_allowed']}",
                    file=sys.stderr,
                )
            print(
                f"[run_pipeline] aborting before load; see {quality_report}",
                file=sys.stderr,
            )
            return EXIT_QUALITY_GATE

        step = "load"
        load(masked, warehouse_db)

        step = "analytics"
        kpis = compute_kpis(warehouse_db)

        step = "dashboard"
        render(kpis, dashboard_html, kpi_summary)

        print("[run_pipeline] all steps OK")
        return EXIT_OK
    except Exception:
        print(f"[run_pipeline] step failed: {step}", file=sys.stderr)
        traceback.print_exc()
        return EXIT_STEP_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
