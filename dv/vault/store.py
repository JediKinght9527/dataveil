"""
Encrypted key vault backed by SQLite.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .crypto import VaultCrypto


class VaultStore:
    def __init__(self, db_path: Path, password: str):
        self.db_path = db_path
        self.password = password
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS secrets (
                    profile TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    encrypted_key BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mapping_registry (
                    hash TEXT PRIMARY KEY,
                    token TEXT NOT NULL,
                    original BLOB NOT NULL,
                    entity_type TEXT,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add_key(self, profile: str, provider: str, base_url: str, api_key: str) -> None:
        blob = VaultCrypto.encrypt(api_key.encode(), self.password)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO secrets
                   (profile, provider, base_url, encrypted_key)
                   VALUES (?, ?, ?, ?)""",
                (profile, provider, base_url, blob),
            )

    def get_key(self, profile: str) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT provider, base_url, encrypted_key FROM secrets WHERE profile = ?",
                (profile,),
            ).fetchone()
            if not row:
                return None
            provider, base_url, blob = row
            api_key = VaultCrypto.decrypt(blob, self.password).decode()
            return {
                "provider": provider,
                "base_url": base_url,
                "api_key": api_key,
            }

    def verify_password(self) -> bool:
        """Verify the password can decrypt existing secrets.

        Returns True for an empty vault (nothing to verify against).
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT encrypted_key FROM secrets LIMIT 1").fetchone()
        if not row:
            return True
        try:
            VaultCrypto.decrypt(row[0], self.password)
            return True
        except Exception:
            return False

    def list_profiles(self) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT profile FROM secrets ORDER BY profile").fetchall()
            return [r[0] for r in rows]

    def remove_key(self, profile: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM secrets WHERE profile = ?", (profile,))
            return cur.rowcount > 0
