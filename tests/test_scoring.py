from __future__ import annotations

import unittest

from domain.enums import PlatformType
from domain.models import MaterialItem, ProductOffer
from domain.scoring import score_offer


class ScoringTests(unittest.TestCase):
    def test_matching_offer_scores_higher(self) -> None:
        material = MaterialItem(row_id=1, serial_no="1", name="电钻", spec="220V 450W", unit="把", brand="博世", bid_unit_price=100.0)
        good_offer = ProductOffer(
            platform=PlatformType.JD,
            title="博世 电钻 220V 450W 把装",
            brand="博世",
            spec_text="220V 450W",
            price=95.0,
            shop_name="京东",
            product_url=None,
            image_url=None,
            source_type="mock",
        )
        bad_offer = ProductOffer(
            platform=PlatformType.JD,
            title="替代品牌 螺丝刀",
            brand="替代品牌",
            spec_text="12V",
            price=30.0,
            shop_name="京东",
            product_url=None,
            image_url=None,
            source_type="mock",
        )

        self.assertGreater(score_offer(material, good_offer).final_score, score_offer(material, bad_offer).final_score)


if __name__ == "__main__":
    unittest.main()
