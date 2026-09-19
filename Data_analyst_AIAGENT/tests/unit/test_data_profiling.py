from tools.data_profiling import profile_dataframe


def test_profile_detects_missing_values(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    missing_cols = {i.column: i.count for i in report.missing_by_column}
    assert missing_cols.get("revenue") == 2


def test_profile_detects_duplicates(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    assert report.duplicate_row_count >= 1
    assert report.duplicate_row_percentage > 0


def test_profile_detects_outlier(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    outlier_cols = {i.column for i in report.outliers_by_column}
    assert "revenue" in outlier_cols


def test_profile_detects_constant_column(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    assert "notes" in report.constant_columns


def test_profile_splits_numeric_and_categorical(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    assert "revenue" in report.numeric_columns
    assert "units" in report.numeric_columns
    assert "region" in report.categorical_columns
    assert "notes" in report.categorical_columns


def test_profile_detects_blank_string_as_invalid(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    invalid_cols = {i.column: i.count for i in report.invalid_value_columns}
    assert invalid_cols.get("region") == 1


def test_profile_descriptive_stats_present_for_numeric_columns(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    assert "revenue" in report.descriptive_stats
    assert "mean" in report.descriptive_stats["revenue"]


def test_profile_row_and_column_counts(synthetic_messy_df):
    report = profile_dataframe(synthetic_messy_df)
    assert report.row_count == len(synthetic_messy_df)
    assert report.column_count == len(synthetic_messy_df.columns)
