import pandas as pd

from tools.analysis_ops import (
    aggregate_by_group,
    extract_numbers,
    match_column,
    validate_narrative_against_result,
)


def test_match_column_exact_and_substring():
    columns = ["Revenue", "Region", "Units"]
    assert match_column("revenue", columns) == "Revenue"
    assert match_column("total revenue", columns) == "Revenue"
    assert match_column("nonexistent", columns) is None


def test_aggregate_by_group_sums_and_sorts_descending():
    df = pd.DataFrame({"region": ["N", "S", "N", "S"], "revenue": [100, 50, 200, 25]})
    result = aggregate_by_group(df, "revenue", "region")
    assert list(result["region"]) == ["N", "S"]
    assert list(result["revenue"]) == [300, 75]


def test_aggregate_without_group_returns_single_row():
    df = pd.DataFrame({"revenue": [10, 20, 30]})
    result = aggregate_by_group(df, "revenue", None)
    assert result["revenue"].iloc[0] == 60


def test_extract_numbers_handles_commas_and_decimals():
    numbers = extract_numbers("Revenue grew to 1,234.5 from 1000.")
    assert 1234.5 in numbers
    assert 1000.0 in numbers


def test_validate_narrative_accepts_numbers_present_in_table():
    table = pd.DataFrame({"region": ["N", "S"], "revenue": [300, 75]})
    problems = validate_narrative_against_result("North led with 300 in revenue.", table)
    assert problems == []


def test_validate_narrative_flags_fabricated_number():
    table = pd.DataFrame({"region": ["N", "S"], "revenue": [300, 75]})
    problems = validate_narrative_against_result("North led with 999999 in revenue.", table)
    assert len(problems) == 1
