from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class HttpResponse:
    status_code: int
    payload: dict[str, Any]


class HttpTransport(Protocol):
    def get_json(self, url: str, params: dict[str, Any]) -> HttpResponse:
        ...


class MockJdTransport:
    def get_json(self, url: str, params: dict[str, Any]) -> HttpResponse:
        query = params.get("query", "")
        brand = params.get("brand")
        spec = params.get("spec")
        payload = {"offers": _build_mock_offers(query, brand, spec)}
        return HttpResponse(status_code=200, payload=payload)


class HttpClient:
    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self._transport.get_json(url, params)
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP request failed with status {response.status_code}")
        return response.payload


def build_mock_http_client() -> HttpClient:
    return HttpClient(MockJdTransport())


def _build_mock_offers(query: str, brand: str | None, spec: str | None) -> list[dict[str, Any]]:
    base_terms = [term for term in [brand, query, spec] if term]
    base_title = " ".join(base_terms).strip() or "通用工具"
    return [
        {
            "skuName": f"{base_title} 京东自营款",
            "brandName": brand or "通用品牌",
            "specification": spec or query,
            "price": 88.0,
            "shopName": "京东自营",
            "skuUrl": "https://example.com/jd/self",
        },
        {
            "skuName": f"{base_title} 工程商家款",
            "brandName": brand or "工程品牌",
            "specification": spec or query,
            "price": 79.5,
            "shopName": "工程五金旗舰店",
            "skuUrl": "https://example.com/jd/store",
        },
        {
            "skuName": f"{base_title} 替代候选",
            "brandName": "替代品牌",
            "specification": spec or query,
            "price": 65.0,
            "shopName": "工业工具专营店",
            "skuUrl": "https://example.com/jd/alt",
        },
    ]
