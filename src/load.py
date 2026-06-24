"""Load layer: write the masked DataFrame to a SQLite warehouse."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def load(df: pd.DataFrame, db_path: Path, table: str = "cases") -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table, conn, if_exists="replace", index=False)
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"[load] wrote {count} rows -> {db_path}::{table}")
