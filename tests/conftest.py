"""Shared test fixtures."""

from __future__ import annotations

import pytest

from src.transform import PII_HMAC_KEY_ENV

TEST_HMAC_KEY = "test-only-hmac-key-not-for-production"


@pytest.fixture(autouse=True)
def pii_hmac_key(monkeypatch):
    """Provide a deterministic test-only HMAC key for every test.

    Individual tests can override or remove it with monkeypatch.
    """
    monkeypatch.setenv(PII_HMAC_KEY_ENV, TEST_HMAC_KEY)
    yield monkeypatch
