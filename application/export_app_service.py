from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from config.settings import AppSettings
from domain.models import CompareResult, MaterialItem
from infra.excel_writer import ExcelWriter


class ExportAppService:
    def __init__(self, settings: AppSettings, excel_writer: ExcelWriter) -> None:
        self._settings = settings
        self._excel_writer = excel_writer

    def export_results(self, materials: list[MaterialItem], results: dict[int, CompareResult]) -> Path:
        frame = self._build_frame(materials, results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = Path(self._settings.export_dir) / f"compare_result_{timestamp}.xlsx"
        return self._excel_writer.write(frame, target)

    def _build_frame(self, materials: list[MaterialItem], results: dict[int, CompareResult]) -> pd.DataFrame:
        rows: list[dict] = []
        for material in materials:
            base = {str(key): value for key, value in material.source_data.items()}
            result = results.get(material.row_id)
            row = {
                **base,
                "推荐平台": result.best_platform.value if result and result.best_platform else "",
                "推荐价格": result.best_price if result else "",
                "京东最低价": result.jd_price if result else "",
                "差价": result.price_diff if result else "",
                "匹配分": result.match_score if result else "",
                "AI 备注": result.ai_comment if result else "",
                "任务状态": result.search_status.value if result else material.task_status.value,
                "错误信息": result.error_message if result else "",
            }
            rows.append(row)
        return pd.DataFrame(rows)
