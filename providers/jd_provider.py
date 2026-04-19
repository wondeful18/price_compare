from __future__ import annotations

from domain.enums import PlatformType
from domain.models import ProductOffer, SearchQuery
from infra.http_client import HttpClient
from providers.base import BaseProvider


class JDOfficialProvider(BaseProvider):
    provider_name = "jd_official"
    provider_version = "mock-v1"
    platform = PlatformType.JD

    def __init__(self, http_client: HttpClient) -> None:
        self._http_client = http_client

    def search(self, query: SearchQuery) -> list[ProductOffer]:
        payload = self._http_client.get_json(
            "mock://jd/search",
            {
                "query": query.keywords[0] if query.keywords else query.normalized_text,
                "brand": query.brand_hint,
                "spec": query.spec_hint.get("spec"),
            },
        )
        return self.parse_response(payload)

    def parse_response(self, payload: dict) -> list[ProductOffer]:
        offers: list[ProductOffer] = []
        for item in payload.get("offers", []):
            offers.append(
                ProductOffer(
                    platform=PlatformType.JD,
                    title=str(item.get("skuName", "")).strip(),
                    brand=_text(item.get("brandName")),
                    spec_text=_text(item.get("specification")),
                    price=_to_float(item.get("price")),
                    shop_name=_text(item.get("shopName")),
                    product_url=_text(item.get("skuUrl")),
                    image_url=_text(item.get("imageUrl")),
                    source_type="mock_api",
                    raw_payload=item,
                )
            )
        return offers


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
