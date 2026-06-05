"""Unified multi-turn Agent console.

Usage:
    cd backend
    python3 scripts/agent_console.py --mode old_user --user_id beauty_lily --session_id beauty_lily_test
    python3 scripts/agent_console.py --mode new_user --user_id new_demo --session_id new_demo
    python3 scripts/agent_console.py --mode old_user --scenario personalization_flow
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.dependencies import get_user_profile_service  # noqa: E402
from app.main import app  # noqa: E402


SCENARIOS = {
    "shopping_flow": [
        "你好",
        "推荐一款适合油皮的洗面奶，100元以内",
        "换一个更清爽一点的",
        "不要日系品牌",
        "把第一款加入购物车",
        "查看购物车",
        "下单吧，地址用默认的",
    ],
    "reference_flow": [
        "帮我推荐500元以内轻一点的跑鞋",
        "第二个适合通勤吗",
        "把第二个加入购物车",
        "购物车里的那个和刚才第一个比一下",
    ],
    "resume_seed": [
        "我一直比较喜欢清爽、性价比高的东西，记住一下",
        "帮我看看拍照好的手机，预算5000以内",
        "先这样，谢谢",
    ],
    "personalization_flow": [
        "我一直比较喜欢清爽、性价比高的护肤品，记住一下",
        "推荐一款适合夏天通勤用的防晒霜",
        "太油腻的不要，价格别太夸张",
        "这几款里面哪个更适合我",
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="多轮对话、memory、状态机和统一输出测试脚本")
    parser.add_argument("messages", nargs="*", help="可选：直接传入多轮用户消息；不传则进入交互模式。")
    parser.add_argument(
        "--mode",
        choices=["old_user", "new_user"],
        default="old_user",
        help="old_user 会在第一轮尝试加载该用户历史；new_user 会在第一轮强制开启新会话。",
    )
    parser.add_argument("--user_id", default="debug_user", help="用户ID，用于长期历史和用户画像。")
    parser.add_argument("--session_id", default=None, help="会话ID，同一个会话ID会延续短期记忆。")
    parser.add_argument("--resume", action="store_true", help="第一轮从该用户最近一次本地历史会话恢复；old_user 默认启用。")
    parser.add_argument("--resume_session_id", default=None, help="指定要恢复的历史会话ID；不填则恢复最近会话。")
    parser.add_argument("--new_session", action="store_true", help="第一轮开启新会话；new_user 默认启用。")
    parser.add_argument("--show_debug", action="store_true", help="展示 system_debug 全量信息。")
    parser.add_argument("--raw", action="store_true", help="打印原始SSE事件。")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), help="运行内置多轮测试场景。")
    parser.add_argument("--input_type", default="text", help="输入类型：text / image_text / image / multimodal。")
    parser.add_argument("--image_path", default=None, help="本地图片路径，多模态测试时使用。")
    parser.add_argument("--image_url", default=None, help="图片URL，多模态测试时使用。")
    parser.add_argument("--image_base64", default=None, help="base64图片内容，多模态测试时使用。")
    parser.add_argument("--voice_url", default=None, help="语音URL占位字段，当前先透传给后端。")
    parser.add_argument("--privacy_mode", default=None, help="隐私模式：standard / semantic / off 等，透传给历史存储。")
    parser.add_argument(
        "--no_auto_profile",
        action="store_true",
        help="批量消息结束后不强制刷新长期画像；交互模式可用 /end 手动刷新。",
    )
    args = parser.parse_args()

    session_id = args.session_id or f"console_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    client = TestClient(app)
    messages = args.messages or (SCENARIOS[args.scenario] if args.scenario else [])
    base_metadata = _build_metadata(args)

    print("多轮测试已启动。每一轮都会带 user_id 和 session_id，并写入本地 storage/user_history。")
    print(f"mode = {args.mode}（old_user=第一轮加载历史，new_user=第一轮新会话）")
    print(f"user_id = {args.user_id}")
    print(f"session_id = {session_id}")
    if args.resume_session_id:
        print(f"resume_session_id = {args.resume_session_id}")
    if args.input_type != "text":
        print(f"input_type = {args.input_type}，多模态信息会通过 metadata 透传给后端。")
    print("命令：/state 当前状态摘要，/memory 短期记忆摘要，/trace 最近执行链路，/profile 长期画像摘要。")
    print("      /debug 或 /all 展示最近一轮完整JSON，/end 生成画像并退出，/quit 退出，/help 查看命令说明。")

    first_turn = True
    last_turn_result: dict[str, Any] | None = None
    if messages:
        for message in messages:
            last_turn_result = _run_turn(
                client=client,
                user_id=args.user_id,
                session_id=session_id,
                message=message,
                resume=_should_resume(args, first_turn),
                new_session=_should_start_new_session(args, first_turn),
                input_type=args.input_type,
                metadata=base_metadata,
                show_debug=args.show_debug,
                raw=args.raw,
            )
            first_turn = False
        if not args.no_auto_profile:
            _refresh_profile(args.user_id)
        return

    while True:
        try:
            message = input("\nUSER> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            _refresh_profile(args.user_id)
            return
        if not message:
            continue
        if message in {"/quit", "quit", "exit"}:
            print("退出。")
            return
        if message == "/end":
            _refresh_profile(args.user_id)
            print("已强制生成/刷新用户画像。退出。")
            return
        if message == "/help":
            _print_help()
            continue
        if message == "/state":
            _print_compact_state(client, session_id)
            continue
        if message == "/memory":
            _print_compact_memory(client, session_id)
            continue
        if message == "/trace":
            _print_compact_trace(client, session_id)
            continue
        if message == "/profile":
            _print_compact_profile(client, session_id, args.user_id)
            continue
        if message in {"/debug", "/all", "/full"}:
            _print_full_debug(client, session_id, args.user_id, last_turn_result)
            continue

        last_turn_result = _run_turn(
            client=client,
            user_id=args.user_id,
            session_id=session_id,
            message=message,
            resume=_should_resume(args, first_turn),
            new_session=_should_start_new_session(args, first_turn),
            input_type=args.input_type,
            metadata=base_metadata,
            show_debug=args.show_debug,
            raw=args.raw,
        )
        first_turn = False


def _run_turn(
    *,
    client: TestClient,
    user_id: str,
    session_id: str,
    message: str,
    resume: bool,
    new_session: bool,
    input_type: str,
    metadata: dict[str, Any],
    show_debug: bool,
    raw: bool,
) -> dict[str, Any] | None:
    print(f"\n=== USER: {message}")
    events: list[tuple[str, dict[str, Any]]] = []
    stream_start = perf_counter()
    progress_header_printed = False
    with client.stream(
            "POST",
            "/api/chat/stream",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "message": message,
                "input_type": input_type,
                "resume": resume,
                "new_session": new_session,
                "metadata": metadata,
            },
        ) as response:
        response.raise_for_status()
        current_event = "message"
        data_lines: list[str] = []
        for line in response.iter_lines():
            line = line.decode("utf-8") if isinstance(line, bytes) else line
            if raw:
                print(line)
            if line == "":
                progress_header_printed = _flush_stream_event(
                    events=events,
                    event_name=current_event,
                    data_lines=data_lines,
                    stream_start=stream_start,
                    progress_header_printed=progress_header_printed,
                )
                current_event = "message"
                data_lines = []
                continue
            if line.startswith("event: "):
                current_event = line.removeprefix("event: ").strip()
            elif line.startswith("data: "):
                data_lines.append(line.removeprefix("data: ").strip())
        if data_lines:
            _flush_stream_event(
                events=events,
                event_name=current_event,
                data_lines=data_lines,
                stream_start=stream_start,
                progress_header_printed=progress_header_printed,
            )
    turn_result = _last_event(events, "turn_result")
    if turn_result:
        _print_turn_result(turn_result, show_debug=show_debug)
        return turn_result
    else:
        print("没有收到 turn_result，下面展示原始事件摘要：")
        print("EVENTS:", " -> ".join(name for name, _ in events))
        return None


def _print_turn_result(payload: dict[str, Any], *, show_debug: bool) -> None:
    print("\n--- frontend_events / 前端动作列表")
    _print_events(payload.get("frontend_events", []))

    print("\n--- frontend_data / 前端动作数据")
    frontend_data = payload.get("frontend_data", {})
    _print_frontend_data_summary(frontend_data)

    if show_debug:
        print("\n--- system_debug / 系统调试信息")
        _print_json(payload.get("system_debug", {}))
    else:
        debug = payload.get("system_debug", {})
        print("\n--- system_debug / 系统调试摘要")
        _print_json(_compact_system_debug(debug))


def _print_help() -> None:
    print(
        """
可用命令：
  /state    查看当前对话状态摘要：流程、意图、类目、当前约束、购物车数量。
  /memory   查看短期记忆摘要：最近几轮话、最近推荐商品、购物车简况。
  /trace    查看最近一轮执行链路：理解结果、检索数量、最终推荐、工具和模型调用。
  /profile  查看长期用户画像摘要：历史会话数、自然语言画像、结构化偏好。
  /debug    展示最近一轮完整 turn_result，以及完整 state/memory/trace/profile。
  /all      同 /debug。
  /end      强制生成/刷新用户画像并退出。
  /quit     退出，不强制刷新画像。
""".strip()
    )


def _print_events(events: list[dict[str, Any]]) -> None:
    if not events:
        print("  本轮没有前端动作。")
        return
    for event in events:
        blocking = "，需等待完成" if event.get("blocking") else ""
        print(
            f"  {event.get('步骤')}. {event.get('动作类型')} -> {event.get('数据参考')}"
            f" | {event.get('含义')}{blocking}"
        )


def _flush_stream_event(
    *,
    events: list[tuple[str, dict[str, Any]]],
    event_name: str,
    data_lines: list[str],
    stream_start: float,
    progress_header_printed: bool,
) -> bool:
    if not data_lines:
        return progress_header_printed
    try:
        data = json.loads("\n".join(data_lines))
    except json.JSONDecodeError:
        data = {"raw": "\n".join(data_lines)}
    events.append((event_name, data))
    if event_name == "progress":
        if not progress_header_printed:
            print("\n--- progress_events / 前端流式进度")
            progress_header_printed = True
        _print_single_progress_event(data, elapsed_ms=(perf_counter() - stream_start) * 1000)
    return progress_header_printed


def _print_single_progress_event(event: dict[str, Any], *, elapsed_ms: float) -> None:
    print(
        f"  {event.get('step')}. [{event.get('stage') or event.get('stage_key')}] "
        f"{event.get('text')} (+{elapsed_ms:.0f}ms)"
    )


def _build_metadata(args: argparse.Namespace) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in ["image_path", "image_url", "image_base64", "voice_url", "privacy_mode", "resume_session_id"]:
        value = getattr(args, key, None)
        if value not in (None, ""):
            metadata[key] = value
    return metadata


def _should_resume(args: argparse.Namespace, first_turn: bool) -> bool:
    if not first_turn:
        return False
    if args.new_session or args.mode == "new_user":
        return False
    return bool(args.resume or args.resume_session_id or args.mode == "old_user")


def _should_start_new_session(args: argparse.Namespace, first_turn: bool) -> bool:
    if not first_turn:
        return False
    if args.resume or args.resume_session_id:
        return False
    return bool(args.new_session or args.mode == "new_user")


def _print_frontend_data_summary(frontend_data: dict[str, Any]) -> None:
    reply = frontend_data.get("reply_message", {}).get("text")
    if reply:
        print("  回复文本：")
        for line in reply.splitlines():
            print(f"    {line}")

    for key, label in [
        ("recommended_products", "推荐商品"),
        ("alternative_products", "相近备选"),
    ]:
        products = _compact_products(frontend_data.get(key))
        if products and products.get("products"):
            print(f"  {label}：")
            for product in products["products"]:
                print(
                    f"    {product['rank']}. {product.get('sku_id')} | {product.get('name')} "
                    f"| ¥{product.get('price')} | score={product.get('score')} | {product.get('reason')}"
                )

    detail = _compact_product_detail(frontend_data.get("product_detail"))
    if detail:
        product = detail.get("product", {})
        print(f"  商品详情：{product.get('sku_id')} | {product.get('name')} | ¥{product.get('price')}")
        qa = detail.get("qa") or {}
        if qa.get("answer"):
            print(f"    回答：{qa.get('answer')}")

    cart_state = _compact_cart_state(frontend_data.get("cart_state"))
    if cart_state:
        print("  购物车/订单：")
        _print_json(cart_state)

    navigation = frontend_data.get("navigation")
    if navigation:
        params = _compact_navigation_params(navigation.get("params", {}))
        print(
            "  页面跳转："
            f"{navigation.get('target_page')} | {navigation.get('reason')} | params={params}"
        )

    clarification = frontend_data.get("clarification_options")
    if clarification:
        print(f"  澄清问题：{clarification.get('question')}")
        options = clarification.get("options") or []
        if options:
            print(f"    快捷选项：{' / '.join(options)}")

    error = frontend_data.get("error_message")
    if error:
        print(f"  错误提示：{error.get('code')} | {error.get('message')}")


def _compact_system_debug(debug: dict[str, Any]) -> dict[str, Any]:
    analysis = debug.get("当前轮次分析", {})
    state_after = debug.get("对话状态变化", {}).get("变化后", {})
    rag = debug.get("RAG检索过程", {})
    model = debug.get("模型调用", {})
    action = debug.get("前端动作决策", {})
    intent_plan = debug.get("Doubao意图计划", {}).get("内容")
    personalization = debug.get("个性化分析", {})
    multimodal = debug.get("多模态分析", {})
    progress = debug.get("进度事件") or debug.get("Progress事件") or {}
    timings = debug.get("运行耗时统计") or {}
    cart_personalization = debug.get("购物车商品侧个性化") or {}
    enhancement = debug.get("商品增强字段使用") or {}
    retrieval_scores = rag.get("检索评分摘要", []) or []
    is_disabled_feature = lambda obj: isinstance(obj, dict) and obj.get("启用") is False and not any(
        v for k, v in obj.items() if k != "启用" and v
    )

    result: dict[str, Any] = {
        "本轮理解": {
            "意图": analysis.get("意图"),
            "流程": analysis.get("业务流程"),
            "类目": f"{analysis.get('商品类别')}/{analysis.get('商品子类')}",
            "价格": analysis.get("价格约束"),
            "正向偏好": analysis.get("正向偏好"),
            "否定约束": analysis.get("否定约束"),
            "需要检索": analysis.get("是否需要检索"),
            "调用大模型": analysis.get("是否调用大模型"),
        },
        "意图计划": intent_plan,
        "状态结果": {
            "当前流程": state_after.get("当前流程"),
            "当前类别": f"{state_after.get('当前类别')}/{state_after.get('当前子类')}",
            "购物车数量": state_after.get("购物车数量"),
            "最近推荐商品": state_after.get("最近推荐商品"),
        },
    }

    # 检索摘要 — 只在执行检索时展示详细信息
    if rag.get("召回商品数量"):
        result["检索摘要"] = {
            "检索方式": rag.get("检索方式"),
            "召回数量": rag.get("召回商品数量"),
            "最终推荐商品ID": rag.get("最终推荐商品ID"),
            "Top评分": [
                {
                    "sku_id": item.get("sku_id"),
                    "score": item.get("score"),
                    "reasons": item.get("matched_reasons", [])[:3],
                }
                for item in retrieval_scores[:3]
            ],
        }
    else:
        result["检索摘要"] = "本轮未执行商品检索"

    # 进度事件 — 精简为关键字段
    result["进度事件"] = {
        "预测工作类型": progress.get("预测工作类型"),
        "已输出数量": progress.get("已输出数量"),
        "停止原因": progress.get("停止原因"),
        "实际总耗时_ms": progress.get("实际总耗时_ms"),
    }

    result["运行耗时"] = {
        "总耗时_ms": timings.get("total_duration_ms"),
        "模块数量": timings.get("module_count"),
        "模型调用耗时_ms": sum(
            call.get("duration_ms", 0)
            for call in (timings.get("模型调用", {}).get("明细") or [])
        ),
        "Top耗时模块": [
            {
                "module": item.get("module"),
                "耗时_ms": item.get("duration_ms"),
                "说明": item.get("中文说明"),
            }
            for item in timings.get("Top耗时模块", [])[:5]
        ],
    }

    result["工具执行"] = _compact_tool_calls(debug.get("工具执行", []))

    # 个性化 — 只在启用时展示详细
    if personalization.get("是否启用个性化"):
        cf = personalization.get("相似历史用户协同过滤") or {}
        result["个性化"] = {
            "领域风格": {
                "角色": (personalization.get("领域导购风格") or {}).get("导购角色"),
                "重点": (personalization.get("领域导购风格") or {}).get("解释重点"),
            },
            "历史证据数": len(personalization.get("本轮选中的历史证据", []) or []),
            "few-shot数": len(personalization.get("本轮使用的few-shot示例", []) or []),
            "协同过滤相似用户": [
                f"{item.get('user_id')} (相似度{item.get('相似度')})"
                for item in cf.get("相似用户", [])[:3]
            ],
        }
    else:
        result["个性化"] = "未启用"

    # 购物车个性化 — 精简核心信息
    if cart_personalization.get("是否启用"):
        result["购物车商品侧个性化"] = {
            "目标类目": cart_personalization.get("目标类目"),
            "参考商品": [
                item.get("sku_id")
                for item in cart_personalization.get("参考购物车商品", [])[:6]
            ],
            "商品标签": cart_personalization.get("商品标签", [])[:6],
            "价格画像": cart_personalization.get("价格画像"),
            "命中规则": [
                item.get("rule_id")
                for item in cart_personalization.get("命中的本地规则", [])[:6]
            ],
            "调用Doubao": cart_personalization.get("是否调用Doubao"),
        }
    else:
        result["购物车商品侧个性化"] = "未启用"

    # 以下模块仅在启用或有效数据时展示
    if enhancement.get("是否启用") and enhancement.get("使用的增强字段"):
        result["商品增强字段"] = {
            "使用字段": enhancement.get("使用的增强字段", [])[:8],
            "非标准标签": enhancement.get("命中的非标准问题标签", [])[:5],
            "适用场景": enhancement.get("命中的适用场景", [])[:5],
        }

    if multimodal.get("是否启用多模态"):
        result["多模态"] = {
            "主要类别": (multimodal.get("图片理解结果", {}) or {}).get("主要商品类别"),
            "融合查询": (multimodal.get("图文融合查询", {}) or {}).get("融合后的检索文本"),
            "库存可覆盖": (multimodal.get("库存匹配判断", {}) or {}).get("库存是否覆盖目标类目"),
        }

    result["前端动作"] = {
        "action": action.get("action"),
        "target_page": action.get("target_page"),
        "是否结束": action.get("should_end_conversation"),
        "来源": action.get("source"),
    }

    return result


def _compact_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in tool_calls:
        payload = item.get("payload") or {}
        compact.append(
            {
                "tool_name": item.get("tool_name"),
                "ok": item.get("ok"),
                "message": item.get("message"),
                "error_code": item.get("error_code"),
                "payload摘要": {
                    "total_items": payload.get("total_items"),
                    "total_price": payload.get("total_price"),
                    "item_ids": [cart_item.get("sku_id") for cart_item in payload.get("items", [])],
                    "order_id": (payload.get("order") or {}).get("order_id"),
                },
            }
        )
    return compact


def _compact_products(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    return {
        "中文说明": payload.get("中文说明"),
        "products": [
            {
                "rank": index,
                "sku_id": product.get("sku_id"),
                "name": product.get("name"),
                "price": product.get("price"),
                "reason": product.get("reason"),
                "score": product.get("score"),
            }
            for index, product in enumerate(payload.get("products", []), start=1)
        ],
    }


def _compact_product_detail(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    product = payload.get("product", {})
    qa = payload.get("qa", {})
    return {
        "中文说明": payload.get("中文说明"),
        "product": {
            "sku_id": product.get("sku_id"),
            "name": product.get("name"),
            "price": product.get("price"),
            "stock": product.get("stock"),
        },
        "qa": qa,
    }


def _compact_cart_state(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    cart = payload.get("cart", {})
    items = cart.get("items", []) if isinstance(cart, dict) else []
    compact = {
        "tool_ok": payload.get("tool_ok"),
        "tool_name": payload.get("tool_name"),
        "message": payload.get("message"),
        "total_items": cart.get("total_items") if isinstance(cart, dict) else None,
        "total_price": cart.get("total_price") if isinstance(cart, dict) else None,
        "items": [
            {
                "sku_id": item.get("sku_id"),
                "name": item.get("name"),
                "quantity": item.get("quantity"),
                "price": item.get("price"),
            }
            for item in items
        ],
    }
    if isinstance(cart, dict) and cart.get("order"):
        order = cart["order"]
        compact["order"] = {
            "order_id": order.get("order_id"),
            "total_price": order.get("total_price"),
            "status": order.get("status"),
        }
    return compact


def _compact_navigation_params(params: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(params, dict):
        return {}
    return {
        key: value
        for key, value in {
            "product_ids": params.get("product_ids"),
            "total_items": params.get("total_items"),
            "total_price": params.get("total_price"),
            "order_id": (params.get("order") or {}).get("order_id") if isinstance(params.get("order"), dict) else params.get("order_id"),
            "item_ids": [item.get("sku_id") for item in params.get("items", [])] if isinstance(params.get("items"), list) else None,
        }.items()
        if value not in (None, [], {})
    }


def _print_compact_state(client: TestClient, session_id: str) -> None:
    state = client.get(f"/api/session/{session_id}/state").json()
    route = state.get("last_model_route", {})
    _print_json(
        {
            "中文说明": "当前对话状态摘要，只展示判断下一轮对话最关键的信息。",
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
            "当前流程": state.get("current_flow"),
            "当前意图": state.get("current_intent"),
            "当前商品主题": {
                "category": state.get("current_category"),
                "sub_category": state.get("current_sub_category"),
            },
            "当前约束": state.get("active_constraints"),
            "缺失信息": state.get("missing_slots"),
            "最近推荐商品ID": state.get("last_recommended_products"),
            "购物车商品数": state.get("cart_total_items"),
            "模型路由摘要": {
                "主处理器": route.get("primary_handler"),
                "需要LLM": route.get("need_llm"),
                "LLM任务": route.get("llm_tasks"),
                "小模型任务": route.get("small_model_tasks"),
            },
        }
    )


def _print_compact_memory(client: TestClient, session_id: str) -> None:
    memory = client.get(f"/api/session/{session_id}/memory").json().get("memory", {})
    recent_messages = memory.get("recent_messages", [])[-4:]
    goods = memory.get("goods", {})
    cart = memory.get("cart", {})
    dialogue = memory.get("dialogue_state_tracking", {})
    _print_json(
        {
            "中文说明": "短期记忆摘要，只展示最近对话、最近推荐、购物车和当前可延续主题。",
            "最近消息": [
                {
                    "role": item.get("role"),
                    "content": _truncate(item.get("content", ""), 90),
                }
                for item in recent_messages
            ],
            "当前可延续主题": {
                "category": dialogue.get("current_category"),
                "sub_category": dialogue.get("current_sub_category"),
                "active_constraints": dialogue.get("active_constraints"),
            },
            "最近推荐商品": [
                {
                    "rank": item.get("rank"),
                    "sku_id": item.get("sku_id"),
                    "name": item.get("name"),
                    "price": item.get("price"),
                    "reason": item.get("reason"),
                }
                for item in goods.get("last_recommendations", [])[:5]
            ],
            "购物车摘要": {
                "total_items": sum(item.get("quantity", 0) for item in cart.get("items", [])),
                "items": [
                    {
                        "sku_id": item.get("sku_id"),
                        "name": item.get("name"),
                        "quantity": item.get("quantity"),
                        "price": item.get("price"),
                    }
                    for item in cart.get("items", [])
                ],
            },
        }
    )


def _print_compact_trace(client: TestClient, session_id: str) -> None:
    traces = client.get(f"/api/session/{session_id}/trace").json().get("traces", [])
    if not traces:
        print("还没有 trace。请先输入一轮用户消息。")
        return
    trace = traces[-1]
    parsed = trace.get("parsed_query", {})
    action = trace.get("frontend_action", {})
    timings = trace.get("runtime_timings", {}) or {}
    cart_personalization = trace.get("cart_personalization", {}) or {}
    _print_json(
        {
            "中文说明": "最近一轮执行链路摘要，用来检查理解、检索、工具、模型和前端动作是否正确。",
            "query_id": trace.get("query_id"),
            "用户输入": trace.get("raw_query"),
            "理解结果": {
                "intent": trace.get("intent"),
                "flow": f"{trace.get('flow_before')} -> {trace.get('flow_after')}",
                "category": parsed.get("category"),
                "sub_category": parsed.get("sub_category"),
                "price_range": parsed.get("price_range"),
                "positive_constraints": parsed.get("positive_constraints"),
                "negative_constraints": parsed.get("negative_constraints"),
                "route_source": parsed.get("route_source"),
            },
            "任务计划": trace.get("task_plan"),
            "检索结果": {
                "召回数量": len(trace.get("retrieved_product_ids", [])),
                "最终推荐": trace.get("selected_product_ids"),
                "Top评分": [
                    {
                        "sku_id": item.get("sku_id"),
                        "score": item.get("score"),
                        "reasons": item.get("matched_reasons", [])[:3],
                    }
                    for item in trace.get("retrieval_scores", [])[:3]
                ],
            },
            "工具执行": trace.get("tool_calls", []),
            "模型调用": {
                "llm_called": trace.get("llm_called"),
                "provider": trace.get("model_route", {}).get("llm_provider"),
                "llm_tasks": trace.get("model_route", {}).get("llm_tasks"),
                "small_model_tasks": trace.get("model_route", {}).get("small_model_tasks"),
            },
            "进度与耗时": {
                "progress模板": (trace.get("progress_plan") or {}).get("progress模板"),
                "总耗时_ms": timings.get("total_duration_ms"),
                "Top耗时模块": [
                    {
                        "module": item.get("module"),
                        "耗时_ms": item.get("duration_ms"),
                    }
                    for item in timings.get("Top耗时模块", [])[:5]
                ],
            },
            "购物车商品侧个性化": {
                "启用": cart_personalization.get("是否启用"),
                "参考商品": [
                    item.get("sku_id")
                    for item in cart_personalization.get("参考购物车商品", [])[:6]
                ],
                "命中规则": [
                    item.get("rule_id")
                    for item in cart_personalization.get("命中的本地规则", [])[:8]
                ],
                "调用Doubao": cart_personalization.get("是否调用Doubao"),
                "排序影响": cart_personalization.get("排序影响", [])[:5],
            },
            "前端动作": {
                "action": action.get("action"),
                "target_page": action.get("target_page"),
                "should_end": action.get("should_end_conversation"),
                "source": action.get("source"),
                "reason": action.get("reason"),
            },
            "输出校验": trace.get("validation_result"),
        }
    )


def _print_compact_profile(client: TestClient, session_id: str, user_id: str) -> None:
    payload = client.get(f"/api/session/{session_id}/profile", params={"user_id": user_id}).json()
    profile = payload.get("profile", {})
    sessions = profile.get("sessions", [])
    _print_json(
        {
            "中文说明": "长期画像摘要，只展示可用于个性化回复的稳定信息。",
            "user_id": profile.get("user_id"),
            "会话数量": len(sessions),
            "最近会话": profile.get("last_session_id"),
            "自然语言画像": profile.get("profile_summary_text"),
            "结构化画像": profile.get("structured_profile"),
            "显式长期偏好": profile.get("explicit_preferences"),
            "历史摘要": profile.get("history_summary"),
        }
    )


def _print_full_debug(
    client: TestClient,
    session_id: str,
    user_id: str,
    last_turn_result: dict[str, Any] | None,
) -> None:
    print("\n--- FULL turn_result / 最近一轮完整输出")
    _print_json(last_turn_result or {"message": "当前进程还没有执行过用户消息。"})
    print("\n--- FULL state / 完整状态接口")
    _print_json(client.get(f"/api/session/{session_id}/state").json())
    print("\n--- FULL memory / 完整短期记忆")
    _print_json(client.get(f"/api/session/{session_id}/memory").json())
    print("\n--- FULL trace / 完整最近trace")
    traces = client.get(f"/api/session/{session_id}/trace").json().get("traces", [])
    _print_json(traces[-1] if traces else {})
    print("\n--- FULL profile / 完整长期画像")
    _print_json(client.get(f"/api/session/{session_id}/profile", params={"user_id": user_id}).json())


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _parse_sse_events(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data = {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ").strip()
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: ").strip())
        events.append((event_name, data))
    return events


def _last_event(events: list[tuple[str, dict]], name: str) -> dict[str, Any] | None:
    for event_name, data in reversed(events):
        if event_name == name:
            return data
    return None


def _refresh_profile(user_id: str) -> None:
    profile = get_user_profile_service().maybe_refresh_profile(user_id, force=True)
    if profile.get("profile_summary_text"):
        print("\n--- 用户画像已更新")
        print(profile["profile_summary_text"])


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
