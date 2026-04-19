from __future__ import annotations

from queue import Empty, Queue

from application.events import TaskEvent


class TaskBus:
    def __init__(self) -> None:
        self._queue: Queue[TaskEvent] = Queue()

    def publish(self, event: TaskEvent) -> None:
        self._queue.put(event)

    def drain(self) -> list[TaskEvent]:
        events: list[TaskEvent] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except Empty:
                return events
