from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteDB:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection
