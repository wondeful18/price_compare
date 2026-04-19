from __future__ import annotations

import os
from dataclasses import dataclass

from config.app_paths import CACHE_DB_PATH, EXPORT_DIR, LOG_DIR, ensure_app_dirs


@dataclass(frozen=True)
class AppSettings:
    app_name: str = "price_compare_desktop"
    window_title: str = "工程采购比价助手 - Phase 4"
    window_width: int = 1400
    window_height: int = 860
    preview_row_limit: int = 500
    max_workers: int = 4
    top_n_offers: int = 3
    jd_mock_enabled: bool = True
    ai_enabled_default: bool = False
    deepseek_mock_enabled: bool = True
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    cache_db_path: str = str(CACHE_DB_PATH)
    log_dir: str = str(LOG_DIR)
    export_dir: str = str(EXPORT_DIR)


def load_settings() -> AppSettings:
    ensure_app_dirs()
    return AppSettings(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        deepseek_mock_enabled=os.getenv("DEEPSEEK_MOCK_ENABLED", "true").lower() != "false",
        ai_enabled_default=os.getenv("AI_ENABLED_DEFAULT", "false").lower() == "true",
        jd_mock_enabled=os.getenv("JD_MOCK_ENABLED", "true").lower() != "false",
    )
