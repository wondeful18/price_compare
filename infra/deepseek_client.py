from __future__ import annotations

from dataclasses import dataclass

from domain.models import MaterialItem, ProductOffer, SearchQuery


@dataclass(slots=True)
class QueryOptimizationResult:
    optimized_keywords: list[str]
    normalized_text: str
    reason: str


class DeepSeekClient:
    def optimize_query(self, material: MaterialItem, base_query: SearchQuery) -> QueryOptimizationResult:
        parts = [part for part in [material.brand, material.name, material.spec] if part]
        optimized = " ".join(parts).strip() or base_query.original_text
        keywords = [optimized]
        if material.name and material.spec:
            keywords.append(f"{material.name} {material.spec}")
        if material.brand and material.name:
            keywords.append(f"{material.brand} {material.name}")
        deduped = []
        seen = set()
        for item in keywords:
            if item and item not in seen:
                deduped.append(item)
                seen.add(item)
        return QueryOptimizationResult(
            optimized_keywords=deduped,
            normalized_text=optimized.lower(),
            reason="AI 根据品牌、名称和规格重排了查询词",
        )

    def explain_match(self, material: MaterialItem, offer: ProductOffer) -> str:
        brand_info = "品牌一致" if material.brand and offer.brand and material.brand in offer.brand else "品牌待人工复核"
        spec_info = "规格已带入搜索" if material.spec else "原始规格缺失"
        return f"{brand_info}；{spec_info}；推荐候选标题为：{offer.title}"
