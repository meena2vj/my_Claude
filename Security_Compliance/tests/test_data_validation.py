from utils.validation import REQUIRED_SCHEMAS, validate_integrity, validate_schema


def test_all_required_datasets_present(datasets):
    assert set(REQUIRED_SCHEMAS) == set(datasets)


def test_schema_has_all_required_columns(datasets):
    for name, df in datasets.items():
        assert validate_schema(name, df) == []


def test_no_duplicate_ids_or_malformed_dates(datasets):
    for name, df in datasets.items():
        assert validate_integrity(name, df) == []


def test_datasets_are_non_empty(datasets):
    for name, df in datasets.items():
        assert len(df) > 0, f"{name} should not be empty"
