from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from domain.enums import PlatformType
from domain.models import ProductOffer, SearchQuery
from infra.sqlite_db import SQLiteDB
from repositories.cache_repository import CacheRepository


class CacheRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "cache.db"
        self.repo = CacheRepository(SQLiteDB(self.db_path))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_round_trip_search_cache(self) -> None:
        query = SearchQuery(
            material_id=1,
            original_text="博世 电钻 220V",
            normalized_text="博世 电钻 220v",
            brand_hint="博世",
            spec_hint={"spec": "220V"},
            keywords=["博世 电钻 220V"],
        )
        offers = [
            ProductOffer(
                platform=PlatformType.JD,
                title="博世 电钻 220V",
                brand="博世",
                spec_text="220V",
                price=99.8,
                shop_name="京东自营",
                product_url="https://example.com",
                image_url=None,
                source_type="mock",
            )
        ]

        self.repo.set_search_cache(
            platform=PlatformType.JD,
            provider_name="jd_official",
            provider_version="mock-v1",
            query=query,
            offers=offers,
        )
        cached = self.repo.get_search_cache(
            platform=PlatformType.JD,
            normalized_query=query.normalized_text,
            provider_name="jd_official",
            provider_version="mock-v1",
        )

        self.assertIsNotNone(cached)
        self.assertEqual(len(cached or []), 1)
        self.assertEqual(cached[0].title, "博世 电钻 220V")

    def test_builds_stable_cache_key(self) -> None:
        key1 = self.repo.build_search_key(PlatformType.JD, "query-a", "v1")
        key2 = self.repo.build_search_key(PlatformType.JD, "query-a", "v1")
        self.assertEqual(key1, key2)


if __name__ == "__main__":
    unittest.main()
