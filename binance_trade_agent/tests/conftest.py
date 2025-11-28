"""
Pytest configuration and fixtures for tests
"""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test database directory and file before running tests"""
    # Create data directory for tests
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # Create test database file
    test_db = data_dir / "test_portfolio.db"
    test_db.touch(exist_ok=True)

    yield

    # Cleanup after all tests (optional)
    # test_db.unlink(missing_ok=True)


@pytest.fixture
def temp_db():
    """Provide a temporary database for individual tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_path.touch()
        yield str(db_path)
