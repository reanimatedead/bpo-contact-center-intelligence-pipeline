"""Tests for the transform layer (PII masking + quality checks)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.transform import (
    PII_HMAC_KEY_ENV,
    MissingPIIKeyError,
    mask_email,
    mask_name,
    mask_phone,
    pseudonymize,
    quality_report,
)


def test_mask_name_is_deterministic():
    assert mask_name("Alice") == mask_name("Alice")
    assert mask_name("Alice") != mask_name("Bob")


def test_mask_raises_without_key(monkeypatch):
    monkeypatch.delenv(PII_HMAC_KEY_ENV, raising=False)
    with pytest.raises(MissingPIIKeyError):
        mask_name("Alice")
    with pytest.raises(MissingPIIKeyError):
        mask_email("alice@example.com")


def test_mask_raises_on_empty_key(monkeypatch):
    monkeypatch.setenv(PII_HMAC_KEY_ENV, "")
    with pytest.raises(MissingPIIKeyError):
        mask_name("Alice")


def test_mask_is_deterministic_under_same_key(monkeypatch):
    monkeypatch.setenv(PII_HMAC_KEY_ENV, "key-one")
    first = mask_name("Alice")
    second = mask_name("Alice")
    assert first == second
    assert mask_email("alice@example.com") == mask_email("alice@example.com")


def test_mask_output_changes_with_key(monkeypatch):
    monkeypatch.setenv(PII_HMAC_KEY_ENV, "key-one")
    with_key_one = mask_name("Alice")
    email_key_one = mask_email("alice@example.com")
    monkeypatch.setenv(PII_HMAC_KEY_ENV, "key-two")
    assert mask_name("Alice") != with_key_one
    assert mask_email("alice@example.com") != email_key_one


def test_mask_name_handles_empty():
    assert mask_name("") == ""
    assert mask_name(None) == ""


def test_mask_phone_keeps_last_four_only():
    out = mask_phone("123-456-7890")
    assert out.endswith("7890")
    assert "123" not in out
    assert "456" not in out


def test_mask_phone_short_input():
    assert mask_phone("12") == "***-***-****"


def test_mask_email_preserves_domain():
    out = mask_email("alice.smith@example.com")
    assert out.endswith("@example.com")
    assert "alice" not in out
    assert "smith" not in out


def test_mask_email_handles_malformed():
    assert mask_email("not-an-email") == ""


def test_pseudonymize_drops_all_raw_pii_keeps_other_columns():
    df = pd.DataFrame({
        "customer_name":  ["Alice"],
        "customer_phone": ["123-456-7890"],
        "customer_email": ["alice@example.com"],
        "case_id":        ["CASE-00001"],
    })
    out = pseudonymize(df)
    assert "Alice" not in out["customer_name"].iloc[0]
    assert "123"   not in out["customer_phone"].iloc[0]
    assert "alice" not in out["customer_email"].iloc[0]
    assert out["case_id"].iloc[0] == "CASE-00001"


def test_quality_report_flags_qa_score_out_of_range():
    raw = pd.DataFrame({
        "customer_name":   ["A", "B"],
        "customer_phone":  ["111-111-1111", "222-222-2222"],
        "customer_email":  ["a@x.com", "b@x.com"],
        "qa_score":        [3, 9],
        "resolution_time": [30, 60],
    })
    masked = pseudonymize(raw)
    report = quality_report(raw, masked)
    qa_row = report[
        (report["column"] == "qa_score")
        & (report["check"].str.startswith("range"))
    ]
    assert int(qa_row["violation_count"].iloc[0]) == 1


def test_quality_report_nan_resolution_time_counts_missing_not_range():
    raw = pd.DataFrame({
        "customer_name":   ["A", "B"],
        "customer_phone":  ["111-111-1111", "222-222-2222"],
        "customer_email":  ["a@x.com", "b@x.com"],
        "qa_score":        [3, 4],
        "resolution_time": [float("nan"), 30],
    })
    masked = pseudonymize(raw)
    report = quality_report(raw, masked)
    missing_row = report[
        (report["column"] == "resolution_time") & (report["check"] == "missing")
    ]
    range_row = report[
        (report["column"] == "resolution_time")
        & (report["check"].str.startswith("range"))
    ]
    assert int(missing_row["violation_count"].iloc[0]) == 1
    assert int(range_row["violation_count"].iloc[0]) == 0


def test_quality_report_flags_resolution_time_zero():
    raw = pd.DataFrame({
        "customer_name":   ["A"],
        "customer_phone":  ["111-111-1111"],
        "customer_email":  ["a@x.com"],
        "qa_score":        [3],
        "resolution_time": [0],
    })
    masked = pseudonymize(raw)
    report = quality_report(raw, masked)
    rt_row = report[
        (report["column"] == "resolution_time")
        & (report["check"].str.startswith("range"))
    ]
    assert int(rt_row["violation_count"].iloc[0]) == 1
