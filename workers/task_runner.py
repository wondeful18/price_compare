from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable


class TaskRunner:
    def __init__(self, max_workers: int) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="search-worker")

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
