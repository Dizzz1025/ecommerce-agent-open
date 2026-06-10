"""Observe real HTTP SSE streaming timing.

This script is intentionally separate from agent_console.py. The console uses
FastAPI TestClient, which is convenient for backend debugging but may buffer SSE
in-process. This observer connects to a running uvicorn server through real HTTP,
so it is closer to what curl / Android / frontend fetch will see.

Example:
    cd backend
    python3 scripts/http_stream_observer.py \
      --message "推荐10000元以内，拍照好的手机" \
      --user_id stream_user \
      --session_id stream_demo
"""

from __future__ import annotations

import argparse
import json
from time import perf_counter
from typing import Any

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="真实 HTTP SSE 流式输出观察脚本")
    parser.add_argument("--base_url", default="http://127.0.0.1:8000", help="FastAPI 服务地址")
    parser.add_argument("--message", required=True, help="用户输入")
    parser.add_argument("--user_id", default="stream_user", help="用户ID")
    parser.add_argument("--session_id", default="stream_session", help="会话ID")
    parser.add_argument("--input_type", default="text", help="text / image_text / image / multimodal")
    parser.add_argument("--resume", action="store_true", help="是否从历史恢复")
    parser.add_argument("--resume_session_id", default=None, help="指定历史会话ID；传入后会自动触发恢复")
    parser.add_argument("--new_session", action="store_true", help="是否开启新会话")
    parser.add_argument("--image_path", default=None, help="本地图片路径，JSON 接口调试用")
    parser.add_argument("--voice_file", default=None, help="本地语音文件路径；传入后调用 /api/chat/stream/voice")
    parser.add_argument("--tts_response", action="store_true", help="语音对话时是否合成语音回复")
    parser.add_argument("--timeout", type=float, default=100.0, help="单轮最长等待秒数")
    args = parser.parse_args()

    metadata: dict[str, Any] = {}
    if args.resume_session_id:
        metadata["resume_session_id"] = args.resume_session_id
    if args.image_path:
        metadata["image_path"] = args.image_path

    payload = {
        "user_id": args.user_id,
        "session_id": args.session_id,
        "message": args.message,
        "input_type": args.input_type,
        "resume": args.resume,
        "new_session": args.new_session,
        "metadata": metadata,
    }
    use_voice = bool(args.voice_file)
    url = args.base_url.rstrip("/") + ("/api/chat/stream/voice" if use_voice else "/api/chat/stream")
    print(f"POST {url}", flush=True)
    print("提示：如果 progress 很快出现，说明真实 HTTP 流式输出正常；正式结果出现后前端应停止 progress。")

    stream_start = perf_counter()
    current_event = "message"
    data_lines: list[str] = []
    event_counts: dict[str, int] = {}
    first_progress_ms: float | None = None
    first_formal_ms: float | None = None

    request_kwargs: dict[str, Any]
    files = None
    if use_voice:
        voice_path = args.voice_file
        files = {"audio": open(voice_path, "rb")}
        request_kwargs = {
            "data": {
                "user_id": args.user_id,
                "session_id": args.session_id,
                "resume": str(args.resume).lower(),
                "new_session": str(args.new_session).lower(),
                "tts_response": str(args.tts_response).lower(),
                **({"resume_session_id": args.resume_session_id} if args.resume_session_id else {}),
            },
            "files": files,
        }
    else:
        request_kwargs = {"json": payload}

    try:
        with httpx.stream("POST", url, timeout=args.timeout, **request_kwargs) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                    continue
                if line.startswith("data:"):
                    data_lines.append(line.split(":", 1)[1].strip())
                    continue
                if line.strip() != "" or not data_lines:
                    continue

                elapsed_ms = (perf_counter() - stream_start) * 1000
                data = _parse_json(data_lines)
                event_counts[current_event] = event_counts.get(current_event, 0) + 1
                if current_event == "progress":
                    first_progress_ms = first_progress_ms if first_progress_ms is not None else elapsed_ms
                    progress_text = data.get("display_text") or data.get("progress_message") or data.get("text") or data.get("message")
                    print(f"[{elapsed_ms:8.1f} ms] progress: {progress_text}", flush=True)
                elif current_event == "voice_transcript":
                    print(f"[{elapsed_ms:8.1f} ms] voice_transcript: {data.get('text') or data.get('message')}", flush=True)
                elif current_event == "voice_output":
                    print(f"[{elapsed_ms:8.1f} ms] voice_output: {data.get('url') or data.get('message')}", flush=True)
                elif current_event == "turn_result":
                    first_formal_ms = first_formal_ms if first_formal_ms is not None else elapsed_ms
                    _print_turn_result(elapsed_ms, data)
                elif current_event in {"state", "token", "product_cards", "products", "frontend_action", "cart", "cart_update"}:
                    if first_formal_ms is None and current_event != "token":
                        first_formal_ms = elapsed_ms
                    if current_event != "token":
                        print(f"[{elapsed_ms:8.1f} ms] {current_event}", flush=True)
                elif current_event == "done":
                    print(f"[{elapsed_ms:8.1f} ms] done: {data.get('finish_reason')}", flush=True)
                    break
                elif current_event == "error":
                    print(f"[{elapsed_ms:8.1f} ms] error: {data}", flush=True)

                current_event = "message"
                data_lines = []
    finally:
        if files:
            files["audio"].close()

    total_ms = (perf_counter() - stream_start) * 1000
    print("\n--- 流式统计")
    print(json.dumps(
        {
            "first_progress_ms": round(first_progress_ms, 2) if first_progress_ms is not None else None,
            "first_formal_event_ms": round(first_formal_ms, 2) if first_formal_ms is not None else None,
            "total_ms": round(total_ms, 2),
            "event_counts": event_counts,
        },
        ensure_ascii=False,
        indent=2,
    ))


def _parse_json(data_lines: list[str]) -> dict[str, Any]:
    raw = "\n".join(data_lines)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _print_turn_result(elapsed_ms: float, data: dict[str, Any]) -> None:
    frontend_data = data.get("frontend_data") or {}
    reply = ((frontend_data.get("reply_message") or {}).get("text") or "").replace("\n", " / ")
    products = (
        (frontend_data.get("recommended_products") or {}).get("products")
        or (frontend_data.get("alternative_products") or {}).get("products")
        or []
    )
    debug = data.get("system_debug") or {}
    timing = debug.get("运行耗时统计") or {}
    print(f"[{elapsed_ms:8.1f} ms] turn_result")
    if reply:
        print(f"  回复：{reply[:180]}")
    if products:
        print("  商品：")
        for item in products[:5]:
            print(f"    - {item.get('sku_id')} | {item.get('name')} | ¥{item.get('price')}")
    if timing:
        print(f"  后端总耗时：{timing.get('total_duration_ms')} ms")


if __name__ == "__main__":
    main()
