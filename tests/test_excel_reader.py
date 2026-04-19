from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from infra.excel_reader import ExcelReader


class ExcelReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reader = ExcelReader()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_reads_explicit_headers(self) -> None:
        path = self.temp_path / "explicit.xlsx"
        df = pd.DataFrame(
            [
                {
                    "序号": "1",
                    "名称": "电钻",
                    "规格": "220V",
                    "数量": 2,
                    "单位": "把",
                    "品牌": "博世",
                    "投标单价": 99.5,
                    "投标总价": 199,
                    "状态": "已采购",
                    "采购价": "89",
                }
            ]
        )
        df.to_excel(path, index=False)

        preview = self.reader.read_preview(path)

        self.assertEqual(preview.total_rows, 1)
        self.assertEqual(preview.items[0].name, "电钻")
        self.assertEqual(preview.items[0].brand, "博世")
        self.assertEqual(preview.items[0].quantity, 2.0)

    def test_reads_positional_fallback_headers(self) -> None:
        path = self.temp_path / "fallback.xlsx"
        df = pd.DataFrame(
            [
                [6, "配套砂轮片", "100*2mm", 20, "片", "Bosch/博世", 7.51, 150.2, "已采购", 3.14]
            ],
            columns=[
                "投标报价清单",
                "Unnamed: 1",
                "Unnamed: 2",
                "Unnamed: 3",
                "Unnamed: 4",
                "Unnamed: 5",
                "Unnamed: 6",
                "Unnamed: 7",
                "Unnamed: 8",
                "采购价",
            ],
        )
        df.to_excel(path, index=False)

        preview = self.reader.read_preview(path)
        item = preview.items[0]

        self.assertEqual(item.serial_no, "6")
        self.assertEqual(item.name, "配套砂轮片")
        self.assertEqual(item.spec, "100*2mm")
        self.assertEqual(item.unit, "片")
        self.assertEqual(item.purchase_price_raw, "3.14")


if __name__ == "__main__":
    unittest.main()
