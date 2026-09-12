from utils.validation import DIRECT_IDENTIFIER_COLUMNS, validate_privacy


def test_no_direct_identifier_columns(datasets):
    for name, df in datasets.items():
        assert validate_privacy(name, df) == []


def test_no_direct_identifier_column_names_anywhere(datasets):
    for df in datasets.values():
        columns = {c.lower() for c in df.columns}
        assert columns.isdisjoint(DIRECT_IDENTIFIER_COLUMNS)


def test_all_files_marked_synthetic(datasets):
    for name, df in datasets.items():
        assert "synthetic" in df.columns, f"{name} missing synthetic marker column"
        assert df["synthetic"].all(), f"{name} has rows not marked synthetic"
