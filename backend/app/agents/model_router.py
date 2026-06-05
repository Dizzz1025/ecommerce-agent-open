from app.models.agent import DialogueFlow, FlowDecision, ModelRouteDecision, ParsedQuery
from app.ml.local_models import LocalModelManager


class ModelRouter:
    """Decides rule/template/small-local/LLM handling for the current turn."""

    def __init__(self, local_models: LocalModelManager | None = None) -> None:
        self.local_models = local_models

    def route(self, parsed_query: ParsedQuery, decision: FlowDecision) -> ModelRouteDecision:
        flow = decision.flow
        small_model_tasks = self._small_model_tasks(parsed_query, decision)
        local_model_status = self.local_models.status() if self.local_models else {}
        if flow in {DialogueFlow.GREETING, DialogueFlow.CHITCHAT, DialogueFlow.OUT_OF_SCOPE, DialogueFlow.INVALID}:
            return ModelRouteDecision(
                difficulty="simple",
                need_llm=False,
                primary_handler="template",
                reason="简单问候、无效输入或非导购问题，模板即可",
                small_model_tasks=small_model_tasks,
                local_model_status=local_model_status,
            )
        if flow in {DialogueFlow.CART_ACTION, DialogueFlow.CHECKOUT, DialogueFlow.PREFERENCE_UPDATE}:
            return ModelRouteDecision(
                difficulty="simple_structured",
                need_llm=False,
                primary_handler="tool_or_memory",
                reason="确定性工具或 memory 写入由后端代码执行",
                small_model_tasks=small_model_tasks,
                local_model_status=local_model_status,
            )
        if flow == DialogueFlow.CLARIFICATION:
            return ModelRouteDecision(
                difficulty="simple_structured",
                need_llm=False,
                primary_handler="clarification_template",
                reason="缺失槽位明确，用本地澄清模板",
                small_model_tasks=small_model_tasks,
                local_model_status=local_model_status,
            )
        if flow in {DialogueFlow.COMPARISON, DialogueFlow.PRODUCT_QA, DialogueFlow.DETAIL}:
            return ModelRouteDecision(
                difficulty="complex_context",
                need_llm=True,
                primary_handler="retrieval_plus_llm",
                reason="需要读取商品事实、历史指代并组织解释",
                llm_tasks=["generate_response"],
                small_model_tasks=small_model_tasks,
                local_model_status=local_model_status,
            )
        if flow == DialogueFlow.SCENE_BUNDLE:
            return ModelRouteDecision(
                difficulty="complex_semantic",
                need_llm=True,
                primary_handler="scene_planner_plus_llm",
                reason="场景化需求需要拆分子需求并生成组合解释",
                llm_tasks=["scene_explanation", "generate_response"],
                small_model_tasks=small_model_tasks,
                local_model_status=local_model_status,
            )
        if parsed_query.confidence < 0.68:
            return ModelRouteDecision(
                difficulty="uncertain",
                need_llm=True,
                primary_handler="llm_fallback",
                reason="规则置信度较低，需要 LLM 辅助表达或澄清",
                llm_tasks=["generate_response"],
                small_model_tasks=small_model_tasks,
                local_model_status=local_model_status,
            )
        if parsed_query.price_range.max is not None or parsed_query.brands_exclude or parsed_query.brands_include:
            return ModelRouteDecision(
                difficulty="medium_structured",
                need_llm=True,
                primary_handler="retrieval_plus_llm",
                reason="结构化条件由后端硬过滤，最终导购话术交给 LLM 结合 RAG 结果生成",
                llm_tasks=["generate_response"],
                small_model_tasks=small_model_tasks,
                local_model_status=local_model_status,
            )
        return ModelRouteDecision(
            difficulty="medium",
            need_llm=True,
            primary_handler="retrieval_plus_llm",
            reason="推荐理由需要自然语言组织，但事实由 RAG 约束",
            llm_tasks=["generate_response"],
            small_model_tasks=small_model_tasks,
            local_model_status=local_model_status,
        )

    @staticmethod
    def _small_model_tasks(parsed_query: ParsedQuery, decision: FlowDecision) -> list[str]:
        tasks: list[str] = []
        if "text2vec_intent" in parsed_query.route_source:
            tasks.append("text2vec_intent_classification")
        if "text2vec_category" in parsed_query.route_source:
            tasks.append("text2vec_category_classification")
        if decision.need_retrieval:
            tasks.extend(["bge_embedding_recall", "text2vec_semantic_recall", "bge_reranker"])
        return tasks
