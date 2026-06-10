from __future__ import annotations

from typing import Any

from app.models.agent import DialogueFlow, FlowDecision, ModelRouteDecision, ParsedQuery
from app.models.domain import SessionState
from app.progress.progress_templates import (
    LATENCY_LEVEL_CONFIG,
    PROGRESS_STAGE_TEMPLATES,
    SCENARIO_PROGRESS_PLANS,
)


class ProgressEventBuilder:
    """Predict user-facing progress events without exposing internal reasoning."""

    def build_parallel(
        self,
        *,
        message: str,
        input_type: str = "text",
        is_old_user: bool = False,
    ) -> dict[str, Any]:
        """Build an immediate, template-only progress plan.

        This method must stay independent from LLM, retrieval, rerank and
        personalization. It exists purely to keep the frontend alive while the
        real backend pipeline runs in parallel.
        """

        scenario_key = self._fast_scenario_key(message, input_type)
        cart_sub_action = self._cart_sub_action(message) if scenario_key == "cart_action" else None
        stages = self._fast_stages(scenario_key, cart_sub_action)
        latency_level = "slow" if scenario_key in {"comparison", "scenario_bundle", "multimodal_search"} else "medium"
        if scenario_key == "cart_action":
            latency_level = "fast"
            # 加购/结算场景可适当增加进度事件数，让体验更自然
            if cart_sub_action in {"cart_add", "checkout"}:
                latency_level = "medium"
        config = LATENCY_LEVEL_CONFIG.get(latency_level, LATENCY_LEVEL_CONFIG["medium"])
        duration_ms = int(config.get("default_display_duration_ms", 700))
        events = self._events_from_stages_lightweight(
            stages=stages,
            message=message,
            max_events=int(config.get("max_events", 5)),
            duration_ms=duration_ms,
            is_old_user=is_old_user,
            cart_sub_action=cart_sub_action,
        )
        work_types = list(dict.fromkeys(event["stage_key"] for event in events))
        return {
            "scenario_key": f"parallel_{scenario_key}",
            "是否启用progress": True,
            "是否并行启动": True,
            "是否老用户": is_old_user,
            "预计耗时等级": latency_level,
            "预测工作类型": work_types,
            "是否需要记忆": "memory_context" in work_types,
            "是否需要检索": "retrieval" in work_types,
            "是否需要Doubao": "不在progress中判断",
            "progress模板": [event["stage_key"] for event in events],
            "events": events,
            "生成时机": "request_entry_parallel",
            "本地快速生成": True,
            "目标首次发送_ms": 500,
            "progress输出间隔_ms": duration_ms,
            "已输出数量": 0,
            "首条progress输出耗时_ms": None,
            "停止原因": None,
        }

    def build_fast(
        self,
        *,
        message: str,
        state: SessionState,
        input_type: str = "text",
    ) -> dict[str, Any]:
        """Build progress events before any LLM call.

        This is intentionally heuristic and local-only: it gives the frontend an
        immediate processing signal while the real intent/RAG/LLM pipeline runs.
        """
        scenario_key = self._fast_scenario_key(message, input_type)
        cart_sub_action = self._cart_sub_action(message) if scenario_key == "cart_action" else None
        stages = self._fast_stages(scenario_key, cart_sub_action)
        has_context = bool(
            state.recent_messages
            or state.cart.items
            or state.user_profile_summary_text
            or state.event_memory.active_recommendation_event_id
        )
        if has_context and "memory_context" not in stages and scenario_key != "cart_action":
            stages.insert(1, "memory_context")
        latency_level = "slow" if scenario_key in {"comparison", "scenario_bundle", "multimodal_search"} else "medium"
        if scenario_key == "cart_action":
            latency_level = "fast"
            if cart_sub_action in {"cart_add", "checkout"}:
                latency_level = "medium"
        config = LATENCY_LEVEL_CONFIG.get(latency_level, LATENCY_LEVEL_CONFIG["medium"])
        events = self._events_from_stages_lightweight(
            stages=stages,
            message=message,
            max_events=int(config.get("max_events", 5)),
            duration_ms=int(config.get("default_display_duration_ms", 700)),
            is_old_user=has_context,
            cart_sub_action=cart_sub_action,
        )
        work_types = list(dict.fromkeys(event["stage_key"] for event in events))
        return {
            "scenario_key": f"fast_{scenario_key}",
            "预计耗时等级": latency_level,
            "预测工作类型": work_types,
            "是否需要记忆": "memory_context" in work_types,
            "是否需要检索": "retrieval" in work_types,
            "是否需要Doubao": "待后续模型路由判断",
            "progress模板": [event["stage_key"] for event in events],
            "events": events,
            "生成时机": "pre_llm_fast",
            "本地快速生成": True,
            "目标首次发送_ms": 500,
        }

    def build(
        self,
        *,
        parsed_query: ParsedQuery,
        decision: FlowDecision,
        state: SessionState,
        model_route: ModelRouteDecision,
        input_type: str = "text",
    ) -> dict[str, Any]:
        scenario_key = self._scenario_key(parsed_query, decision, input_type)
        cart_sub_action = self._cart_sub_action(parsed_query.raw_message) if scenario_key == "cart_action" else None
        plan = dict(SCENARIO_PROGRESS_PLANS.get(scenario_key) or SCENARIO_PROGRESS_PLANS["recommendation"])
        # 购物车场景按子动作选阶段列表
        if scenario_key == "cart_action" and cart_sub_action:
            sub_stages = plan.get("sub_action_stages", {}).get(cart_sub_action)
            if sub_stages:
                stages = list(sub_stages)
            else:
                stages = list(plan.get("stages", []))
        else:
            stages = list(plan.get("stages", []))
        latency_level = str(plan.get("latency_level") or self._latency_level(decision, model_route))
        if decision.need_retrieval and "retrieval" not in stages:
            stages.append("retrieval")
        if model_route.need_llm and "response_composition" not in stages:
            stages.append("response_composition")
        if state.recent_messages and "memory_context" not in stages and scenario_key != "cart_action":
            stages.insert(1, "memory_context")

        config = LATENCY_LEVEL_CONFIG.get(latency_level, LATENCY_LEVEL_CONFIG["medium"])
        max_events = int(config.get("max_events", 5))
        duration_ms = int(config.get("default_display_duration_ms", 700))
        selected_stages = stages[:max_events]
        events = []
        events = self._events_from_stages(
            stages=selected_stages,
            message=parsed_query.raw_message,
            max_events=max_events,
            duration_ms=duration_ms,
            state=state,
            cart_sub_action=cart_sub_action,
        )

        work_types = list(dict.fromkeys(selected_stages))
        return {
            "scenario_key": scenario_key,
            "预计耗时等级": latency_level,
            "预测工作类型": work_types,
            "是否需要记忆": "memory_context" in work_types,
            "是否需要检索": decision.need_retrieval,
            "是否需要Doubao": model_route.need_llm,
            "progress模板": [event["stage_key"] for event in events],
            "events": events,
        }

    def _events_from_stages(
        self,
        *,
        stages: list[str],
        message: str,
        max_events: int,
        duration_ms: int,
        state: SessionState,
        cart_sub_action: str | None = None,
    ) -> list[dict[str, Any]]:
        selected_stages = stages[:max_events]
        events: list[dict[str, Any]] = []
        for index, stage_key in enumerate(selected_stages, start=1):
            template_group = PROGRESS_STAGE_TEMPLATES.get(stage_key, {})
            templates_raw = template_group.get("templates", [])
            if not templates_raw:
                continue
            # 购物车专用阶段：templates 是 dict，按子动作选模板列表
            if isinstance(templates_raw, dict):
                sub = cart_sub_action or "default"
                templates = templates_raw.get(sub) or templates_raw.get("default", [])
            else:
                templates = templates_raw
            if not templates:
                continue
            text = self._progress_text(message=message, stage_key=stage_key, templates=templates, state=state)
            detail_text = self._stage_detail_text(
                stage_key=stage_key,
                message=message,
                is_old_user=bool(state.recent_messages or state.user_profile_summary_text),
                cart_sub_action=cart_sub_action,
                step=index,
            )
            events.append(
                {
                    "event_type": "progress_message",
                    "中文说明": "展示系统处理中状态，减少用户等待感。",
                    "step": index,
                    "stage": template_group.get("stage", stage_key),
                    "stage_key": stage_key,
                    "text": text,
                    "detail_text": detail_text,
                    "display_text": f"{text}\n{detail_text}" if detail_text else text,
                    "display_duration_ms": duration_ms,
                    "display_duration_sec": round(duration_ms / 1000, 1),
                    "can_be_replaced": True,
                }
            )
        return events

    def _events_from_stages_lightweight(
        self,
        *,
        stages: list[str],
        message: str,
        max_events: int,
        duration_ms: int,
        is_old_user: bool,
        cart_sub_action: str | None = None,
    ) -> list[dict[str, Any]]:
        selected_stages = stages[:max_events]
        events: list[dict[str, Any]] = []
        for index, stage_key in enumerate(selected_stages, start=1):
            template_group = PROGRESS_STAGE_TEMPLATES.get(stage_key, {})
            templates_raw = template_group.get("templates", [])
            if not templates_raw:
                continue
            # 购物车专用阶段：templates 是 dict，按子动作选模板列表
            if isinstance(templates_raw, dict):
                sub = cart_sub_action or "default"
                templates = templates_raw.get(sub) or templates_raw.get("default", [])
            else:
                templates = templates_raw
            if not templates:
                continue
            if stage_key == "memory_context" and is_old_user:
                text = "正在结合您的历史偏好和购买习惯筛选商品。"
            else:
                text = templates[_stable_index(message, stage_key, len(templates))]
            detail_text = self._stage_detail_text(
                stage_key=stage_key,
                message=message,
                is_old_user=is_old_user,
                cart_sub_action=cart_sub_action,
                step=index,
            )
            events.append(
                {
                    "event_type": "progress_message",
                    "中文说明": "展示系统处理中状态，减少用户等待感。",
                    "step": index,
                    "stage": template_group.get("stage", stage_key),
                    "stage_key": stage_key,
                    "text": text,
                    "detail_text": detail_text,
                    "display_text": f"{text}\n{detail_text}" if detail_text else text,
                    "display_duration_ms": duration_ms,
                    "display_duration_sec": round(duration_ms / 1000, 1),
                    "can_be_replaced": True,
                }
            )
        return events

    def _stage_detail_text(
        self,
        *,
        stage_key: str,
        message: str,
        is_old_user: bool,
        cart_sub_action: str | None,
        step: int,
    ) -> str | None:
        """Build one short UI-facing processing note.

        The note describes observable backend work, not model inner reasoning,
        so it can be generated locally and emitted immediately.
        """

        if stage_key in {"cart_inventory_check", "cart_updating", "cart_checkout_processing"}:
            if cart_sub_action == "cart_add":
                return _progress_detail(
                    "我会先核对商品和数量，再同步购物车状态。",
                    "这一步会聚焦你明确要加购的商品，让购物车结果保持清楚准确。",
                )
            if cart_sub_action == "cart_remove":
                return _progress_detail(
                    "我会优先确认你要调整的商品，让购物车变化和你的表达保持一致。",
                    "如果你用了“刚才那个”或“第二个”这样的说法，系统会先根据最近的商品记录准确定位目标。",
                )
            if cart_sub_action == "checkout":
                return _progress_detail(
                    "我会核对购物车商品、数量和金额，再生成可展示的结算信息。",
                    "信息充足时会直接准备订单确认所需的数据，必要时也会给出清楚的下一步提示。",
                )
            return _progress_detail(
                "我会只执行你明确要求的购物车动作。",
                "商品、数量和操作结果都会从后端状态中确认后再返回给前端。",
            )

        if stage_key == "memory_context" and is_old_user:
            return _progress_detail(
                "历史偏好只作为软参考，本轮你明确说出的条件会优先执行。",
                "系统会把你这次说的预算、品类和偏好放在最前面，再结合历史选择优化排序。",
            )

        if stage_key not in {"retrieval", "selection_rerank", "response_composition"}:
            return None
        if step > 5:
            return None

        domain = _domain_key(message)
        if stage_key == "retrieval":
            return {
                "digital": _progress_detail(
                    "我会重点看预算、核心功能和日常体验，优先寻找更贴近需求的数码商品。",
                    "如果你提到拍照、续航、办公或游戏，我会把这些功能词转成更具体的检索条件。",
                ),
                "beauty": _progress_detail(
                    "我会优先核对品类、肤质、功效和成分品牌偏好。",
                    "像油皮、干皮、敏感肌这类信息会作为适配信号参与筛选，让推荐更贴近真实护肤需求。",
                ),
                "clothing": _progress_detail(
                    "我会结合版型、材质和使用场景，优先找真正适合穿搭或出行的商品。",
                    "如果你说的是通勤、旅行或运动，我会把场景拆成更稳定的商品筛选方向。",
                ),
                "food": _progress_detail(
                    "我会留意口味、甜度、规格和适合分享/日常饮用的特点。",
                    "如果你提到无糖、早餐、办公室或健身后补给，我会优先找更贴近这些场景的真实商品。",
                ),
            }.get(
                domain,
                _progress_detail(
                    "我会先从真实商品库里找可展示的候选商品，再做筛选。",
                    "商品名称、价格和推荐依据都会以数据库信息为准，让前端展示更稳定可靠。",
                ),
            )
        if stage_key == "selection_rerank":
            return {
                "digital": _progress_detail(
                    "排序时会更重视功能匹配、价格段和实际使用场景。",
                    "我会优先展示和你需求更接近的设备，让预算、功能和场景一起参与选择。",
                ),
                "beauty": _progress_detail(
                    "排序时会更重视功效贴合、肤质适配和评价反馈。",
                    "如果你提出了成分或肤感偏好，我会把这些重点放进推荐优先级里一起考虑。",
                ),
                "clothing": _progress_detail(
                    "排序时会更重视场景适配、舒适度和搭配实用性。",
                    "同类商品里会优先展示更适合当前场景的款式，方便你直接对比卡片。",
                ),
                "food": _progress_detail(
                    "排序时会更重视口味偏好、健康约束和规格价格。",
                    "我会优先展示更贴近你口味和场景的选择，同时保留有参考价值的真实备选。",
                ),
            }.get(
                domain,
                _progress_detail(
                    "排序时会优先保留更贴合你核心需求的商品。",
                    "候选结果会按匹配度整理，方便你直接查看最值得关注的商品卡片。",
                ),
            )
        if stage_key == "response_composition":
            if is_old_user:
                return _progress_detail(
                    "我会把个性化重点自然放进语气、排序和推荐理由里。",
                    "这些偏好只作为辅助参考，最终展示仍然以本轮需求和商品事实为准。",
                )
            return _progress_detail(
                "我会把结论写短一点，更多细节交给商品卡片展示。",
                "回复会优先给出可行动的推荐结果，让你能快速看到商品、价格和主要理由。",
            )
        return None

    @staticmethod
    def _progress_text(
        *,
        message: str,
        stage_key: str,
        templates: list[str],
        state: SessionState,
    ) -> str:
        if stage_key == "memory_context":
            has_cart = bool(state.cart.items)
            has_profile = bool(state.user_profile_summary_text)
            if has_cart and has_profile:
                return "正在根据你的购物车记录和历史偏好筛选商品。"
            if has_cart:
                return "正在结合购物车里的商品做搭配和兼容推荐。"
            if has_profile:
                return "正在结合你的历史偏好调整推荐重点。"
        return templates[_stable_index(message, stage_key, len(templates))]

    @staticmethod
    def _fast_scenario_key(message: str, input_type: str) -> str:
        if input_type != "text":
            return "multimodal_search"
        if any(term in message for term in ["加入购物车", "加购物车", "加购", "删除", "删掉", "移除", "清空", "结算", "下单", "付款", "购物车"]):
            return "cart_action"
        if any(term in message for term in ["对比", "比较", "哪个更", "哪款更"]):
            return "comparison"
        if any(term in message for term in ["介绍", "详情", "看看", "第一个", "第二个", "第三个", "这款", "那个"]):
            return "product_detail"
        if any(term in message for term in ["搭配", "一整套", "清单", "旅行", "度假", "健身", "通勤套装"]):
            return "scenario_bundle"
        return "recommendation"

    @staticmethod
    def _cart_sub_action(message: str) -> str:
        """Detect the specific cart sub-action from the message text.

        Priority order matters: checkout before cart_view (结算 contains 购物车
        implicitly), cart_clear before cart_remove, etc.
        """
        if any(term in message for term in ["结算", "下单", "付款", "支付", "买单"]):
            return "checkout"
        if any(term in message for term in ["清空", "全部删除", "全部移除", "全删掉"]):
            return "cart_clear"
        if any(term in message for term in ["加入购物车", "加购物车", "加购", "都加", "都加入", "一起加"]):
            return "cart_add"
        if any(term in message for term in ["删除", "移除", "删掉", "去掉", "不要", "不想", "拿掉", "撤掉"]):
            return "cart_remove"
        if any(term in message for term in ["查看购物车", "看看购物车", "购物车里有什么", "打开购物车", "看一下购物车"]):
            return "cart_view"
        if any(term in message for term in ["购物车"]):
            return "cart_view"
        return "default"

    @staticmethod
    def _fast_stages(scenario_key: str, cart_sub_action: str | None = None) -> list[str]:
        if scenario_key == "cart_action":
            sub_action = cart_sub_action or "default"
            plan = SCENARIO_PROGRESS_PLANS.get("cart_action", {})
            sub_stages = plan.get("sub_action_stages", {}).get(sub_action, plan.get("stages", []))
            return list(sub_stages)
        if scenario_key == "product_detail":
            return ["intent_understanding", "memory_context", "retrieval", "response_composition"]
        if scenario_key == "comparison":
            return ["intent_understanding", "memory_context", "retrieval", "selection_rerank", "response_composition"]
        return ["intent_understanding", "constraint_extraction", "retrieval", "selection_rerank", "response_composition"]

    @staticmethod
    def _scenario_key(parsed_query: ParsedQuery, decision: FlowDecision, input_type: str) -> str:
        if input_type != "text":
            return "multimodal_search"
        mapping = {
            DialogueFlow.GREETING: "greeting",
            DialogueFlow.RECOMMENDATION: "recommendation",
            DialogueFlow.FILTERING: "filtering",
            DialogueFlow.EXCLUSION: "negative_constraints",
            DialogueFlow.REFINEMENT: "multi_turn_refinement",
            DialogueFlow.PRODUCT_QA: "product_detail",
            DialogueFlow.COMPARISON: "comparison",
            DialogueFlow.SCENE_BUNDLE: "scenario_bundle",
            DialogueFlow.CART_ACTION: "cart_action",
            DialogueFlow.CHECKOUT: "cart_action",
            DialogueFlow.CLARIFICATION: "clarification",
            DialogueFlow.NO_RESULT: "no_result_with_alternatives",
            DialogueFlow.OUT_OF_SCOPE: "out_of_scope",
        }
        return mapping.get(decision.flow, "recommendation")

    @staticmethod
    def _latency_level(decision: FlowDecision, model_route: ModelRouteDecision) -> str:
        if decision.flow in {DialogueFlow.COMPARISON, DialogueFlow.SCENE_BUNDLE}:
            return "slow"
        if model_route.need_llm or decision.need_retrieval:
            return "medium"
        return "fast"


def _stable_index(message: str, key: str, size: int) -> int:
    if size <= 1:
        return 0
    value = sum(ord(ch) for ch in f"{message}:{key}")
    return value % size


def _progress_detail(*sentences: str) -> str:
    """Join 2-3 safe, user-facing progress detail sentences."""

    cleaned = [str(item).strip().rstrip("。！？") for item in sentences if str(item or "").strip()]
    if len(cleaned) < 2:
        cleaned.append("系统会以商品库中的真实信息为准，整理成前端可以直接展示的结果")
    return "。".join(cleaned[:3]) + "。"


def _domain_key(message: str) -> str:
    text = message or ""
    if any(term in text for term in ["手机", "耳机", "电脑", "平板", "拍照", "续航", "数码", "充电", "降噪"]):
        return "digital"
    if any(term in text for term in ["护肤", "防晒", "面霜", "精华", "洁面", "洗面奶", "洁面乳", "爽肤水", "化妆水", "口红", "粉底", "眼线", "肤质", "控油", "保湿"]):
        return "beauty"
    if any(term in text for term in ["短袖", "外套", "背包", "鞋", "穿搭", "通勤", "旅行", "健身", "瑜伽", "跑步"]):
        return "clothing"
    if any(term in text for term in ["饮料", "零食", "早餐", "咖啡", "低糖", "无糖", "好吃", "好喝", "食品"]):
        return "food"
    return "general"
