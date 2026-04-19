from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.export_app_service import ExportAppService
from config.settings import AppSettings
from domain.enums import PlatformType, TaskStatus
from domain.models import CompareResult, MaterialItem
from infra.excel_writer import ExcelWriter


class ExportAppServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.export_dir = Path(self.temp_dir.name)
        self.settings = AppSettings(export_dir=str(self.export_dir))
        self.service = ExportAppService(self.settings, ExcelWriter())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_exports_result_workbook(self) -> None:
        material = MaterialItem(
            row_id=1,
            serial_no="1",
            name="电钻",
            spec="220V",
            source_data={"序号": "1", "名称": "电钻", "规格": "220V"},
        )
        result = CompareResult(
            material_id=1,
            best_platform=PlatformType.JD,
            best_price=88.0,
            jd_price=88.0,
            taobao_price=None,
            pdd_price=None,
            price_diff=0.0,
            match_score=0.8,
            match_level=None,
            ai_comment="推荐标题: 电钻",
            top_offers=[],
            score_detail=None,
            search_status=TaskStatus.DONE,
        )

        export_path = self.service.export_results([material], {1: result})

        self.assertTrue(export_path.exists())
        self.assertEqual(export_path.suffix.lower(), ".xlsx")


if __name__ == "__main__":
    unittest.main()
