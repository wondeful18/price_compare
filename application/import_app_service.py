from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from application.dto import MaterialRowDTO
from domain.models import ImportPreview, MaterialItem
from infra.excel_reader import ExcelReader, ExcelReaderError


class ImportAppServiceError(Exception):
    """User-facing import service error."""


@dataclass(slots=True)
class ImportResult:
    preview: ImportPreview
    rows: list[MaterialRowDTO]


class ImportAppService:
    def __init__(self, excel_reader: ExcelReader) -> None:
        self._excel_reader = excel_reader

    def import_file(self, file_path: str | Path) -> ImportResult:
        try:
            preview = self._excel_reader.read_preview(file_path)
        except ExcelReaderError as exc:
            raise ImportAppServiceError(str(exc)) from exc
        return ImportResult(preview=preview, rows=[self._to_row(item) for item in preview.items])

    @staticmethod
    def _to_row(item: MaterialItem) -> MaterialRowDTO:
        return MaterialRowDTO(
            row_id=item.row_id,
            serial_no=item.serial_no or "",
            name=item.name,
            spec=item.spec or "",
            quantity="" if item.quantity is None else str(item.quantity),
            unit=item.unit or "",
            brand=item.brand or "",
            bid_unit_price="" if item.bid_unit_price is None else str(item.bid_unit_price),
            bid_total_price="" if item.bid_total_price is None else str(item.bid_total_price),
            status=item.status or "",
            purchase_price_raw=item.purchase_price_raw or "",
            task_status=item.task_status.value,
        )
