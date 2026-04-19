from __future__ import annotations

import logging
from pathlib import Path

from config.app_paths import LOG_DIR, ensure_app_dirs


def setup_logger() -> None:
    ensure_app_dirs()
    log_file = Path(LOG_DIR) / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
