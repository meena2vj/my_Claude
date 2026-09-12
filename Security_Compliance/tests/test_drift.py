import generate_synthetic_data as gen
from utils.validation import validate_drift


def test_freshly_generated_data_matches_its_own_baseline(datasets):
    expected = gen._expected_ranges(datasets)
    current = {
        test_name: {
            "mean": round(float(group["result_value"].mean()), 2),
            "std": round(float(group["result_value"].std()), 2),
        }
        for test_name, group in datasets["labs"].groupby("test_name")
    }
    assert validate_drift(current, expected) == []


def test_shifted_distribution_is_flagged_as_drift():
    expected = {"ALT": {"mean": 25.0, "std": 8.0}}
    shifted = {"ALT": {"mean": 25.0 + 8.0 * 5, "std": 8.0}}
    problems = validate_drift(shifted, expected)
    assert len(problems) == 1
    assert "ALT" in problems[0]


def test_within_tolerance_is_not_flagged():
    expected = {"ALT": {"mean": 25.0, "std": 8.0}}
    close = {"ALT": {"mean": 26.0, "std": 8.0}}
    assert validate_drift(close, expected) == []
