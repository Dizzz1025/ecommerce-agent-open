from app.memory.session_memory import SessionMemory
from app.models.domain import CartItem, CartStateItem
from app.models.schemas import CartSnapshot
from app.repositories.product_repository import ProductRepository


class CartService:
    def __init__(
        self,
        session_memory: SessionMemory,
        product_repository: ProductRepository,
    ) -> None:
        self.session_memory = session_memory
        self.product_repository = product_repository

    def get_snapshot(self, session_id: str) -> CartSnapshot:
        state = self.session_memory.get_or_create(session_id)
        items: list[CartItem] = []
        total_price = 0.0
        total_items = 0
        for saved_item in state.cart.items:
            product = self.product_repository.get_product(saved_item.sku_id)
            if product is None:
                continue
            total_price += saved_item.quantity * product.price
            total_items += saved_item.quantity
            items.append(
                CartItem(
                    sku_id=product.sku_id,
                    name=product.name,
                    price=product.price,
                    quantity=saved_item.quantity,
                    image_url=product.image_url,
                )
            )
        return CartSnapshot(
            items=items,
            total_price=round(total_price, 2),
            total_items=total_items,
        )

    def add(
        self,
        session_id: str,
        sku_id: str,
        quantity: int = 1,
        source: str = "button",
    ) -> CartSnapshot:
        product = self._require_product(sku_id)
        state = self.session_memory.get_or_create(session_id)
        existing = next((item for item in state.cart.items if item.sku_id == sku_id), None)
        if existing is not None:
            existing.quantity += quantity
        else:
            state.cart.items.append(
                CartStateItem(
                    sku_id=product.sku_id,
                    quantity=quantity,
                )
            )
        self.session_memory.sync_cart(
            session_id,
            items=state.cart.items,
            last_updated_by=source,
        )
        return self.get_snapshot(session_id)

    def remove(self, session_id: str, sku_id: str, source: str = "button") -> CartSnapshot:
        state = self.session_memory.get_or_create(session_id)
        state.cart.items = [item for item in state.cart.items if item.sku_id != sku_id]
        self.session_memory.sync_cart(
            session_id,
            items=state.cart.items,
            last_updated_by=source,
        )
        return self.get_snapshot(session_id)

    def update_quantity(
        self,
        session_id: str,
        sku_id: str,
        quantity: int,
        source: str = "button",
    ) -> CartSnapshot:
        state = self.session_memory.get_or_create(session_id)
        self._require_product(sku_id)
        for item in state.cart.items:
            if item.sku_id == sku_id:
                item.quantity = quantity
                break
        else:
            state.cart.items.append(CartStateItem(sku_id=sku_id, quantity=quantity))
        self.session_memory.sync_cart(
            session_id,
            items=state.cart.items,
            last_updated_by=source,
        )
        return self.get_snapshot(session_id)

    def clear(self, session_id: str, source: str = "button") -> CartSnapshot:
        state = self.session_memory.get_or_create(session_id)
        state.cart.items = []
        self.session_memory.sync_cart(
            session_id,
            items=state.cart.items,
            last_updated_by=source,
        )
        return self.get_snapshot(session_id)

    def _require_product(self, sku_id: str):
        product = self.product_repository.get_product(sku_id)
        if product is None:
            raise ValueError(f"Product not found: {sku_id}")
        return product
