"""Transform layer: PII pseudonymization + data quality checks.

This layer runs BEFORE the load step. Raw PII never reaches the warehouse.

Pseudonymization uses keyed HMAC-SHA256. The key MUST be provided via the
``BPO_PII_HMAC_KEY`` environment variable; there is no fallback. An unkeyed
hash of low-entropy inputs (names, email local parts) is trivially reversible
by dictionary attack, so running without a key is treated as a hard error.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

import pandas as pd

QA_SCORE_RANGE = (1, 5)
RESOLUTION_TIME_MIN = 1

PII_HMAC_KEY_ENV = "BPO_PII_HMAC_KEY"


class MissingPIIKeyError(RuntimeError):
    """Raised when the PII pseudonymization key is not configured."""


def _get_hmac_key() -> bytes:
    key = os.environ.get(PII_HMAC_KEY_ENV, "")
    if not key:
        raise MissingPIIKeyError(
            f"PII pseudonymization key is not set. Export {PII_HMAC_KEY_ENV} "
            "(a long random secret, e.g. `openssl rand -hex 32`) before running "
            "the pipeline. Refusing to fall back to unkeyed hashing because it "
            "is reversible by dictionary attack."
        )
    return key.encode("utf-8")


def _hmac_short(value: str) -> str:
    return hmac.new(_get_hmac_key(), value.encode("utf-8"), hashlib.sha256).hexdigest()[:12]


def mask_name(name) -> str:
    if not isinstance(name, str) or not name:
        return ""
    return _hmac_short(name)


def mask_phone(phone) -> str:
    if not isinstance(phone, str):
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 4:
        return "***-***-****"
    return f"***-***-{digits[-4:]}"


def mask_email(email) -> str:
    if not isinstance(email, str) or "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    return f"{_hmac_short(local)}@{domain}"


def pseudonymize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["customer_name"]  = out["customer_name"].map(mask_name)
    out["customer_phone"] = out["customer_phone"].map(mask_phone)
    out["customer_email"] = out["customer_email"].map(mask_email)
    return out


def quality_report(df_raw: pd.DataFrame, df_masked: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []

    for col in df_raw.columns:
        missing = int(df_raw[col].isna().sum())
        rows.append({
            "column":          col,
            "check":           "missing",
            "violation_count": missing,
            "total":           str(len(df_raw)),
        })

    rt = df_raw.get("resolution_time")
    if rt is not None:
        # NaN rows are already counted by the "missing" check above;
        # the range check only applies to non-missing values.
        bad = int((rt.dropna() < RESOLUTION_TIME_MIN).sum())
        rows.append({
            "column":          "resolution_time",
            "check":           f"range (>= {RESOLUTION_TIME_MIN})",
            "violation_count": bad,
            "total":           str(len(df_raw)),
        })

    qa = df_raw.get("qa_score")
    if qa is not None:
        lo, hi = QA_SCORE_RANGE
        bad = int(((qa < lo) | (qa > hi)).sum())
        rows.append({
            "column":          "qa_score",
            "check":           f"range [{lo}, {hi}]",
            "violation_count": bad,
            "total":           str(len(df_raw)),
        })

    for col in ("customer_name", "customer_phone", "customer_email"):
        raw_distinct    = int(df_raw[col].nunique())
        masked_distinct = int(df_masked[col].nunique())
        rows.append({
            "column":          col,
            "check":           "masking distinct (raw -> masked)",
            "violation_count": 0,
            "total":           f"{raw_distinct} -> {masked_distinct}",
        })

    return pd.DataFrame(rows)


def transform(df: pd.DataFrame, report_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pseudonymize and quality-check the raw frame.

    Returns ``(masked, report)`` so the caller can evaluate the quality gate
    against the report instead of only writing it to CSV.
    """
    masked = pseudonymize(df)
    report = quality_report(df, masked)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(report_path, index=False)
    print(f"[transform] pseudonymized {len(masked)} rows; quality report -> {report_path}")
    return masked, report
