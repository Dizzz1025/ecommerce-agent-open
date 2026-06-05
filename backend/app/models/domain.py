from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IntentType(StrEnum):
    RECOMMEND = "recommend"
    FILTER = "filter"
    REFINE = "refine"
    COMPARE = "compare"
    CLARIFY = "clarify"
    DETAIL = "detail"
    SCENE_BUNDLE = "scene_bundle"
    PREFERENCE = "preference"
    CART_ADD = "cart_add"
    CART_REMOVE = "cart_remove"
    CART_UPDATE = "cart_update"
    CART_CLEAR = "cart_clear"
    CART_VIEW = "cart_view"
    CART_KEEP_ONLY = "cart_keep_only"
    CHECKOUT = "checkout"
    CHITCHAT = "chitchat"
    OUT_OF_SCOPE = "out_of_scope"
    INVALID = "invalid"


class ProductSpotlight(BaseModel):
    skin_type: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    description: str = ""


class ProductSku(BaseModel):
    sku_id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    price: float


class Product(BaseModel):
    # sku_id remains the public identifier used by Android, cart, details, and SSE.
    sku_id: str
    product_id: str | None = None
    name: str
    title: str | None = None
    category: str
    sub_category: str | None = None
    brand: str
    price: float
    base_price: float | None = None
    stock: int
    image_url: str
    image_path: str | None = None
    skus: list[ProductSku] = Field(default_factory=list)
    spotlight: ProductSpotlight = Field(default_factory=ProductSpotlight)
    reviews_summary: str
    rag_knowledge: dict[str, Any] = Field(default_factory=dict)
    product_highlight: str = ""
    highlight_short: str = ""
    highlight_detail: str = ""
    suitable_scenarios: list[str] = Field(default_factory=list)
    target_user_tags: list[str] = Field(default_factory=list)
    non_standard_query_tags: list[str] = Field(default_factory=list)
    searchable_text: str = ""
    tags: list[str] = Field(default_factory=list)


class CartItem(BaseModel):
    sku_id: str
    name: str
    price: float
    quantity: int
    image_url: str


class ProductCard(BaseModel):
    sku_id: str
    product_id: str | None = None
    name: str
    category: str
    sub_category: str | None = None
    brand: str
    price: float
    stock: int
    image_url: str
    reason: str
    highlight_short: str = ""
    suitable_scenarios: list[str] = Field(default_factory=list)
    target_user_tags: list[str] = Field(default_factory=list)
    non_standard_query_tags: list[str] = Field(default_factory=list)
    matched_reasons: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    score: float | None = None
    presentation: "ProductPresentation | None" = None


class ProductPresentation(BaseModel):
    type: str
    option_label: str | None = None
    reason: str | None = None
    trade_off: str | None = None
    summary: str | None = None
    advantages: list[str] = Field(default_factory=list)
    suitable_for: str | None = None
    key_features: list[str] = Field(default_factory=list)
    matched_need: str | None = None
    usage_advice: str | None = None
    bundle_role: str | None = None
    bundle_reason: str | None = None
    usage_scenario: str | None = None
    content_source: str = "fallback"


class ComparisonDimensionItem(BaseModel):
    sku_id: str
    value: str


class ComparisonDimension(BaseModel):
    name: str
    items: list[ComparisonDimensionItem] = Field(default_factory=list)
    better_sku_id: str | None = None


class ComparisonConclusion(BaseModel):
    recommended_sku_id: str | None = None
    reason: str = ""
    alternative_sku_id: str | None = None
    alternative_reason: str | None = None


class ComparisonData(BaseModel):
    dimensions: list[ComparisonDimension] = Field(default_factory=list)
    conclusion: ComparisonConclusion = Field(default_factory=ComparisonConclusion)


class RecommendationRecord(BaseModel):
    rank: int
    sku_id: str
    name: str
    category: str
    query_id: str
    reason: str | None = None
    price: float | None = None


class MemoryEventRecord(BaseModel):
    event_id: str
    event_type: str
    turn_id: int | str | None = None
    timestamp: str
    user_query: str | None = None
    source_event_id: str | None = None
    category: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    related_product_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class ReferenceResolveResult(BaseModel):
    resolved: dict[str, str] = Field(default_factory=dict)
    product_ids: list[str] = Field(default_factory=list)
    source_event_id: str | None = None
    source: str = "failed"
    reference_texts: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class ProductBriefRecord(BaseModel):
    rank: int | None = None
    sku_id: str
    name: str
    category: str | None = None
    sub_category: str | None = None
    price: float | None = None
    reason: str | None = None


class RecommendationEvent(BaseModel):
    event_id: str
    query_id: str
    turn_id: int
    source_message: str
    category: str | None = None
    sub_category: str | None = None
    rank_to_sku: dict[str, str] = Field(default_factory=dict)
    products: list[ProductBriefRecord] = Field(default_factory=list)
    recommendation_mode: str = "exact"
    result_status: str = "exact_match"
    unmet_constraints: dict[str, Any] = Field(default_factory=dict)
    relaxed_constraints: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ProductDetailEvent(BaseModel):
    event_id: str
    query_id: str
    turn_id: int
    source_message: str
    sku_id: str
    target_ref: str | None = None
    source_event_id: str | None = None
    source_rank: int | None = None
    created_at: str


class ComparisonEvent(BaseModel):
    event_id: str
    query_id: str
    turn_id: int
    source_message: str
    sku_ids: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    resolved_references: dict[str, str] = Field(default_factory=dict)
    comparison_dimensions: list[str] = Field(default_factory=list)
    source_event_id: str | None = None
    created_at: str


class CartEvent(BaseModel):
    event_id: str
    query_id: str
    turn_id: int
    source_message: str
    action: str
    sku_ids: list[str] = Field(default_factory=list)
    quantity: int | None = None
    target_ref: str | None = None
    source_event_id: str | None = None
    tool_result: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class EventMemory(BaseModel):
    recommendation_events: list[RecommendationEvent] = Field(default_factory=list)
    product_detail_events: list[ProductDetailEvent] = Field(default_factory=list)
    comparison_events: list[ComparisonEvent] = Field(default_factory=list)
    cart_events: list[CartEvent] = Field(default_factory=list)
    active_recommendation_event_id: str | None = None
    active_detail_sku_id: str | None = None
    active_comparison_event_id: str | None = None
    active_cart_sku_id: str | None = None


class GlobalPreferences(BaseModel):
    price_preference: str | None = None
    preferred_brands: list[str] = Field(default_factory=list)
    excluded_brands: list[str] = Field(default_factory=list)
    preferred_style: list[str] = Field(default_factory=list)
    avoid_terms: list[str] = Field(default_factory=list)


def _default_category_preferences() -> dict[str, dict[str, Any]]:
    return {
        "beauty_skincare": {},
        "electronics": {},
        "shoes": {},
        "clothing": {},
        "food": {},
    }


class UserPreferences(BaseModel):
    global_preferences: GlobalPreferences = Field(default_factory=GlobalPreferences)
    category_preferences: dict[str, dict[str, Any]] = Field(default_factory=_default_category_preferences)


class GoodsContext(BaseModel):
    last_recommendations: list[RecommendationRecord] = Field(default_factory=list)
    last_candidates: list[RecommendationRecord] = Field(default_factory=list)
    viewed_skus: list[str] = Field(default_factory=list)
    compared_skus: list[str] = Field(default_factory=list)


class ConversationTurn(BaseModel):
    role: str
    content: str
    timestamp: str


class BehaviourRecord(BaseModel):
    turn_id: int
    intent: str
    query_id: str
    user_query: str
    target_category: str | None = None
    related_sku_ids: list[str] = Field(default_factory=list)
    timestamp: str


class DialogueStateTracking(BaseModel):
    current_intent: str = IntentType.RECOMMEND.value
    current_flow: str = "recommendation"
    current_category: str | None = None
    current_sub_category: str | None = None
    slots: dict[str, Any] = Field(default_factory=dict)
    active_constraints: dict[str, Any] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    resolved_references: dict[str, str] = Field(default_factory=dict)
    last_task_plan: list[str] = Field(default_factory=list)
    pending_need: dict[str, Any] = Field(default_factory=dict)
    last_model_route: dict[str, Any] = Field(default_factory=dict)
    last_trace: dict[str, Any] = Field(default_factory=dict)


class CartStateItem(BaseModel):
    sku_id: str
    quantity: int


class CartState(BaseModel):
    items: list[CartStateItem] = Field(default_factory=list)
    last_updated_by: str | None = None


class SessionState(BaseModel):
    session_id: str
    user_id: str | None = None
    recent_messages: list[ConversationTurn] = Field(default_factory=list)
    user: UserPreferences = Field(default_factory=UserPreferences)
    user_profile_summary_text: str | None = None
    user_profile_structured: dict[str, Any] = Field(default_factory=dict)
    goods: GoodsContext = Field(default_factory=GoodsContext)
    memory_events: list[MemoryEventRecord] = Field(default_factory=list)
    event_memory: EventMemory = Field(default_factory=EventMemory)
    behaviours: list[BehaviourRecord] = Field(default_factory=list)
    dialogue_state_tracking: DialogueStateTracking = Field(default_factory=DialogueStateTracking)
    cart: CartState = Field(default_factory=CartState)
    trace_log: list[dict[str, Any]] = Field(default_factory=list)
    checkout_guidance: dict[str, Any] | None = None
