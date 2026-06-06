import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


PRODUCT_VARIANTS = {
    "p_beauty_001": ("s_p_beauty_001_1", {"容量": "30ml 经典装"}),
    "p_beauty_002": ("s_p_beauty_002_1", {"容量": "30ml 标准装"}),
    "p_beauty_003": ("s_p_beauty_003_1", {"容量": "160ml 标准装"}),
    "p_beauty_004": ("s_p_beauty_004_1", {"容量": "30ml 经典装"}),
    "p_beauty_010": ("s_p_beauty_010_1", {"规格": "60ml 经典金瓶"}),
    "p_beauty_023": ("s_p_beauty_023_1", {"产品规格": "50ml 清盈型"}),
    "p_digital_007": ("s_p_digital_007_1", {"版本": "标准版", "颜色": "典雅黑"}),
    "p_digital_018": (
        "s_p_digital_018_1",
        {
            "产品版本": "标准版 AirPods Pro 3",
            "充电盒类型": "MagSafe 充电盒",
            "定制服务": "无刻印",
            "附加服务": "无AppleCare+",
        },
    ),
    "p_digital_020": (
        "s_p_digital_020_1",
        {
            "屏幕尺寸": "13英寸",
            "芯片": "M5芯片",
            "内存": "16GB内存",
            "固态存储": "512GB SSD",
            "颜色": "天蓝色",
        },
    ),
    "p_food_003": ("s_p_food_003_1", {"容量": "500ml", "包装": "单瓶装"}),
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


def test_products_api_returns_sku_id_products() -> None:
    response = client.get("/api/products")
    assert response.status_code == 200
    payload = response.json()
    assert "products" in payload
    assert payload["products"][0]["sku_id"] == "p_beauty_001"


def test_product_detail_api_returns_real_product() -> None:
    response = client.get("/api/products/p_beauty_001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["product"]["sku_id"] == "p_beauty_001"
    assert "雅诗兰黛" in payload["product"]["name"]


def test_cart_api_flow() -> None:
    session_id = "test-cart-session"
    add_response = client.post(
        "/api/cart/add",
        json={
            "session_id": session_id,
            "sku_id": "p_beauty_035",
            "quantity": 1,
            "source": "button",
        },
    )
    assert add_response.status_code == 200
    assert add_response.json()["items"][0]["sku_id"] == "p_beauty_035"

    get_response = client.get("/api/cart", params={"session_id": session_id})
    assert get_response.status_code == 200
    assert get_response.json()["items"][0]["sku_id"] == "p_beauty_035"


def test_multi_sku_cart_api_rejects_missing_specs() -> None:
    session_id = f"test-cart-missing-specs-{uuid4().hex}"
    response = client.post(
        "/api/cart/add",
        json={
            "session_id": session_id,
            "sku_id": "p_beauty_001",
            "quantity": 1,
            "source": "button",
        },
    )
    assert response.status_code == 400
    assert "requires selected_sku_id" in response.json()["detail"]

    cart_response = client.get("/api/cart", params={"session_id": session_id})
    assert cart_response.status_code == 200
    assert cart_response.json()["items"] == []


def test_multi_sku_cart_api_rejects_invalid_specs() -> None:
    session_id = f"test-cart-invalid-specs-{uuid4().hex}"
    response = client.post(
        "/api/cart/add",
        json={
            "session_id": session_id,
            "sku_id": "p_beauty_001",
            "selected_sku_id": "not-a-real-sku",
            "selected_specs": {"容量": "30ml"},
            "quantity": 1,
            "source": "button",
        },
    )
    assert response.status_code == 400
    assert "valid selected_sku_id" in response.json()["detail"]

    cart_response = client.get("/api/cart", params={"session_id": session_id})
    assert cart_response.status_code == 200
    assert cart_response.json()["items"] == []


def test_cart_keeps_selected_specs_and_variant_price() -> None:
    session_id = f"test-cart-specs-{uuid4().hex}"
    first = client.post(
        "/api/cart/add",
        json={
            "session_id": session_id,
            "sku_id": "p_beauty_001",
            "selected_sku_id": "s_p_beauty_001_1",
            "selected_specs": {"容量": "30ml 经典装"},
            "unit_price": 1,
            "quantity": 1,
            "source": "test",
        },
    )
    assert first.status_code == 200
    first_item = first.json()["items"][0]
    assert first_item["selected_sku_id"] == "s_p_beauty_001_1"
    assert first_item["selected_specs"] == {"容量": "30ml 经典装"}
    assert first_item["spec_summary"] == "30ml 经典装"
    assert first_item["price"] == 720.0

    second = client.post(
        "/api/cart/add",
        json={
            "session_id": session_id,
            "sku_id": "p_beauty_001",
            "selected_sku_id": "s_p_beauty_001_2",
            "selected_specs": {"容量": "50ml 加大装"},
            "quantity": 1,
            "source": "test",
        },
    )
    assert second.status_code == 200
    second_cart = second.json()
    assert len(second_cart["items"]) == 2
    assert {item["selected_sku_id"] for item in second_cart["items"]} == {
        "s_p_beauty_001_1",
        "s_p_beauty_001_2",
    }

    third = client.post(
        "/api/cart/add",
        json={
            "session_id": session_id,
            "sku_id": "p_beauty_001",
            "selected_sku_id": "s_p_beauty_001_1",
            "selected_specs": {"容量": "30ml 经典装"},
            "quantity": 1,
            "source": "test",
        },
    )
    assert third.status_code == 200
    third_items = third.json()["items"]
    assert len(third_items) == 2
    first_variant = next(item for item in third_items if item["selected_sku_id"] == "s_p_beauty_001_1")
    second_variant = next(item for item in third_items if item["selected_sku_id"] == "s_p_beauty_001_2")
    assert first_variant["quantity"] == 2
    assert second_variant["quantity"] == 1
    assert third.json()["total_items"] == 3
    assert third.json()["total_price"] == 2420.0

    get_response = client.get("/api/cart", params={"session_id": session_id})
    assert get_response.status_code == 200
    assert all(item["cart_item_id"] for item in get_response.json()["items"])
    assert {item["spec_summary"] for item in get_response.json()["items"]} == {
        "30ml 经典装",
        "50ml 加大装",
    }


def test_chat_cart_add_multi_sku_requires_spec_selection() -> None:
    session_id = f"test-chat-spec-selection-{uuid4().hex}"
    first = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款小棕瓶精华"},
    )
    assert first.status_code == 200

    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款加入购物车"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert "cart_update" not in [name for name, _ in events]
    turn = _event(events, "turn_result")
    assert "cart_state" not in turn["frontend_data"]
    spec_selection = turn["frontend_data"]["spec_selection"]
    assert spec_selection["product_id"] == "p_beauty_001"
    assert len(spec_selection["sku_options"]) == 3
    assert spec_selection["sku_options"][0]["sku_id"] == "s_p_beauty_001_1"

    cart_response = client.get("/api/cart", params={"session_id": session_id})
    assert cart_response.status_code == 200
    assert cart_response.json()["items"] == []


def test_chat_cart_add_multi_sku_with_explicit_spec_adds_variant() -> None:
    session_id = f"test-chat-explicit-spec-{uuid4().hex}"
    first = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款小棕瓶精华"},
    )
    assert first.status_code == 200

    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款30ml加入购物车"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert "cart_update" in [name for name, _ in events]
    turn = _event(events, "turn_result")
    cart = turn["frontend_data"]["cart_state"]["cart"]
    assert cart["items"][0]["selected_sku_id"] == "s_p_beauty_001_1"
    assert cart["items"][0]["selected_specs"] == {"容量": "30ml 经典装"}
    assert cart["items"][0]["spec_summary"] == "30ml 经典装"
    assert cart["items"][0]["price"] == 720.0


def test_large_cart_view_update_remove_and_checkout_flow() -> None:
    session_id = "test-boundary-large-cart"
    for sku_id, quantity in [
        ("p_beauty_010", 5),
        ("p_beauty_023", 5),
        ("p_digital_007", 2),
        ("p_food_003", 8),
    ]:
        response = _add_cart_variant(session_id, sku_id, quantity)
        assert response.status_code == 200

    view_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "查看购物车"},
    )
    view_turn = _event(_parse_sse_events(view_response.text), "turn_result")
    assert view_turn["frontend_data"]["cart_state"]["cart"]["total_items"] == 20
    assert view_turn["frontend_data"]["navigation"]["target_page"] == "cart_page"

    update_response = client.post(
        "/api/cart/update",
        json={"session_id": session_id, "sku_id": "p_beauty_010", "quantity": 2},
    )
    assert update_response.status_code == 200
    update_cart = update_response.json()
    assert update_cart["total_items"] == 17
    assert update_cart["items"][0]["quantity"] == 2

    remove_response = client.post(
        "/api/cart/remove",
        json={"session_id": session_id, "sku_id": "p_beauty_023"},
    )
    assert remove_response.status_code == 200
    remove_cart = remove_response.json()
    assert remove_cart["total_items"] == 12
    assert all(item["sku_id"] != "p_beauty_023" for item in remove_cart["items"])

    checkout_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "现在结算下单，用默认地址"},
    )
    checkout_turn = _event(_parse_sse_events(checkout_response.text), "turn_result")
    checkout_cart = checkout_turn["frontend_data"]["cart_state"]["cart"]
    assert checkout_cart["total_items"] == 12
    assert checkout_cart["order"]["status"] == "created"
    assert checkout_turn["frontend_data"]["navigation"]["target_page"] == "checkout_page"


def test_chat_stream_returns_token_cards_and_done() -> None:
    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": "test-chat-session",
            "message": "推荐一款适合油皮的洗面奶",
        },
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "token" in event_names
    assert "product_cards" in event_names
    assert "turn_result" in event_names
    assert "done" in event_names

    product_cards = next(data for name, data in events if name == "product_cards")
    assert product_cards["products"][0]["sku_id"] == "p_beauty_011"
    assert product_cards["products"][0]["presentation"]["type"] == "recommendation"
    assert product_cards["products"][0]["presentation"]["option_label"] == "方案一"
    assert product_cards["products"][0]["presentation"]["reason"]
    turn_result = next(data for name, data in events if name == "turn_result")
    assert turn_result["frontend_events"][0]["动作类型"] == "show_reply"
    assert turn_result["frontend_events"][1]["数据参考"] == "recommended_products"
    assert turn_result["frontend_data"]["scene_type"] == "recommendation"
    assert "reply_message" in turn_result["frontend_data"]
    assert "system_debug" in turn_result
    presentation_debug = turn_result["system_debug"]["场景展示生成"]
    assert presentation_debug["scene_type"] == "recommendation"
    assert presentation_debug["content_source_by_sku"][product_cards["products"][0]["sku_id"]] in {"llm", "fallback"}


def test_recommendation_and_cart_add_do_not_auto_navigate() -> None:
    session_id = "test-no-auto-navigation"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款性价比高的手机"},
    )
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    event_types = [item["动作类型"] for item in turn_result["frontend_events"]]
    assert "show_products" in event_types
    assert "navigate" not in event_types
    assert "page_state" not in turn_result["frontend_data"]

    add_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款加入购物车"},
    )
    add_turn = _event(_parse_sse_events(add_response.text), "turn_result")
    add_event_types = [item["动作类型"] for item in add_turn["frontend_events"]]
    assert "show_spec_selection" in add_event_types
    assert "update_cart" not in add_event_types
    assert "cart_state" not in add_turn["frontend_data"]
    assert "spec_selection" in add_turn["frontend_data"]
    assert "navigate" not in add_event_types


def test_explicit_cart_and_product_detail_requests_can_navigate() -> None:
    session_id = "test-explicit-navigation"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款性价比高的手机"},
    )
    detail_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "查看第一款商品详情"},
    )
    detail_turn = _event(_parse_sse_events(detail_response.text), "turn_result")
    detail_events = [item["动作类型"] for item in detail_turn["frontend_events"]]
    assert "show_product_detail" in detail_events
    assert detail_turn["frontend_data"]["navigation"]["target_page"] == "product_detail_page"

    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款加入购物车"},
    )
    cart_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "查看购物车"},
    )
    cart_turn = _event(_parse_sse_events(cart_response.text), "turn_result")
    assert cart_turn["frontend_data"]["navigation"]["target_page"] == "cart_page"


def test_clear_cart_phrase_with_historical_add_word_does_not_add_again() -> None:
    session_id = "test-clear-cart-after-historical-add-phrase"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款适合户外的防晒"},
    )
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款加入购物车"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "刚才加购的防晒不要了，清空购物车"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    cart_state = turn_result["frontend_data"]["cart_state"]
    assert cart_state["tool_name"] == "clear_cart"
    assert cart_state["cart"]["total_items"] == 0
    assert "加入购物车" not in turn_result["frontend_data"]["reply_message"]["text"]

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["intent"] == "cart_clear"
    assert trace["tool_calls"][0]["tool_name"] == "clear_cart"
    assert "了" not in trace["parsed_query"]["negative_constraints"]


def test_product_detail_uses_stable_recommendation_event_memory() -> None:
    session_id = "test-stable-recommendation-event-memory"
    first_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐10000元以内，拍照好的手机"},
    )
    assert first_response.status_code == 200
    first_turn = _event(_parse_sse_events(first_response.text), "turn_result")
    recommended = first_turn["frontend_data"]["recommended_products"]["products"]
    assert len(recommended) >= 2
    first_sku = recommended[0]["sku_id"]
    second_sku = recommended[1]["sku_id"]

    second_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "我觉得第二个不错，给我介绍下"},
    )
    assert second_response.status_code == 200
    second_turn = _event(_parse_sse_events(second_response.text), "turn_result")
    assert second_turn["frontend_data"]["product_detail"]["product"]["sku_id"] == second_sku
    assert "当前商品信息里没有明确标明" not in second_turn["frontend_data"]["reply_message"]["text"]

    third_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "第一款呢，给我介绍下"},
    )
    assert third_response.status_code == 200
    third_turn = _event(_parse_sse_events(third_response.text), "turn_result")
    assert third_turn["frontend_data"]["product_detail"]["product"]["sku_id"] == first_sku

    state = client.get(f"/api/session/{session_id}/state").json()
    assert state["last_recommended_products"][:2] == [first_sku, second_sku]
    event_memory = third_turn["system_debug"]["记忆变化"]["事件记忆"]
    assert event_memory["当前推荐事件"]["rank_to_sku"]["第一款"] == first_sku
    assert event_memory["当前推荐事件"]["rank_to_sku"]["第二个"] == second_sku


def test_running_shoe_followup_ellipsis_uses_original_recommendation_event() -> None:
    session_id = "test-running-shoe-event-memory"
    first_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐三款跑鞋"},
    )
    first_turn = _event(_parse_sse_events(first_response.text), "turn_result")
    products = first_turn["frontend_data"]["recommended_products"]["products"]
    assert len(products) >= 2
    first_sku = products[0]["sku_id"]
    second_sku = products[1]["sku_id"]

    first_detail_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "第一个给我介绍一下"},
    )
    first_detail = _event(_parse_sse_events(first_detail_response.text), "turn_result")
    assert first_detail["frontend_data"]["product_detail"]["product"]["sku_id"] == first_sku

    second_detail_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "第二个呢"},
    )
    second_detail = _event(_parse_sse_events(second_detail_response.text), "turn_result")
    assert second_detail["frontend_data"]["product_detail"]["product"]["sku_id"] == second_sku
    event_memory = second_detail["system_debug"]["事件级记忆"]
    assert event_memory["最近推荐事件rank映射"]["1"] == first_sku
    assert event_memory["最近推荐事件rank映射"]["2"] == second_sku
    assert event_memory["本轮指代解析来源"] == "memory_events"


def test_alternative_products_are_saved_as_recommendation_event_memory() -> None:
    session_id = "test-alternative-product-event-memory"
    first_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐3000元以内拍照好的手机"},
    )
    assert first_response.status_code == 200
    first_turn = _event(_parse_sse_events(first_response.text), "turn_result")
    alternatives = first_turn["frontend_data"]["alternative_products"]["products"]
    assert len(alternatives) >= 2
    second_sku = alternatives[1]["sku_id"]
    first_event_memory = first_turn["system_debug"]["事件级记忆"]
    assert first_event_memory["本轮是否写入事件"] is True
    assert first_event_memory["写入事件类型"] == "recommendation"
    assert first_event_memory["最近推荐事件rank映射"]["2"] == second_sku

    detail_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "我觉得第二个不错，给我介绍下"},
    )
    detail_turn = _event(_parse_sse_events(detail_response.text), "turn_result")
    assert detail_turn["frontend_data"]["product_detail"]["product"]["sku_id"] == second_sku
    resolution = detail_turn["system_debug"]["事件级记忆"]
    assert resolution["本轮指代解析来源"] == "memory_events"
    assert resolution["本轮解析出的商品ID"] == [second_sku]


def test_comparison_event_uses_recommendation_rank_memory() -> None:
    session_id = "test-comparison-event-memory"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐防晒霜"},
    )
    first_turn = _event(_parse_sse_events(response.text), "turn_result")
    products = first_turn["frontend_data"]["recommended_products"]["products"]
    first_sku = products[0]["sku_id"]
    second_sku = products[1]["sku_id"]

    compare_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "第一款和第二款哪个更适合油皮"},
    )
    compare_turn = _event(_parse_sse_events(compare_response.text), "turn_result")
    compare_products = compare_turn["frontend_data"]["recommended_products"]["products"]
    assert [item["sku_id"] for item in compare_products] == [first_sku, second_sku]
    assert compare_turn["frontend_data"]["scene_type"] == "comparison"
    assert "comparison_data" in compare_turn["frontend_data"]
    assert all(item["presentation"]["type"] == "comparison" for item in compare_products)
    conclusion = compare_turn["frontend_data"]["comparison_data"]["conclusion"]
    assert conclusion["recommended_sku_id"] in {first_sku, second_sku}
    event_memory = compare_turn["system_debug"]["事件级记忆"]
    assert event_memory["写入事件类型"] == "comparison"
    assert event_memory["本轮指代解析来源"] == "memory_events"
    assert set(event_memory["本轮解析出的商品ID"]) == {first_sku, second_sku}


def test_cart_event_uses_recommendation_rank_memory() -> None:
    session_id = "test-cart-event-memory"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐蓝牙耳机"},
    )
    first_turn = _event(_parse_sse_events(response.text), "turn_result")
    products = first_turn["frontend_data"]["recommended_products"]["products"]
    second_sku = products[1]["sku_id"]

    add_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第二个MagSafe无刻印无AppleCare加入购物车"},
    )
    add_turn = _event(_parse_sse_events(add_response.text), "turn_result")
    cart_items = add_turn["frontend_data"]["cart_state"]["cart"]["items"]
    assert cart_items[0]["sku_id"] == second_sku
    event_memory = add_turn["system_debug"]["事件级记忆"]
    assert event_memory["写入事件类型"] == "cart_action"
    assert event_memory["本轮指代解析来源"] == "memory_events"


def test_history_restore_keeps_recommendation_event_rank_memory() -> None:
    user_id = f"restore-event-user-{uuid4().hex}"
    source_session_id = f"restore-source-{uuid4().hex}"
    restored_session_id = f"restore-target-{uuid4().hex}"
    first_response = client.post(
        "/api/chat/stream",
        json={"user_id": user_id, "session_id": source_session_id, "message": "推荐10000元以内拍照好的手机"},
    )
    first_turn = _event(_parse_sse_events(first_response.text), "turn_result")
    first_sku = first_turn["frontend_data"]["recommended_products"]["products"][0]["sku_id"]

    restored_response = client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": restored_session_id,
            "resume": True,
            "message": "第一款呢，给我介绍下",
        },
    )
    restored_turn = _event(_parse_sse_events(restored_response.text), "turn_result")
    assert restored_turn["frontend_data"]["product_detail"]["product"]["sku_id"] == first_sku
    assert restored_turn["system_debug"]["历史恢复状态"]["是否恢复"] is True
    assert restored_turn["system_debug"]["事件级记忆"]["本轮指代解析来源"] == "memory_events"


def test_remove_cart_phrase_with_historical_add_word_does_not_add_again() -> None:
    session_id = "test-remove-cart-after-historical-add-phrase"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款适合户外的防晒"},
    )
    add_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款60ml加入购物车"},
    )
    add_turn = _event(_parse_sse_events(add_response.text), "turn_result")
    added_items = add_turn["frontend_data"]["cart_state"]["cart"]["items"]
    assert added_items
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "刚才加购的防晒不要了"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    cart_state = turn_result["frontend_data"]["cart_state"]
    assert cart_state["tool_name"] == "remove_from_cart"
    assert cart_state["cart"]["total_items"] == 0

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["intent"] == "cart_remove"
    assert trace["tool_calls"][0]["tool_name"] == "remove_from_cart"


def test_backpack_single_product_request_is_not_scene_bundle() -> None:
    session_id = "test-backpack-not-scene-bundle"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "情侣一周短途海边度假，穿搭、护肤、随身好物全套搭配"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "重新挑选一款适合通勤和旅行的背包"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    products = turn_result["frontend_data"]["recommended_products"]["products"]
    assert products
    assert all(product["sub_category"] == "背包" for product in products)
    assert "拖鞋" not in turn_result["frontend_data"]["reply_message"]["text"]
    assert "泳衣" not in turn_result["frontend_data"]["reply_message"]["text"]

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["intent"] in {"recommend", "refine"}
    assert trace["flow_after"] != "scene_bundle"
    assert trace["parsed_query"]["category"] == "服饰运动"
    assert trace["parsed_query"]["sub_category"] == "背包"
    assert trace["selected_product_ids"]


def test_intent_plan_executes_add_then_checkout_sequence() -> None:
    session_id = "test-intent-plan-add-then-checkout"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款适合油皮的洗面奶"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款120g加入购物车，然后直接下单，用默认地址"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    cart_state = turn_result["frontend_data"]["cart_state"]
    assert cart_state["tool_name"] == "mock_checkout"
    assert cart_state["cart"]["total_items"] == 1
    assert "order" in cart_state["cart"]

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["parsed_query"]["intent_plan"]["is_multi_intent"] is True
    assert [step["intent"] for step in trace["parsed_query"]["intent_plan"]["steps"]] == ["cart_add", "checkout"]
    assert [call["tool_name"] for call in trace["tool_calls"]] == ["add_to_cart", "mock_checkout"]


def test_mixed_cart_clear_then_recommend_backpack_plan_continues_retrieval() -> None:
    session_id = "test-mixed-clear-then-backpack"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐防晒霜"},
    )
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款60ml加入购物车"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "刚才加购的防晒不要了，清空购物车，重新挑选一款适合通勤和旅行的背包"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "cart_update" in event_names
    assert "product_cards" in event_names

    turn_result = _event(events, "turn_result")
    products = turn_result["frontend_data"]["recommended_products"]["products"]
    assert products
    assert all(product["category"] == "服饰运动" for product in products)
    assert all(product["sub_category"] == "背包" for product in products)
    assert turn_result["frontend_data"]["cart_state"]["cart"]["total_items"] == 0
    assert turn_result["system_debug"]["Doubao意图计划"]["内容"]["is_multi_intent"] is True

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["intent"] == "refine"
    assert trace["parsed_query"]["category"] == "服饰运动"
    assert trace["parsed_query"]["sub_category"] == "背包"
    assert [step["intent"] for step in trace["parsed_query"]["intent_plan"]["steps"]] == ["cart_clear", "refine"]
    assert [call["tool_name"] for call in trace["tool_calls"]] == ["clear_cart"]


def test_mixed_add_remove_then_recommend_executes_all_steps_in_order() -> None:
    session_id = "test-mixed-add-remove-recommend"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐防晒霜"},
    )
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第二款50ml清盈型加入购物车"},
    )
    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": session_id,
            "message": "帮我把你推荐的第一个60ml防晒乳加到购物车，把购物车中其他的防晒乳全部删掉，再给我推荐一个200块左右的背包，也是旅游使用的",
        },
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    assert "已把" in turn_result["frontend_data"]["reply_message"]["text"]
    assert "移除" in turn_result["frontend_data"]["reply_message"]["text"]
    product_payload = turn_result["frontend_data"].get("recommended_products") or turn_result["frontend_data"].get("alternative_products")
    assert product_payload and product_payload["products"]
    assert all(product["category"] == "服饰运动" for product in product_payload["products"])
    assert all(product["sub_category"] == "背包" for product in product_payload["products"])
    assert all("防晒" not in product["reason"] for product in product_payload["products"])
    cart_items = turn_result["frontend_data"]["cart_state"]["cart"]["items"]
    assert len(cart_items) == 1
    assert cart_items[0]["sku_id"].startswith("p_beauty_")

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert [step["intent"] for step in trace["parsed_query"]["intent_plan"]["steps"]] == ["cart_add", "cart_remove", "refine"]
    assert [call["tool_name"] for call in trace["tool_calls"]] == ["add_to_cart", "remove_from_cart"]
    assert trace["parsed_query"]["category"] == "服饰运动"
    assert trace["parsed_query"]["sub_category"] == "背包"


def test_fuzzy_remove_previous_cart_item_then_add_second_with_quantity() -> None:
    session_id = "test-fuzzy-remove-then-add-quantity"
    first_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐功能饮料"},
    )
    first_turn = _event(_parse_sse_events(first_response.text), "turn_result")
    second_product = first_turn["frontend_data"]["recommended_products"]["products"][1]
    first_add = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款单瓶装加入购物车"},
    )
    first_add_turn = _event(_parse_sse_events(first_add.text), "turn_result")
    assert first_add_turn["frontend_data"]["cart_state"]["cart"]["items"]
    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": session_id,
            "message": "我不喜欢刚才加到购物车的那个饮料了，你帮我把现在推荐的第二个往购物车加6瓶吧",
        },
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    assert "cart_state" not in turn_result["frontend_data"]
    spec_selection = turn_result["frontend_data"]["spec_selection"]
    assert spec_selection["product_id"] == second_product["sku_id"]
    assert len(spec_selection["sku_options"]) >= 1
    cart = client.get("/api/cart", params={"session_id": session_id}).json()
    assert cart["total_items"] == 0

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert [step["intent"] for step in trace["parsed_query"]["intent_plan"]["steps"]] == ["cart_remove", "cart_add"]
    assert trace["parsed_query"]["intent_plan"]["steps"][1]["quantity"] == 6
    assert [call["tool_name"] for call in trace["tool_calls"]] == ["remove_from_cart", "need_spec_selection"]


def test_debug_state_and_trace_are_recorded() -> None:
    session_id = "test-debug-session"
    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": session_id,
            "message": "推荐一款手机",
        },
    )
    assert response.status_code == 200

    state_response = client.get(f"/api/session/{session_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["current_flow"] == "clarification"
    assert state["last_model_route"]["primary_handler"] == "clarification_template"

    trace_response = client.get(f"/api/session/{session_id}/trace")
    assert trace_response.status_code == 200
    traces = trace_response.json()["traces"]
    assert traces
    assert traces[-1]["task_plan"][0] == "preprocess_input"


def test_preference_with_product_context_updates_preference_and_recommends() -> None:
    session_id = "test-pref-session"
    pref_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "我一直比较喜欢清爽一点的护肤品"},
    )
    assert pref_response.status_code == 200
    events = _parse_sse_events(pref_response.text)
    event_names = [name for name, _ in events]
    assert "product_cards" in event_names
    assert "recommendation" in pref_response.text

    memory = client.get(f"/api/session/{session_id}/memory").json()["memory"]
    assert "清爽" in memory["user"]["global_preferences"]["preferred_style"]

    out_response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "帮我写一篇作文"},
    )
    assert out_response.status_code == 200
    assert "out_of_scope" in out_response.text


def test_chinese_price_and_local_model_scores_are_traceable() -> None:
    session_id = "test-local-model-session"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款手机"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "拍照好一点，预算四千以内"},
    )
    assert response.status_code == 200
    assert "p_digital_016" in response.text

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["parsed_query"]["price_range"]["max"] == 4000
    assert "bge_embedding_recall" in trace["model_route"]["small_model_tasks"]
    assert trace["retrieval_scores"]
    assert "bge_reranker" in trace["retrieval_scores"][0]["raw_scores"]


def test_checkout_creates_demo_order_payload() -> None:
    session_id = "test-checkout-session"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款适合油皮的洗面奶"},
    )
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "把第一款120g加入购物车"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "下单吧，地址用默认的"},
    )
    assert response.status_code == 200
    assert "demo_order_" in response.text


def test_budget_is_hard_filter_and_frontend_action_is_emitted() -> None:
    session_id = "test-budget-hard-filter"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "我的预算是5000元，帮我选一款适合女生用的拍照好的手机"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "frontend_action" in event_names

    product_cards = next(data for name, data in events if name == "product_cards")
    assert product_cards["products"]
    assert all(product["price"] <= 5000 for product in product_cards["products"])

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["parsed_query"]["price_range"]["max"] == 5000
    assert trace["frontend_action"]["target_page"] in {"product_list", "chat"}
    assert trace["frontend_events"][0]["动作类型"] == "show_reply"


def test_budget_complaint_triggers_new_retrieval_instead_of_preference_note() -> None:
    session_id = "test-budget-complaint-refine"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款性价比高的手机"},
    )
    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": session_id,
            "message": "我是要便宜的手机，价格大概在2000到4000元，你给的几款都好贵呀，我不喜欢，超出我的预算了",
        },
    )
    assert response.status_code == 200
    assert "p_digital_016" in response.text
    assert "长期记忆" not in next(
        data for name, data in _parse_sse_events(response.text) if name == "turn_result"
    )["frontend_data"]["reply_message"]["text"]

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["intent"] == "refine"
    assert trace["flow_after"] == "refinement"
    assert trace["parsed_query"]["price_range"] == {"min": 2000.0, "max": 4000.0}
    assert trace["model_route"]["need_llm"] is True
    assert trace["selected_product_ids"] == ["p_digital_016"]


def test_followup_which_are_suitable_inherits_previous_phone_budget() -> None:
    session_id = "test-budget-followup-inherits"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款性价比高的手机"},
    )
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "价格大概在2000到4000元，刚才几款太贵了"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "那你倒是告诉我哪些合适呀"},
    )
    assert response.status_code == 200
    assert "p_digital_016" in response.text
    assert "你想看哪一类商品" not in response.text

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["flow_after"] == "refinement"
    assert trace["parsed_query"]["category"] == "数码电子"
    assert trace["parsed_query"]["sub_category"] == "智能手机"
    assert trace["parsed_query"]["price_range"] == {"min": 2000.0, "max": 4000.0}


def test_phone_topic_is_locked_when_user_refines_camera_and_price() -> None:
    session_id = "test-phone-topic-lock"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款手机"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "我想要个拍照好看的，价格也别太贵"},
    )
    assert response.status_code == 200

    events = _parse_sse_events(response.text)
    product_payload = next(data for name, data in events if name == "product_cards")
    assert product_payload["products"]
    assert all(not product["sku_id"].startswith("p_beauty_") for product in product_payload["products"])
    assert all(product["sku_id"].startswith("p_digital_") for product in product_payload["products"])
    assert all(product["category"] == "数码电子" for product in product_payload["products"])
    assert all(product["sub_category"] == "智能手机" for product in product_payload["products"])

    turn_result = next(data for name, data in events if name == "turn_result")
    frontend_products = turn_result["frontend_data"]["recommended_products"]["products"]
    assert frontend_products
    assert all(product["category"] == "数码电子" for product in frontend_products)
    assert all(product["sub_category"] == "智能手机" for product in frontend_products)

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["parsed_query"]["category"] == "数码电子"
    assert trace["parsed_query"]["sub_category"] == "智能手机"
    assert "context_topic_lock" in trace["parsed_query"]["route_source"]
    assert trace["selected_product_ids"]


def test_cross_category_switch_from_phone_to_outerwear_is_not_locked() -> None:
    session_id = "test-cross-category-phone-to-outerwear"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款拍照好的手机"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "我不看手机了，想看看休闲外套，通勤能穿的"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    turn_result = _event(events, "turn_result")
    product_payload = turn_result["frontend_data"].get("recommended_products") or turn_result["frontend_data"].get("alternative_products")
    if product_payload:
        product_cards = product_payload["products"]
    else:
        detail_payload = turn_result["frontend_data"].get("product_detail")
        assert detail_payload
        product_cards = [detail_payload["product"]]
    assert product_cards
    assert all(product["category"] == "服饰运动" for product in product_cards)
    assert all(product["category"] != "数码电子" for product in product_cards)
    event_types = [item["动作类型"] for item in turn_result["frontend_events"]]
    assert "show_products" in event_types or "show_product_detail" in event_types

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["parsed_query"]["category"] == "服饰运动"
    assert trace["parsed_query"]["sub_category"] in {"防晒衣", None}
    assert "context_topic_lock" not in trace["parsed_query"]["route_source"]


def test_no_exact_match_returns_relaxed_alternatives() -> None:
    session_id = "test-boundary-no-exact-match"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款连衣裙，500以内"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    turn_result = _event(events, "turn_result")
    products = turn_result["frontend_data"]["alternative_products"]["products"]
    assert products
    assert all(product["category"] == "服饰运动" for product in products)
    assert all(product["price"] <= 500 for product in products)
    assert [product["presentation"]["option_label"] for product in products[:3]] == ["方案一", "方案二", "方案三"][: len(products[:3])]
    alternative_event_products = _event(events, "alternatives")["products"]
    assert all(product["presentation"]["type"] == "recommendation" for product in alternative_event_products)
    assert "show_error" not in [item["动作类型"] for item in turn_result["frontend_events"]]

    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["parsed_query"]["sub_category"] == "连衣裙"
    assert trace["selected_product_ids"]


def test_sunscreen_exclusion_keeps_hard_negative_constraints() -> None:
    session_id = "test-sunscreen-exclusion"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐防晒霜，但我不要含酒精的，也不要日系品牌"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    product_cards = _event(events, "product_cards")["products"]
    assert [product["sku_id"] for product in product_cards] == ["p_beauty_006"]
    assert "p_beauty_010" not in [product["sku_id"] for product in product_cards]
    turn_result = _event(events, "turn_result")
    event_types = [item["动作类型"] for item in turn_result["frontend_events"]]
    assert "show_error" not in event_types


def test_short_sleeve_exclusion_prefers_loose_basic_uniqlo() -> None:
    session_id = "test-short-sleeve-exclusion"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "买夏季短袖，不要紧身款，不要大Logo印花，想要宽松基础款"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    product_cards = _event(events, "product_cards")["products"]
    assert product_cards[0]["sku_id"] == "p_clothes_001"
    assert "这款" in product_cards[0]["reason"]


def test_northwest_self_drive_scene_does_not_inherit_previous_category() -> None:
    session_id = "test-northwest-scene"
    client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "买夏季短袖，不要紧身款，不要大Logo印花，想要宽松基础款"},
    )
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "下周去西北自驾旅行，帮我搭配一套户外用品清单"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    product_cards = _event(events, "product_cards")["products"]
    sku_ids = {product["sku_id"] for product in product_cards}
    assert {"p_clothes_014", "p_clothes_017", "p_clothes_024", "p_clothes_025"}.issubset(sku_ids)
    assert sku_ids & {"p_beauty_010", "p_beauty_023"}
    trace = client.get(f"/api/session/{session_id}/trace").json()["traces"][-1]
    assert trace["parsed_query"]["intent"] == "scene_bundle"
    assert trace["parsed_query"]["negative_constraints"] == []


def test_remove_expensive_cart_item_then_checkout() -> None:
    session_id = "test-remove-expensive-then-checkout"
    first = _add_cart_variant(session_id, "p_digital_007", 1)
    assert first.status_code == 200
    second = _add_cart_variant(session_id, "p_digital_018", 1)
    assert second.status_code == 200
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "删除较贵的那款再付款"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    turn_result = _event(events, "turn_result")
    cart = turn_result["frontend_data"]["cart_state"]["cart"]
    assert cart["total_items"] == 1
    assert cart["items"][0]["sku_id"] == "p_digital_007"
    assert "order" in cart
    assert turn_result["frontend_data"]["navigation"]["target_page"] == "checkout_page"


def test_personalization_debug_uses_relevant_history_evidence() -> None:
    session_id = "test-personalization-debug"
    client.post(
        "/api/chat/stream",
        json={
            "user_id": "personalization_user",
            "session_id": session_id,
            "message": "我一直比较喜欢清爽、性价比高的护肤品，记住一下",
        },
    )
    response = client.post(
        "/api/chat/stream",
        json={
            "user_id": "personalization_user",
            "session_id": session_id,
            "message": "推荐一款清爽一点的防晒霜",
        },
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    personalization = turn_result["system_debug"]["个性化分析"]
    assert personalization["是否启用个性化"] is True
    assert personalization["本轮选中的历史证据"]
    assert personalization["本轮使用的few-shot示例"]
    assert "用户画像" not in turn_result["frontend_data"]["reply_message"]["text"]


def test_positive_response_strategy_for_exact_match_recommendation() -> None:
    session_id = "test-positive-exact-match"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "买夏季短袖，不要紧身款，不要大Logo印花，想要宽松基础款"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    reply = turn_result["frontend_data"]["reply_message"]["text"]
    assert not reply.startswith(("抱歉", "没有找到", "没有符合"))
    assert "都不是完全符合" not in reply
    assert "不是完全符合要求" not in reply
    strategy = turn_result["system_debug"]["回复策略"]
    assert strategy["匹配状态"] in {"exact_match", "partial_match"}
    assert strategy["是否启用积极回复"] is True
    assert strategy["是否避免否定开头"] is True


def test_positive_response_strategy_for_alternative_products() -> None:
    session_id = "test-positive-alternative"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐3000元以内拍照好的手机"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    reply = turn_result["frontend_data"]["reply_message"]["text"]
    assert reply.startswith("我先为你挑")
    assert not reply.startswith(("抱歉", "没有找到", "没有符合"))
    assert "alternative_products" in turn_result["frontend_data"]
    strategy = turn_result["system_debug"]["回复策略"]
    assert strategy["匹配状态"] == "alternative"
    assert strategy["是否启用积极回复"] is True


def test_out_of_scope_response_gives_clear_guidance() -> None:
    session_id = "test-positive-out-of-scope"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "帮我写一篇作文"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    reply = turn_result["frontend_data"]["reply_message"]["text"]
    assert "美妆护肤" in reply and "数码电子" in reply
    assert "导购任务" in reply
    assert turn_result["system_debug"]["回复策略"]["匹配状态"] == "out_of_scope"


def test_personalized_response_strategy_is_soft_reference_and_hidden() -> None:
    user_id = "positive_personalization_user"
    session_id = "test-positive-personalization"
    client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "我一直比较喜欢清爽、性价比高的护肤品，记住一下",
        },
    )
    response = client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "推荐一款清爽防晒",
        },
    )
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    reply = turn_result["frontend_data"]["reply_message"]["text"]
    assert "用户画像" not in reply
    strategy = turn_result["system_debug"]["回复策略"]
    assert strategy["使用的个性化参考"]
    assert "硬约束" in strategy["当前轮需求优先级"]


def test_recommendation_reply_length_is_mobile_friendly_and_grounded() -> None:
    session_id = "test-positive-length-grounded"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款适合油皮的洗面奶"},
    )
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    reply = turn_result["frontend_data"]["reply_message"]["text"]
    sentence_count = sum(reply.count(mark) for mark in ["。", "！", "？", "\n"])
    assert sentence_count <= 4
    products = turn_result["frontend_data"]["recommended_products"]["products"]
    assert not any(item["name"] in reply for item in products)
    expected_labels = ["方案一", "方案二", "方案三"][:len(products[:3])]
    assert [item["presentation"]["option_label"] for item in products[:3]] == expected_labels
    assert all(item["presentation"]["reason"] for item in products)
    assert "优惠券" not in reply and "限时库存" not in reply


def test_multimodal_backpack_image_text_fuses_visual_query(tmp_path) -> None:
    image_path = tmp_path / "commute_backpack.jpg"
    image_path.write_bytes(b"fake image bytes for multimodal smoke test")
    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": "test-multimodal-backpack",
            "message": "有没有类似这种款式，但价格低一点的背包",
            "input_type": "image_text",
            "metadata": {"image_path": str(image_path)},
        },
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    turn_result = _event(events, "turn_result")
    multimodal = turn_result["system_debug"]["多模态分析"]
    assert multimodal["是否启用多模态"] is True
    assert multimodal["图片理解结果"]["主要商品类别"] == "背包"
    assert multimodal["库存匹配判断"]["库存是否覆盖目标类目"] is True
    products = turn_result["frontend_data"]["recommended_products"]["products"]
    assert products
    assert all(product["sub_category"] == "背包" for product in products)


def test_multimodal_unsupported_visual_category_does_not_invent_products(tmp_path) -> None:
    image_path = tmp_path / "large_plush_toy.jpg"
    image_path.write_bytes(b"fake image bytes for multimodal smoke test")
    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": "test-multimodal-unsupported",
            "message": "找同款毛绒玩偶，要大号版本",
            "input_type": "image_text",
            "metadata": {"image_path": str(image_path)},
        },
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    assert "毛绒玩偶" in turn_result["frontend_data"]["reply_message"]["text"]
    assert "recommended_products" not in turn_result["frontend_data"]
    multimodal = turn_result["system_debug"]["多模态分析"]
    assert multimodal["库存匹配判断"]["库存是否覆盖目标类目"] is False


def test_privacy_off_disables_personalization_context() -> None:
    user_id = "privacy_off_user"
    session_id = "test-privacy-off"
    first = client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "关闭个性化推荐，不要根据历史推荐",
        },
    )
    assert first.status_code == 200
    first_turn = _event(_parse_sse_events(first.text), "turn_result")
    assert first_turn["system_debug"]["隐私保护"]["个性化模式"] == "off"

    response = client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "推荐一款清爽一点的防晒霜",
        },
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    privacy = turn_result["system_debug"]["隐私保护"]
    personalization = turn_result["system_debug"]["个性化分析"]
    assert privacy["个性化模式"] == "off"
    assert privacy["是否允许个性化"] is False
    assert personalization["是否启用个性化"] is False
    assert personalization["本轮选中的历史证据"] == []
    assert "用户画像" not in turn_result["frontend_data"]["reply_message"]["text"]


def test_semantic_privacy_uses_structured_memory_without_raw_few_shot() -> None:
    user_id = "privacy_semantic_user"
    session_id = "test-privacy-semantic"
    client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "我一直比较喜欢清爽、性价比高的护肤品，记住一下",
        },
    )
    client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "推荐一款适合夏天通勤的防晒霜",
        },
    )
    switch = client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "开启隐私个性化，只用语义摘要，不要用原文历史",
        },
    )
    assert switch.status_code == 200
    response = client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "再推荐一款清爽防晒",
        },
    )
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    privacy = turn_result["system_debug"]["隐私保护"]
    personalization = turn_result["system_debug"]["个性化分析"]
    assert privacy["个性化模式"] == "semantic"
    assert privacy["是否允许个性化"] is True
    assert privacy["是否允许使用历史原文做个性化"] is False
    assert personalization["是否启用个性化"] is True
    assert personalization["本轮使用的few-shot示例"] == []
    assert personalization["本轮选中的历史证据"]
    assert all(
        item.get("是否包含历史原文") is False
        for item in personalization["本轮选中的历史证据"]
        if "是否包含历史原文" in item
    )

    profile = client.get(f"/api/session/{session_id}/profile", params={"user_id": user_id}).json()["profile"]
    assert profile["privacy_settings"]["personalization_mode"] == "semantic"
    assert profile["semantic_memory"]["category_counts"]
    assert profile["memory_cards"]
    assert profile["profile_summary_text"]


def test_privacy_command_with_product_request_still_recommends_products() -> None:
    user_id = "privacy_combo_user"
    session_id = "test-privacy-combo"
    response = client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "开启隐私个性化，只用语义信息，然后推荐一款适合通勤的背包",
        },
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    event_types = [item["动作类型"] for item in turn_result["frontend_events"]]
    assert "show_products" in event_types
    assert turn_result["system_debug"]["隐私保护"]["个性化模式"] == "semantic"
    products = turn_result["frontend_data"]["recommended_products"]["products"]
    assert products
    assert all(product["sub_category"] == "背包" for product in products)


def test_raw_history_can_be_disabled_while_semantic_memory_remains() -> None:
    user_id = "privacy_no_raw_user"
    session_id = "test-privacy-no-raw"
    response = client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "不要保存聊天，开启隐私个性化，然后推荐一款性价比高的饮料",
        },
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    assert turn_result["system_debug"]["隐私保护"]["是否保存原始历史"] is False

    profile = client.get(f"/api/session/{session_id}/profile", params={"user_id": user_id}).json()["profile"]
    session = client.get(f"/api/session/{session_id}/history", params={"user_id": user_id}).json()["session"]
    assert profile["privacy_settings"]["store_raw_history"] is False
    assert profile["semantic_memory"]["category_counts"]
    assert session["turns"][-1]["raw_text_hidden"] is True
    assert session["turns"][-1]["user_input"] == "[已按隐私设置隐藏原始用户输入]"


def test_turn_result_contains_runtime_timing_summary() -> None:
    session_id = f"test-runtime-{uuid4()}"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款适合油皮的洗面奶"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    timings = turn_result["system_debug"]["运行耗时统计"]

    assert timings["total_duration_ms"] >= 0
    assert timings["模块明细"]
    assert timings["Top耗时模块"]
    assert "模型调用" in timings
    model_calls = timings["模型调用"]
    assert model_calls["planned_call_count"] >= 1
    assert model_calls["mock_call_count"] >= 1
    assert model_calls["real_http_call_count"] == 0
    assert model_calls["明细"]
    assert all(item["llm_is_mock"] for item in model_calls["明细"] if item["provider"] == "MockLLMClient")
    module_names = {item["module"] for item in timings["模块明细"]}
    assert {"memory_read", "query_understanding", "rag_retrieval", "response_generation"} <= module_names
    model_debug = turn_result["system_debug"]["模型调用"]
    assert model_debug["Doubao是否真实调用"] is False
    assert model_debug["mock_call_count"] >= 1
    assert model_debug["real_http_call_count"] == 0
    assert turn_result["system_debug"]["场景展示生成"]["content_source_by_sku"]


def test_progress_events_are_emitted_and_debugged() -> None:
    session_id = f"test-progress-{uuid4()}"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款性价比高的手机"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "progress" in event_names
    assert event_names.index("progress") < event_names.index("turn_result")

    progress_events = [data for name, data in events if name == "progress"]
    assert progress_events[0]["event_type"] == "progress_message"
    assert progress_events[0]["text"]
    assert progress_events[0]["can_be_replaced"] is True

    turn_result = _event(events, "turn_result")
    progress_debug = turn_result["system_debug"]["Progress事件"]
    assert progress_debug["progress事件数量"] == len(progress_events)
    assert progress_debug["预测工作类型"]
    assert progress_debug["实际总耗时_ms"] >= 0


def test_cart_aware_personalization_boosts_apple_ecosystem_accessory() -> None:
    session_id = f"test-cart-aware-{uuid4()}"
    add_response = _add_cart_variant(session_id, "p_digital_020")
    assert add_response.status_code == 200

    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "推荐一款降噪蓝牙耳机"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    products = turn_result["frontend_data"]["recommended_products"]["products"]
    assert products[0]["sku_id"] == "p_digital_018"

    cart_debug = turn_result["system_debug"]["购物车商品侧个性化"]
    assert cart_debug["是否启用"] is True
    assert cart_debug["参考购物车商品"][0]["sku_id"] == "p_digital_020"
    assert "Apple生态" in cart_debug["商品标签"]
    assert cart_debug["命中的本地规则"][0]["rule_id"] == "apple_macbook_ecosystem"
    assert any(item["sku_id"] == "p_digital_018" for item in cart_debug["排序影响"])


def test_enhanced_product_fields_are_loaded_and_used_for_nonstandard_query() -> None:
    product_response = client.get("/api/products/p_beauty_003")
    assert product_response.status_code == 200
    product = product_response.json()["product"]
    assert product["highlight_short"]
    assert "皮肤干燥起皮" in product["non_standard_query_tags"]

    session_id = f"test-enhancement-{uuid4()}"
    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "皮肤干燥起皮，有没有清爽保湿的护肤品"},
    )
    assert response.status_code == 200
    turn_result = _event(_parse_sse_events(response.text), "turn_result")
    enhancement_debug = turn_result["system_debug"]["商品增强字段使用"]
    assert "non_standard_query_tags" in enhancement_debug["使用的增强字段"]
    assert any("皮肤干" in tag or "保湿" in tag for tag in enhancement_debug["命中的非标准问题标签"])
    products = (
        turn_result["frontend_data"].get("recommended_products", {}).get("products")
        or turn_result["frontend_data"].get("alternative_products", {}).get("products")
    )
    assert products


def test_three_virtual_histories_resume_and_cart_personalization_rules() -> None:
    cases = [
        (
            "sophia_digital",
            "sophia_digital_01",
            "我还想买个iPad，最好好看一点，和我现在的苹果设备搭配",
            "apple_macbook_ecosystem",
            "平板电脑",
        ),
        (
            "alex_sports",
            "alex_sports_01",
            "我还想买双适合健身和跑步的运动鞋，性价比要高",
            "training_apparel_to_shoes",
            "跑步鞋",
        ),
        (
            "victoria_beauty",
            "victoria_beauty_01",
            "推荐一款更高端、能和我购物车里精华水搭配的面霜或护肤品",
            "premium_skincare_routine",
            "面霜",
        ),
    ]
    for user_id, source_session_id, message, expected_rule, expected_sub_category in cases:
        session_id = f"test-history-cart-aware-{user_id}-{uuid4()}"
        response = client.post(
            "/api/chat/stream",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "message": message,
                "resume": True,
                "metadata": {"resume_session_id": source_session_id},
            },
        )
        assert response.status_code == 200
        turn_result = _event(_parse_sse_events(response.text), "turn_result")
        assert turn_result["system_debug"]["历史恢复状态"]["是否恢复"] is True
        cart_debug = turn_result["system_debug"]["购物车商品侧个性化"]
        assert cart_debug["是否启用"] is True
        assert expected_rule in [item["rule_id"] for item in cart_debug["命中的本地规则"]]
        products = (
            turn_result["frontend_data"].get("recommended_products", {}).get("products")
            or turn_result["frontend_data"].get("alternative_products", {}).get("products")
        )
        assert products
        assert products[0]["sub_category"] == expected_sub_category
