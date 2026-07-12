"""Quality gate: evaluate the transform quality report against thresholds.

Thresholds live in ``rules/quality_gate.yaml`` (configuration, not code).
The pipeline runner turns any gate failure into a non-zero exit code so that
quality violations block downstream consumption instead of only landing in a
CSV nobody reads.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

DEFAULT_GATE_CONFIG = Path("rules/quality_gate.yaml")


def load_gate_config(path: Path = DEFAULT_GATE_CONFIG) -> dict:
    """Load the gate thresholds from YAML."""
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"quality gate config is not a mapping: {path}")
    return config


def _max_allowed(check: str, config: dict) -> int:
    default = int(config.get("default_max_violations", 0))
    checks = config.get("checks") or {}
    for prefix, rule in checks.items():
        if check.startswith(str(prefix)):
            return int((rule or {}).get("max_violations", default))
    return default


def evaluate_gate(report: pd.DataFrame, config: dict) -> list[dict]:
    """Return the list of gate failures (empty list = gate passed).

    Each failure describes the offending quality-report row and the limit
    it exceeded.
    """
    failures: list[dict] = []
    for row in report.itertuples(index=False):
        check = str(row.check)
        count = int(row.violation_count)
        allowed = _max_allowed(check, config)
        if count > allowed:
            failures.append({
                "column": str(row.column),
                "check": check,
                "violation_count": count,
                "max_allowed": allowed,
            })
    return failures
