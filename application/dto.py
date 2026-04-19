from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MaterialRowDTO:
    row_id: int
    serial_no: str
    name: str
    spec: str
    quantity: str
    unit: str
    brand: str
    bid_unit_price: str
    bid_total_price: str
    status: str
    purchase_price_raw: str
    task_status: str
    recommended_platform: str = ""
    recommended_price: str = ""
    jd_price: str = ""
    match_score: str = ""
    ai_comment: str = ""
    error_message: str = ""
