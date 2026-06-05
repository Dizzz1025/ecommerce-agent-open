from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_session_memory
from app.core.dependencies import get_user_history_store
from app.memory.session_memory import SessionMemory
from app.memory.user_history_store import UserHistoryStore
from app.models.schemas import AgentTraceResponse, SessionMemoryResponse, SessionStateResponse

router = APIRouter()


@router.get("/{session_id}/state", response_model=SessionStateResponse)
async def get_session_state(
    session_id: str,
    session_memory: SessionMemory = Depends(get_session_memory),
) -> SessionStateResponse:
    state = session_memory.get_or_create(session_id)
    dialogue = state.dialogue_state_tracking
    return SessionStateResponse(
        session_id=session_id,
        user_id=state.user_id,
        current_flow=dialogue.current_flow,
        current_intent=dialogue.current_intent,
        current_category=dialogue.current_category,
        current_sub_category=dialogue.current_sub_category,
        active_constraints=dialogue.active_constraints,
        missing_slots=dialogue.missing_slots,
        last_retrieved_products=[item.sku_id for item in state.goods.last_candidates],
        last_recommended_products=[item.sku_id for item in state.goods.last_recommendations],
        cart_total_items=sum(item.quantity for item in state.cart.items),
        last_model_route=dialogue.last_model_route,
        pending_need=dialogue.pending_need,
        user_profile_summary_text=state.user_profile_summary_text,
        user_profile_structured=state.user_profile_structured,
        last_trace=dialogue.last_trace,
    )


@router.get("/{session_id}/memory", response_model=SessionMemoryResponse)
async def get_session_memory_dump(
    session_id: str,
    session_memory: SessionMemory = Depends(get_session_memory),
) -> SessionMemoryResponse:
    state = session_memory.get_or_create(session_id)
    return SessionMemoryResponse(
        session_id=session_id,
        memory=state.model_dump(),
    )


@router.get("/{session_id}/trace", response_model=AgentTraceResponse)
async def get_session_trace(
    session_id: str,
    session_memory: SessionMemory = Depends(get_session_memory),
) -> AgentTraceResponse:
    state = session_memory.get_or_create(session_id)
    return AgentTraceResponse(session_id=session_id, traces=state.trace_log)


@router.get("/{session_id}/profile")
async def get_user_profile(
    session_id: str,
    user_id: str | None = Query(default=None),
    session_memory: SessionMemory = Depends(get_session_memory),
    history_store: UserHistoryStore = Depends(get_user_history_store),
):
    state = session_memory.get_or_create(session_id)
    effective_user_id = user_id or state.user_id or session_id
    return {
        "中文说明": "本接口用于调试本地长期用户画像和历史会话索引。",
        "user_id": effective_user_id,
        "profile": history_store.load_profile(effective_user_id),
    }


@router.get("/{session_id}/history")
async def get_session_history(
    session_id: str,
    user_id: str | None = Query(default=None),
    session_memory: SessionMemory = Depends(get_session_memory),
    history_store: UserHistoryStore = Depends(get_user_history_store),
):
    state = session_memory.get_or_create(session_id)
    effective_user_id = user_id or state.user_id or session_id
    return {
        "中文说明": "本接口用于调试本地用户历史文件，确认每轮输入、回复、推荐商品和隐私保存策略。",
        "user_id": effective_user_id,
        "session_id": session_id,
        "session": history_store.load_session(effective_user_id, session_id) or {},
    }
