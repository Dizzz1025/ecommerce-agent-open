from typing import Any

from pydantic import BaseModel, Field

from app.models.domain import CartItem, Product
from app.models.agent import AgentTrace, CandidateProduct


class HealthResponse(BaseModel):
    status: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: str | None = None
    input_type: str = "text"
    resume: bool = False
    new_session: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductResponse(BaseModel):
    product: Product


class ProductListResponse(BaseModel):
    products: list[Product]


class CartSnapshot(BaseModel):
    items: list[CartItem] = Field(default_factory=list)
    total_price: float = 0.0
    total_items: int = 0


class CartAddRequest(BaseModel):
    session_id: str
    sku_id: str
    quantity: int = Field(default=1, ge=1)
    source: str = "button"


class CartRemoveRequest(BaseModel):
    session_id: str
    sku_id: str


class CartUpdateRequest(BaseModel):
    session_id: str
    sku_id: str
    quantity: int = Field(..., ge=1)


class CartClearRequest(BaseModel):
    session_id: str


class SessionStateResponse(BaseModel):
    session_id: str
    user_id: str | None = None
    current_flow: str
    current_intent: str
    current_category: str | None = None
    current_sub_category: str | None = None
    active_constraints: dict[str, Any] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    last_retrieved_products: list[str] = Field(default_factory=list)
    last_recommended_products: list[str] = Field(default_factory=list)
    cart_total_items: int = 0
    last_model_route: dict[str, Any] = Field(default_factory=dict)
    pending_need: dict[str, Any] = Field(default_factory=dict)
    user_profile_summary_text: str | None = None
    user_profile_structured: dict[str, Any] = Field(default_factory=dict)
    last_trace: dict[str, Any] = Field(default_factory=dict)


class SessionMemoryResponse(BaseModel):
    session_id: str
    memory: dict[str, Any]


class RetrievalDebugResponse(BaseModel):
    parsed_query: dict[str, Any]
    candidates: list[CandidateProduct]


class AgentTraceResponse(BaseModel):
    session_id: str
    traces: list[AgentTrace | dict[str, Any]]
