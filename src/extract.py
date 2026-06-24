"""Extract layer: read raw synthetic cases from CSV and validate schema."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "case_id",
    "contact_date",
    "customer_name",
    "customer_phone",
    "customer_email",
    "symptom_category",
    "symptom_description",
    "purchase_source",
    "warranty_status",
    "third_party",
    "resolution_time",
    "qa_score",
    "escalation_level",
    "agent_id",
}


def extract(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"input not found: {path}. did you run `make seed`?")
    df = pd.read_csv(path, parse_dates=["contact_date"])
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"input schema missing columns: {sorted(missing)}")
    print(f"[extract] loaded {len(df)} rows <- {path}")
    return df
