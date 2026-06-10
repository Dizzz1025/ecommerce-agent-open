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
        call_debug: dict[str, Any] | None = None,
    ) -> None:
        if not called:
            item = {
                "module": module,
                "provider": provider,
                "purpose": purpose,
                "duration_ms": round(duration_ms, 2),
                "llm_call_attempted": False,
                "llm_is_mock": provider == "MockLLMClient",
                "http_request_sent": False,
                "http_request_succeeded": False,
                "http_status_code": None,
                "raw_output_received": False,
                "fallback_triggered": False,
                "fallback_reason": "skipped_by_policy",
                "call_succeeded": False,
                "skipped_by_policy": True,
            }
            self._model_calls.append(item)
            return
        item = {
            "module": module,
            "provider": provider,
            "purpose": purpose,
            "duration_ms": round(duration_ms, 2),
        }
        item.update(_model_call_debug_fields(call_debug or {}, provider))
        if call_debug:
            item["call_debug"] = call_debug
        self._model_calls.append(item)

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
                **_model_call_stats(self._model_calls),
                "明细": self._model_calls,
            },
            "Top耗时模块": top,
        }


def _now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def _model_call_debug_fields(call_debug: dict[str, Any], provider: str | None) -> dict[str, Any]:
    is_mock = bool(call_debug.get("llm_is_mock")) or provider == "MockLLMClient"
    attempted = bool(call_debug.get("llm_call_attempted", True))
    http_sent = bool(call_debug.get("http_request_sent"))
    http_succeeded = bool(call_debug.get("http_request_succeeded"))
    fallback = bool(call_debug.get("fallback_triggered"))
    raw_received = bool(call_debug.get("raw_output_received"))
    succeeded = (http_succeeded and raw_received and not fallback) or (is_mock and raw_received and not fallback)
    return {
        "llm_call_attempted": attempted,
        "llm_is_mock": is_mock,
        "http_request_sent": http_sent,
        "http_request_succeeded": http_succeeded,
        "http_status_code": call_debug.get("http_status_code"),
        "raw_output_received": raw_received,
        "fallback_triggered": fallback,
        "fallback_reason": call_debug.get("fallback_reason"),
        "call_succeeded": succeeded,
    }


def _model_call_stats(calls: list[dict[str, Any]]) -> dict[str, Any]:
    attempted = [item for item in calls if item.get("llm_call_attempted")]
    successful = [item for item in attempted if item.get("call_succeeded")]
    failed = [
        item
        for item in attempted
        if item.get("fallback_triggered")
        or (item.get("http_request_sent") and not item.get("http_request_succeeded"))
    ]
    return {
        "planned_call_count": len(calls),
        "attempted_call_count": len(attempted),
        "real_http_call_count": sum(1 for item in calls if item.get("http_request_sent") and not item.get("llm_is_mock")),
        "successful_call_count": len(successful),
        "failed_call_count": len(failed),
        "mock_call_count": sum(1 for item in calls if item.get("llm_is_mock")),
        "fallback_count": sum(1 for item in calls if item.get("fallback_triggered")),
    }
