from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional


class BenchmarkCache:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "benchmark_cache.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS captions (
                    cache_key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    cache_key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    def get_caption(self, cache_key: str) -> Optional[str]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM captions WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        return row[0] if row else None

    def set_caption(self, cache_key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO captions(cache_key, value, created_at)
                VALUES(?, ?, ?)
                """,
                (cache_key, value, time.time()),
            )

    def get_embedding(self, cache_key: str) -> Optional[list[float]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM embeddings WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def set_embedding(self, cache_key: str, value: list[float]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO embeddings(cache_key, value, created_at)
                VALUES(?, ?, ?)
                """,
                (cache_key, json.dumps(value), time.time()),
            )
