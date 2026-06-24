"""Analytics layer: standard contact-center KPIs from the SQLite warehouse."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

SLA_MINUTES = 60


def _load_cases(db_path: Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM cases",
            conn,
            parse_dates=["contact_date"],
        )
    return df


def compute_kpis(db_path: Path) -> dict[str, pd.DataFrame]:
    df = _load_cases(db_path)

    total = len(df)
    aht = round(float(df["resolution_time"].mean()), 2)
    escalation_rate = round(float((df["escalation_level"].isin(["T2", "T3"])).mean()) * 100, 2)
    sla_rate = round(float((df["resolution_time"] <= SLA_MINUTES).mean()) * 100, 2)
    avg_qa = round(float(df["qa_score"].mean()), 2)

    summary = pd.DataFrame({
        "metric": [
            "total_cases",
            "avg_handling_time_min",
            "escalation_rate_pct",
            "sla_hit_rate_pct",
            "avg_qa_score",
        ],
        "value": [total, aht, escalation_rate, sla_rate, avg_qa],
    })

    by_category = (
        df.groupby("symptom_category").size().reset_index(name="case_count")
          .sort_values("case_count", ascending=False)
          .reset_index(drop=True)
    )

    by_source = (
        df.groupby("purchase_source").size().reset_index(name="case_count")
          .sort_values("case_count", ascending=False)
          .reset_index(drop=True)
    )

    weekly = (
        df.assign(week=df["contact_date"].dt.to_period("W").astype(str))
          .groupby("week").size().reset_index(name="case_count")
          .sort_values("week")
          .reset_index(drop=True)
    )

    return {
        "summary":     summary,
        "by_category": by_category,
        "by_source":   by_source,
        "weekly":      weekly,
    }
