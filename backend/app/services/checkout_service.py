from app.models.schemas import CartSnapshot
from app.services.cart_service import CartService


class CheckoutService:
    def __init__(self, cart_service: CartService) -> None:
        self.cart_service = cart_service

    def preview_checkout(self, session_id: str) -> CartSnapshot:
        return self.cart_service.get_snapshot(session_id)

