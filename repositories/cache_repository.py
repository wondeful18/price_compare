from __future__ import annotations

import json
import logging
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import md5
from typing import Any

from domain.enums import PlatformType
from domain.models import ProductOffer, SearchQuery
from infra.sqlite_db import SQLiteDB


logger = logging.getLogger(__name__)


class CacheRepository:
    def __init__(self, db: SQLiteDB) -> None:
        self._db = db
        self._init_schema()

    def _init_schema(self) -> None:
        with closing(self._db.connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT NOT NULL UNIQUE,
                    platform TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    provider_version TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    normalized_query TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    hit_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT NOT NULL UNIQUE,
                    task_type TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def build_search_key(self, platform: PlatformType, normalized_query: str, provider_version: str) -> str:
        raw = f"{platform.value}|{normalized_query}|{provider_version}"
        return md5(raw.encode("utf-8")).hexdigest()

    def get_search_cache(
        self,
        *,
        platform: PlatformType,
        normalized_query: str,
        provider_name: str,
        provider_version: str,
    ) -> list[ProductOffer] | None:
        cache_key = self.build_search_key(platform, normalized_query, provider_version)
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._db.connect()) as conn:
            row = conn.execute(
                """
                SELECT response_json, expires_at, hit_count
                FROM search_cache
                WHERE cache_key = ? AND platform = ? AND provider_name = ? AND provider_version = ?
                """,
                (cache_key, platform.value, provider_name, provider_version),
            ).fetchone()
            if row is None:
                return None
            if row["expires_at"] <= now:
                logger.info("cache expired: %s", cache_key)
                return None
            conn.execute("UPDATE search_cache SET hit_count = ? WHERE cache_key = ?", (int(row["hit_count"]) + 1, cache_key))
            conn.commit()
            logger.info("cache hit: %s", cache_key)
            payload = json.loads(row["response_json"])
            return [self._deserialize_offer(item) for item in payload]

    def set_search_cache(
        self,
        *,
        platform: PlatformType,
        provider_name: str,
        provider_version: str,
        query: SearchQuery,
        offers: list[ProductOffer],
        ttl_days: int = 2,
    ) -> None:
        cache_key = self.build_search_key(platform, query.normalized_text, provider_version)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=ttl_days)
        payload = json.dumps([self._serialize_offer(offer) for offer in offers], ensure_ascii=False)
        with closing(self._db.connect()) as conn:
            conn.execute(
                """
                INSERT INTO search_cache (
                    cache_key, platform, provider_name, provider_version, query_text,
                    normalized_query, response_json, created_at, expires_at, hit_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_json = excluded.response_json,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (
                    cache_key,
                    platform.value,
                    provider_name,
                    provider_version,
                    query.original_text,
                    query.normalized_text,
                    payload,
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
            conn.commit()
        logger.info("cache store: %s", cache_key)

    def get_ai_cache(self, cache_key: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._db.connect()) as conn:
            row = conn.execute(
                "SELECT output_json, expires_at FROM ai_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if row is None or row["expires_at"] <= now:
                return None
            return json.loads(row["output_json"])

    def set_ai_cache(self, *, cache_key: str, task_type: str, payload: dict[str, Any], ttl_days: int = 14) -> None:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=ttl_days)
        with closing(self._db.connect()) as conn:
            conn.execute(
                """
                INSERT INTO ai_cache (cache_key, task_type, output_json, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    output_json = excluded.output_json,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (cache_key, task_type, json.dumps(payload, ensure_ascii=False), now.isoformat(), expires_at.isoformat()),
            )
            conn.commit()

    @staticmethod
    def _serialize_offer(offer: ProductOffer) -> dict:
        payload = asdict(offer)
        payload["platform"] = offer.platform.value
        return payload

    @staticmethod
    def _deserialize_offer(item: dict) -> ProductOffer:
        return ProductOffer(
            platform=PlatformType(item["platform"]),
            title=item["title"],
            brand=item.get("brand"),
            spec_text=item.get("spec_text"),
            price=item.get("price"),
            shop_name=item.get("shop_name"),
            product_url=item.get("product_url"),
            image_url=item.get("image_url"),
            source_type=item.get("source_type", "cache"),
            raw_payload=item.get("raw_payload"),
        )
