from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _force_real_runtime() -> None:
    os.environ["USE_MOCK_LLM"] = "false"
    os.environ.setdefault("ENABLE_LOCAL_MODELS", "true")


@dataclass
class AcceptanceCase:
    case_id: str
    group: str
    query: str
    expectation: str
    expected_category: str | None = None
    expected_sub_categories: set[str] = field(default_factory=set)
    expected_any_sku: set[str] = field(default_factory=set)
    forbidden_categories: set[str] = field(default_factory=set)
    forbidden_sub_categories: set[str] = field(default_factory=set)
    required_negative: set[str] = field(default_factory=set)
    min_products: int = 1
    allow_no_result_with_alternatives: bool = False


SINGLE_CASES: list[AcceptanceCase] = [
    AcceptanceCase("S01", "美妆护肤", "推荐一款男生能用的控油洁面", "识别洁面需求，男生作为人群偏好，优先召回男士洁面或控油洁面。", "美妆护肤", {"洁面", "男士洁面"}, {"p_beauty_035"}),
    AcceptanceCase("S02", "美妆护肤", "推荐一款防晒霜，不要含酒精的", "识别防晒需求，不含酒精作为否定约束，不能推荐精华或粉底。", "美妆护肤", {"防晒", "防晒喷雾"}, {"p_beauty_006", "p_beauty_034"}, required_negative={"酒精"}),
    AcceptanceCase("S03", "美妆护肤", "我是敏感肌，想要一款保湿修护面霜", "识别敏感肌、保湿、修护、面霜，优先修护面霜/特护霜。", "美妆护肤", {"面霜"}, {"p_beauty_007", "p_beauty_012"}),
    AcceptanceCase("S04", "美妆护肤", "最近皮肤干燥起皮，有什么可以买", "生活化需求转为保湿/修护推荐，主动给具体商品。", "美妆护肤", {"面霜", "面膜", "化妆水", "精华", "安瓶"}, {"p_beauty_007", "p_beauty_012", "p_beauty_019", "p_beauty_022"}),
    AcceptanceCase("S05", "美妆护肤", "上妆总是卡粉，有什么底妆或妆前推荐", "识别底妆/妆前/保湿场景，理由围绕卡粉、服帖、妆前保湿。", "美妆护肤", {"粉底液", "BB霜", "素颜霜", "隔离霜", "蜜粉"}),
    AcceptanceCase("S06", "美妆护肤", "想要一个适合通勤的清爽防晒，不要太油", "识别通勤、清爽肤感、防晒，不要太油作为肤感约束。", "美妆护肤", {"防晒", "防晒喷雾"}, {"p_beauty_006", "p_beauty_023", "p_beauty_034"}, required_negative={"油腻"}),
    AcceptanceCase("S07", "美妆护肤", "推荐一个学生党能接受的底妆，别太贵", "识别底妆和价格敏感，推荐价格友好的 BB 霜、蜜粉、素颜霜、隔离。", "美妆护肤", {"粉底液", "BB霜", "素颜霜", "隔离霜", "蜜粉"}, {"p_beauty_037", "p_beauty_026", "p_beauty_013"}),
    AcceptanceCase("S08", "食品饮料", "想喝点什么，但是不要含糖的饮料", "识别食品饮料推荐和无糖约束，不能把果汁直接说成无糖。", "食品饮料", {"茶饮", "碳酸饮料", "矿泉水", "咖啡", "功能饮料"}, {"p_food_003", "p_food_014", "p_food_015", "p_food_024"}, required_negative={"糖"}),
    AcceptanceCase("S09", "食品饮料", "下午困了，想喝点提神的", "识别提神饮品，优先咖啡或功能饮料。", "食品饮料", {"咖啡", "功能饮料", "茶饮"}, {"p_food_001", "p_food_022", "p_food_023", "p_food_005"}),
    AcceptanceCase("S10", "食品饮料", "健身后想补充点东西", "识别健身后补给场景，避免夸大承诺。", "食品饮料", {"蛋白粉", "能量棒", "牛奶", "酸奶", "功能饮料"}, {"p_food_028", "p_food_035", "p_food_026"}),
    AcceptanceCase("S11", "食品饮料", "想买点办公室能囤的低负担零食", "识别办公室囤货和低负担零食，避免绝对健康承诺。", "食品饮料", {"坚果/零食", "苏打饼干", "蒟蒻果冻", "黑巧克力"}, {"p_food_030", "p_food_037", "p_food_009"}),
    AcceptanceCase("S12", "食品饮料", "早餐想吃点方便的，最好能搭配牛奶", "识别早餐便利场景，给组合推荐。", "食品饮料", {"即食麦片", "牛奶", "酸奶", "咖啡", "苏打饼干", "方便食品"}, {"p_food_032", "p_food_007", "p_food_016", "p_food_010"}),
    AcceptanceCase("S13", "食品饮料", "想要低卡一点的零食", "非标准标签匹配低卡零食，避免减肥和医疗承诺。", "食品饮料", {"蒟蒻果冻", "黑巧克力", "苏打饼干", "坚果/零食"}, {"p_food_037", "p_food_030", "p_food_029"}),
    AcceptanceCase("S14", "数码电子", "我想买个适合看书的电子设备", "识别阅读设备，优先电子书阅读器或平板，不应推荐手机。", "数码电子", {"电子书阅读器", "平板电脑"}, {"p_digital_030"}),
    AcceptanceCase("S15", "数码电子", "打游戏手机发烫怎么办，有什么可以买", "问题式表达转为手机散热器/游戏配件需求。", "数码电子", {"手机散热器", "游戏手柄", "游戏鼠标", "智能手机"}, {"p_digital_035"}),
    AcceptanceCase("S16", "数码电子", "有没有适合办公的轻薄设备", "识别办公轻薄设备，推荐轻薄本、平板或办公本。", "数码电子", {"笔记本电脑", "平板电脑", "家用打印机", "显示器"}, {"p_digital_020", "p_digital_023", "p_digital_004"}),
    AcceptanceCase("S17", "数码电子", "想要一个适合学生记笔记和看课件的平板", "识别学生、笔记、课件和平板场景。", "数码电子", {"平板电脑"}, {"p_digital_011", "p_digital_019", "p_digital_025"}),
    AcceptanceCase("S18", "服饰运动", "推荐一件适合通勤的外套", "外套不能被单一子类锁死，应在防晒衣、卫衣、冲锋衣等中筛选。", "服饰运动", {"冲锋衣", "羽绒服", "防晒衣", "卫衣", "休闲衬衫"}, {"p_clothes_032", "p_clothes_005", "p_clothes_022"}),
    AcceptanceCase("S19", "场景组合", "去三亚度假需要买什么", "场景组合推荐，考虑防晒、防晒衣、帽子、拖鞋、泳衣、背包等。", None, {"防晒衣", "沙滩拖鞋", "泳衣", "帽子", "背包", "防晒"}, {"p_clothes_032", "p_clothes_037", "p_clothes_029", "p_clothes_024", "p_beauty_006", "p_beauty_034"}),
    AcceptanceCase("S20", "场景组合", "健身房新手需要买什么装备", "场景拆解为速干T恤、运动短裤、跑鞋、运动袜、蛋白粉等。", None, {"速干T恤", "运动短裤", "跑步鞋", "运动袜", "运动内衣", "蛋白粉"}, {"p_clothes_020", "p_clothes_023", "p_clothes_028", "p_food_028"}),
    AcceptanceCase("S21", "服饰运动", "我要跑步穿的短袖，不要太厚", "推荐速干、轻薄、跑步训练短袖，不应推荐卫衣或厚外套。", "服饰运动", {"短袖T恤", "速干T恤"}, {"p_clothes_020", "p_clothes_021", "p_clothes_002"}, required_negative={"厚"}),
    AcceptanceCase("S22", "服饰运动", "推荐一条适合瑜伽的裤子", "识别瑜伽裤/运动裤需求。", "服饰运动", {"瑜伽裤", "骑行裤", "运动长裤"}, {"p_clothes_016", "p_clothes_033"}),
    AcceptanceCase("S23", "服饰运动", "我想买一个通勤和短途旅行都能用的背包", "识别通勤+短途旅行双场景，推荐容量、背负和日常通勤兼顾的背包。", "服饰运动", {"背包"}, {"p_clothes_018", "p_clothes_025"}),
]


MULTI_CASES: list[dict[str, Any]] = [
    {
        "case_id": "M-A",
        "name": "多轮状态切换测试",
        "turns": ["推荐一款拍照好的手机", "想喝点什么，但是不要含糖的饮料", "具体单品吧", "第一个给我介绍一下"],
        "expectation": "第二轮切换到食品饮料；第三轮继续无糖饮料任务；第四轮第一个指代无糖饮料。",
    },
    {
        "case_id": "M-B",
        "name": "多轮详情与购物车测试",
        "turns": ["推荐三款适合跑步的短袖", "第一个给我介绍一下", "第二个呢", "那把第二个加入购物车"],
        "expectation": "第二/三轮均解析第一轮推荐列表；第四轮加入购物车的是第一轮第二个短袖。",
    },
    {
        "case_id": "M-C",
        "name": "多轮比较与反选测试",
        "turns": ["推荐三款防晒霜", "第一个和第二个哪个更适合户外", "推荐一款不要含酒精的"],
        "expectation": "第二轮比较防晒；第三轮继续防晒反选，不推荐精华或粉底。",
    },
]


def _parse_sse_events(raw: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data: dict[str, Any] = {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ").strip()
            elif line.startswith("data: "):
                text = line.removeprefix("data: ").strip()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = {"raw": text}
        events.append((event_name, data))
    return events


def _last_event(events: list[tuple[str, dict[str, Any]]], name: str) -> dict[str, Any]:
    for event_name, data in reversed(events):
        if event_name == name:
            return data
    return {}


def _frontend_event_types(turn_result: dict[str, Any]) -> list[str]:
    return [item.get("动作类型") or item.get("event_type") for item in turn_result.get("frontend_events") or []]


def _debug(turn_result: dict[str, Any]) -> dict[str, Any]:
    return turn_result.get("system_debug") or {}


def _analysis(debug: dict[str, Any]) -> dict[str, Any]:
    return debug.get("本轮理解") or debug.get("当前轮次分析") or {}


def _cart_data(turn_result: dict[str, Any]) -> dict[str, Any]:
    return (turn_result.get("frontend_data") or {}).get("cart_state") or {}


def _cart_items(cart_state: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(cart_state.get("items"), list):
        return cart_state["items"]
    nested = cart_state.get("cart")
    if isinstance(nested, dict) and isinstance(nested.get("items"), list):
        return nested["items"]
    return []


def _reply(turn_result: dict[str, Any]) -> str:
    return ((turn_result.get("frontend_data") or {}).get("reply_message") or {}).get("text", "")


def _product_dicts(turn_result: dict[str, Any]) -> list[dict[str, Any]]:
    data = turn_result.get("frontend_data") or {}
    products: list[dict[str, Any]] = []
    for key in ["recommended_products", "alternative_products", "product_cards"]:
        value = data.get(key)
        if isinstance(value, dict) and isinstance(value.get("products"), list):
            products.extend(value["products"])
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for product in products:
        sku = product.get("sku_id") or product.get("product_id")
        if not sku or sku in seen:
            continue
        seen.add(sku)
        unique.append(product)
    return unique


def _safe_debug_summary(turn_result: dict[str, Any]) -> dict[str, Any]:
    debug = _debug(turn_result)
    analysis = _analysis(debug)
    rag = debug.get("检索摘要") or debug.get("RAG检索过程") or {}
    tools = (debug.get("工具与模型") or {}).get("工具执行") or debug.get("工具执行") or []
    models = (debug.get("工具与模型") or {}).get("模型调用") or debug.get("模型调用") or {}
    timing = debug.get("耗时统计") or debug.get("运行耗时") or {}
    return {
        "本轮理解": analysis,
        "检索摘要": rag,
        "工具执行": tools,
        "模型调用": models,
        "耗时统计": timing,
        "回复策略": debug.get("回复策略") or {},
    }


def _post_chat(client: Any, *, user_id: str, session_id: str, message: str) -> dict[str, Any]:
    start = perf_counter()
    response = client.post(
        "/api/chat/stream",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": message,
            "input_type": "text",
            "metadata": {},
        },
    )
    duration_s = round(perf_counter() - start, 3)
    response.raise_for_status()
    events = _parse_sse_events(response.text)
    turn_result = _last_event(events, "turn_result")
    if not turn_result:
        raise RuntimeError(f"turn_result missing for message={message!r}: {response.text[:500]}")
    return {
        "duration_s": duration_s,
        "raw_event_names": [name for name, _ in events],
        "turn_result": turn_result,
    }


def _load_product_map() -> dict[str, Any]:
    from app.core.config import get_settings
    from app.repositories.product_repository import ProductRepository

    settings = get_settings()
    repo = ProductRepository(settings.product_data_path, settings.product_dataset_dir)
    return {item.sku_id: item for item in repo.list_products()}


def _enrich_products(products: list[dict[str, Any]], product_map: dict[str, Any]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in products:
        sku = item.get("sku_id") or item.get("product_id")
        product = product_map.get(sku)
        enriched.append(
            {
                "rank": item.get("rank"),
                "sku_id": sku,
                "name": item.get("name") or getattr(product, "name", None),
                "price": item.get("price") or getattr(product, "price", None),
                "category": item.get("category") or getattr(product, "category", None),
                "sub_category": item.get("sub_category") or getattr(product, "sub_category", None),
                "reason": item.get("reason"),
                "score": item.get("score"),
            }
        )
    return enriched


def _score_single(case: AcceptanceCase, result: dict[str, Any], product_map: dict[str, Any]) -> tuple[bool, list[str]]:
    turn_result = result["turn_result"]
    products = _enrich_products(_product_dicts(turn_result), product_map)
    debug = _debug(turn_result)
    analysis = _analysis(debug)
    issues: list[str] = []
    category = analysis.get("商品类别") or analysis.get("类目")
    sub = analysis.get("商品子类") or analysis.get("子类")
    negatives = set(analysis.get("否定约束") or [])
    product_categories = {item.get("category") for item in products if item.get("category")}
    product_subs = {item.get("sub_category") for item in products if item.get("sub_category")}
    product_ids = {item.get("sku_id") for item in products if item.get("sku_id")}
    if case.expected_category and category != case.expected_category:
        issues.append(f"解析类目={category}，期望={case.expected_category}")
    if case.expected_category and product_categories and any(cat != case.expected_category for cat in product_categories):
        issues.append(f"推荐商品类目错位={sorted(product_categories)}")
    if case.expected_sub_categories and products and not (product_subs & case.expected_sub_categories):
        issues.append(f"未命中期望子类，实际={sorted(product_subs)}，期望包含={sorted(case.expected_sub_categories)}")
    if case.expected_any_sku and products and not (product_ids & case.expected_any_sku):
        issues.append(f"未命中关键SKU，实际={sorted(product_ids)}，期望任一={sorted(case.expected_any_sku)}")
    missing_negative = case.required_negative - negatives
    if missing_negative:
        issues.append(f"否定约束缺失={sorted(missing_negative)}，实际={sorted(negatives)}")
    if len(products) < case.min_products:
        issues.append(f"推荐商品数={len(products)}，少于{case.min_products}")
    return not issues, issues


def _brief_turn(raw: dict[str, Any], product_map: dict[str, Any]) -> dict[str, Any]:
    turn_result = raw["turn_result"]
    products = _enrich_products(_product_dicts(turn_result), product_map)
    analysis = _analysis(_debug(turn_result))
    return {
        "duration_s": raw["duration_s"],
        "raw_event_names": raw["raw_event_names"],
        "frontend_events": _frontend_event_types(turn_result),
        "reply": _reply(turn_result),
        "analysis": analysis,
        "products": products,
        "cart_state": _cart_data(turn_result),
        "system_debug": _safe_debug_summary(turn_result),
    }


def _run_single_cases(client: Any, product_map: dict[str, Any], only: set[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in SINGLE_CASES:
        if only and case.case_id not in only:
            continue
        raw = _post_chat(
            client,
            user_id="real_acceptance_user",
            session_id=f"real_single_{case.case_id}_{uuid4().hex[:8]}",
            message=case.query,
        )
        ok, issues = _score_single(case, raw, product_map)
        row = _brief_turn(raw, product_map)
        row.update(
            {
                "case_id": case.case_id,
                "group": case.group,
                "query": case.query,
                "expectation": case.expectation,
                "ok": ok,
                "issues": issues,
            }
        )
        rows.append(row)
        print(f"{'PASS' if ok else 'FAIL'} {case.case_id} {case.query} {row['duration_s']}s {issues}")
    return rows


def _score_multi(case_id: str, turns: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if case_id == "M-A":
        if len(turns) >= 4:
            if turns[1]["analysis"].get("商品类别") != "食品饮料":
                issues.append("第二轮没有切换到食品饮料")
            if turns[2]["analysis"].get("商品类别") != "食品饮料":
                issues.append("第三轮没有继续食品饮料 pending task")
            if turns[3]["analysis"].get("商品类别") != "食品饮料":
                issues.append("第四轮详情没有保持食品饮料指代")
            first_detail_reply = turns[3].get("reply", "")
            if any(word in first_detail_reply for word in ["手机", "OPPO", "华为", "iPhone"]):
                issues.append("第四轮回复疑似回到手机商品")
    elif case_id == "M-B":
        if turns and len(turns[0].get("products") or []) >= 2:
            expected_second = turns[0]["products"][1]["sku_id"]
            cart = turns[-1].get("cart_state") or {}
            item_ids = {item.get("sku_id") for item in _cart_items(cart)}
            if expected_second not in item_ids:
                issues.append(f"购物车未加入第一轮第二个商品，期望={expected_second}，实际={sorted(item_ids)}")
        else:
            issues.append("第一轮没有足够短袖推荐，无法验证第二个加购")
    elif case_id == "M-C":
        if len(turns) >= 3:
            if turns[0]["analysis"].get("商品类别") != "美妆护肤":
                issues.append("第一轮未识别防晒类目")
            if turns[1]["analysis"].get("商品类别") != "美妆护肤":
                issues.append("第二轮比较没有保持防晒类目")
            third_products = turns[2].get("products") or []
            third_subs = {item.get("sub_category") for item in third_products}
            third_ids = {item.get("sku_id") for item in third_products}
            if not (third_subs & {"防晒", "防晒喷雾"}):
                issues.append(f"第三轮未推荐防晒，实际子类={sorted(third_subs)}")
            if not (third_ids & {"p_beauty_006", "p_beauty_034"}):
                issues.append(f"第三轮未命中不含酒精防晒关键SKU，实际={sorted(third_ids)}")
    return not issues, issues


def _run_multi_cases(client: Any, product_map: dict[str, Any], only: set[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for multi_case in MULTI_CASES:
        if only and multi_case["case_id"] not in only:
            continue
        session_id = f"real_multi_{multi_case['case_id']}_{uuid4().hex[:8]}"
        turn_rows: list[dict[str, Any]] = []
        for turn_index, message in enumerate(multi_case["turns"], start=1):
            raw = _post_chat(
                client,
                user_id=f"real_acceptance_{multi_case['case_id']}",
                session_id=session_id,
                message=message,
            )
            row = _brief_turn(raw, product_map)
            row.update({"turn": turn_index, "query": message})
            turn_rows.append(row)
        ok, issues = _score_multi(multi_case["case_id"], turn_rows)
        rows.append(
            {
                "case_id": multi_case["case_id"],
                "name": multi_case["name"],
                "expectation": multi_case["expectation"],
                "ok": ok,
                "issues": issues,
                "turns": turn_rows,
            }
        )
        print(f"{'PASS' if ok else 'FAIL'} {multi_case['case_id']} {multi_case['name']} {issues}")
    return rows


def _write_summary_markdown(path: Path, *, config: dict[str, Any], single: list[dict[str, Any]], multi: list[dict[str, Any]]) -> None:
    single_passed = sum(1 for item in single if item["ok"])
    multi_passed = sum(1 for item in multi if item["ok"])
    lines = [
        "# 真实 Doubao 高难度验收明细",
        "",
        "本文件由 `backend/scripts/real_doubao_acceptance.py` 生成，所有用例均强制关闭 Mock LLM，并通过当前 FastAPI chat stream 路由执行真实后端流程。",
        "",
        f"- LLM Client: `{config['llm_client']}`",
        f"- USE_MOCK_LLM: `{config['use_mock_llm']}`",
        f"- Doubao base_url configured: `{config['doubao_base_url_configured']}`",
        f"- Doubao api_key configured: `{config['doubao_api_key_configured']}`",
        f"- 单轮通过：{single_passed}/{len(single)}",
        f"- 多轮通过：{multi_passed}/{len(multi)}",
        "",
        "## 单轮结果",
        "",
        "| ID | Query | 结果 | 耗时 | 类目/子类 | 推荐SKU | 真实回复摘要 | frontend_events | system_debug摘要 | 失败原因 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in single:
        analysis = item["analysis"]
        debug = item["system_debug"]
        model = (debug.get("模型调用") or {}).get("客户端") or (debug.get("模型调用") or {}).get("调用客户端")
        rag = debug.get("检索摘要") or {}
        reply_summary = item.get("reply", "").replace("\n", "；")
        if len(reply_summary) > 80:
            reply_summary = reply_summary[:77] + "..."
        lines.append(
            "| {case_id} | {query} | {status} | {duration}s | {cat}/{sub} | {skus} | {reply} | {events} | model={model}; recall={recall}; final={final} | {issues} |".format(
                case_id=item["case_id"],
                query=item["query"],
                status="通过" if item["ok"] else "失败",
                duration=item["duration_s"],
                cat=analysis.get("商品类别") or analysis.get("类目"),
                sub=analysis.get("商品子类") or analysis.get("子类"),
                skus=", ".join(product["sku_id"] for product in item["products"]),
                reply=reply_summary,
                events=", ".join(str(event) for event in item["frontend_events"]),
                model=model,
                recall=rag.get("召回数量") or rag.get("召回商品数量"),
                final=", ".join(rag.get("最终推荐商品ID") or []),
                issues="；".join(item["issues"]) if item["issues"] else "-",
            )
        )
    lines.extend(["", "## 多轮结果", ""])
    for item in multi:
        lines.extend(
            [
                f"### {item['case_id']} {item['name']}",
                "",
                f"- 期望：{item['expectation']}",
                f"- 结果：{'通过' if item['ok'] else '失败'}",
                f"- 问题：{'；'.join(item['issues']) if item['issues'] else '-'}",
                "",
                "| 轮次 | Query | 耗时 | 类目/子类 | 推荐SKU | 购物车SKU | frontend_events |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for turn in item["turns"]:
            analysis = turn["analysis"]
            cart_ids = [cart_item.get("sku_id") for cart_item in _cart_items(turn.get("cart_state") or {})]
            lines.append(
                "| {turn} | {query} | {duration}s | {cat}/{sub} | {skus} | {cart_ids} | {events} |".format(
                    turn=turn["turn"],
                    query=turn["query"],
                    duration=turn["duration_s"],
                    cat=analysis.get("商品类别") or analysis.get("类目"),
                    sub=analysis.get("商品子类") or analysis.get("子类"),
                    skus=", ".join(product["sku_id"] for product in turn["products"]),
                    cart_ids=", ".join(cart_ids),
                    events=", ".join(str(event) for event in turn["frontend_events"]),
                )
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", default="../storage/test_results/real_doubao_acceptance_latest.json")
    parser.add_argument("--markdown-output", default="../../docs/真实Doubao验收明细.md")
    parser.add_argument("--only", default="", help="Comma-separated case IDs, e.g. S06,S12,M-B.")
    args = parser.parse_args()

    _force_real_runtime()
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.core.dependencies import get_llm_client
    from app.main import app

    settings = get_settings()
    llm_client = get_llm_client()
    config = {
        "use_mock_llm": settings.use_mock_llm,
        "enable_local_models": settings.enable_local_models,
        "doubao_base_url_configured": bool(settings.doubao_base_url),
        "doubao_api_key_configured": bool(settings.doubao_api_key),
        "doubao_model": settings.doubao_model,
        "llm_client": llm_client.__class__.__name__,
        "product_dataset_dir": str(settings.product_dataset_dir),
    }
    if config["use_mock_llm"] or config["llm_client"] != "DoubaoClient":
        raise RuntimeError(f"真实验收禁止使用 Mock LLM，当前配置={config}")

    client = TestClient(app)
    product_map = _load_product_map()
    only = {item.strip() for item in args.only.split(",") if item.strip()} or None
    single = _run_single_cases(client, product_map, only=only)
    multi = _run_multi_cases(client, product_map, only=only)
    payload = {"config": config, "single": single, "multi": multi}

    json_path = Path(args.json_output)
    if not json_path.is_absolute():
        json_path = Path(__file__).resolve().parent / json_path
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown_path = Path(args.markdown_output)
    if not markdown_path.is_absolute():
        markdown_path = Path(__file__).resolve().parent / markdown_path
    _write_summary_markdown(markdown_path, config=config, single=single, multi=multi)

    single_passed = sum(1 for item in single if item["ok"])
    multi_passed = sum(1 for item in multi if item["ok"])
    print(f"single_passed={single_passed}/{len(single)}")
    print(f"multi_passed={multi_passed}/{len(multi)}")
    print(f"json={json_path}")
    print(f"markdown={markdown_path}")
    return 0 if single_passed == len(single) and multi_passed == len(multi) else 1


if __name__ == "__main__":
    sys.exit(main())
