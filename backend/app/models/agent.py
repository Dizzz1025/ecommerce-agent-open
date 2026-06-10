from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DialogueFlow(StrEnum):
    GREETING = "greeting"
    RECOMMENDATION = "recommendation"
    FILTERING = "filtering"
    REFINEMENT = "refinement"
    CLARIFICATION = "clarification"
    EXCLUSION = "exclusion"
    COMPARISON = "comparison"
    PRODUCT_QA = "product_qa"
    SCENE_BUNDLE = "scene_bundle"
    CART_ACTION = "cart_action"
    CHECKOUT = "checkout"
    PREFERENCE_UPDATE = "preference_update"
    NO_RESULT = "no_result"
    CHITCHAT = "chitchat"
    OUT_OF_SCOPE = "out_of_scope"
    INVALID = "invalid"
    DETAIL = "detail"


class TaskType(StrEnum):
    PREPROCESS_INPUT = "preprocess_input"
    ROUTE_MODEL = "route_model"
    MERGE_CONTEXT = "merge_context"
    EXTRACT_CONSTRAINTS = "extract_constraints"
    RESOLVE_REFERENCE = "resolve_reference"
    REWRITE_QUERY = "rewrite_query"
    RETRIEVE_PRODUCTS = "retrieve_products"
    FILTER_PRODUCTS = "filter_products"
    RERANK_PRODUCTS = "rerank_products"
    COMPARE_PRODUCTS = "compare_products"
    ANSWER_PRODUCT_QUESTION = "answer_product_question"
    PLAN_SCENE_BUNDLE = "plan_scene_bundle"
    CLARIFY_USER_NEED = "clarify_user_need"
    EXECUTE_CART_ACTION = "execute_cart_action"
    SAVE_USER_PREFERENCE = "save_user_preference"
    GENERATE_RESPONSE = "generate_response"
    UPDATE_MEMORY = "update_memory"
    VALIDATE_RESPONSE = "validate_response"
    DISPATCH_FRONTEND_EVENTS = "dispatch_frontend_events"


class PriceRange(BaseModel):
    min: float | None = None
    max: float | None = None


class CartAction(BaseModel):
    action: str
    quantity: int | None = None
    target_ref: str | None = None
    sku_id: str | None = None
    keep_categories: list[str] = Field(default_factory=list)
    keep_sub_categories: list[str] = Field(default_factory=list)
    exclude_sku_ids: list[str] = Field(default_factory=list)


class IntentStep(BaseModel):
    step: int
    intent: str
    action: str | None = None
    source_text: str = ""
    target_ref: str | None = None
    quantity: int | None = None
    sku_id: str | None = None
    keep_categories: list[str] = Field(default_factory=list)
    keep_sub_categories: list[str] = Field(default_factory=list)
    exclude_sku_ids: list[str] = Field(default_factory=list)
    requires_tool: bool = False
    requires_retrieval: bool = False


class IntentPlan(BaseModel):
    primary_intent: str
    steps: list[IntentStep] = Field(default_factory=list)
    is_multi_intent: bool = False
    needs_llm_resolution: bool = False
    resolution_source: str = "rule"
    confidence: float = 0.0
    reason: str = ""


class ParsedQuery(BaseModel):
    raw_message: str
    intent: str
    category: str | None = None
    sub_category: str | None = None
    price_range: PriceRange = Field(default_factory=PriceRange)
    positive_constraints: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    brands_include: list[str] = Field(default_factory=list)
    brands_exclude: list[str] = Field(default_factory=list)
    compare_targets: list[str] = Field(default_factory=list)
    cart_action: CartAction | None = None
    referents: list[str] = Field(default_factory=list)
    mentioned_products: list[str] = Field(default_factory=list)
    scenario: str | None = None
    target_user: str | None = None
    sub_intent: str | None = None
    rewritten_query: str = ""
    need_clarification: bool = False
    clarification_slots: list[str] = Field(default_factory=list)
    inherit_context: bool = False
    confidence: float = 0.0
    route_source: str = "rule"
    uncertain_points: list[str] = Field(default_factory=list)
    intent_plan: IntentPlan | None = None


class FlowDecision(BaseModel):
    flow: DialogueFlow
    reason: str
    need_retrieval: bool = False
    need_llm: bool = False
    missing_slots: list[str] = Field(default_factory=list)


class PlannedTask(BaseModel):
    task_type: TaskType
    description: str
    local: bool = True
    data_access: bool = False
    llm_call: bool = False


class TaskPlan(BaseModel):
    flow: DialogueFlow
    tasks: list[PlannedTask] = Field(default_factory=list)

    @property
    def task_names(self) -> list[str]:
        return [task.task_type.value for task in self.tasks]


class RetrievalFilters(BaseModel):
    category: str | None = None
    sub_category: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    brands_include: list[str] = Field(default_factory=list)
    brands_exclude: list[str] = Field(default_factory=list)
    positive_constraints: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)


class CandidateProduct(BaseModel):
    candidate_id: str
    product_id: str
    sku_id: str
    name: str
    display_title: str | None = None
    brand: str
    category: str
    sub_category: str | None = None
    price: float
    image_url: str
    matched_reasons: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    violated_constraints: list[str] = Field(default_factory=list)
    displayable: bool = True
    filtered_out: bool = False
    filter_reason: str | None = None
    score: float = 0.0
    raw_scores: dict[str, float] = Field(default_factory=dict)
    enhancement_matches: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    ok: bool
    tool_name: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None


class InputPreprocessResult(BaseModel):
    raw_message: str
    normalized_message: str
    input_type: str = "text"
    valid: bool = True
    reason: str | None = None
    is_repeated: bool = False
    simple_route: str | None = None
    template_reply: str | None = None


class ModelRouteDecision(BaseModel):
    difficulty: str
    need_llm: bool
    primary_handler: str
    reason: str
    llm_tasks: list[str] = Field(default_factory=list)
    small_model_tasks: list[str] = Field(default_factory=list)
    local_model_status: dict[str, Any] = Field(default_factory=dict)


class PreferenceUpdateResult(BaseModel):
    updated: bool = False
    message: str = ""
    updates: dict[str, Any] = Field(default_factory=dict)
    needs_confirmation: bool = False


class ProductQAResult(BaseModel):
    answered: bool
    answer: str
    product_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    missing_field: str | None = None


class SceneSubQuery(BaseModel):
    label: str
    category: str | None = None
    sub_category: str | None = None
    query: str
    reason: str


class ScenePlan(BaseModel):
    scenario: str
    sub_queries: list[SceneSubQuery] = Field(default_factory=list)
    unsupported_needs: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    ok: bool = True
    issues: list[str] = Field(default_factory=list)
    repaired: bool = False


class FrontendActionDecision(BaseModel):
    action: str = "stay_chat"
    target_page: str = "chat"
    should_end_conversation: bool = False
    reason: str = ""
    confidence: float = 0.6
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = "rule"


class UnifiedTurnOutput(BaseModel):
    frontend_events: list[dict[str, Any]] = Field(default_factory=list)
    frontend_data: dict[str, Any] = Field(default_factory=dict)
    system_debug: dict[str, Any] = Field(default_factory=dict)


class AgentTrace(BaseModel):
    session_id: str
    query_id: str
    raw_query: str
    normalized_query: str
    intent: str | None = None
    flow_before: str | None = None
    flow_after: str | None = None
    difficulty: str | None = None
    model_route: dict[str, Any] = Field(default_factory=dict)
    parsed_query: dict[str, Any] = Field(default_factory=dict)
    task_plan: list[str] = Field(default_factory=list)
    retrieved_product_ids: list[str] = Field(default_factory=list)
    selected_product_ids: list[str] = Field(default_factory=list)
    filtered_product_ids: list[str] = Field(default_factory=list)
    retrieval_scores: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    llm_called: bool = False
    memory_read_keys: list[str] = Field(default_factory=list)
    memory_update_keys: list[str] = Field(default_factory=list)
    validation_result: dict[str, Any] = Field(default_factory=dict)
    runtime_timings: dict[str, Any] = Field(default_factory=dict)
    progress_plan: dict[str, Any] = Field(default_factory=dict)
    fallback_result: dict[str, Any] = Field(default_factory=dict)
    cart_personalization: dict[str, Any] = Field(default_factory=dict)
    product_enhancement: dict[str, Any] = Field(default_factory=dict)
    personalization_context: dict[str, Any] = Field(default_factory=dict)
    multimodal_context: dict[str, Any] = Field(default_factory=dict)
    reference_resolution: dict[str, Any] = Field(default_factory=dict)
    response_strategy: dict[str, Any] = Field(default_factory=dict)
    presentation: dict[str, Any] = Field(default_factory=dict)
    frontend_action: dict[str, Any] = Field(default_factory=dict)
    frontend_events: list[dict[str, Any]] = Field(default_factory=list)
    legacy_sse_events: list[str] = Field(default_factory=list)
    unified_output: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
