"""Shared test fixtures."""
from pathlib import Path

import pytest

from dv.vault.store import VaultStore


@pytest.fixture
def temp_vault(tmp_path: Path):
    """Create a temporary vault for testing."""
    db_path = tmp_path / "vault.db"
    return VaultStore(db_path=db_path, password="test-password-123")
