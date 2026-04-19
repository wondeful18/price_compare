from __future__ import annotations

import re

from domain.enums import MatchLevel
from domain.models import MaterialItem, ProductOffer, ScoreDetail


def score_offer(material: MaterialItem, offer: ProductOffer) -> ScoreDetail:
    brand_score = 1.0 if _contains(offer.brand, material.brand) else 0.0
    spec_score = _token_overlap(material.spec, offer.spec_text)
    title_score = _token_overlap(f"{material.name} {material.spec or ''}", offer.title)
    unit_score = 1.0 if _contains(offer.spec_text, material.unit) or _contains(offer.title, material.unit) else 0.0
    price_penalty = _price_penalty(material.bid_unit_price, offer.price)
    final_score = (
        brand_score * 0.20
        + spec_score * 0.35
        + title_score * 0.30
        + unit_score * 0.15
        - price_penalty * 0.10
    )
    return ScoreDetail(
        brand_score=round(brand_score, 4),
        spec_score=round(spec_score, 4),
        title_score=round(title_score, 4),
        unit_score=round(unit_score, 4),
        price_penalty=round(price_penalty, 4),
        final_score=round(max(final_score, 0.0), 4),
    )


def match_level_from_score(score: float | None) -> MatchLevel | None:
    if score is None:
        return None
    if score >= 0.75:
        return MatchLevel.HIGH
    if score >= 0.45:
        return MatchLevel.MEDIUM
    return MatchLevel.LOW


def _contains(text: str | None, keyword: str | None) -> bool:
    if not text or not keyword:
        return False
    return keyword.lower() in text.lower()


def _token_overlap(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    left_tokens = set(_tokenize(left))
    right_tokens = set(_tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = left_tokens & right_tokens
    return len(overlap) / max(len(left_tokens), len(right_tokens))


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[\s,，;/x×*]+", text.lower()) if token]


def _price_penalty(bid_price: float | None, offer_price: float | None) -> float:
    if not bid_price or not offer_price or bid_price <= 0:
        return 0.0
    ratio = abs(offer_price - bid_price) / bid_price
    if ratio <= 0.2:
        return 0.0
    if ratio <= 0.5:
        return 0.5
    return 1.0
