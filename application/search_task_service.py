from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass

from application.ai_service import AiService
from application.compare_app_service import CompareAppService
from application.events import TaskEvent
from application.query_builder_service import QueryBuilderService
from domain.enums import TaskStatus
from domain.models import CompareResult, MaterialItem, SearchQuery
from providers.base import SearchProvider
from repositories.cache_repository import CacheRepository
from workers.task_bus import TaskBus
from workers.task_runner import TaskRunner


@dataclass(slots=True)
class BatchSearchSession:
    task_id: str
    total_items: int


class SearchTaskService:
    def __init__(
        self,
        provider: SearchProvider,
        query_builder: QueryBuilderService,
        compare_service: CompareAppService,
        cache_repository: CacheRepository | None,
        ai_service: AiService | None,
        task_runner: TaskRunner,
        task_bus: TaskBus,
    ) -> None:
        self._provider = provider
        self._query_builder = query_builder
        self._compare_service = compare_service
        self._cache_repository = cache_repository
        self._ai_service = ai_service
        self._task_runner = task_runner
        self._task_bus = task_bus
        self._cancellation = threading.Event()
        self._pending = 0
        self._lock = threading.Lock()
        self._task_id: str | None = None
        self._enable_ai = False

    def start_batch(self, materials: list[MaterialItem], enable_ai: bool = False) -> BatchSearchSession:
        self._cancellation = threading.Event()
        self._enable_ai = enable_ai
        task_id = uuid.uuid4().hex
        self._task_id = task_id
        with self._lock:
            self._pending = len(materials)
        self._task_bus.publish(
            TaskEvent(event_type="batch_started", task_id=task_id, payload={"total": len(materials), "ai_enabled": enable_ai})
        )
        for material in materials:
            self._task_runner.submit(self._process_item, task_id, material)
        return BatchSearchSession(task_id=task_id, total_items=len(materials))

    def stop_batch(self) -> None:
        if self._task_id is None:
            return
        self._cancellation.set()
        self._task_bus.publish(TaskEvent(event_type="batch_stopping", task_id=self._task_id))

    def _process_item(self, task_id: str, material: MaterialItem) -> None:
        if self._cancellation.is_set():
            self._finish_one(task_id)
            return
        self._task_bus.publish(TaskEvent(event_type="item_started", task_id=task_id, material_id=material.row_id))
        try:
            query = self._query_builder.build(material)
            ai_reason = None
            if self._enable_ai and self._ai_service is not None:
                query, ai_reason = self._ai_service.optimize_query(material, query)

            if self._cancellation.is_set():
                raise RuntimeError("任务已停止")

            offers, cache_hit = self._fetch_offers(query)
            retried_with_ai = False
            if not offers and self._enable_ai and self._ai_service is not None:
                optimized_retry_query, retry_reason = self._ai_service.optimize_query(material, self._fallback_query(material, query))
                retry_offers, retry_cache_hit = self._fetch_offers(optimized_retry_query)
                if retry_offers:
                    query = optimized_retry_query
                    offers = retry_offers
                    cache_hit = retry_cache_hit
                    retried_with_ai = True
                    ai_reason = retry_reason

            compare_result = self._compare_service.compare(material, offers)
            if compare_result.top_offers and self._enable_ai and self._ai_service is not None:
                compare_result.ai_comment = self._ai_service.explain_match(material, compare_result.top_offers[0])
            elif ai_reason and compare_result.ai_comment:
                compare_result.ai_comment = f"{compare_result.ai_comment}；{ai_reason}"
            elif ai_reason:
                compare_result.ai_comment = ai_reason

            if cache_hit:
                compare_result.search_status = TaskStatus.CACHED
                compare_result.cache_hit = True

            self._task_bus.publish(
                TaskEvent(
                    event_type="item_finished",
                    task_id=task_id,
                    material_id=material.row_id,
                    payload={
                        "result": compare_result,
                        "query": query,
                        "offers": offers,
                        "cache_hit": cache_hit,
                        "ai_used": self._enable_ai and self._ai_service is not None,
                        "retried_with_ai": retried_with_ai,
                    },
                )
            )
        except Exception as exc:
            compare_result = CompareResult(
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
                cache_hit=False,
                error_message=str(exc),
            )
            self._task_bus.publish(
                TaskEvent(
                    event_type="item_failed",
                    task_id=task_id,
                    material_id=material.row_id,
                    payload={"result": compare_result},
                    error=str(exc),
                )
            )
        finally:
            self._finish_one(task_id)

    def _fetch_offers(self, query: SearchQuery) -> tuple[list, bool]:
        cache_hit = False
        offers = None
        if self._cache_repository is not None:
            offers = self._cache_repository.get_search_cache(
                platform=self._provider.platform,
                normalized_query=query.normalized_text,
                provider_name=self._provider.provider_name,
                provider_version=self._provider.provider_version,
            )
            cache_hit = offers is not None
        if offers is None:
            offers = self._provider.search(query)
            if self._cache_repository is not None:
                self._cache_repository.set_search_cache(
                    platform=self._provider.platform,
                    provider_name=self._provider.provider_name,
                    provider_version=self._provider.provider_version,
                    query=query,
                    offers=offers,
                )
        return offers, cache_hit

    @staticmethod
    def _fallback_query(material: MaterialItem, query: SearchQuery) -> SearchQuery:
        fallback_keywords = []
        if material.name:
            fallback_keywords.append(material.name)
        if material.spec:
            fallback_keywords.append(material.spec)
        return SearchQuery(
            material_id=query.material_id,
            original_text=query.original_text,
            normalized_text=" ".join(fallback_keywords).lower() or query.normalized_text,
            brand_hint=query.brand_hint,
            spec_hint=query.spec_hint,
            keywords=fallback_keywords or query.keywords,
        )

    def _finish_one(self, task_id: str) -> None:
        with self._lock:
            self._pending -= 1
            remaining = self._pending
        if remaining == 0:
            self._task_bus.publish(TaskEvent(event_type="batch_finished", task_id=task_id))
