from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from domain.models import ImportPreview, MaterialItem


class ExcelReaderError(Exception):
    """Raised when excel loading or parsing fails."""


@dataclass(frozen=True)
class FieldSpec:
    key: str
    aliases: tuple[str, ...]
    positional_index: int | None = None


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("serial_no", ("序号", "编号", "投标报价清单"), 0),
    FieldSpec("name", ("名称", "物料名称", "商品名称"), 1),
    FieldSpec("spec", ("规格", "型号", "规格型号"), 2),
    FieldSpec("quantity", ("数量", "采购数量"), 3),
    FieldSpec("unit", ("单位",), 4),
    FieldSpec("brand", ("品牌",), 5),
    FieldSpec("bid_unit_price", ("投标单价", "单价"), 6),
    FieldSpec("bid_total_price", ("投标总价", "总价", "金额"), 7),
    FieldSpec("status", ("状态", "采购状态"), 8),
    FieldSpec("purchase_price_raw", ("采购价", "采购价格", "采购价（原始文本）"), 9),
)


class ExcelReader:
    def read_preview(self, file_path: str | Path) -> ImportPreview:
        path = Path(file_path)
        self._validate_input(path)

        try:
            with pd.ExcelFile(path, engine="openpyxl") as workbook:
                sheet_name = workbook.sheet_names[0]
                frame = workbook.parse(sheet_name=sheet_name)
        except Exception as exc:  # pragma: no cover - pandas/openpyxl error surface
            raise ExcelReaderError(f"读取 Excel 失败: {exc}") from exc

        if frame.empty:
            raise ExcelReaderError("Excel 首个工作表为空。")

        prepared = self._prepare_frame(frame)
        mapped = self._build_column_mapping(prepared.columns.tolist())
        items = self._to_material_items(prepared, mapped)

        if not items:
            raise ExcelReaderError("未能从 Excel 中解析出有效物料行。")

        return ImportPreview(
            sheet_name=sheet_name,
            total_rows=len(items),
            detected_columns=list(prepared.columns),
            items=items,
        )

    @staticmethod
    def _validate_input(path: Path) -> None:
        if not path.exists():
            raise ExcelReaderError(f"文件不存在: {path}")
        if path.suffix.lower() != ".xlsx":
            raise ExcelReaderError("当前仅支持 .xlsx 文件。")

    @staticmethod
    def _prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
        prepared = frame.copy()
        prepared.columns = [ExcelReader._normalize_header(col) for col in prepared.columns]
        prepared = prepared.dropna(how="all")
        prepared = prepared.fillna("")
        return prepared

    @staticmethod
    def _normalize_header(value: Any) -> str:
        text = str(value).strip()
        return text if text else "Unnamed"

    @staticmethod
    def _normalize_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return None
        return text

    @staticmethod
    def _to_optional_float(value: Any) -> float | None:
        if value in ("", None):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _build_column_mapping(self, columns: list[str]) -> dict[str, str | None]:
        mapping: dict[str, str | None] = {}
        used_columns: set[str] = set()
        normalized_columns = {column: self._normalize_header(column).lower() for column in columns}

        for spec in FIELD_SPECS:
            matched_column = None
            for column, normalized in normalized_columns.items():
                if column in used_columns:
                    continue
                if any(alias.lower() == normalized for alias in spec.aliases):
                    matched_column = column
                    break
            if matched_column is None and spec.positional_index is not None and spec.positional_index < len(columns):
                candidate = columns[spec.positional_index]
                if candidate not in used_columns:
                    matched_column = candidate
            mapping[spec.key] = matched_column
            if matched_column is not None:
                used_columns.add(matched_column)
        return mapping

    def _to_material_items(self, frame: pd.DataFrame, mapping: dict[str, str | None]) -> list[MaterialItem]:
        items: list[MaterialItem] = []
        for index, row in frame.iterrows():
            name = self._get_value(row, mapping["name"])
            serial_no = self._get_value(row, mapping["serial_no"])
            if not name and not serial_no:
                continue
            item = MaterialItem(
                row_id=len(items) + 1,
                serial_no=self._normalize_text(serial_no),
                name=self._normalize_text(name) or "未命名物料",
                spec=self._normalize_text(self._get_value(row, mapping["spec"])),
                quantity=self._to_optional_float(self._get_value(row, mapping["quantity"])),
                unit=self._normalize_text(self._get_value(row, mapping["unit"])),
                brand=self._normalize_text(self._get_value(row, mapping["brand"])),
                bid_unit_price=self._to_optional_float(self._get_value(row, mapping["bid_unit_price"])),
                bid_total_price=self._to_optional_float(self._get_value(row, mapping["bid_total_price"])),
                status=self._normalize_text(self._get_value(row, mapping["status"])),
                purchase_price_raw=self._normalize_text(self._get_value(row, mapping["purchase_price_raw"])),
                source_row_index=index + 2,
                source_data={column: row[column] for column in frame.columns},
            )
            items.append(item)
        return items

    @staticmethod
    def _get_value(row: pd.Series, column_name: str | None) -> Any:
        if column_name is None:
            return None
        return row.get(column_name)
