from __future__ import annotations

from typing import Any

from app.models.agent import (
    CandidateProduct,
    DialogueFlow,
    FlowDecision,
    FrontendActionDecision,
    ParsedQuery,
    ProductQAResult,
    ScenePlan,
    ToolExecutionResult,
    UnifiedTurnOutput,
)
from app.models.domain import Product, ProductCard, SessionState


class FrontendEventBuilder:
    """Build the stable three-part output consumed by Android and debug tools."""

    _event_meanings = {
        "show_reply": "展示系统回复",
        "show_products": "展示推荐商品卡片或商品图片",
        "show_product_detail": "展示某个商品详情信息",
        "navigate": "按照用户提示跳转页面",
        "update_cart": "更新购物车状态",
        "update_page_state": "更新页面上的非对话性信息",
        "show_clarification_options": "展示澄清问题或推荐选项",
        "show_error": "展示错误或无结果提示",
    }

    _page_map = {
        "chat": "chat_page",
        "product_list": "product_list_page",
        "product_detail": "product_detail_page",
        "cart": "cart_page",
        "checkout": "checkout_page",
        "scenario": "scenario_page",
        "home": "home_page",
    }

    def build(
        self,
        *,
        session_id: str,
        user_id: str,
        response_text: str,
        parsed_query: ParsedQuery,
        decision: FlowDecision,
        state_before: dict[str, Any],
        state_after: SessionState,
        cards: list[ProductCard],
        products: list[Product],
        candidates: list[CandidateProduct],
        alternatives: list[CandidateProduct],
        tool_result: ToolExecutionResult | None,
        qa_result: ProductQAResult | None,
        scene_plan: ScenePlan | None,
        frontend_action: FrontendActionDecision,
        trace_payload: dict[str, Any],
        history_restored: bool = False,
        restored_from_session_id: str | None = None,
        legacy_sse_events: list[str] | None = None,
    ) -> UnifiedTurnOutput:
        events: list[dict[str, Any]] = []
        data: dict[str, Any] = {}

        data["reply_message"] = {
            "中文说明": "系统要展示给用户的回复文本。",
            "text": response_text,
        }
        self._add_event(events, "show_reply", "reply_message")

        if decision.flow == DialogueFlow.CLARIFICATION:
            data["clarification_options"] = self._build_clarification_options(response_text, decision)
            self._add_event(events, "show_clarification_options", "clarification_options")

        if cards and not qa_result:
            data["recommended_products"] = {
                "中文说明": "本轮推荐给用户看的商品卡片，全部来自本地商品库和检索结果。",
                "products": [card.model_dump() for card in cards],
            }
            self._add_event(events, "show_products", "recommended_products")
        elif alternatives:
            data["alternative_products"] = {
                "中文说明": "没有完全命中时提供的相近备选商品，前端可作为弱提示展示。",
                "products": [self._candidate_to_card_like(item) for item in alternatives[:3]],
            }
            self._add_event(events, "show_products", "alternative_products")

        if qa_result and products:
            data["product_detail"] = {
                "中文说明": "商品详情或商品问答结果，商品信息来自数据库，回答依据来自商品事实。",
                "product": products[0].model_dump(),
                "qa": qa_result.model_dump(),
            }
            self._add_event(events, "show_product_detail", "product_detail")

        if tool_result and tool_result.payload:
            data["cart_state"] = {
                "中文说明": "购物车工具执行后的真实购物车状态。",
                "tool_ok": tool_result.ok,
                "tool_name": tool_result.tool_name,
                "message": tool_result.message,
                "cart": tool_result.payload,
            }
            self._add_event(events, "update_cart", "cart_state")

        navigation = self._build_navigation(frontend_action)
        if navigation is not None:
            data["navigation"] = navigation
            self._add_event(events, "navigate", "navigation", blocking=True)

        if self._should_emit_page_state(
            decision=decision,
            cards=cards,
            alternatives=alternatives,
            tool_result=tool_result,
            qa_result=qa_result,
            scene_plan=scene_plan,
            frontend_action=frontend_action,
        ):
            page_state = self._build_page_state(
                session_id=session_id,
                user_id=user_id,
                state=state_after,
                parsed_query=parsed_query,
                decision=decision,
                frontend_action=frontend_action,
                scene_plan=scene_plan,
            )
            data["page_state"] = page_state
            self._add_event(events, "update_page_state", "page_state")

        debug = self._build_system_debug(
            session_id=session_id,
            user_id=user_id,
            parsed_query=parsed_query,
            decision=decision,
            state_before=state_before,
            state_after=state_after,
            trace_payload=trace_payload,
            tool_result=tool_result,
            frontend_action=frontend_action,
            history_restored=history_restored,
            restored_from_session_id=restored_from_session_id,
            legacy_sse_events=legacy_sse_events or [],
        )
        return UnifiedTurnOutput(
            frontend_events=events,
            frontend_data=data,
            system_debug=debug,
        )

    def build_error(
        self,
        *,
        session_id: str,
        user_id: str,
        message: str,
        state_before: dict[str, Any],
        state_after: SessionState,
        trace_payload: dict[str, Any],
        legacy_sse_events: list[str] | None = None,
    ) -> UnifiedTurnOutput:
        events: list[dict[str, Any]] = []
        data = {
            "reply_message": {
                "中文说明": "系统异常时展示给用户的兜底回复。",
                "text": "系统处理时遇到问题，请稍后重试。",
            },
            "error_message": {
                "中文说明": "后端异常信息，前端只需要展示 message，不需要展示内部错误。",
                "code": "AGENT_ERROR",
                "message": "系统处理时遇到问题，请稍后重试。",
            },
        }
        self._add_event(events, "show_reply", "reply_message")
        self._add_event(events, "show_error", "error_message")
        debug = {
            "中文说明": "本部分用于后端调试，展示异常发生前后的系统状态。",
            "历史恢复状态": {"是否恢复": False},
            "对话状态变化": {"变化前": state_before, "变化后": self._state_summary(state_after)},
            "异常信息": {"message": message},
            "原始SSE事件": legacy_sse_events or [],
            "trace": trace_payload,
        }
        return UnifiedTurnOutput(frontend_events=events, frontend_data=data, system_debug=debug)

    def _add_event(
        self,
        events: list[dict[str, Any]],
        event_type: str,
        data_ref: str,
        *,
        blocking: bool = False,
    ) -> None:
        events.append(
            {
                "步骤": len(events) + 1,
                "动作类型": event_type,
                "含义": self._event_meanings[event_type],
                "数据参考": data_ref,
                "blocking": blocking,
            }
        )

    def _build_clarification_options(self, response_text: str, decision: FlowDecision) -> dict[str, Any]:
        options_by_slot = {
            "category": ["护肤美妆", "手机耳机", "跑鞋穿搭"],
            "priority": ["拍照", "续航", "性价比"],
            "sub_category_or_scene": ["具体单品", "场景搭配"],
        }
        options = []
        for slot in decision.missing_slots:
            options.extend(options_by_slot.get(slot, []))
        return {
            "中文说明": "当用户需求不完整时，前端可以展示这些快捷选项。",
            "question": response_text,
            "missing_slots": decision.missing_slots,
            "options": list(dict.fromkeys(options)),
        }

    def _build_navigation(self, frontend_action: FrontendActionDecision) -> dict[str, Any] | None:
        if frontend_action.target_page in {"chat", "product_list"}:
            return None
        return {
            "中文说明": "页面跳转动作。前端可以按 target_page 切换页面，并使用 params 定位商品或订单。",
            "target_page": self._page_map.get(frontend_action.target_page, frontend_action.target_page),
            "reason": frontend_action.reason,
            "should_end_conversation": frontend_action.should_end_conversation,
            "params": frontend_action.payload,
        }

    @staticmethod
    def _should_emit_page_state(
        *,
        decision: FlowDecision,
        cards: list[ProductCard],
        alternatives: list[CandidateProduct],
        tool_result: ToolExecutionResult | None,
        qa_result: ProductQAResult | None,
        scene_plan: ScenePlan | None,
        frontend_action: FrontendActionDecision,
    ) -> bool:
        if frontend_action.target_page not in {"chat", "product_list"}:
            return True
        if decision.flow in {DialogueFlow.CHECKOUT}:
            return True
        # Product cards, clarification options and ordinary cart updates already
        # carry the data the client needs. Avoid repeating the same state unless
        # a real page-level transition or checkout preview is involved.
        return False

    def _build_page_state(
        self,
        *,
        session_id: str,
        user_id: str,
        state: SessionState,
        parsed_query: ParsedQuery,
        decision: FlowDecision,
        frontend_action: FrontendActionDecision,
        scene_plan: ScenePlan | None,
    ) -> dict[str, Any]:
        return {
            "中文说明": "页面上的非对话性状态，前端可用于更新角标、筛选条件和当前展示模块。",
            "session_id": session_id,
            "user_id": user_id,
            "current_flow": decision.flow.value,
            "current_intent": parsed_query.intent,
            "current_category": state.dialogue_state_tracking.current_category,
            "current_sub_category": state.dialogue_state_tracking.current_sub_category,
            "active_constraints": state.dialogue_state_tracking.active_constraints,
            "cart_badge_count": sum(item.quantity for item in state.cart.items),
            "recommended_product_ids": [item.sku_id for item in state.goods.last_recommendations],
            "scene": scene_plan.scenario if scene_plan else None,
            "frontend_action": frontend_action.model_dump(),
        }

    def _build_system_debug(
        self,
        *,
        session_id: str,
        user_id: str,
        parsed_query: ParsedQuery,
        decision: FlowDecision,
        state_before: dict[str, Any],
        state_after: SessionState,
        trace_payload: dict[str, Any],
        tool_result: ToolExecutionResult | None,
        frontend_action: FrontendActionDecision,
        history_restored: bool,
        restored_from_session_id: str | None,
        legacy_sse_events: list[str],
    ) -> dict[str, Any]:
        model_route = trace_payload.get("model_route", {})
        runtime_timings = trace_payload.get("runtime_timings", {}) or {}
        model_call_summary = runtime_timings.get("模型调用", {}) or {}
        model_call_details = model_call_summary.get("明细", []) or []
        has_model_call = bool(trace_payload.get("llm_called")) or bool(model_call_summary.get("调用次数"))
        has_doubao_call = (
            model_route.get("llm_provider") == "DoubaoClient"
            and (
                bool(trace_payload.get("llm_called"))
                or any(item.get("provider") == "DoubaoClient" for item in model_call_details)
            )
        )
        model_call_purposes = list(
            dict.fromkeys(
                [
                    *model_route.get("llm_tasks", []),
                    *[item.get("purpose") for item in model_call_details if item.get("purpose")],
                ]
            )
        )
        return {
            "中文说明": "本部分用于后端调试，展示本轮对话中系统内部状态、记忆、检索和任务执行情况。",
            "当前轮次分析": {
                "session_id": session_id,
                "user_id": user_id,
                "意图": parsed_query.intent,
                "业务流程": decision.flow.value,
                "商品类别": parsed_query.category,
                "商品子类": parsed_query.sub_category,
                "价格约束": parsed_query.price_range.model_dump(),
                "正向偏好": parsed_query.positive_constraints,
                "否定约束": parsed_query.negative_constraints,
                "包含品牌": parsed_query.brands_include,
                "排除品牌": parsed_query.brands_exclude,
                "是否需要检索": decision.need_retrieval,
                "是否调用大模型": has_model_call,
            },
            "Doubao意图计划": {
                "中文说明": "Doubao 返回并被系统解析后的 IntentPlan。steps 表示本轮多个动作的执行顺序；requires_tool 为工具动作，requires_retrieval 为需要商品检索/推荐的动作。",
                "内容": (trace_payload.get("parsed_query", {}) or {}).get("intent_plan"),
            },
            "对话状态变化": {
                "变化前": state_before,
                "变化后": self._state_summary(state_after),
            },
            "记忆变化": {
                "短期记忆": {
                    "中文说明": "记录当前会话最近消息和最近推荐商品。",
                    "最近消息数": len(state_after.recent_messages),
                    "最近推荐商品": [item.model_dump() for item in state_after.goods.last_recommendations],
                    "可解析指代数量": len(state_after.dialogue_state_tracking.resolved_references),
                },
                "事件记忆": self._event_memory_debug(state_after),
                "长期记忆": {
                    "中文说明": "用户画像和长期偏好只来自明确表达或历史摘要，不强行推断敏感信息。",
                    "用户画像摘要": state_after.user_profile_summary_text,
                    "结构化用户画像": state_after.user_profile_structured,
                    "显式长期偏好": state_after.user.model_dump(),
                },
                "更新字段": trace_payload.get("memory_update_keys", []),
            },
            "事件级记忆": self._event_level_memory_debug(trace_payload, state_after),
            "运行耗时统计": runtime_timings,
            "Progress事件": self._progress_debug(trace_payload),
            "进度事件": self._progress_debug(trace_payload),
            "购物车商品侧个性化": self._cart_personalization_debug(trace_payload),
            "商品增强字段使用": self._product_enhancement_debug(trace_payload),
            "回复策略": self._response_strategy_debug(trace_payload),
            "个性化分析": self._personalization_debug(trace_payload),
            "隐私保护": self._privacy_debug(trace_payload, state_after),
            "层次记忆": self._hierarchical_memory_debug(trace_payload, state_after),
            "多模态分析": self._multimodal_debug(trace_payload),
            "RAG检索过程": {
                "检索方式": self._retrieval_methods(model_route) if decision.need_retrieval else ["本轮未执行商品检索"],
                "召回商品数量": len(trace_payload.get("retrieved_product_ids", [])),
                "召回商品ID": trace_payload.get("retrieved_product_ids", [])[:20],
                "过滤商品数量": len(trace_payload.get("filtered_product_ids", [])),
                "过滤商品ID样例": trace_payload.get("filtered_product_ids", [])[:20],
                "最终推荐商品ID": trace_payload.get("selected_product_ids", []),
                "检索评分摘要": trace_payload.get("retrieval_scores", [])[:5],
            },
            "工具执行": trace_payload.get("tool_calls", []),
            "模型调用": {
                "LLM是否调用": has_model_call,
                "Doubao是否真实调用": has_doubao_call,
                "调用客户端": model_route.get("llm_provider"),
                "调用目的": model_call_purposes,
                "模型调用次数": model_call_summary.get("调用次数", 0),
                "模型调用总耗时_ms": model_call_summary.get("总耗时_ms", 0),
                "本地小模型任务": model_route.get("small_model_tasks", []),
                "前端动作决策来源": frontend_action.source,
            },
            "输出校验": trace_payload.get("validation_result", {}),
            "历史恢复状态": {
                "中文说明": "说明本轮是否从用户历史会话中恢复上下文。",
                "是否恢复": history_restored,
                "恢复的用户": user_id if history_restored else None,
                "恢复的会话": restored_from_session_id,
                "恢复后的当前类别": state_after.dialogue_state_tracking.current_category if history_restored else None,
                "恢复后的候选商品": [item.sku_id for item in state_after.goods.last_candidates] if history_restored else [],
            },
            "前端动作决策": frontend_action.model_dump(),
            "原始SSE事件": legacy_sse_events,
        }

    @staticmethod
    def _personalization_debug(trace_payload: dict[str, Any]) -> dict[str, Any]:
        context = trace_payload.get("personalization_context") or {}
        return {
            "中文说明": "展示本轮回复中使用了哪些用户历史和个性化信息。该部分只用于调试，不展示给普通用户。",
            "是否启用个性化": bool(context.get("是否启用个性化")),
            "使用的用户画像摘要": context.get("用户画像摘要"),
            "领域导购风格": context.get("领域导购风格", {}),
            "本轮选中的历史证据": context.get("本轮相关历史证据", [])[:5],
            "本轮使用的few-shot示例": context.get("few_shot示例", [])[:3],
            "相似人群参考": context.get("相似人群参考", {}),
            "相似历史用户协同过滤": context.get("相似历史用户协同过滤", {}),
            "个性化生成策略": context.get("个性化生成策略"),
            "用户画像更新": context.get("用户画像更新候选", {}),
            "新用户冷启动": context.get("新用户冷启动", {}),
        }

    @staticmethod
    def _response_strategy_debug(trace_payload: dict[str, Any]) -> dict[str, Any]:
        strategy = trace_payload.get("response_strategy") or {}
        return {
            "中文说明": "记录本轮回复采用的导购话术策略，用于检查是否积极、简短、grounded。",
            "匹配状态": strategy.get("匹配状态"),
            "是否启用积极回复": strategy.get("是否启用积极回复", True),
            "是否避免否定开头": strategy.get("是否避免否定开头", True),
            "长度策略": strategy.get("长度策略"),
            "使用的个性化参考": strategy.get("使用的个性化参考", []),
            "当前轮需求优先级": strategy.get("当前轮需求优先级"),
            "事实约束": strategy.get("事实约束"),
        }

    @staticmethod
    def _progress_debug(trace_payload: dict[str, Any]) -> dict[str, Any]:
        plan = trace_payload.get("progress_plan") or {}
        timings = trace_payload.get("runtime_timings") or {}
        planned_events = plan.get("events", [])
        emitted_count = plan.get("已输出数量")
        if emitted_count is None:
            emitted_count = len(planned_events)
        return {
            "中文说明": "展示本轮为了减少前端等待感而预测并发送的 progress events。",
            "预测工作类型": plan.get("预测工作类型", []),
            "预计耗时等级": plan.get("预计耗时等级"),
            "是否启用progress": plan.get("是否启用progress", bool(plan.get("events"))),
            "是否并行启动": bool(plan.get("是否并行启动")),
            "是否老用户": bool(plan.get("是否老用户")),
            "生成时机": plan.get("生成时机"),
            "本地快速生成": bool(plan.get("本地快速生成")),
            "目标首次发送_ms": plan.get("目标首次发送_ms"),
            "首条progress输出耗时_ms": plan.get("首条progress输出耗时_ms"),
            "首次progress生成耗时_ms": plan.get("首次progress生成耗时_ms"),
            "progress输出间隔_ms": plan.get("progress输出间隔_ms"),
            "已输出数量": plan.get("已输出数量"),
            "停止原因": plan.get("停止原因"),
            "实际总耗时_ms": timings.get("total_duration_ms"),
            "最终主流程耗时_ms": plan.get("最终主流程耗时_ms"),
            "使用的progress模板": plan.get("progress模板", []),
            "计划progress事件数量": len(planned_events),
            "progress事件数量": emitted_count,
            "实际输出progress事件数量": emitted_count,
            "events": planned_events,
        }

    @staticmethod
    def _cart_personalization_debug(trace_payload: dict[str, Any]) -> dict[str, Any]:
        context = trace_payload.get("cart_personalization") or {}
        return {
            "中文说明": "展示购物车商品侧个性化如何作为软约束影响本轮排序。当前用户明确需求仍是硬约束。",
            "是否启用": bool(context.get("是否启用")),
            "禁用原因": context.get("禁用原因"),
            "目标类目": context.get("目标类目"),
            "参考购物车商品": context.get("参考购物车商品", []),
            "忽略的非同类购物车商品": context.get("忽略的非同类购物车商品", []),
            "商品标签": context.get("商品标签", []),
            "价格画像": context.get("价格画像", {}),
            "库存覆盖": context.get("库存覆盖", {}),
            "命中的本地规则": context.get("命中的本地规则", []),
            "是否调用Doubao": bool(context.get("是否调用Doubao")),
            "是否需要复杂搭配分析": bool(context.get("是否需要复杂搭配分析")),
            "复杂搭配分析处理方式": context.get("复杂搭配分析处理方式"),
            "排序影响": context.get("排序影响", []),
        }

    @staticmethod
    def _product_enhancement_debug(trace_payload: dict[str, Any]) -> dict[str, Any]:
        context = trace_payload.get("product_enhancement") or {}
        return {
            "中文说明": "展示本轮如何使用商品增强字段参与 query enhancement、召回重排、推荐理由、详情问答和比较事实。",
            "是否启用": bool(context.get("是否启用")),
            "使用的增强字段": context.get("使用的增强字段", []),
            "命中的非标准问题标签": context.get("命中的非标准问题标签", []),
            "命中的适用场景": context.get("命中的适用场景", []),
            "命中的人群标签": context.get("命中的人群标签", []),
            "排序影响": context.get("排序影响", []),
        }

    @staticmethod
    def _multimodal_debug(trace_payload: dict[str, Any]) -> dict[str, Any]:
        context = trace_payload.get("multimodal_context") or {}
        return {
            "中文说明": "展示本轮图片输入、视觉分析和图文融合查询过程。该部分只用于调试，不展示给普通用户。",
            "是否启用多模态": bool(context.get("是否启用多模态")),
            "图片输入": context.get("图片输入", {}),
            "图片理解结果": context.get("图片理解结果", {}),
            "图文融合查询": context.get("图文融合查询", {}),
            "视觉匹配商品": context.get("视觉匹配商品", {}),
            "库存匹配判断": context.get("库存匹配判断", {}),
        }

    @staticmethod
    def _privacy_debug(trace_payload: dict[str, Any], state_after: SessionState) -> dict[str, Any]:
        context = trace_payload.get("personalization_context") or {}
        settings = context.get("隐私设置") or {}
        return {
            "中文说明": "展示本轮个性化是否受到隐私设置约束。普通用户页面不展示。",
            "个性化模式": settings.get("personalization_mode", "full"),
            "是否允许个性化": settings.get("personalization_enabled", True),
            "是否允许使用历史原文做个性化": settings.get("use_raw_history_for_personalization", True),
            "是否仅使用语义摘要": settings.get("semantic_memory_only", False),
            "是否保存原始历史": settings.get("store_raw_history", True),
        }

    @staticmethod
    def _hierarchical_memory_debug(trace_payload: dict[str, Any], state_after: SessionState) -> dict[str, Any]:
        context = trace_payload.get("personalization_context") or {}
        update = context.get("用户画像更新候选", {})
        return {
            "中文说明": "展示短期记忆向长期语义记忆晋升的候选观察。具体长期结果保存在本地 profile.json。",
            "短期会话消息数": len(state_after.recent_messages),
            "最近推荐商品数": len(state_after.goods.last_recommendations),
            "本轮是否产生晋升候选": bool(update.get("是否更新")),
            "本轮晋升候选观察": update.get("新增观察", []),
        }

    @staticmethod
    def _event_memory_debug(state_after: SessionState) -> dict[str, Any]:
        event_memory = state_after.event_memory
        active_recommendation = None
        for event in reversed(event_memory.recommendation_events):
            if event.event_id == event_memory.active_recommendation_event_id:
                active_recommendation = event
                break
        if active_recommendation is None and event_memory.recommendation_events:
            active_recommendation = event_memory.recommendation_events[-1]
        return {
            "中文说明": "事件记忆用于稳定保存一次业务动作本身，尤其是推荐列表顺序，避免用户说“第一款/第二个”时被后续详情页覆盖。",
            "当前推荐事件": {
                "event_id": active_recommendation.event_id if active_recommendation else None,
                "query_id": active_recommendation.query_id if active_recommendation else None,
                "rank_to_sku": active_recommendation.rank_to_sku if active_recommendation else {},
            },
            "最近统一事件": [item.model_dump() for item in state_after.memory_events[-5:]],
            "当前详情商品": event_memory.active_detail_sku_id,
            "最近对比商品": state_after.goods.compared_skus,
            "最近购物车相关商品": event_memory.active_cart_sku_id,
        }

    @staticmethod
    def _event_level_memory_debug(trace_payload: dict[str, Any], state_after: SessionState) -> dict[str, Any]:
        latest_event = state_after.memory_events[-1] if state_after.memory_events else None
        latest_recommendation = next(
            (event for event in reversed(state_after.memory_events) if event.event_type == "recommendation"),
            None,
        )
        reference_resolution = trace_payload.get("reference_resolution") or {}
        raw_query = trace_payload.get("raw_query")
        current_turn_written = bool(latest_event and (not raw_query or latest_event.user_query == raw_query))
        return {
            "是否启用": True,
            "本轮是否写入事件": current_turn_written,
            "写入事件类型": latest_event.event_type if current_turn_written and latest_event else None,
            "最近事件ID": latest_event.event_id if latest_event else None,
            "最近推荐事件ID": latest_recommendation.event_id if latest_recommendation else None,
            "最近推荐事件rank映射": (latest_recommendation.payload.get("rank_to_sku", {}) if latest_recommendation else {}),
            "本轮指代解析来源": reference_resolution.get("source", "failed"),
            "本轮解析出的商品ID": reference_resolution.get("product_ids", []),
            "本轮解析明细": {
                "source_event_id": reference_resolution.get("source_event_id"),
                "resolved": reference_resolution.get("resolved", {}),
                "reference_texts": reference_resolution.get("reference_texts", []),
                "confidence": reference_resolution.get("confidence", 0.0),
            },
        }

    @staticmethod
    def _retrieval_methods(model_route: dict[str, Any]) -> list[str]:
        methods = ["结构化过滤", "关键词匹配", "属性/约束匹配"]
        small_tasks = model_route.get("small_model_tasks", [])
        local_enabled = bool(model_route.get("local_model_status", {}).get("enabled", True))
        if local_enabled and "bge_embedding_recall" in small_tasks:
            methods.append("BGE向量召回")
        if local_enabled and "text2vec_semantic_recall" in small_tasks:
            methods.append("text2vec语义召回")
        if local_enabled and "bge_reranker" in small_tasks:
            methods.append("BGE重排序")
        return methods

    @staticmethod
    def _state_summary(state: SessionState) -> dict[str, Any]:
        dialogue = state.dialogue_state_tracking
        return {
            "当前流程": dialogue.current_flow,
            "当前意图": dialogue.current_intent,
            "当前类别": dialogue.current_category,
            "当前子类": dialogue.current_sub_category,
            "活跃约束": dialogue.active_constraints,
            "缺失槽位": dialogue.missing_slots,
            "购物车数量": sum(item.quantity for item in state.cart.items),
            "最近推荐商品": [item.sku_id for item in state.goods.last_recommendations],
        }

    @staticmethod
    def _candidate_to_card_like(candidate: CandidateProduct) -> dict[str, Any]:
        meaningful = [
            item.removeprefix("匹配") for item in candidate.matched_reasons
            if item and item not in {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选"}
        ][:3]
        if candidate.score < 0.5:
            if meaningful:
                reason = f"这款更适合作为备选，主要可取点是{'、'.join(meaningful)}，可以先点开确认细节。"
            else:
                reason = "这款更适合作为备选，来自当前相关类目，可以先点开确认细节。"
        elif meaningful:
            reason = f"这款比较贴合你对{'、'.join(meaningful)}的要求，适合优先查看。"
        elif candidate.sub_category:
            reason = f"这款属于{candidate.sub_category}类目，和你当前想看的方向比较接近。"
        else:
            reason = "这款来自当前商品库的真实匹配结果，可以进一步查看。"
        return {
            "sku_id": candidate.sku_id,
            "product_id": candidate.product_id,
            "name": candidate.name,
            "category": candidate.category,
            "sub_category": candidate.sub_category,
            "brand": candidate.brand,
            "price": candidate.price,
            "image_url": candidate.image_url,
            "reason": reason,
            "score": candidate.score,
        }
