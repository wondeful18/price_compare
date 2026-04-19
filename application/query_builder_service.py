from __future__ import annotations

import re

from domain.models import MaterialItem, SearchQuery


class QueryBuilderService:
    def build(self, material: MaterialItem) -> SearchQuery:
        original_parts = [material.name, material.spec, material.brand]
        original_text = " ".join(part for part in original_parts if part).strip()
        normalized_text = self._normalize_text(original_text)
        keywords = self._build_keywords(material, normalized_text)
        spec_hint: dict[str, str] = {}
        if material.spec:
            spec_hint["spec"] = material.spec
        if material.unit:
            spec_hint["unit"] = material.unit
        return SearchQuery(
            material_id=material.row_id,
            original_text=original_text,
            normalized_text=normalized_text,
            brand_hint=material.brand,
            spec_hint=spec_hint,
            keywords=keywords,
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        compact = re.sub(r"\s+", " ", text).strip().lower()
        return re.sub(r"[，,;/]+", " ", compact)

    def _build_keywords(self, material: MaterialItem, normalized_text: str) -> list[str]:
        parts: list[str] = []
        if material.name:
            parts.append(material.name.strip())
        if material.spec:
            parts.append(material.spec.strip())
        base = " ".join(parts).strip()
        keywords = [base] if base else []
        if material.brand and base:
            keywords.append(f"{material.brand} {base}")
        if normalized_text and normalized_text not in keywords:
            keywords.append(normalized_text)
        deduped: list[str] = []
        seen: set[str] = set()
        for keyword in keywords:
            normalized = keyword.strip()
            if normalized and normalized not in seen:
                deduped.append(normalized)
                seen.add(normalized)
        return deduped
