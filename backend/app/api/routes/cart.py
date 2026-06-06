from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_cart_service
from app.models.schemas import (
    CartAddRequest,
    CartClearRequest,
    CartRemoveRequest,
    CartSnapshot,
    CartUpdateRequest,
)
from app.services.cart_service import CartService

router = APIRouter()


@router.get("", response_model=CartSnapshot)
async def get_cart(
    session_id: str = Query(..., description="Current chat session ID."),
    cart_service: CartService = Depends(get_cart_service),
) -> CartSnapshot:
    return cart_service.get_snapshot(session_id)


@router.get("/{session_id}", response_model=CartSnapshot)
async def get_cart_by_path(
    session_id: str,
    cart_service: CartService = Depends(get_cart_service),
) -> CartSnapshot:
    return cart_service.get_snapshot(session_id)


@router.post("/add", response_model=CartSnapshot)
async def add_cart_item(
    payload: CartAddRequest,
    cart_service: CartService = Depends(get_cart_service),
) -> CartSnapshot:
    return cart_service.add(
        session_id=payload.session_id,
        sku_id=payload.sku_id,
        quantity=payload.quantity,
        selected_sku_id=payload.selected_sku_id,
        selected_specs=payload.selected_specs,
        unit_price=payload.unit_price,
        product_name=payload.product_name,
        image_url=payload.image_url,
        spec_summary=payload.spec_summary,
        source=payload.source,
    )


@router.post("/remove", response_model=CartSnapshot)
async def remove_cart_item(
    payload: CartRemoveRequest,
    cart_service: CartService = Depends(get_cart_service),
) -> CartSnapshot:
    return cart_service.remove(
        session_id=payload.session_id,
        sku_id=payload.sku_id,
        cart_item_id=payload.cart_item_id,
        source="button",
    )


@router.post("/update", response_model=CartSnapshot)
async def update_cart_item(
    payload: CartUpdateRequest,
    cart_service: CartService = Depends(get_cart_service),
) -> CartSnapshot:
    return cart_service.update_quantity(
        session_id=payload.session_id,
        sku_id=payload.sku_id,
        cart_item_id=payload.cart_item_id,
        quantity=payload.quantity,
        source="button",
    )


@router.post("/clear", response_model=CartSnapshot)
async def clear_cart(
    payload: CartClearRequest,
    cart_service: CartService = Depends(get_cart_service),
) -> CartSnapshot:
    return cart_service.clear(session_id=payload.session_id, source="button")


@router.post("/{session_id}/clear", response_model=CartSnapshot)
async def clear_cart_by_path(
    session_id: str,
    cart_service: CartService = Depends(get_cart_service),
) -> CartSnapshot:
    return cart_service.clear(session_id=session_id, source="button")
