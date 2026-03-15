"""Tests for pre_llm gate Python-side logic (PII redaction)."""
from __future__ import annotations

import pytest

from risk_gates.gates.pre_llm import _redact_pii
from risk_gates.schemas import PIIMatch


class TestRedactPII:
    def test_ssn_redacted(self) -> None:
        text = "My SSN is 123-45-6789 please help."
        result, matches = _redact_pii(text)
        assert "123-45-6789" not in result
        assert "6789" in result  # last 4 preserved
        assert len(matches) == 1
        assert matches[0].pii_type == "ssn"

    def test_email_redacted(self) -> None:
        text = "Contact me at john.doe@example.com for details."
        result, matches = _redact_pii(text)
        assert "john.doe@example.com" not in result
        assert "jo" in result  # first 2 chars preserved
        assert any(m.pii_type == "email" for m in matches)

    def test_credit_card_redacted(self) -> None:
        text = "My card is 4111 1111 1111 1111."
        result, matches = _redact_pii(text)
        assert "4111 1111 1111 1111" not in result
        assert "1111" in result  # last 4 preserved
        assert any(m.pii_type == "credit_card" for m in matches)

    def test_no_pii_unchanged(self) -> None:
        text = "What is the current price of AAPL stock?"
        result, matches = _redact_pii(text)
        assert result == text
        assert matches == []

    def test_multiple_pii_types(self) -> None:
        text = "SSN: 123-45-6789, email: test@test.com"
        result, matches = _redact_pii(text)
        assert len(matches) >= 2
        assert "123-45-6789" not in result
        assert "test@test.com" not in result

    def test_pii_match_indices_valid(self) -> None:
        text = "SSN 123-45-6789 end"
        result, matches = _redact_pii(text)
        for m in matches:
            assert m.start_index >= 0
            assert m.end_index > m.start_index
