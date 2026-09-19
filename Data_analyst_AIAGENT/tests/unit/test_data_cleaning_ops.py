from tools.data_cleaning_ops import build_default_plan, execute_plan
from tools.data_profiling import profile_dataframe


def test_build_default_plan_covers_all_detected_issues(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    plan = build_default_plan(synthetic_messy_df, report)
    action_types = {a.action_type for a in plan}

    assert "impute_missing" in action_types
    assert "drop_duplicates" in action_types
    assert "flag_outliers" in action_types
    assert "flag_constant_column" in action_types
    assert "flag_invalid_values" in action_types


def test_execute_plan_never_mutates_raw_data(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    plan = build_default_plan(synthetic_messy_df, report)
    original = synthetic_messy_df.copy(deep=True)

    execute_plan(synthetic_messy_df, plan)

    assert synthetic_messy_df.equals(original)


def test_execute_plan_imputes_missing_and_drops_duplicates(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    plan = build_default_plan(synthetic_messy_df, report)

    clean_df, log = execute_plan(synthetic_messy_df, plan)

    assert clean_df["revenue"].isna().sum() == 0
    assert clean_df.duplicated().sum() == 0
    assert len(clean_df) < len(synthetic_messy_df)
    assert all(action.executed for action in log)


def test_execute_plan_does_not_alter_values_for_flag_only_actions(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    plan = build_default_plan(synthetic_messy_df, report)

    clean_df, _ = execute_plan(synthetic_messy_df, plan)

    # The extreme outlier is flagged, not removed or changed.
    assert 100000.0 in clean_df["revenue"].values


def test_build_default_plan_empty_for_clean_data():
    import pandas as pd

    clean = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    report = profile_dataframe(clean)
    plan = build_default_plan(clean, report)
    assert plan == []
