from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.ai_service import AiService
from application.query_builder_service import QueryBuilderService
from domain.enums import PlatformType
from domain.models import MaterialItem, ProductOffer
from infra.deepseek_client import DeepSeekClient
from infra.sqlite_db import SQLiteDB
from repositories.cache_repository import CacheRepository


class AiServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_repo = CacheRepository(SQLiteDB(Path(self.temp_dir.name) / "cache.db"))
        self.service = AiService(DeepSeekClient(), self.cache_repo)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_optimize_query_returns_keywords(self) -> None:
        material = MaterialItem(row_id=1, serial_no="1", name="电钻", spec="220V 450W", brand="博世")
        base_query = QueryBuilderService().build(material)

        optimized_query, reason = self.service.optimize_query(material, base_query)

        self.assertTrue(optimized_query.keywords)
        self.assertIn("博世 电钻 220V 450W", optimized_query.keywords)
        self.assertTrue(reason)

    def test_explain_match_uses_cache(self) -> None:
        material = MaterialItem(row_id=1, serial_no="1", name="电钻", spec="220V 450W", brand="博世")
        offer = ProductOffer(
            platform=PlatformType.JD,
            title="博世 电钻 220V 450W",
            brand="博世",
            spec_text="220V 450W",
            price=88.0,
            shop_name="京东自营",
            product_url=None,
            image_url=None,
            source_type="mock",
        )

        comment1 = self.service.explain_match(material, offer)
        comment2 = self.service.explain_match(material, offer)

        self.assertEqual(comment1, comment2)


if __name__ == "__main__":
    unittest.main()
