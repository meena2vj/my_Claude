"""Unit tests for src/parsing.py safe-parsing helpers."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.parsing import is_blank, to_date, to_float, to_yes_no


class TestIsBlank:
    @pytest.mark.parametrize("value", [None, "", "   ", float("nan"), pd.NA])
    def test_blank_values(self, value):
        assert is_blank(value) is True

    @pytest.mark.parametrize("value", ["0", 0, "No", "abc", -1, 3.14])
    def test_non_blank_values(self, value):
        assert is_blank(value) is False


class TestToFloat:
    def test_parses_int_string(self):
        assert to_float("100") == 100.0

    def test_parses_float_string(self):
        assert to_float("5.5") == 5.5

    def test_parses_numeric_type(self):
        assert to_float(42) == 42.0

    def test_parses_negative(self):
        assert to_float("-5") == -5.0

    def test_blank_returns_none(self):
        assert to_float("") is None
        assert to_float(None) is None
        assert to_float(float("nan")) is None

    def test_non_numeric_string_returns_none(self):
        assert to_float("abc") is None
        assert to_float("N/A") is None


class TestToDate:
    def test_parses_iso_date(self):
        assert to_date("2026-01-01") == date(2026, 1, 1)

    def test_parses_date_object(self):
        assert to_date(date(2026, 1, 1)) == date(2026, 1, 1)

    def test_blank_returns_none(self):
        assert to_date("") is None
        assert to_date(None) is None

    def test_unparseable_string_returns_none(self):
        assert to_date("not-a-date") is None

    def test_invalid_calendar_date_returns_none(self):
        assert to_date("2026-13-45") is None
        assert to_date("31/02/2026") is None


class TestToYesNo:
    @pytest.mark.parametrize("value", ["Yes", "yes", "YES", " Yes ", "true", "1"])
    def test_recognised_true_values(self, value):
        assert to_yes_no(value) is True

    @pytest.mark.parametrize("value", ["No", "no", "NO", " No ", "false", "0"])
    def test_recognised_false_values(self, value):
        assert to_yes_no(value) is False

    def test_blank_returns_none(self):
        assert to_yes_no("") is None
        assert to_yes_no(None) is None

    def test_unrecognised_string_returns_none(self):
        assert to_yes_no("maybe") is None
        assert to_yes_no("Y") is None
