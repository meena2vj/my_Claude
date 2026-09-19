"""Shared fixtures for unit/integration tests."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _isolate_observability_dbs(tmp_path, monkeypatch):
    """Redirect the trace/memory SQLite stores to a per-test tmp path.

    Several agents call `trace_store.log_event`/`memory_service.save_turn`
    as a real side effect (not just through a mocked LLM call site), so
    without this every test run would write into the real
    `data/db/*.sqlite` files instead of staying isolated.
    """
    from observability import trace_store
    from services import memory_service

    monkeypatch.setattr(trace_store, "TRACE_DB_PATH", tmp_path / "traces.sqlite")
    monkeypatch.setattr(memory_service, "MEMORY_DB_PATH", tmp_path / "memory.sqlite")


@pytest.fixture
def synthetic_messy_df() -> pd.DataFrame:
    """A DataFrame with known, deliberately-seeded quality issues:
    - 'region': one blank string, one constant-adjacent value used elsewhere
    - 'revenue': 2 missing values, one extreme outlier
    - 'notes': a constant column (same value in every row)
    - 2 exact duplicate rows
    """
    df = pd.DataFrame(
        {
            "region": ["North", "South", "East", "West", "", "North", "North"],
            "revenue": [100.0, 110.0, np.nan, 105.0, np.nan, 100000.0, 100.0],
            "units": [10, 11, 9, 10, 8, 12, 10],
            "notes": ["ok"] * 7,
        }
    )
    # duplicate the first row exactly, to create a known duplicate count
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    return df
