from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    IDLE = "未处理"
    READY = "待处理"
    RUNNING = "搜索中"
    CACHED = "使用缓存"
    DONE = "已完成"
    FAILED = "失败"


class PlatformType(str, Enum):
    JD = "jd"
    TAOBAO = "taobao"
    PDD = "pdd"
    UNKNOWN = "unknown"


class MatchLevel(str, Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"
