import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_shopping_agent
from app.main import app
from app.multimodal.visual_query_builder import VisualQueryBuilder


client = TestClient(app)


PRODUCT_VARIANTS = {
    "p_beauty_001": ("s_p_beauty_001_1", {"容量": "30ml 经典装"}),
    "p_beauty_002": ("s_p_beauty_002_1", {"容量": "30ml 标准装"}),
    "p_beauty_003": ("s_p_beauty_003_1", {"容量": "160ml 标准装"}),
    "p_beauty_004": ("s_p_beauty_004_1", {"容量": "30ml 经典装"}),
}


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


def _event(events: list[tuple[str, dict]], name: str) -> dict:
    return next(data for event_name, data in events if event_name == name)


def _add_cart_variant(session_id: str, sku_id: str, quantity: int = 1):
    selected_sku_id, selected_specs = PRODUCT_VARIANTS[sku_id]
    return client.post(
        "/api/cart/add",
        json={
            "session_id": session_id,
            "sku_id": sku_id,
            "selected_sku_id": selected_sku_id,
            "selected_specs": selected_specs,
            "quantity": quantity,
            "source": "test",
        },
    )


def test_intent_plan_quantity_five_is_used_for_bulk_cart_add() -> None:
    session_id = f"accept-quantity-{uuid4()}"
    rec_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐两款适合户外用的防晒乳"},
    )
    rec_turn = _event(_parse_sse_events(rec_response.text), "turn_result")
    assert len(rec_turn["frontend_data"]["recommended_products"]["products"]) >= 2

    add_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款60ml经典金瓶和第二款50ml清盈型防晒乳都加入购物车，各加5瓶"},
    )
    add_turn = _event(_parse_sse_events(add_response.text), "turn_result")
    cart_state = add_turn["frontend_data"]["cart_state"]["cart"]

    assert cart_state["total_items"] == 10
    assert len(cart_state["items"]) == 2
    assert {item["quantity"] for item in cart_state["items"]} == {5}

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["parsed_query"]["intent_plan"]["steps"][0]["quantity"] == 5
    assert trace["tool_calls"][0]["payload"]["items"][0]["quantity"] == 5


def test_cart_progress_uses_cart_specific_templates() -> None:
    session_id = f"accept-progress-{uuid4()}"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款性价比高的手机"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款标准版典雅黑加入购物车"},
    )
    events = _parse_sse_events(response.text)
    progress_texts = [data.get("text", "") for name, data in events if name == "progress"]

    assert progress_texts
    assert any(("购物车" in text or "加购" in text or "库存" in text) for text in progress_texts)
    assert not any("正在判断你是想要推荐、比较、详情" in text for text in progress_texts)
    assert not any("历史偏好和购买习惯筛选商品" in text for text in progress_texts)


def test_stream_upload_endpoint_returns_unified_sse_shape() -> None:
    session_id = f"accept-upload-{uuid4()}"
    response = client.post(
        "/api/chat/stream/upload",
        data={
            "session_id": session_id,
            "user_id": session_id,
            "message": "帮我看看图片里的化妆品，有没有类似的护肤品",
            "input_type": "image_text",
        },
        files={"image": ("cosmetic.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "progress" in event_names
    assert "turn_result" in event_names
    assert "done" in event_names

    turn_result = _event(events, "turn_result")
    assert "frontend_events" in turn_result
    assert "frontend_data" in turn_result
    assert "system_debug" in turn_result
    assert turn_result["system_debug"]["多模态分析"]["是否启用多模态"] is True


def test_visual_query_builder_fuzzy_matches_estee_lauder_serum() -> None:
    fused = VisualQueryBuilder().build(
        message="想要雅诗兰黛小棕瓶这种同款或相似精华",
        visual_result={
            "主要商品类别": "雅诗兰黛小棕瓶面部精华",
            "候选商品类别": ["护肤品", "精华液"],
            "颜色": ["棕色"],
            "款式": ["精华瓶"],
            "材质或质感": [],
            "图案": [],
            "使用场景": ["日常护肤"],
            "相似检索关键词": ["雅诗兰黛 小棕瓶 精华"],
        },
    )

    assert fused["映射商品类别"] == "美妆护肤"
    assert fused["映射商品子类"] == "精华"
    assert fused["库存是否覆盖目标类目"] is True


def test_checkout_closing_guidance_appears_after_add_and_cools_down_after_decline() -> None:
    session_id = f"accept-closing-{uuid4()}"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款适合油皮的洗面奶"},
    )
    add_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款120g加入购物车"},
    )
    add_turn = _event(_parse_sse_events(add_response.text), "turn_result")
    add_text = add_turn["frontend_data"]["reply_message"]["text"]
    assert "结算" in add_text or "订单" in add_text or "收货" in add_text

    decline_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "先不结算，我再看看"},
    )
    decline_turn = _event(_parse_sse_events(decline_response.text), "turn_result")
    decline_text = decline_turn["frontend_data"]["reply_message"]["text"]
    assert "生成订单预览" not in decline_text


@pytest.mark.parametrize(
    ("sku_ids", "expected_phrase"),
    [
        (["p_beauty_001", "p_beauty_002"], "购物车里现在有2件商品"),
        (["p_beauty_001", "p_beauty_002", "p_beauty_003", "p_beauty_004"], "购物车里已经有4件商品了"),
    ],
)
def test_checkout_closing_guidance_summarizes_multi_item_carts(sku_ids: list[str], expected_phrase: str) -> None:
    session_id = f"accept-closing-count-{uuid4()}"
    for sku_id in sku_ids:
        response = _add_cart_variant(session_id, sku_id)
        assert response.status_code == 200

    view_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "查看购物车"},
    )
    view_turn = _event(_parse_sse_events(view_response.text), "turn_result")
    reply = view_turn["frontend_data"]["reply_message"]["text"]

    assert expected_phrase in reply
    assert "合计" in reply
    assert "订单" in reply or "收货地址" in reply or "结算" in reply


def test_global_exception_safety_net_returns_unified_error(monkeypatch) -> None:
    agent = get_shopping_agent()

    def boom(*args, **kwargs):
        raise RuntimeError("forced acceptance test error")

    monkeypatch.setattr(agent.query_understanding, "parse", boom)

    response = client.post(
        "/api/chat/stream",
        json={"session_id": f"accept-error-{uuid4()}", "message": "推荐一款适合通勤的背包"},
    )
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]

    assert "turn_result" in event_names
    assert "error" in event_names
    assert event_names[-1] == "done"
    turn_result = _event(events, "turn_result")
    assert turn_result["frontend_data"]["reply_message"]["text"] == "系统处理时遇到问题，请稍后重试。"
    assert turn_result["frontend_data"]["error_message"]["code"] == "AGENT_ERROR"
    assert turn_result["frontend_events"][0]["动作类型"] == "show_reply"
    assert turn_result["frontend_events"][1]["动作类型"] == "show_error"
