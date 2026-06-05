from app.models.schemas import CartSnapshot
from app.services.checkout_service import CheckoutService


class CheckoutTool:
    def __init__(self, checkout_service: CheckoutService) -> None:
        self.checkout_service = checkout_service

    def preview(self, session_id: str) -> CartSnapshot:
        return self.checkout_service.preview_checkout(session_id=session_id)

