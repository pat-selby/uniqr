"""Pytest fixtures shared across the detection regression suite."""

import pytest
from uniqr.decode import Scanner


@pytest.fixture(scope="session")
def scanner() -> Scanner:
    return Scanner()
