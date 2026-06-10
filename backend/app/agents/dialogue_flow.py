from app.models.agent import DialogueFlow, FlowDecision, ParsedQuery
from app.models.domain import IntentType, SessionState


class DialogueFlowController:
    """Small state machine that decides which business flow owns the turn."""

    def decide(self, parsed: ParsedQuery, state: SessionState) -> FlowDecision:
        intent = parsed.intent
        if intent == IntentType.INVALID.value:
            return FlowDecision(flow=DialogueFlow.INVALID, reason="无效输入", need_retrieval=False, need_llm=False)
        if intent == IntentType.OUT_OF_SCOPE.value:
            return FlowDecision(flow=DialogueFlow.OUT_OF_SCOPE, reason="非导购或超出商品库范围", need_retrieval=False, need_llm=False)
        if intent in {
            IntentType.CART_ADD.value,
            IntentType.CART_REMOVE.value,
            IntentType.CART_UPDATE.value,
            IntentType.CART_CLEAR.value,
            IntentType.CART_VIEW.value,
            IntentType.CART_KEEP_ONLY.value,
            IntentType.CHECKOUT.value,
        }:
            return FlowDecision(
                flow=DialogueFlow.CHECKOUT if intent == IntentType.CHECKOUT.value else DialogueFlow.CART_ACTION,
                reason="用户表达了确定性购物车或结算动作",
                need_retrieval=False,
                need_llm=False,
            )
        if intent == IntentType.PREFERENCE.value:
            if (
                parsed.category
                or state.dialogue_state_tracking.current_category
                or parsed.positive_constraints
                or parsed.negative_constraints
                or parsed.price_range.min is not None
                or parsed.price_range.max is not None
                or parsed.brands_include
                or parsed.brands_exclude
            ):
                return FlowDecision(
                    flow=DialogueFlow.REFINEMENT if parsed.inherit_context or state.dialogue_state_tracking.current_category else DialogueFlow.RECOMMENDATION,
                    reason="用户表达偏好，同时存在可推进的商品需求，先保存偏好并继续推荐",
                    need_retrieval=True,
                    need_llm=True,
                )
            return FlowDecision(
                flow=DialogueFlow.PREFERENCE_UPDATE,
                reason="用户表达了可写入长期记忆的稳定偏好",
                need_retrieval=False,
                need_llm=False,
            )
        if intent == IntentType.CHITCHAT.value:
            return FlowDecision(
                flow=DialogueFlow.CHITCHAT,
                reason="非电商闲聊或寒暄",
                need_retrieval=False,
                need_llm=False,
            )
        if intent == IntentType.COMPARE.value:
            return FlowDecision(
                flow=DialogueFlow.COMPARISON,
                reason="用户要求比较两个或多个商品",
                need_retrieval=True,
                need_llm=True,
            )
        if intent == IntentType.DETAIL.value:
            return FlowDecision(
                flow=DialogueFlow.PRODUCT_QA,
                reason="用户要求查看或解释商品详情",
                need_retrieval=True,
                need_llm=True,
            )
        if intent == IntentType.SCENE_BUNDLE.value:
            return FlowDecision(
                flow=DialogueFlow.SCENE_BUNDLE,
                reason="用户提出场景化组合需求",
                need_retrieval=True,
                need_llm=True,
            )
        if parsed.need_clarification:
            return FlowDecision(
                flow=DialogueFlow.CLARIFICATION,
                reason="类目、用途或关键偏好不足，先主动澄清",
                need_retrieval=False,
                need_llm=False,
                missing_slots=parsed.clarification_slots,
            )
        if (parsed.inherit_context or intent == IntentType.REFINE.value) and (
            parsed.price_range.min is not None or parsed.price_range.max is not None
        ):
            return FlowDecision(
                flow=DialogueFlow.REFINEMENT,
                reason="用户在上一轮基础上调整预算或价格接受范围",
                need_retrieval=True,
                need_llm=True,
            )
        if parsed.negative_constraints or parsed.brands_exclude:
            return FlowDecision(
                flow=DialogueFlow.EXCLUSION,
                reason="用户提供了否定约束，需要硬过滤",
                need_retrieval=True,
                need_llm=True,
            )
        if parsed.inherit_context or intent == IntentType.REFINE.value:
            return FlowDecision(
                flow=DialogueFlow.REFINEMENT,
                reason="用户在上一轮推荐基础上继续细化",
                need_retrieval=True,
                need_llm=True,
            )
        if intent == IntentType.FILTER.value or parsed.price_range.max is not None or parsed.brands_include:
            return FlowDecision(
                flow=DialogueFlow.FILTERING,
                reason="用户给出结构化筛选条件",
                need_retrieval=True,
                need_llm=True,
            )
        return FlowDecision(
            flow=DialogueFlow.RECOMMENDATION,
            reason="默认导购推荐流程",
            need_retrieval=True,
            need_llm=True,
        )
