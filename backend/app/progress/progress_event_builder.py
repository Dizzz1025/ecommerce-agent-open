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
            events.append(
                {
                    "event_type": "progress_message",
                    "中文说明": "展示系统处理中状态，减少用户等待感。",
                    "step": index,
                    "stage": template_group.get("stage", stage_key),
                    "stage_key": stage_key,
                    "text": text,
                    "display_duration_ms": duration_ms,
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
            events.append(
                {
                    "event_type": "progress_message",
                    "中文说明": "展示系统处理中状态，减少用户等待感。",
                    "step": index,
                    "stage": template_group.get("stage", stage_key),
                    "stage_key": stage_key,
                    "text": text,
                    "display_duration_ms": duration_ms,
                    "can_be_replaced": True,
                }
            )
        return events

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
