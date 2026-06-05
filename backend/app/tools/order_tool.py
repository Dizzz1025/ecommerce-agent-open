from app.services.order_service import OrderService
from app.models.schemas import CartSnapshot


class OrderTool:
    def __init__(self, order_service: OrderService) -> None:
        self.order_service = order_service

    def create_order(self, session_id: str, cart_snapshot: CartSnapshot) -> dict:
        return self.order_service.create_demo_order(
            session_id=session_id,
            cart_snapshot=cart_snapshot,
        )
