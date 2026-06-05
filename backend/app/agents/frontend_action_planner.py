from __future__ import annotations

from app.llm.base import BaseLLMClient
from app.models.agent import (
    CandidateProduct,
    DialogueFlow,
    FlowDecision,
    FrontendActionDecision,
    ParsedQuery,
    ProductQAResult,
    ScenePlan,
    ToolExecutionResult,
)
from app.models.domain import ProductCard, SessionState


class FrontendActionPlanner:
    """Decides UI actions after the backend has produced the business result.

    Doubao is used as an optional constrained judge. The final action is still
    validated locally against an allow-list, so a bad model response cannot ask
    the Android client to do arbitrary work.
    """

    _allowed_actions = {
        "stay_chat",
        "ask_clarification",
        "show_product_list",
        "show_product_detail",
        "show_cart",
        "show_checkout_preview",
        "show_scene_bundle",
        "finish_conversation",
    }
    _allowed_pages = {"chat", "product_list", "product_detail", "cart", "checkout", "scenario"}

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def decide(
        self,
        *,
        parsed_query: ParsedQuery,
        decision: FlowDecision,
        state: SessionState,
        cards: list[ProductCard],
        candidates: list[CandidateProduct],
        response_text: str,
        tool_result: ToolExecutionResult | None = None,
        qa_result: ProductQAResult | None = None,
        scene_plan: ScenePlan | None = None,
    ) -> FrontendActionDecision:
        fallback = self._rule_decision(
            parsed_query=parsed_query,
            decision=decision,
            cards=cards,
            tool_result=tool_result,
            qa_result=qa_result,
            scene_plan=scene_plan,
        )
        return self._enforce_navigation_policy(
            fallback,
            parsed_query=parsed_query,
            decision=decision,
            tool_result=tool_result,
            qa_result=qa_result,
        )

    def _rule_decision(
        self,
        *,
        parsed_query: ParsedQuery,
        decision: FlowDecision,
        cards: list[ProductCard],
        tool_result: ToolExecutionResult | None,
        qa_result: ProductQAResult | None,
        scene_plan: ScenePlan | None,
    ) -> FrontendActionDecision:
        if decision.flow == DialogueFlow.CLARIFICATION:
            return FrontendActionDecision(
                action="ask_clarification",
                target_page="chat",
                reason="需要用户补充关键信息",
                confidence=0.95,
                payload={"missing_slots": decision.missing_slots},
            )
        if decision.flow == DialogueFlow.SCENE_BUNDLE:
            return FrontendActionDecision(
                action="show_scene_bundle",
                target_page="chat",
                reason="场景化组合推荐需要展示方案和多商品卡片",
                confidence=0.9,
                payload={"scenario": scene_plan.scenario if scene_plan else None},
            )
        if decision.flow == DialogueFlow.PRODUCT_QA and qa_result:
            return FrontendActionDecision(
                action="show_product_detail",
                target_page="product_detail" if self._explicit_product_detail_navigation(parsed_query.raw_message) else "chat",
                reason="用户正在询问具体商品详情",
                confidence=0.86,
                payload={"product_ids": qa_result.product_ids},
            )
        if decision.flow == DialogueFlow.CART_ACTION:
            if (
                tool_result
                and tool_result.ok
                and (
                    tool_result.tool_name in {"remove_then_checkout", "mock_checkout"}
                    or bool(tool_result.payload.get("order"))
                )
            ):
                return FrontendActionDecision(
                    action="show_checkout_preview",
                    target_page="checkout" if self._explicit_checkout_navigation(parsed_query.raw_message) else "chat",
                    should_end_conversation=True,
                    reason="用户要求完成购物车操作后直接结算，需要展示订单预览",
                    confidence=0.94,
                    payload=tool_result.payload,
                )
            should_end = any(term in parsed_query.raw_message for term in ["买完", "结束", "就这样", "不用了", "够了", "谢谢", "拜拜"])
            return FrontendActionDecision(
                action="show_cart",
                target_page="cart" if self._explicit_cart_navigation(parsed_query.raw_message) else "chat",
                should_end_conversation=should_end,
                reason="购物车状态发生变化或用户查看购物车",
                confidence=0.92,
                payload=tool_result.payload if tool_result else {},
            )
        if decision.flow == DialogueFlow.CHECKOUT:
            return FrontendActionDecision(
                action="show_checkout_preview",
                target_page="checkout" if self._explicit_checkout_navigation(parsed_query.raw_message) else "chat",
                reason="用户发起结算，需要展示订单预览",
                confidence=0.94,
                payload=tool_result.payload if tool_result else {},
            )
        if cards:
            return FrontendActionDecision(
                action="show_product_list",
                target_page="chat",
                reason="本轮产生了可展示商品卡片",
                confidence=0.88,
                payload={"product_ids": [card.sku_id for card in cards]},
            )
        if decision.flow in {DialogueFlow.GREETING, DialogueFlow.CHITCHAT} and any(term in parsed_query.raw_message for term in ["谢谢", "不用了", "没事了", "先这样"]):
            return FrontendActionDecision(
                action="finish_conversation",
                target_page="chat",
                should_end_conversation=True,
                reason="用户表达了结束当前导购的意图",
                confidence=0.8,
            )
        return FrontendActionDecision(
            action="stay_chat",
            target_page="chat",
            reason="继续留在聊天页等待下一轮输入",
            confidence=0.7,
        )

    def _coerce_model_decision(self, payload: dict, fallback: FrontendActionDecision) -> FrontendActionDecision | None:
        if not payload:
            return None
        action = str(payload.get("action") or "")
        target_page = str(payload.get("target_page") or "")
        if action not in self._allowed_actions or target_page not in self._allowed_pages:
            return None
        try:
            confidence = float(payload.get("confidence", 0.7))
        except (TypeError, ValueError):
            confidence = 0.7
        return FrontendActionDecision(
            action=action,
            target_page=target_page,
            should_end_conversation=bool(payload.get("should_end_conversation", False)),
            reason=str(payload.get("reason") or fallback.reason),
            confidence=max(0.0, min(1.0, confidence)),
            payload=fallback.payload,
            source="doubao",
        )

    def _enforce_navigation_policy(
        self,
        decision_payload: FrontendActionDecision,
        *,
        parsed_query: ParsedQuery,
        decision: FlowDecision,
        tool_result: ToolExecutionResult | None,
        qa_result: ProductQAResult | None,
    ) -> FrontendActionDecision:
        """Keep page navigation user-driven.

        The backend can always send display data such as product cards or cart
        updates, but it should only tell the client to switch pages when the
        user's wording clearly asks for that page or transaction step.
        """

        target_page = decision_payload.target_page
        if target_page in {"chat", "product_list"}:
            return decision_payload

        raw_message = parsed_query.raw_message
        allowed_target = False
        if target_page == "product_detail":
            allowed_target = bool(qa_result) and self._explicit_product_detail_navigation(raw_message)
        elif target_page == "cart":
            allowed_target = self._explicit_cart_navigation(raw_message)
        elif target_page == "checkout":
            allowed_target = bool(tool_result and tool_result.ok) and self._explicit_checkout_navigation(raw_message)
        elif target_page == "scenario":
            allowed_target = self._explicit_scene_navigation(raw_message)

        if allowed_target:
            return decision_payload

        return decision_payload.model_copy(
            update={
                "target_page": "chat",
                "reason": f"{decision_payload.reason}；未识别到用户明确要求切换页面，因此保持在聊天页",
                "source": decision_payload.source,
            }
        )

    @staticmethod
    def _explicit_product_detail_navigation(message: str) -> bool:
        detail_terms = ["详情", "详情页", "商品页", "打开", "点开", "跳转", "进入", "查看", "看看", "看一下"]
        referent_terms = [
            "第一个", "第一款", "第1个", "第1款",
            "第二个", "第二款", "第2个", "第2款",
            "第三个", "第三款", "第3个", "第3款",
            "这款", "这个", "刚才那款", "刚才那个",
        ]
        return any(term in message for term in detail_terms) and any(term in message for term in referent_terms)

    @staticmethod
    def _explicit_cart_navigation(message: str) -> bool:
        cart_page_terms = [
            "查看购物车", "看购物车", "看看购物车", "打开购物车", "去购物车",
            "进入购物车", "跳到购物车", "跳转购物车", "购物车页面", "购物车页",
            "在购物车页面", "到购物车里",
        ]
        return any(term in message for term in cart_page_terms)

    @staticmethod
    def _explicit_checkout_navigation(message: str) -> bool:
        checkout_terms = ["结算", "下单", "付款", "支付", "去付款", "提交订单", "确认订单"]
        return any(term in message for term in checkout_terms)

    @staticmethod
    def _explicit_scene_navigation(message: str) -> bool:
        scene_terms = ["方案页", "清单页", "打开方案", "查看方案", "跳转方案"]
        return any(term in message for term in scene_terms)
