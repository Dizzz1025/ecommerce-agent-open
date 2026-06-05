from app.models.schemas import CartSnapshot
from app.services.cart_service import CartService


class CartTool:
    def __init__(self, cart_service: CartService) -> None:
        self.cart_service = cart_service

    def add(
        self,
        session_id: str,
        sku_id: str,
        quantity: int,
        source: str,
    ) -> CartSnapshot:
        return self.cart_service.add(
            session_id=session_id,
            sku_id=sku_id,
            quantity=quantity,
            source=source,
        )

    def remove(self, session_id: str, sku_id: str, source: str) -> CartSnapshot:
        return self.cart_service.remove(session_id=session_id, sku_id=sku_id, source=source)

    def update(self, session_id: str, sku_id: str, quantity: int, source: str) -> CartSnapshot:
        return self.cart_service.update_quantity(
            session_id=session_id,
            sku_id=sku_id,
            quantity=quantity,
            source=source,
        )

    def clear(self, session_id: str, source: str) -> CartSnapshot:
        return self.cart_service.clear(session_id=session_id, source=source)
