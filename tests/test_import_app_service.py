from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from application.import_app_service import ImportAppService
from infra.excel_reader import ExcelReader


class ImportAppServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ImportAppService(ExcelReader())
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_imports_rows_as_dto(self) -> None:
        path = self.temp_path / "import.xlsx"
        df = pd.DataFrame(
            [
                {"序号": "9", "名称": "电钻", "规格": "200V，450W", "数量": 2, "单位": "把", "品牌": "大艺", "采购价": "99.8"},
                {"序号": "11", "名称": "配套钻头", "规格": "ф8×160", "数量": 5, "单位": "个", "品牌": "博世", "采购价": "5.0"},
            ]
        )
        df.to_excel(path, index=False)

        result = self.service.import_file(path)

        self.assertEqual(result.preview.total_rows, 2)
        self.assertEqual(len(result.rows), 2)
        self.assertEqual(result.rows[0].name, "电钻")
        self.assertEqual(result.rows[1].brand, "博世")


if __name__ == "__main__":
    unittest.main()
