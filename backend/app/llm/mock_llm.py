import json
import re
from time import perf_counter

from app.llm.base import BaseLLMClient
from app.models.domain import IntentType


class MockLLMClient(BaseLLMClient):
    def __init__(self) -> None:
        self.last_call_debug: dict = {}

    def generate_response(
        self,
        intent: IntentType,
        message: str,
        context: str,
        product_names: list[str],
    ) -> str:
        output = self._generate_response_internal(
            intent=intent,
            message=message,
            context=context,
            product_names=product_names,
        )
        self.last_call_debug = {
            "llm_provider": "mock",
            "llm_is_mock": True,
            "llm_call_attempted": True,
            "http_request_sent": False,
            "http_request_succeeded": False,
            "http_status_code": None,
            "raw_output_received": bool(output),
            "raw_output_preview": output[:2000],
            "fallback_triggered": False,
            "fallback_reason": None,
            "intent": intent.value,
            "context_length": len(context),
            "product_name_count": len(product_names),
        }
        return output

    def _generate_response_internal(
        self,
        intent: IntentType,
        message: str,
        context: str,
        product_names: list[str],
    ) -> str:
        if "STRUCTURED_PRESENTATION_JSON" in context:
            return _structured_presentation_response(intent=intent, context=context)
        if intent == IntentType.DETAIL and product_names:
            products = _extract_product_facts(context)
            item = products[0] if products else {"name": product_names[0], "price": None, "reason": ""}
            price = f"，售价 ¥{item['price']:g}" if item.get("price") is not None else ""
            facts = _extract_detail_evidence(context)
            lines = [f"可以的，这款是 {item['name']}{price}。"]
            if facts:
                for index, fact in enumerate(facts[:2], start=1):
                    lines.append(f"{index}. {fact}")
            else:
                reason = _humanize_reason(item.get("reason") or "")
                lines.append(f"1. 它和你当前关注的{reason}比较接近，可以作为重点查看对象。")
            lines.append("如果你愿意，我也可以继续帮你和列表里另一款做简短对比。")
            return "\n".join(lines)
        if intent == IntentType.CHECKOUT:
            return "我先整理了当前购物车，你可以继续确认地址和数量。"
        if intent == IntentType.CART_ADD and product_names:
            return f"已经先帮你加入购物车：{product_names[0]}。下面我继续把相关商品卡片展示给你。"
        if intent == IntentType.CART_REMOVE and product_names:
            return f"我先按当前上下文处理了移出购物车：{product_names[0]}。"
        if intent == IntentType.CART_CLEAR:
            return "购物车已经清空，我们可以重新开始挑选。"
        if product_names:
            products = _extract_product_facts(context)
            if "Draft response:" in context and any(term in context for term in ["更接近需求", "alternative", "fallback"]):
                prefix = "我先为你挑了几款更接近需求的选择"
            elif "超出" in message or "太贵" in message or "好贵" in message or "预算" in message:
                prefix = "我重新按你这次的预算筛了一遍"
            else:
                prefix = "我为你挑了几款更合适的选择"
            if products:
                best = products[0]
                reason = _humanize_reason(best.get("reason") or "")
                price = f"，¥{best['price']:g}" if best.get("price") is not None else ""
                lines = [f"{prefix}，优先看 {best['name']}{price}。它比较符合你对{reason}的要求，可以先点开看卡片。"]
                others = "、".join(item["name"] for item in products[1:3] if item.get("name"))
                if others:
                    lines.append(f"另外 {others} 也可以作为备选，图片、价格和参数我都放在商品卡片里。")
                lines.append("想继续推进的话，可以直接说“把第一款加入购物车”。")
                return "\n".join(lines)
            return f"{prefix}：{'、'.join(product_names[:3])}。可以先看卡片，再决定是否加入购物车。"
        return "这个需求我需要再缩小一点范围。你可以补充预算、品牌或使用场景，我马上继续帮你挑。"

    def decide_frontend_action(self, context: dict) -> dict:
        return {}

    def analyze_user_profile(self, context: dict) -> dict:
        text = str(context.get("最近对话", ""))
        self_info = []
        categories = []
        if "小朋友" in text or "4岁" in text or "四岁" in text:
            self_info.append("用户自述/扮演为小朋友，推荐饮食类商品时应优先考虑少糖、小包装、不含咖啡因")
            categories.append("儿童饮品/零食")
        if "女性" in text or "女生" in text or "职场新人" in text:
            self_info.append("用户明确提到女性或职场新人使用场景")
            categories.append("早餐速食/美妆/日用百货")
        return {
            "自然语言用户画像": "用户表达较直接，倾向于先给出需求再逐步补充条件。购物时通常关注预算、功能和适用场景，适合先给简洁结论再给少量理由。" + ("明确上下文：" + "、".join(self_info) + "。" if self_info else ""),
            "结构化用户画像": {
                "说话风格": "直接、口语化",
                "语言风格": "偏简洁",
                "价格偏好": "关注预算和性价比",
                "商品类别偏好": categories,
                "品牌偏好": [],
                "排斥条件": [],
                "决策风格": "先看结论，再按条件细化",
                "信息关注点": ["价格", "功能", "适用场景"],
                "客服交互偏好": "可以接受系统主动澄清，但一次不要问太多",
                "用户自述信息": self_info,
            },
        }

    def analyze_image(self, context: dict) -> dict:
        message = str(context.get("message", ""))
        image_source = str(context.get("image_url") or context.get("image_path") or "")
        text = f"{message} {image_source}".lower()
        if any(term in text for term in ["backpack", "背包", "双肩包"]):
            category = "背包"
            candidates = ["背包", "双肩包", "通勤包"]
            style = ["简约", "通勤", "户外休闲"]
            keywords = ["通勤 双肩 背包", "户外 轻量 背包"]
        elif any(term in text for term in ["shoe", "sneaker", "老爹鞋", "鞋"]):
            category = "老爹鞋"
            candidates = ["老爹鞋", "运动鞋", "跑步鞋"]
            style = ["厚底", "运动休闲"]
            keywords = ["厚底 运动鞋", "休闲 跑步鞋"]
        elif any(term in text for term in ["dress", "连衣裙", "裙"]):
            category = "连衣裙"
            candidates = ["连衣裙", "长裙", "女装"]
            style = ["通勤风", "日常出街"]
            keywords = ["通勤 连衣裙", "日常 长裙"]
        elif any(term in text for term in ["phone", "手机", "smartphone"]):
            category = "手机"
            candidates = ["手机", "智能手机", "拍照手机"]
            style = ["轻薄", "影像", "日常使用"]
            keywords = ["拍照 智能手机", "轻薄 5G 手机"]
        elif any(term in text for term in ["cosmetic", "makeup", "skincare", "化妆品", "彩妆", "护肤"]):
            category = "化妆品"
            candidates = ["化妆品", "护肤品", "彩妆"]
            style = ["精致", "日常护理"]
            keywords = ["护肤品 化妆品", "彩妆 护肤"]
        elif any(term in text for term in ["toy", "doll", "玩偶", "毛绒"]):
            category = "毛绒玩偶"
            candidates = ["毛绒玩偶", "玩具"]
            style = ["柔软", "大号"]
            keywords = ["大号 毛绒玩偶"]
        else:
            category = "商品"
            candidates = ["商品"]
            style = ["图片主体不明确"]
            keywords = [message or "相似商品"]
        return {
            "主要商品类别": category,
            "候选商品类别": candidates,
            "颜色": _mock_colors(text),
            "款式": style,
            "材质或质感": [],
            "图案": [],
            "使用场景": _mock_scenes(text),
            "相似检索关键词": keywords,
            "置信度": 0.72,
            "不确定点": ["Mock 模式未真实读取图片像素，仅根据文本和文件名模拟视觉结果"],
        }

    def resolve_user_intent(self, context: dict) -> dict:
        start = perf_counter()
        payload = self._resolve_user_intent_internal(context)
        self.last_call_debug = {
            "llm_provider": "mock",
            "llm_is_mock": True,
            "llm_call_attempted": True,
            "http_request_sent": False,
            "http_request_succeeded": False,
            "http_status_code": None,
            "raw_output_received": bool(payload),
            "raw_output_preview": _truncate(json.dumps(payload, ensure_ascii=False, default=str)),
            "json_parse_succeeded": bool(payload),
            "fallback_triggered": False,
            "fallback_reason": None,
            "purpose": "intent_plan_resolution",
            "message_length": len(str(context.get("message", ""))),
            "context_keys": list(context.keys())[:20],
            "duration_ms": _elapsed_ms(start),
        }
        return payload

    def _resolve_user_intent_internal(self, context: dict) -> dict:
        message = str(context.get("message", ""))
        category, sub_category = _mock_category(message)
        current_state = context.get("current_state", {}) if isinstance(context.get("current_state"), dict) else {}
        if category is None and any(term in message for term in ["继续", "再", "换", "重新", "便宜", "预算", "刚才", "那款", "这个"]):
            category = current_state.get("current_category")
            sub_category = current_state.get("current_sub_category")
        price_range = _mock_price_range(message)
        positives = _mock_positive_constraints(message)
        negatives = _mock_negative_constraints(message)
        referents = _mock_referents(message)

        if (
            _has_add_command(message)
            and any(term in message for term in ["其他", "全部删", "都删", "删掉"])
            and any(term in message for term in ["推荐", "挑选", "选择"])
            and category
        ):
            retrieval_phrase = _after_last_action_phrase(message)
            retrieval_category, retrieval_sub_category = _mock_category(retrieval_phrase)
            return _intent_payload(
                "refine",
                message,
                retrieval_category or category,
                retrieval_sub_category or sub_category,
                _mock_price_range(retrieval_phrase),
                _mock_positive_constraints(retrieval_phrase),
                negatives,
                referents,
                steps=["cart_add", "cart_remove", "refine"],
                step_sources=[
                    _before_phrase(message, ["把购物车中其他", "购物车中其他", "其他的", "删掉", "删除", "全部删", "都删", "再给", "再推荐"]),
                    _between_phrases(message, ["其他"], ["再给", "再推荐", "重新", "挑选"]) or "其他商品删掉",
                    retrieval_phrase,
                ],
                step_target_refs=["第一个" if "第一个" in message else (referents[0] if referents else None), None, None],
                cart_action={"action": "cart_add", "quantity": 1, "target_ref": "第一个" if "第一个" in message else (referents[0] if referents else None)},
                confidence=0.92,
                reason="用户要求加购、清理购物车中其他匹配商品，并继续推荐新商品",
            )
        if (
            any(term in message for term in ["不喜欢刚才加", "不要刚才加", "刚才加到购物车"])
            and _has_add_command(message)
            and any(term in message for term in ["第二个", "第二款", "第2个", "第2款"])
        ):
            return _intent_payload(
                "cart_add",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["cart_remove", "cart_add"],
                step_sources=[
                    "刚才加到购物车的那个饮料不要了",
                    _after_phrase(message, ["第二个", "第二款", "第2个", "第2款"]) or "第二个加入购物车",
                ],
                step_target_refs=["刚才那个", "第二个"],
                step_quantities=[None, _mock_quantity(message) or 1],
                cart_action={"action": "cart_add", "quantity": _mock_quantity(message) or 1, "target_ref": "第二个"},
                confidence=0.93,
                reason="用户先表达删除刚才加购饮料，再要求按数量加购当前第二个推荐商品",
            )
        if (
            ("清空购物车" in message or "购物车清空" in message or "都不要了" in message)
            and any(term in message for term in ["重新", "再", "推荐", "挑选", "选择", "想要"])
            and category
        ):
            return _intent_payload(
                "refine",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["cart_clear", "refine"],
                step_sources=["清空购物车", _after_last_action_phrase(message)],
                cart_action={"action": "cart_clear"},
                confidence=0.94,
                reason="用户要求先清空购物车，再重新挑选商品",
            )
        if "清空购物车" in message or "购物车清空" in message or "都不要了" in message:
            return _intent_payload(
                "cart_clear",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["cart_clear"],
                cart_action={"action": "cart_clear", "target_ref": referents[0] if referents else None},
                confidence=0.96,
                reason="用户明确要求清空购物车",
            )
        if any(term in message for term in ["只留下", "只保留", "其他都不要", "别的都删"]):
            return _intent_payload(
                "cart_keep_only",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["cart_keep_only"],
                cart_action={
                    "action": "cart_keep_only",
                    "target_ref": referents[0] if referents else None,
                    "keep_categories": [category] if category and not sub_category else [],
                    "keep_sub_categories": [sub_category] if sub_category else [],
                },
                confidence=0.92,
                reason="用户要求购物车只保留指定商品范围",
            )
        if _has_add_command(message) and any(term in message for term in ["下单", "结算", "付款", "支付"]):
            return _intent_payload(
                "checkout",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["cart_add", "checkout"],
                cart_action={"action": "cart_add", "quantity": 1, "target_ref": referents[0] if referents else None},
                confidence=0.95,
                reason="用户要求先加购再结算",
            )
        if any(term in message for term in ["不要了", "删掉", "删除", "移出购物车"]):
            return _intent_payload(
                "cart_remove",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["cart_remove"],
                cart_action={"action": "cart_remove", "target_ref": referents[0] if referents else None},
                confidence=0.9,
                reason="用户表达了移除商品",
            )
        if any(term in message for term in ["查看购物车", "看看购物车", "购物车里有什么"]):
            return _intent_payload(
                "cart_view",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["cart_view"],
                cart_action={"action": "cart_view"},
                confidence=0.95,
                reason="用户明确要查看购物车",
            )
        if any(term in message for term in ["以后", "之后", "长期", "记住", "我一直", "我通常", "我平时", "经常", "比较喜欢"]):
            return _intent_payload(
                "preference",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["preference"],
                confidence=0.9,
                reason="用户表达了相对稳定的偏好",
            )
        if any(term in message for term in ["下单", "结算", "付款", "支付", "总价", "总价格", "一共多少钱"]):
            return _intent_payload(
                "checkout",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["checkout"],
                cart_action={"action": "checkout"},
                confidence=0.93,
                reason="用户要求结算或查看订单总价",
            )
        if _has_add_command(message):
            return _intent_payload(
                "cart_add",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["cart_add"],
                cart_action={"action": "cart_add", "quantity": 1, "target_ref": referents[0] if referents else None},
                confidence=0.9,
                reason="用户要求加入购物车",
            )
        if any(term in message.lower() for term in ["vs", "pk"]) or any(term in message for term in ["对比", "比较", "哪个更", "哪款更", "哪个好", "最好", "最适合"]):
            return _intent_payload(
                "compare",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["compare"],
                compare_targets=referents,
                confidence=0.88,
                reason="用户要求比较候选商品",
            )
        if any(term in message for term in ["详情", "看看", "打开", "具体说说", "介绍", "介绍下", "讲讲", "说说", "参数", "成分", "材质", "特点", "怎么样", "值得买吗", "不错"]):
            return _intent_payload(
                "detail",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["detail"],
                confidence=0.86,
                reason="用户要求查看商品详情",
            )
        if _is_scene_bundle(message):
            return _intent_payload(
                "scene_bundle",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["scene_bundle"],
                scenario=_mock_scenario(message),
                confidence=0.88,
                reason="用户明确要求组合搭配或清单",
            )
        if any(term in message for term in ["重新", "再", "换", "便宜", "太贵", "好贵", "不要", "不含", "预算", "还有", "别的", "哪些合适", "合适呀", "合适啊", "告诉我哪些"]):
            return _intent_payload(
                "refine",
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=["refine"],
                inherit_context=category is None,
                confidence=0.84,
                reason="用户在上一轮基础上补充或修改条件",
            )
        if category or positives or price_range.get("min") is not None or price_range.get("max") is not None:
            intent = "filter" if price_range.get("min") is not None or price_range.get("max") is not None else "recommend"
            return _intent_payload(
                intent,
                message,
                category,
                sub_category,
                price_range,
                positives,
                negatives,
                referents,
                steps=[intent],
                confidence=0.82,
                reason="用户提出商品需求",
            )
        return _intent_payload(
            "chitchat",
            message,
            None,
            None,
            {"min": None, "max": None},
            [],
            [],
            [],
            steps=["chitchat"],
            need_clarification=False,
            confidence=0.78,
            reason="未识别到明确商品需求",
        )


def _extract_product_facts(context: str) -> list[dict]:
    products: list[dict] = []
    for line in context.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("- product_id=") or stripped.startswith("- sku_id=")):
            continue
        fields: dict[str, str] = {}
        for part in stripped.removeprefix("- ").split(" | "):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            fields[key.strip()] = value.strip()
        if not fields.get("name"):
            continue
        price = _mock_float(fields.get("price"))
        score = _mock_float(fields.get("score")) or _mock_float(fields.get("match_score"))
        products.append(
            {
                "sku_id": fields.get("sku_id") or fields.get("product_id") or "",
                "name": fields["name"],
                "brand": fields.get("brand", ""),
                "price": price,
                "score": score,
                "reason": fields.get("reason") or fields.get("reasons") or "",
                "highlight_short": fields.get("highlight_short") or "",
                "matched_reasons": _split_fact_list(fields.get("matched_reasons")),
                "suitable_scenarios": _split_fact_list(fields.get("suitable_scenarios")),
                "target_user_tags": _split_fact_list(fields.get("target_user_tags")),
                "tags": _split_fact_list(fields.get("tags")),
                "risk_notes": _split_fact_list(fields.get("risk_notes")),
            }
        )
    return products


def _structured_presentation_response(intent: IntentType, context: str) -> str:
    products = _extract_product_facts(context)
    if "Task: comparison_presentation" in context or intent == IntentType.COMPARE:
        items = []
        for item in products[:3]:
            reason = _humanize_reason(item.get("reason") or "")
            items.append(
                {
                    "sku_id": item.get("sku_id"),
                    "summary": f"{item['name']}在{reason}上更值得关注。",
                    "advantages": [part for part in reason.split("、") if part][:3],
                    "trade_off": None,
                    "suitable_for": f"更适合关注{reason}的需求。",
                }
            )
        dimensions = [
            {
                "name": "价格",
                "items": [
                    {"sku_id": item.get("sku_id"), "value": f"¥{item['price']:g}"}
                    for item in products[:3]
                    if item.get("price") is not None
                ],
                "better_sku_id": min(
                    [item for item in products[:3] if item.get("price") is not None],
                    key=lambda item: item["price"],
                ).get("sku_id") if any(item.get("price") is not None for item in products[:3]) else None,
            },
            {
                "name": "匹配理由",
                "items": [
                    {"sku_id": item.get("sku_id"), "value": _humanize_reason(item.get("reason") or "")}
                    for item in products[:3]
                ],
                "better_sku_id": None,
            },
        ]
        return json.dumps(
            {
                "items": items,
                "comparison_data": {
                    "dimensions": dimensions,
                    "conclusion": {
                        "recommended_sku_id": products[0].get("sku_id") if products else None,
                        "reason": "结合当前需求，可以先重点看第一款，再用价格和匹配理由对照其他商品。",
                        "alternative_sku_id": products[1].get("sku_id") if len(products) > 1 else None,
                        "alternative_reason": "第二款也可以作为横向对照选择。",
                    },
                },
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "items": [
                {
                    "sku_id": item.get("sku_id"),
                    "reason": _mock_presentation_reason(item),
                    "trade_off": _mock_presentation_tradeoff(item),
                }
                for item in products[:3]
            ]
        },
        ensure_ascii=False,
    )


def _mock_presentation_reason(item: dict) -> str:
    facts = []
    for value in [
        item.get("highlight_short"),
        *_humanized_facts(item.get("matched_reasons") or []),
        *_humanized_facts(item.get("suitable_scenarios") or []),
        *_humanized_facts(item.get("target_user_tags") or []),
        *_humanized_facts(item.get("tags") or []),
    ]:
        text = _clean_mock_fact(value)
        if text and text not in facts:
            facts.append(text)
    price = item.get("price")
    price_text = f"¥{price:g}" if price is not None else "当前价"
    if facts:
        return f"{item['name']}当前价格{price_text}，亮点是{'、'.join(facts[:3])}，和你的需求匹配度更具体。"
    reason = _humanize_reason(item.get("reason") or "")
    return f"{item['name']}当前价格{price_text}，检索理由包含{reason}，可以作为一个具体方案查看。"


def _mock_presentation_tradeoff(item: dict) -> str | None:
    risks = _humanized_facts(item.get("risk_notes") or [])
    keywords = ("偏", "较", "不足", "不适合", "可能", "需要", "少", "低", "重", "厚", "贵")
    for risk in risks:
        if any(keyword in risk for keyword in keywords):
            return risk
    return None


def _mock_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _split_fact_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,，、]", value) if item.strip()]


def _humanized_facts(values: list[str]) -> list[str]:
    return [_clean_mock_fact(item) for item in values if _clean_mock_fact(item)]


def _clean_mock_fact(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if text in {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选"}:
        return ""
    return text.removeprefix("匹配").removeprefix("贴合问题标签:").removeprefix("购物车偏好:")


def _extract_detail_evidence(context: str) -> list[str]:
    facts: list[str] = []
    capture = False
    for line in context.splitlines():
        stripped = line.strip()
        if stripped.startswith("商品事实证据"):
            capture = True
            continue
        if capture and stripped.startswith("- "):
            fact = stripped.removeprefix("- ").strip()
            if fact.startswith("基础信息") or fact.startswith("商品标签"):
                continue
            if "：" in fact:
                fact = fact.split("：", 1)[-1].strip()
            facts.append(fact[:120])
        elif capture and stripped and not stripped.startswith("- "):
            if facts:
                break
    return list(dict.fromkeys(facts))


def _humanize_reason(reason: str) -> str:
    parts = [
        item.removeprefix("匹配").removeprefix("贴合问题标签:").removeprefix("购物车偏好:")
        for item in reason.split("、")
        if item and item not in {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选"}
    ]
    return "、".join(parts[:3]) or "和你当前的需求比较接近"


def _intent_payload(
    intent: str,
    message: str,
    category: str | None,
    sub_category: str | None,
    price_range: dict,
    positives: list[str],
    negatives: list[str],
    referents: list[str],
    *,
    steps: list[str],
    step_sources: list[str] | None = None,
    step_target_refs: list[str | None] | None = None,
    step_quantities: list[int | None] | None = None,
    cart_action: dict | None = None,
    compare_targets: list[str] | None = None,
    scenario: str | None = None,
    inherit_context: bool = False,
    need_clarification: bool | None = None,
    confidence: float = 0.82,
    reason: str = "mock structured intent",
) -> dict:
    if need_clarification is None:
        need_clarification = intent in {"recommend", "filter", "refine"} and not category and not inherit_context
    step_payload = []
    tool_intents = {"cart_add", "cart_remove", "cart_update", "cart_clear", "cart_view", "cart_keep_only", "checkout"}
    retrieval_intents = {"recommend", "filter", "refine", "compare", "detail", "scene_bundle"}
    for index, step_intent in enumerate(steps, start=1):
        source_text = step_sources[index - 1] if step_sources and index - 1 < len(step_sources) else message
        target_ref = step_target_refs[index - 1] if step_target_refs and index - 1 < len(step_target_refs) else (referents[0] if referents else None)
        quantity = step_quantities[index - 1] if step_quantities and index - 1 < len(step_quantities) else _mock_quantity(source_text)
        step_payload.append(
            {
                "step": index,
                "intent": step_intent,
                "action": step_intent,
                "source_text": source_text,
                "target_ref": target_ref,
                "quantity": quantity,
                "sku_id": None,
                "keep_categories": [],
                "keep_sub_categories": [],
                "exclude_sku_ids": [],
                "requires_tool": step_intent in tool_intents,
                "requires_retrieval": step_intent in retrieval_intents,
            }
        )
    return {
        "primary_intent": intent,
        "intent_plan": {
            "primary_intent": intent,
            "steps": step_payload,
            "is_multi_intent": len(step_payload) > 1,
            "confidence": confidence,
            "reason": reason,
        },
        "category": category,
        "sub_category": sub_category,
        "price_range": price_range,
        "positive_constraints": positives,
        "negative_constraints": negatives,
        "brands_include": [],
        "brands_exclude": [],
        "compare_targets": compare_targets or [],
        "referents": referents,
        "mentioned_products": [],
        "cart_action": cart_action,
        "scenario": scenario,
        "target_user": _mock_target_user(message),
        "need_clarification": need_clarification,
        "clarification_slots": ["category"] if need_clarification else [],
        "inherit_context": inherit_context,
        "rewritten_query": " ".join(item for item in [message, category, sub_category, *positives] if item),
        "confidence": confidence,
        "uncertain_points": [],
    }


def _mock_category(message: str) -> tuple[str | None, str | None]:
    aliases = {
        "洗面奶": ("美妆护肤", "洁面"),
        "洁面": ("美妆护肤", "洁面"),
        "防晒": ("美妆护肤", "防晒"),
        "面霜": ("美妆护肤", "面霜"),
        "眼线笔": ("美妆护肤", "眼线笔"),
        "手机": ("数码电子", "智能手机"),
        "数码": ("数码电子", None),
        "耳机": ("数码电子", "真无线耳机"),
        "蓝牙耳机": ("数码电子", "真无线耳机"),
        "背包": ("服饰运动", "背包"),
        "双肩包": ("服饰运动", "背包"),
        "运动帽": ("服饰运动", "帽子"),
        "鸭舌帽": ("服饰运动", "帽子"),
        "棒球帽": ("服饰运动", "帽子"),
        "帽子": ("服饰运动", "帽子"),
        "跑步鞋": ("服饰运动", "跑步鞋"),
        "运动鞋": ("服饰运动", "跑步鞋"),
        "短袖": ("服饰运动", "短袖T恤"),
        "T恤": ("服饰运动", "短袖T恤"),
        "t恤": ("服饰运动", "短袖T恤"),
        "饮料": ("食品饮料", None),
        "零食": ("食品饮料", "坚果/零食"),
        "早餐速食": ("食品饮料", "方便食品"),
        "速食": ("食品饮料", "方便食品"),
        "发圈": ("日用百货", "发圈"),
        "文具": ("日用百货", "办公文具"),
        "办公文具": ("日用百货", "办公文具"),
        "桌面收纳": ("日用百货", "桌面收纳"),
    }
    matches: list[tuple[int, tuple[str | None, str | None]]] = []
    for alias, category in aliases.items():
        index = message.rfind(alias)
        if index >= 0:
            matches.append((index, category))
    if matches:
        return sorted(matches, key=lambda item: item[0])[-1][1]
    if "拍照" in message and not any(term in message for term in ["防晒", "妆", "护肤"]):
        return "数码电子", "智能手机"
    return None, None


def _mock_price_range(message: str) -> dict:
    amount_pattern = r"(?:[1-9]\d*(?:\.\d+)?[kK]|\d+(?:\.\d+)?)"
    range_match = re.search(rf"({amount_pattern})\s*(?:-|到|至|~)\s*({amount_pattern})", message)
    if range_match:
        low, high = float(range_match.group(1).lower().replace("k", "000")), float(range_match.group(2).lower().replace("k", "000"))
        return {"min": min(low, high), "max": max(low, high)}
    max_match = re.search(rf"({amount_pattern})\s*(?:元|块)?\s*(?:以下|以内|内)", message)
    if max_match:
        return {"min": None, "max": float(max_match.group(1).lower().replace("k", "000"))}
    budget_match = re.search(rf"(?:预算|只剩|还剩|剩下|还有|零花钱)[^0-9]*({amount_pattern})", message)
    if budget_match:
        return {"min": None, "max": float(budget_match.group(1).lower().replace("k", "000"))}
    return {"min": None, "max": None}


def _mock_positive_constraints(message: str) -> list[str]:
    terms = [
        "拍照", "性价比", "便宜", "通勤", "旅行", "旅游", "轻量", "低糖", "无糖", "不甜", "低脂",
        "无油", "小包装", "亲子", "分享", "控油", "温和", "清爽", "防晒", "降噪", "续航",
        "健身", "训练", "运动", "速干", "透气", "遮阳",
    ]
    normalized = {"便宜": "性价比", "不甜": "低糖"}
    return list(dict.fromkeys(normalized.get(term, term) for term in terms if term in message))


def _mock_negative_constraints(message: str) -> list[str]:
    constraints = []
    for term in ["酒精", "日系", "甜味", "糖", "防水", "粗头", "紧身", "印花", "大包装", "糕点", "谷物"]:
        if term in message and any(neg in message[max(0, message.find(term) - 8):message.find(term) + len(term)] for neg in ["不", "不要", "别", "无", "不能"]):
            constraints.append(term)
    return list(dict.fromkeys(constraints))


def _mock_referents(message: str) -> list[str]:
    refs = ["第一款", "第一个", "第二款", "第二个", "第三款", "第三个", "刚才那个", "刚才那款", "这个", "这款", "它"]
    return [ref for ref in refs if ref in message]


def _has_add_command(message: str) -> bool:
    if "加购" in message and any(term in message for term in ["刚才加购的", "之前加购的", "已经加购的"]):
        return False
    return any(
        term in message
        for term in [
            "加入购物车", "加到购物车", "加购物车", "购物车加", "往购物车加",
            "放购物车", "放进购物车", "加购", "买这个", "要这个",
        ]
    )


def _is_scene_bundle(message: str) -> bool:
    markers = ["一套", "全套", "清单", "方案", "搭配", "组合", "配齐"]
    return any(marker in message for marker in markers)


def _mock_scenario(message: str) -> str | None:
    for term in ["西北", "海边", "度假", "旅行", "通勤", "健身", "职场新人", "入职", "小朋友"]:
        if term in message:
            return term
    return None


def _mock_colors(text: str) -> list[str]:
    colors = ["黑色", "白色", "蓝色", "浅蓝色", "红色", "粉色", "灰色", "绿色", "米色", "棕色"]
    return [color for color in colors if color in text]


def _mock_scenes(text: str) -> list[str]:
    scenes = ["通勤", "旅行", "户外", "日常出街", "海边", "健身", "学生", "职场"]
    return [scene for scene in scenes if scene in text]


def _mock_target_user(message: str) -> str | None:
    for term in ["小朋友", "4岁", "四岁", "女生", "女性", "爸爸妈妈", "爸爸", "妈妈", "学生", "职场新人"]:
        if term in message:
            return "小朋友" if term in {"4岁", "四岁"} else term
    return None


def _mock_quantity(message: str) -> int | None:
    matches = list(re.finditer(r"(?:加|买|来|要|改成|改为)?\s*(\d+|[一二两三四五六七八九十两]+)\s*(?:瓶|件|个|份|双|台|盒|包|箱)", message))
    usable = [match for match in matches if match.start(1) == 0 or message[match.start(1) - 1] != "第"]
    if not usable:
        return None
    token = usable[-1].group(1)
    if token.isdigit():
        return int(token)
    digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    return digits.get(token)


def _after_last_action_phrase(message: str) -> str:
    markers = ["重新", "再", "推荐", "挑选", "选择", "想要"]
    positions = [message.rfind(marker) for marker in markers if message.rfind(marker) >= 0]
    if not positions:
        return message
    return message[max(positions):].strip("，,。 ")


def _before_phrase(message: str, markers: list[str]) -> str:
    positions = [message.find(marker) for marker in markers if message.find(marker) >= 0]
    if not positions:
        return message
    return message[:min(positions)].strip("，,。 ")


def _between_phrases(message: str, start_markers: list[str], end_markers: list[str]) -> str | None:
    starts = [message.find(marker) for marker in start_markers if message.find(marker) >= 0]
    if not starts:
        return None
    start = min(starts)
    ends = [message.find(marker, start + 1) for marker in end_markers if message.find(marker, start + 1) >= 0]
    end = min(ends) if ends else len(message)
    return message[start:end].strip("，,。 ") or None


def _after_phrase(message: str, markers: list[str]) -> str | None:
    positions = [(message.find(marker), marker) for marker in markers if message.find(marker) >= 0]
    if not positions:
        return None
    index, marker = min(positions, key=lambda item: item[0])
    return message[index:index + len(message)].strip("，,。 ") or marker


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 2)


def _truncate(text: str | None, limit: int = 2000) -> str | None:
    if text is None:
        return None
    return text if len(text) <= limit else text[: limit - 1] + "…"
