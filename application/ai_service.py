from __future__ import annotations

import json
from hashlib import md5

from domain.models import MaterialItem, ProductOffer, SearchQuery
from infra.deepseek_client import DeepSeekClient, QueryOptimizationResult
from repositories.cache_repository import CacheRepository


class AiService:
    def __init__(self, client: DeepSeekClient, cache_repository: CacheRepository | None = None) -> None:
        self._client = client
        self._cache_repository = cache_repository

    def optimize_query(self, material: MaterialItem, base_query: SearchQuery) -> tuple[SearchQuery, str]:
        cache_key = self._build_key("optimize_query", material.row_id, base_query.original_text)
        cached = self._cache_repository.get_ai_cache(cache_key) if self._cache_repository else None
        if cached is not None:
            result = QueryOptimizationResult(**cached)
        else:
            result = self._client.optimize_query(material, base_query)
            if self._cache_repository is not None:
                self._cache_repository.set_ai_cache(
                    cache_key=cache_key,
                    task_type="optimize_query",
                    payload={
                        "optimized_keywords": result.optimized_keywords,
                        "normalized_text": result.normalized_text,
                        "reason": result.reason,
                    },
                )
        optimized_query = SearchQuery(
            material_id=base_query.material_id,
            original_text=base_query.original_text,
            normalized_text=result.normalized_text,
            brand_hint=base_query.brand_hint,
            spec_hint=base_query.spec_hint,
            keywords=result.optimized_keywords,
        )
        return optimized_query, result.reason

    def explain_match(self, material: MaterialItem, offer: ProductOffer) -> str:
        cache_key = self._build_key("explain_match", material.row_id, json.dumps({"title": offer.title, "brand": offer.brand}, ensure_ascii=False))
        cached = self._cache_repository.get_ai_cache(cache_key) if self._cache_repository else None
        if cached is not None:
            return str(cached["comment"])
        comment = self._client.explain_match(material, offer)
        if self._cache_repository is not None:
            self._cache_repository.set_ai_cache(
                cache_key=cache_key,
                task_type="explain_match",
                payload={"comment": comment},
            )
        return comment

    @staticmethod
    def _build_key(task_type: str, material_id: int, payload: str) -> str:
        raw = f"{task_type}|{material_id}|{payload}"
        return md5(raw.encode("utf-8")).hexdigest()
