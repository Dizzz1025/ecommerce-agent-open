from app.memory.session_memory import SessionMemory
from app.models.domain import CartItem, CartStateItem, Product
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
            variant = self._find_variant(
                product=product,
                selected_sku_id=saved_item.selected_sku_id,
                selected_specs=saved_item.selected_specs,
            )
            selected_sku_id = saved_item.selected_sku_id or (variant.sku_id if variant else None)
            selected_specs = self._normalized_specs(
                variant.properties if variant else saved_item.selected_specs
            )
            spec_summary = saved_item.spec_summary or self._format_specs(selected_specs)
            unit_price = self._unit_price(product, variant, saved_item.unit_price)
            cart_item_id = saved_item.cart_item_id or self._cart_item_id(
                product_id=product.sku_id,
                selected_sku_id=selected_sku_id,
                selected_specs=selected_specs,
            )
            total_price += saved_item.quantity * unit_price
            total_items += saved_item.quantity
            items.append(
                CartItem(
                    cart_item_id=cart_item_id,
                    sku_id=product.sku_id,
                    selected_sku_id=selected_sku_id,
                    selected_specs=selected_specs,
                    spec_summary=spec_summary,
                    name=saved_item.name or product.name,
                    price=unit_price,
                    quantity=saved_item.quantity,
                    image_url=saved_item.image_url or product.image_url,
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
        selected_sku_id: str | None = None,
        selected_specs: dict | None = None,
        unit_price: float | None = None,
        product_name: str | None = None,
        image_url: str | None = None,
        spec_summary: str | None = None,
        source: str = "button",
    ) -> CartSnapshot:
        product = self._require_product(sku_id)
        state = self.session_memory.get_or_create(session_id)
        requested_specs = self._normalized_specs(selected_specs or {})
        if len(product.skus) > 1 and not selected_sku_id and not requested_specs:
            raise ValueError("Multi-SKU product requires selected_sku_id or selected_specs")
        variant = self._find_variant(
            product=product,
            selected_sku_id=selected_sku_id,
            selected_specs=requested_specs,
        )
        if len(product.skus) > 1 and variant is None:
            raise ValueError("Multi-SKU product requires a valid selected_sku_id or complete selected_specs")
        effective_selected_sku_id = selected_sku_id
        effective_specs = requested_specs
        if variant is not None:
            effective_selected_sku_id = variant.sku_id
            effective_specs = self._normalized_specs(variant.properties)
        effective_price = self._unit_price(product, variant, unit_price)
        effective_spec_summary = spec_summary or self._format_specs(effective_specs)
        cart_item_id = self._cart_item_id(
            product_id=product.sku_id,
            selected_sku_id=effective_selected_sku_id,
            selected_specs=effective_specs,
        )
        existing = next(
            (
                item
                for item in state.cart.items
                if self._state_item_id(item) == cart_item_id
            ),
            None,
        )
        if existing is not None:
            existing.quantity += quantity
        else:
            state.cart.items.append(
                CartStateItem(
                    sku_id=product.sku_id,
                    quantity=quantity,
                    cart_item_id=cart_item_id,
                    selected_sku_id=effective_selected_sku_id,
                    selected_specs=effective_specs,
                    spec_summary=effective_spec_summary,
                    unit_price=effective_price,
                    name=product_name or product.name,
                    image_url=image_url or product.image_url,
                )
            )
        self.session_memory.sync_cart(
            session_id,
            items=state.cart.items,
            last_updated_by=source,
        )
        return self.get_snapshot(session_id)

    def remove(
        self,
        session_id: str,
        sku_id: str,
        cart_item_id: str | None = None,
        source: str = "button",
    ) -> CartSnapshot:
        state = self.session_memory.get_or_create(session_id)
        if cart_item_id:
            state.cart.items = [
                item for item in state.cart.items if self._state_item_id(item) != cart_item_id
            ]
        else:
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
        cart_item_id: str | None = None,
        source: str = "button",
    ) -> CartSnapshot:
        state = self.session_memory.get_or_create(session_id)
        product = self._require_product(sku_id)
        for item in state.cart.items:
            if cart_item_id:
                matches = self._state_item_id(item) == cart_item_id
            else:
                matches = item.sku_id == sku_id
            if matches:
                item.quantity = quantity
                break
        else:
            state.cart.items.append(
                CartStateItem(
                    sku_id=product.sku_id,
                    quantity=quantity,
                    cart_item_id=cart_item_id or product.sku_id,
                    unit_price=product.price,
                    name=product.name,
                    image_url=product.image_url,
                )
            )
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

    def _state_item_id(self, item: CartStateItem) -> str:
        return item.cart_item_id or self._cart_item_id(
            product_id=item.sku_id,
            selected_sku_id=item.selected_sku_id,
            selected_specs=item.selected_specs,
        )

    @staticmethod
    def _normalized_specs(raw_specs: dict | None) -> dict[str, str]:
        if not raw_specs:
            return {}
        cleaned: dict[str, str] = {}
        for key, value in raw_specs.items():
            key_text = str(key).strip()
            value_text = str(value).strip()
            if key_text and value_text and value_text.lower() != "null":
                cleaned[key_text] = value_text
        return {key: cleaned[key] for key in sorted(cleaned)}

    def _find_variant(
        self,
        *,
        product: Product,
        selected_sku_id: str | None,
        selected_specs: dict | None,
    ):
        if selected_sku_id:
            variant = next((item for item in product.skus if item.sku_id == selected_sku_id), None)
            if variant is not None:
                return variant
        normalized_specs = self._normalized_specs(selected_specs)
        if not normalized_specs:
            return None
        for variant in product.skus:
            variant_specs = self._normalized_specs(variant.properties)
            if variant_specs == normalized_specs:
                return variant
        return None

    def _unit_price(self, product: Product, variant, requested_price: float | None) -> float:
        if variant is not None:
            return float(variant.price)
        if requested_price is not None:
            return float(requested_price)
        return float(product.price)

    def _cart_item_id(
        self,
        *,
        product_id: str,
        selected_sku_id: str | None,
        selected_specs: dict | None,
    ) -> str:
        if selected_sku_id:
            return f"{product_id}::{selected_sku_id}"
        normalized_specs = self._normalized_specs(selected_specs)
        if normalized_specs:
            spec_key = "|".join(f"{key}={value}" for key, value in normalized_specs.items())
            return f"{product_id}::{spec_key}"
        return product_id

    @staticmethod
    def _format_specs(selected_specs: dict | None) -> str | None:
        if not selected_specs:
            return None
        values = [str(value).strip() for _, value in sorted(selected_specs.items()) if str(value).strip()]
        return " · ".join(values) if values else None
