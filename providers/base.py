from __future__ import annotations

from typing import Protocol

from domain.enums import PlatformType
from domain.models import ProductOffer, SearchQuery


class SearchProvider(Protocol):
    provider_name: str
    provider_version: str
    platform: PlatformType

    def search(self, query: SearchQuery) -> list[ProductOffer]:
        ...


class BaseProvider:
    provider_name = "base"
    provider_version = "v1"
    platform = PlatformType.UNKNOWN
