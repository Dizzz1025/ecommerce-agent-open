from datetime import datetime
from uuid import uuid4

from app.models.schemas import CartSnapshot


class OrderService:
    """Creates deterministic demo orders from a cart snapshot."""

    def create_order(
        self,
        *,
        session_id: str,
        cart_snapshot: CartSnapshot,
        address_mode: str = "default",
    ) -> dict:
        order_id = f"demo_order_{uuid4().hex[:10]}"
        return {
            "order_id": order_id,
            "session_id": session_id,
            "status": "created",
            "address_mode": address_mode,
            "total_items": cart_snapshot.total_items,
            "total_price": cart_snapshot.total_price,
            "items": [item.model_dump() for item in cart_snapshot.items],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "message": "Demo 已生成订单预览，不会触发真实支付。",
        }

    def create_demo_order(self, session_id: str, cart_snapshot: CartSnapshot) -> dict:
        return self.create_order(session_id=session_id, cart_snapshot=cart_snapshot)
