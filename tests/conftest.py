import os
import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def isolated_db_path(monkeypatch, tmp_path):
    """
    Ensure every test runs with an isolated database in a temporary directory.
    This prevents cross-test pollution and leaves no files behind.
    """
    db_file = tmp_path / "test_isolated.sqlite"
    monkeypatch.setenv("ENGRAM_DB_PATH", str(db_file))
    
    try:
        from engram.core import _INITIALIZED_PATHS, init_db
        _INITIALIZED_PATHS.clear()
        init_db(force=True)
    except ImportError:
        pass
    
    yield
    
    # SQLite files in tmp_path are automatically cleaned up by pytest
