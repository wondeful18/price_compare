from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from application.ai_service import AiService
from application.compare_app_service import CompareAppService
from application.query_builder_service import QueryBuilderService
from application.search_task_service import SearchTaskService
from config.settings import load_settings
from domain.models import MaterialItem
from infra.deepseek_client import DeepSeekClient
from infra.http_client import build_mock_http_client
from infra.sqlite_db import SQLiteDB
from providers.jd_provider import JDOfficialProvider
from repositories.cache_repository import CacheRepository
from workers.task_bus import TaskBus
from workers.task_runner import TaskRunner


class SearchTaskServiceTests(unittest.TestCase):
    def test_emits_item_and_batch_events(self) -> None:
        settings = load_settings()
        task_bus = TaskBus()
        runner = TaskRunner(max_workers=1)
        temp_dir = tempfile.TemporaryDirectory()
        cache_repo = CacheRepository(SQLiteDB(Path(temp_dir.name) / "cache.db"))
        service = SearchTaskService(
            provider=JDOfficialProvider(build_mock_http_client()),
            query_builder=QueryBuilderService(),
            compare_service=CompareAppService(settings.top_n_offers),
            cache_repository=cache_repo,
            ai_service=AiService(DeepSeekClient(), cache_repo),
            task_runner=runner,
            task_bus=task_bus,
        )
        materials = [MaterialItem(row_id=1, serial_no="1", name="电钻", spec="220V", brand="博世")]

        service.start_batch(materials, enable_ai=True)

        events = []
        for _ in range(30):
            events.extend(task_bus.drain())
            if any(event.event_type == "batch_finished" for event in events):
                break
            time.sleep(0.05)
        runner.shutdown()
        temp_dir.cleanup()

        event_types = [event.event_type for event in events]
        self.assertIn("batch_started", event_types)
        self.assertIn("item_started", event_types)
        self.assertIn("item_finished", event_types)
        self.assertIn("batch_finished", event_types)
        self.assertTrue(any(event.payload.get("ai_used") for event in events if event.event_type == "item_finished"))


if __name__ == "__main__":
    unittest.main()
