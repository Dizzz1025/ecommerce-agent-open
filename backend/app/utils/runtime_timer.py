from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from time import perf_counter
from typing import Any


class RuntimeTimer:
    """Lightweight per-turn timing collector."""

    def __init__(self) -> None:
        self._turn_start_perf = perf_counter()
        self._turn_start_wall = _now()
        self._records: list[dict[str, Any]] = []
        self._model_calls: list[dict[str, Any]] = []

    @contextmanager
    def measure(self, module: str, description: str | None = None):
        start_perf = perf_counter()
        start_wall = _now()
        try:
            yield
        finally:
            end_perf = perf_counter()
            record = {
                "module": module,
                "中文说明": description or module,
                "start_time": start_wall,
                "end_time": _now(),
                "duration_ms": round((end_perf - start_perf) * 1000, 2),
            }
            self._records.append(record)

    def mark_model_call(
        self,
        *,
        module: str,
        provider: str | None,
        purpose: str,
        duration_ms: float,
        called: bool = True,
    ) -> None:
        if not called:
            return
        self._model_calls.append(
            {
                "module": module,
                "provider": provider,
                "purpose": purpose,
                "duration_ms": round(duration_ms, 2),
            }
        )

    def last_duration(self, module: str) -> float:
        for record in reversed(self._records):
            if record["module"] == module:
                return float(record["duration_ms"])
        return 0.0

    def elapsed_ms(self) -> float:
        return round((perf_counter() - self._turn_start_perf) * 1000, 2)

    def summary(self) -> dict[str, Any]:
        total_ms = round((perf_counter() - self._turn_start_perf) * 1000, 2)
        top = sorted(self._records, key=lambda item: item["duration_ms"], reverse=True)[:5]
        return {
            "中文说明": "本部分统计本轮后端主要模块耗时，用于定位等待时间瓶颈。计时为轻量级 wall-clock 统计，不包含前端渲染时间。",
            "turn_start_time": self._turn_start_wall,
            "turn_end_time": _now(),
            "total_duration_ms": total_ms,
            "module_count": len(self._records),
            "模块明细": self._records,
            "模型调用": {
                "调用次数": len(self._model_calls),
                "总耗时_ms": round(sum(item["duration_ms"] for item in self._model_calls), 2),
                "明细": self._model_calls,
            },
            "Top耗时模块": top,
        }


def _now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")
