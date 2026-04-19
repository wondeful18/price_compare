from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
EXPORT_DIR = DATA_DIR / "exports"
CACHE_DB_PATH = DATA_DIR / "cache.db"


def ensure_app_dirs() -> None:
    for path in (DATA_DIR, LOG_DIR, EXPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)
