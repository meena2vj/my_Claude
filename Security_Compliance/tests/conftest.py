import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import generate_synthetic_data as gen


@pytest.fixture(scope="session")
def datasets() -> dict:
    return gen.generate_all(seed=42)
