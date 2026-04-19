from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.enums import MatchLevel, PlatformType, TaskStatus


@dataclass(slots=True)
class MaterialItem:
    row_id: int
    serial_no: str | None
    name: str
    spec: str | None = None
    quantity: float | None = None
    unit: str | None = None
    brand: str | None = None
    bid_unit_price: float | None = None
    bid_total_price: float | None = None
    status: str | None = None
    purchase_price_raw: str | None = None
    source_row_index: int | None = None
    source_data: dict[str, Any] = field(default_factory=dict)
    task_status: TaskStatus = TaskStatus.READY
    error_message: str | None = None


@dataclass(slots=True)
class ImportPreview:
    sheet_name: str
    total_rows: int
    detected_columns: list[str]
    items: list[MaterialItem]


@dataclass(slots=True)
class SearchQuery:
    material_id: int
    original_text: str
    normalized_text: str
    brand_hint: str | None
    spec_hint: dict[str, str]
    keywords: list[str]


@dataclass(slots=True)
class ProductOffer:
    platform: PlatformType
    title: str
    brand: str | None
    spec_text: str | None
    price: float | None
    shop_name: str | None
    product_url: str | None
    image_url: str | None
    source_type: str
    raw_payload: dict[str, Any] | None = None


@dataclass(slots=True)
class ScoreDetail:
    brand_score: float
    spec_score: float
    title_score: float
    unit_score: float
    price_penalty: float
    final_score: float


@dataclass(slots=True)
class CompareResult:
    material_id: int
    best_platform: PlatformType | None
    best_price: float | None
    jd_price: float | None
    taobao_price: float | None
    pdd_price: float | None
    price_diff: float | None
    match_score: float | None
    match_level: MatchLevel | None
    ai_comment: str | None
    top_offers: list[ProductOffer]
    score_detail: ScoreDetail | None
    search_status: TaskStatus
    cache_hit: bool = False
    error_message: str | None = None
