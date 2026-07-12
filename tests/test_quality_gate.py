"""Tests for the quality gate (threshold evaluation + pipeline exit codes)."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from pipeline.run_pipeline import EXIT_OK, EXIT_QUALITY_GATE, main
from src.quality_gate import evaluate_gate, load_gate_config

GATE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "rules" / "quality_gate.yaml"

COLUMNS = [
    "case_id", "contact_date", "customer_name", "customer_phone",
    "customer_email", "symptom_category", "symptom_description",
    "purchase_source", "warranty_status", "third_party",
    "resolution_time", "qa_score", "escalation_level", "agent_id",
]


def _case_row(i: int, resolution_time: int = 30, qa_score: int = 3) -> dict:
    return {
        "case_id":             f"CASE-{i:05d}",
        "contact_date":        "2026-06-01",
        "customer_name":       f"Customer {i}",
        "customer_phone":      f"123-456-{7000 + i:04d}",
        "customer_email":      f"customer{i}@example.com",
        "symptom_category":    "battery",
        "symptom_description": "battery drains rapidly",
        "purchase_source":     "official",
        "warranty_status":     "in_scope",
        "third_party":         False,
        "resolution_time":     resolution_time,
        "qa_score":            qa_score,
        "escalation_level":    "T1",
        "agent_id":            "AGENT-001",
    }


def _write_cases(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _run(tmp_path: Path, rows: list[dict]) -> int:
    input_csv = tmp_path / "cases.csv"
    _write_cases(input_csv, rows)
    return main(
        input_csv=input_csv,
        warehouse_db=tmp_path / "warehouse.db",
        quality_report=tmp_path / "quality_report.csv",
        dashboard_html=tmp_path / "dashboard.html",
        kpi_summary=tmp_path / "kpi_summary.csv",
        gate_config_path=GATE_CONFIG_PATH,
    )


def test_evaluate_gate_flags_rows_over_threshold():
    config = load_gate_config(GATE_CONFIG_PATH)
    report = pd.DataFrame([
        {"column": "qa_score", "check": "range [1, 5]", "violation_count": 2, "total": "10"},
        {"column": "qa_score", "check": "missing",      "violation_count": 0, "total": "10"},
    ])
    failures = evaluate_gate(report, config)
    assert len(failures) == 1
    assert failures[0]["column"] == "qa_score"
    assert failures[0]["check"] == "range [1, 5]"
    assert failures[0]["violation_count"] == 2
    assert failures[0]["max_allowed"] == 0


def test_evaluate_gate_passes_clean_report():
    config = load_gate_config(GATE_CONFIG_PATH)
    report = pd.DataFrame([
        {"column": "qa_score",        "check": "missing",      "violation_count": 0, "total": "10"},
        {"column": "resolution_time", "check": "range (>= 1)", "violation_count": 0, "total": "10"},
    ])
    assert evaluate_gate(report, config) == []


def test_pipeline_exits_zero_on_clean_data(tmp_path):
    rows = [_case_row(i) for i in range(1, 6)]
    assert _run(tmp_path, rows) == EXIT_OK


def test_pipeline_exits_nonzero_on_quality_violation(tmp_path):
    rows = [_case_row(i) for i in range(1, 5)]
    rows.append(_case_row(5, qa_score=9))       # out of range [1, 5]
    rows.append(_case_row(6, resolution_time=0))  # below minimum 1
    exit_code = _run(tmp_path, rows)
    assert exit_code == EXIT_QUALITY_GATE
    assert exit_code != 0


def test_pipeline_gate_failure_skips_load(tmp_path):
    rows = [_case_row(1, qa_score=9)]
    _run(tmp_path, rows)
    assert not (tmp_path / "warehouse.db").exists()
    assert not (tmp_path / "dashboard.html").exists()
