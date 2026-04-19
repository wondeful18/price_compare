from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TaskEvent:
    event_type: str
    task_id: str
    material_id: int | None = None
    payload: dict[str, Any] | None = None
    error: str | None = None
