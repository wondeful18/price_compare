from __future__ import annotations

from domain.enums import PlatformType, TaskStatus
from domain.models import CompareResult, MaterialItem, ProductOffer, ScoreDetail
from domain.scoring import match_level_from_score, score_offer


class CompareAppService:
    def __init__(self, top_n: int = 3) -> None:
        self._top_n = top_n

    def compare(self, material: MaterialItem, offers: list[ProductOffer]) -> CompareResult:
        if not offers:
            return CompareResult(
                material_id=material.row_id,
                best_platform=None,
                best_price=None,
                jd_price=None,
                taobao_price=None,
                pdd_price=None,
                price_diff=None,
                match_score=None,
                match_level=None,
                ai_comment=None,
                top_offers=[],
                score_detail=None,
                search_status=TaskStatus.FAILED,
                error_message="未找到候选商品",
            )

        scored: list[tuple[ProductOffer, ScoreDetail]] = [(offer, score_offer(material, offer)) for offer in offers]
        ranked = sorted(scored, key=lambda pair: pair[1].final_score, reverse=True)
        best_offer, best_score = ranked[0]
        top_offers = [pair[0] for pair in ranked[: self._top_n]]

        return CompareResult(
            material_id=material.row_id,
            best_platform=best_offer.platform,
            best_price=best_offer.price,
            jd_price=self._find_platform_price(offers, PlatformType.JD),
            taobao_price=self._find_platform_price(offers, PlatformType.TAOBAO),
            pdd_price=self._find_platform_price(offers, PlatformType.PDD),
            price_diff=self._price_diff(material.bid_unit_price, best_offer.price),
            match_score=best_score.final_score,
            match_level=match_level_from_score(best_score.final_score),
            ai_comment=f"推荐标题: {best_offer.title}",
            top_offers=top_offers,
            score_detail=best_score,
            search_status=TaskStatus.DONE,
            error_message=None,
        )

    @staticmethod
    def _find_platform_price(offers: list[ProductOffer], platform: PlatformType) -> float | None:
        prices = [offer.price for offer in offers if offer.platform == platform and offer.price is not None]
        return min(prices) if prices else None

    @staticmethod
    def _price_diff(bid_price: float | None, best_price: float | None) -> float | None:
        if bid_price is None or best_price is None:
            return None
        return round(best_price - bid_price, 4)
