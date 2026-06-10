import re

from app.models.agent import ParsedQuery, ToolExecutionResult
from app.models.domain import Product, ProductSku, SessionState
from app.repositories.product_repository import ProductRepository
from app.services.cart_service import CartService
from app.services.order_service import OrderService


class ActionExecutor:
    def __init__(
        self,
        cart_service: CartService,
        product_repository: ProductRepository,
        order_service: OrderService | None = None,
    ) -> None:
        self.cart_service = cart_service
        self.product_repository = product_repository
        self.order_service = order_service or OrderService()

    def execute_cart_action(
        self,
        *,
        session_id: str,
        parsed_query: ParsedQuery,
        state: SessionState,
    ) -> ToolExecutionResult:
        action = parsed_query.cart_action.action if parsed_query.cart_action else parsed_query.intent
        try:
            if action == "cart_clear":
                snapshot = self.cart_service.clear(session_id=session_id, source="dialogue")
                return ToolExecutionResult(
                    ok=True,
                    tool_name="clear_cart",
                    message="购物车已经清空。",
                    payload=snapshot.model_dump(),
                )
            if action == "cart_view":
                snapshot = self.cart_service.get_snapshot(session_id=session_id)
                if snapshot.items:
                    return ToolExecutionResult(
                        ok=True,
                        tool_name="view_cart",
                        message=f"当前购物车里有 {snapshot.total_items} 件商品，合计 ¥{snapshot.total_price:g}。",
                        payload=snapshot.model_dump(),
                    )
                return ToolExecutionResult(
                    ok=True,
                    tool_name="view_cart",
                    message="当前购物车还是空的，可以先从推荐商品里选一款加入。",
                    payload=snapshot.model_dump(),
                )
            if action == "checkout":
                snapshot = self.cart_service.get_snapshot(session_id=session_id)
                if not snapshot.items:
                    return ToolExecutionResult(
                        ok=False,
                        tool_name="mock_checkout",
                        message="购物车还是空的，暂时不能下单。",
                        payload=snapshot.model_dump(),
                        error_code="CART_EMPTY",
                    )
                order = self.order_service.create_order(
                    session_id=session_id,
                    cart_snapshot=snapshot,
                    address_mode="default" if "默认" in parsed_query.raw_message else "unspecified",
                )
                payload = snapshot.model_dump()
                payload["order"] = order
                return ToolExecutionResult(
                    ok=True,
                    tool_name="mock_checkout",
                    message=f"已为你生成订单预览 {order['order_id']}，共 {snapshot.total_items} 件，合计 ¥{snapshot.total_price:g}。Demo 阶段不会真实支付。",
                    payload=payload,
                )
            if action == "cart_keep_only":
                snapshot = self._keep_only(session_id=session_id, parsed_query=parsed_query)
                return ToolExecutionResult(
                    ok=True,
                    tool_name="cart_keep_only",
                    message="已按你的要求整理购物车，只保留匹配的商品。",
                    payload=snapshot.model_dump(),
                )

            if action == "cart_remove" and self._is_bulk_remove(parsed_query):
                snapshot = self._remove_matching(session_id=session_id, parsed_query=parsed_query)
                return ToolExecutionResult(
                    ok=True,
                    tool_name="remove_from_cart",
                    message="已按你的要求从购物车移除匹配的商品。",
                    payload=snapshot.model_dump(),
                )

            if (
                action == "cart_add"
                and self._is_bulk_add(parsed_query)
                and len(parsed_query.mentioned_products) > 1
            ):
                spec_result = self._bulk_spec_selection_result(parsed_query, state)
                if spec_result is not None:
                    return spec_result
                snapshot = self._add_explicit_products(session_id=session_id, parsed_query=parsed_query)
                return ToolExecutionResult(
                    ok=True,
                    tool_name="add_to_cart",
                    message=f"已把你指定的商品加入购物车，当前共 {snapshot.total_items} 件。",
                    payload=snapshot.model_dump(),
                )

            if (
                action == "cart_add"
                and self._is_bulk_add(parsed_query)
                and not (parsed_query.cart_action and parsed_query.cart_action.sku_id)
            ):
                spec_result = self._bulk_spec_selection_result(parsed_query, state)
                if spec_result is not None:
                    return spec_result
                snapshot = self._add_matching_recommendations(session_id=session_id, parsed_query=parsed_query, state=state)
                return ToolExecutionResult(
                    ok=True,
                    tool_name="add_to_cart",
                    message=f"已把匹配的商品加入购物车，当前共 {snapshot.total_items} 件。",
                    payload=snapshot.model_dump(),
                )

            sku_id = self._resolve_target_sku(parsed_query, state, cart_first=(action in {"cart_remove", "cart_update"}))
            if sku_id is None:
                return ToolExecutionResult(
                    ok=False,
                    tool_name=action,
                    message="我还没确定你指的是哪款商品，可以说“第一款”或“第二款”。",
                    error_code="REFERENT_AMBIGUOUS",
                )

            quantity = parsed_query.cart_action.quantity if parsed_query.cart_action and parsed_query.cart_action.quantity else 1
            if action == "cart_add":
                product = self._require_product_for_cart(sku_id)
                variant = self._resolve_variant_from_query(product, parsed_query)
                if self._needs_spec_selection(product, variant):
                    return ToolExecutionResult(
                        ok=True,
                        tool_name="need_spec_selection",
                        message="这款商品有以下规格，请选择后加入购物车：",
                        payload=self._build_spec_selection_payload(product, quantity),
                    )
                snapshot = self._add_product_variant(
                    session_id=session_id,
                    product=product,
                    variant=variant,
                    quantity=quantity,
                    source="dialogue",
                )
                product_name = next((item.name for item in snapshot.items if item.sku_id == product.sku_id), product.name)
                spec_text = self._format_specs(variant.properties if variant else {})
                return ToolExecutionResult(
                    ok=True,
                    tool_name="add_to_cart",
                    message=f"已把 {product_name}{f'（{spec_text}）' if spec_text else ''} 加入购物车，数量 {quantity}。",
                    payload=snapshot.model_dump(),
                )
            if action == "cart_remove":
                snapshot = self.cart_service.remove(session_id=session_id, sku_id=sku_id, source="dialogue")
                if _has_checkout_after_remove(parsed_query.raw_message):
                    snapshot = self.cart_service.get_snapshot(session_id=session_id)
                    if not snapshot.items:
                        return ToolExecutionResult(
                            ok=False,
                            tool_name="remove_then_checkout",
                            message="我已经移除了你说的那款商品，不过购物车现在是空的，暂时不能结算。",
                            payload=snapshot.model_dump(),
                            error_code="CART_EMPTY",
                        )
                    order = self.order_service.create_order(
                        session_id=session_id,
                        cart_snapshot=snapshot,
                        address_mode="default" if "默认" in parsed_query.raw_message else "unspecified",
                    )
                    payload = snapshot.model_dump()
                    payload["order"] = order
                    return ToolExecutionResult(
                        ok=True,
                        tool_name="remove_then_checkout",
                        message=f"已先移除较贵的商品，并为剩余商品生成订单预览 {order['order_id']}，共 {snapshot.total_items} 件，合计 ¥{snapshot.total_price:g}。Demo 阶段不会真实支付。",
                        payload=payload,
                    )
                return ToolExecutionResult(
                    ok=True,
                    tool_name="remove_from_cart",
                    message="已从购物车移除这款商品。",
                    payload=snapshot.model_dump(),
                )
            if action == "cart_update":
                snapshot = self.cart_service.update_quantity(
                    session_id=session_id,
                    sku_id=sku_id,
                    quantity=quantity,
                    source="dialogue",
                )
                return ToolExecutionResult(
                    ok=True,
                    tool_name="update_cart_quantity",
                    message=f"已把这款商品数量改为 {quantity}。",
                    payload=snapshot.model_dump(),
                )
        except Exception as exc:
            return ToolExecutionResult(
                ok=False,
                tool_name=action,
                message=str(exc),
                error_code="TOOL_ERROR",
            )

        return ToolExecutionResult(
            ok=False,
            tool_name=action,
            message="这个购物车动作暂时还不支持。",
            error_code="UNSUPPORTED_ACTION",
        )

    def _resolve_target_sku(self, parsed_query: ParsedQuery, state: SessionState, *, cart_first: bool) -> str | None:
        if cart_first and any(term in parsed_query.raw_message for term in ["较贵", "更贵", "最贵", "贵的那款", "价格高"]):
            return _select_cart_item_by_price(state=state, product_repository=self.product_repository, reverse=True)
        if cart_first and any(term in parsed_query.raw_message for term in ["较便宜", "更便宜", "最便宜", "便宜的那款", "价格低"]):
            return _select_cart_item_by_price(state=state, product_repository=self.product_repository, reverse=False)
        if parsed_query.cart_action and parsed_query.cart_action.sku_id:
            return parsed_query.cart_action.sku_id
        sku_id = self._resolve_from_memory_events(parsed_query, state)
        if sku_id:
            return sku_id
        for product_id in parsed_query.mentioned_products:
            product = self.product_repository.get_product(product_id)
            if product:
                return product.sku_id
        if parsed_query.cart_action and parsed_query.cart_action.target_ref:
            sku_id = state.dialogue_state_tracking.resolved_references.get(parsed_query.cart_action.target_ref)
            if sku_id:
                return sku_id
        for ref in parsed_query.referents:
            sku_id = state.dialogue_state_tracking.resolved_references.get(ref)
            if sku_id:
                return sku_id
        for item in state.cart.items:
            product = self.product_repository.get_product(item.sku_id)
            if not product:
                continue
            haystack = f"{product.name} {product.brand} {product.category} {product.sub_category or ''}"
            if any(term and term in haystack for term in [parsed_query.category, parsed_query.sub_category, *parsed_query.positive_constraints]):
                return item.sku_id
        if cart_first and len(state.cart.items) == 1:
            return state.cart.items[0].sku_id
        if state.goods.last_recommendations:
            return state.goods.last_recommendations[0].sku_id
        return None

    def _require_product_for_cart(self, sku_id: str) -> Product:
        product = self.product_repository.get_product(sku_id)
        if product is None:
            raise ValueError(f"Product not found: {sku_id}")
        return product

    @staticmethod
    def _needs_spec_selection(product: Product, variant: ProductSku | None) -> bool:
        return len(product.skus) > 1 and variant is None

    @staticmethod
    def _default_variant(product: Product) -> ProductSku | None:
        return product.skus[0] if product.skus else None

    def _bulk_spec_selection_result(
        self,
        parsed_query: ParsedQuery,
        state: SessionState,
    ) -> ToolExecutionResult | None:
        targets = self._bulk_add_targets(parsed_query, state)
        for product in targets:
            variant = self._resolve_variant_from_query(product, parsed_query)
            if self._needs_spec_selection(product, variant):
                quantity = parsed_query.cart_action.quantity if parsed_query.cart_action and parsed_query.cart_action.quantity else 1
                return ToolExecutionResult(
                    ok=True,
                    tool_name="need_spec_selection",
                    message=f"{product.name} 有多个规格，请先选择后加入购物车：",
                    payload=self._build_spec_selection_payload(product, quantity),
                )
        return None

    def _bulk_add_targets(self, parsed_query: ParsedQuery, state: SessionState) -> list[Product]:
        products: list[Product] = []
        if parsed_query.mentioned_products:
            for sku_id in parsed_query.mentioned_products:
                product = self.product_repository.get_product(sku_id)
                if product and product.sku_id not in {item.sku_id for item in products}:
                    products.append(product)
            return products
        wanted_sub_categories = self._wanted_sub_categories(parsed_query.raw_message)
        for record in state.goods.last_recommendations:
            product = self.product_repository.get_product(record.sku_id)
            if not product:
                continue
            if wanted_sub_categories and product.sub_category not in wanted_sub_categories:
                continue
            products.append(product)
        if not products:
            sku_id = self._resolve_target_sku(parsed_query, state, cart_first=False)
            product = self.product_repository.get_product(sku_id) if sku_id else None
            if product:
                products.append(product)
        return products

    def _resolve_variant_from_query(self, product: Product, parsed_query: ParsedQuery) -> ProductSku | None:
        if not product.skus:
            return None
        action_sku_id = parsed_query.cart_action.sku_id if parsed_query.cart_action else None
        if action_sku_id:
            direct = next((sku for sku in product.skus if sku.sku_id == action_sku_id), None)
            if direct is not None:
                return direct
        if len(product.skus) == 1:
            return product.skus[0]
        raw_message = _normalize_spec_text(parsed_query.raw_message)
        scored_matches = [
            (self._sku_match_score(sku, raw_message), sku)
            for sku in product.skus
        ]
        scored_matches = [(score, sku) for score, sku in scored_matches if score > 0]
        if not scored_matches:
            return self._default_variant(product)
        best_score = max(score for score, _ in scored_matches)
        best_matches = [sku for score, sku in scored_matches if score == best_score]
        return best_matches[0] if len(best_matches) == 1 else self._default_variant(product)

    @staticmethod
    def _sku_matches_message(sku: ProductSku, normalized_message: str) -> bool:
        return ActionExecutor._sku_match_score(sku, normalized_message) > 0

    @staticmethod
    def _sku_match_score(sku: ProductSku, normalized_message: str) -> int:
        values = [str(value).strip() for value in sku.properties.values() if str(value).strip()]
        if not values:
            return 0
        return sum(_spec_value_match_score(value, normalized_message) for value in values)

    def _build_spec_selection_payload(self, product: Product, quantity: int) -> dict:
        sku_options = [self._sku_option_payload(product, sku) for sku in product.skus]
        return {
            "type": "need_spec_selection",
            "product_id": product.sku_id,
            "productId": product.sku_id,
            "product_name": product.name,
            "productName": product.name,
            "image_url": product.image_url,
            "imageUrl": product.image_url,
            "quantity": quantity,
            "sku_options": sku_options,
            "skuOptions": sku_options,
        }

    def _sku_option_payload(self, product: Product, sku: ProductSku) -> dict:
        selected_specs = self._normalized_specs(sku.properties)
        spec_text = self._format_specs(selected_specs) or sku.sku_id
        stock = _sku_stock(sku, product.stock)
        return {
            "product_id": product.sku_id,
            "productId": product.sku_id,
            "sku_id": sku.sku_id,
            "skuId": sku.sku_id,
            "selected_specs": selected_specs,
            "selectedSpecs": selected_specs,
            "spec_text": spec_text,
            "specText": spec_text,
            "price": float(sku.price),
            "stock": stock,
            "available": stock is None or stock > 0,
        }

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

    @staticmethod
    def _format_specs(selected_specs: dict | None) -> str | None:
        if not selected_specs:
            return None
        values = [str(value).strip() for _, value in sorted(selected_specs.items()) if str(value).strip()]
        return " · ".join(values) if values else None

    def _add_product_variant(
        self,
        *,
        session_id: str,
        product: Product,
        variant: ProductSku | None,
        quantity: int,
        source: str,
    ):
        selected_specs = self._normalized_specs(variant.properties if variant else {})
        return self.cart_service.add(
            session_id=session_id,
            sku_id=product.sku_id,
            quantity=quantity,
            selected_sku_id=variant.sku_id if variant else None,
            selected_specs=selected_specs,
            unit_price=variant.price if variant else product.price,
            product_name=product.name,
            image_url=product.image_url,
            spec_summary=self._format_specs(selected_specs),
            source=source,
        )

    @staticmethod
    def _resolve_from_memory_events(parsed_query: ParsedQuery, state: SessionState) -> str | None:
        references: list[str] = []
        if parsed_query.cart_action and parsed_query.cart_action.target_ref:
            references.append(parsed_query.cart_action.target_ref)
        references.extend(parsed_query.referents)
        references.extend(_extract_reference_terms(parsed_query.raw_message))
        references = list(dict.fromkeys([ref for ref in references if ref]))
        if not references:
            return None

        if any(_is_cart_event_reference(ref) for ref in references):
            for event in reversed(state.memory_events):
                if event.event_type == "cart_action" and event.related_product_ids:
                    return event.related_product_ids[0]

        latest_recommendation = next(
            (event for event in reversed(state.memory_events) if event.event_type == "recommendation"),
            None,
        )
        if latest_recommendation:
            alias_map = latest_recommendation.payload.get("reference_alias_to_sku") or {}
            rank_map = latest_recommendation.payload.get("rank_to_sku") or {}
            for ref in references:
                sku_id = alias_map.get(ref)
                if sku_id:
                    return sku_id
                rank = _rank_ref_to_int(ref)
                if rank is not None:
                    sku_id = rank_map.get(str(rank))
                    if sku_id:
                        return sku_id

        pronouns = {"这个", "这款", "这一款", "它", "那个", "那款", "刚才那个", "刚才那款"}
        if any(ref in pronouns for ref in references):
            for event in reversed(state.memory_events):
                if event.related_product_ids:
                    return event.related_product_ids[0]
        return None

    def _keep_only(self, session_id: str, parsed_query: ParsedQuery):
        snapshot = self.cart_service.get_snapshot(session_id)
        keep_sku_ids: set[str] = set()
        keep_categories = set(parsed_query.cart_action.keep_categories if parsed_query.cart_action else [])
        keep_sub_categories = set(parsed_query.cart_action.keep_sub_categories if parsed_query.cart_action else [])
        for item in snapshot.items:
            product = self.product_repository.get_product(item.sku_id)
            if not product:
                continue
            if product.category in keep_categories or (product.sub_category and product.sub_category in keep_sub_categories):
                keep_sku_ids.add(product.sku_id)
        for item in list(snapshot.items):
            if item.sku_id not in keep_sku_ids:
                self.cart_service.remove(session_id=session_id, sku_id=item.sku_id, source="dialogue")
        return self.cart_service.get_snapshot(session_id)

    def _remove_matching(self, session_id: str, parsed_query: ParsedQuery):
        snapshot = self.cart_service.get_snapshot(session_id)
        excluded = set(parsed_query.cart_action.exclude_sku_ids if parsed_query.cart_action else [])
        for item in list(snapshot.items):
            if item.sku_id in excluded:
                continue
            product = self.product_repository.get_product(item.sku_id)
            if product and self._matches_remove_target(product, parsed_query):
                self.cart_service.remove(session_id=session_id, sku_id=item.sku_id, source="dialogue")
        return self.cart_service.get_snapshot(session_id)

    def _add_matching_recommendations(self, session_id: str, parsed_query: ParsedQuery, state: SessionState):
        wanted_sub_categories = self._wanted_sub_categories(parsed_query.raw_message)
        quantity = parsed_query.cart_action.quantity if parsed_query.cart_action and parsed_query.cart_action.quantity else 1
        added = False
        for record in state.goods.last_recommendations:
            product = self.product_repository.get_product(record.sku_id)
            if not product:
                continue
            if wanted_sub_categories and product.sub_category not in wanted_sub_categories:
                continue
            variant = self._resolve_variant_from_query(product, parsed_query)
            if self._needs_spec_selection(product, variant):
                continue
            self._add_product_variant(
                session_id=session_id,
                product=product,
                variant=variant,
                quantity=quantity,
                source="dialogue",
            )
            added = True
        if not added:
            sku_id = self._resolve_target_sku(parsed_query, state, cart_first=False)
            if sku_id:
                product = self.product_repository.get_product(sku_id)
                variant = self._resolve_variant_from_query(product, parsed_query) if product else None
                if product and not self._needs_spec_selection(product, variant):
                    self._add_product_variant(
                        session_id=session_id,
                        product=product,
                        variant=variant,
                        quantity=quantity,
                        source="dialogue",
                    )
        return self.cart_service.get_snapshot(session_id)

    def _add_explicit_products(self, session_id: str, parsed_query: ParsedQuery):
        quantity = parsed_query.cart_action.quantity if parsed_query.cart_action and parsed_query.cart_action.quantity else 1
        seen: set[str] = set()
        for sku_id in parsed_query.mentioned_products:
            if sku_id in seen:
                continue
            product = self.product_repository.get_product(sku_id)
            if not product:
                continue
            variant = self._resolve_variant_from_query(product, parsed_query)
            if self._needs_spec_selection(product, variant):
                continue
            self._add_product_variant(
                session_id=session_id,
                product=product,
                variant=variant,
                quantity=quantity,
                source="dialogue",
            )
            seen.add(sku_id)
        return self.cart_service.get_snapshot(session_id)

    @staticmethod
    def _is_bulk_remove(parsed_query: ParsedQuery) -> bool:
        return any(term in parsed_query.raw_message for term in ["所有", "全部", "都", "全都", "一切"])

    @staticmethod
    def _is_bulk_add(parsed_query: ParsedQuery) -> bool:
        return any(term in parsed_query.raw_message for term in ["都加入", "都加", "一起加入", "一起加", "和"]) and "购物车" in parsed_query.raw_message

    @staticmethod
    def _wanted_sub_categories(raw_message: str) -> set[str]:
        mapping = {
            "办公文具": "办公文具",
            "文具": "办公文具",
            "桌面收纳": "桌面收纳",
            "收纳": "桌面收纳",
            "通勤小物件": "通勤小物",
            "通勤小物": "通勤小物",
            "发圈": "发圈",
            "眼线笔": "眼线笔",
            "零食": "坚果/零食",
            "饮料": "乳酸菌饮品",
            "耳机": "真无线耳机",
            "蓝牙耳机": "真无线耳机",
            "无线耳机": "真无线耳机",
            "降噪耳机": "真无线耳机",
        }
        return {sub for key, sub in mapping.items() if key in raw_message}

    @staticmethod
    def _matches_remove_target(product, parsed_query: ParsedQuery) -> bool:
        raw = parsed_query.raw_message
        if "饮料" in raw or "喝的" in raw:
            return product.category == "食品饮料" and product.sub_category in {
                "茶饮",
                "碳酸饮料",
                "功能饮料",
                "牛奶",
                "酸奶",
                "咖啡",
                "乳酸菌饮品",
            }
        if parsed_query.sub_category:
            return product.sub_category == parsed_query.sub_category
        if parsed_query.category:
            return product.category == parsed_query.category
        return False


def _has_checkout_after_remove(raw_message: str) -> bool:
    return any(term in raw_message for term in ["再付款", "并付款", "付款", "支付", "结算", "下单"])


def _normalize_spec_text(value: object) -> str:
    normalized = re.sub(r"\s+", "", str(value).strip().lower())
    return re.sub(r"[+＋]", "", normalized)


def _spec_value_matches(value: str, normalized_message: str) -> bool:
    return _spec_value_match_score(value, normalized_message) > 0


def _spec_value_match_score(value: str, normalized_message: str) -> int:
    normalized_value = _normalize_spec_text(value)
    if not normalized_value:
        return 0
    if normalized_value in normalized_message:
        return 4
    meaningful_tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9+]+", normalized_value)
    shared_tokens = [token for token in meaningful_tokens if token in normalized_message]
    if shared_tokens:
        return len(shared_tokens)
    chinese_text = "".join(re.findall(r"[\u4e00-\u9fff]+", normalized_value))
    chinese_bigrams = {chinese_text[index : index + 2] for index in range(max(len(chinese_text) - 1, 0))}
    shared_bigrams = [token for token in chinese_bigrams if token in normalized_message]
    if shared_bigrams:
        return len(shared_bigrams)
    parts = [
        part
        for part in re.split(r"[·/|,，、;；\s]+", value)
        if part.strip()
    ]
    matched_parts = [_normalize_spec_text(part) for part in parts if _normalize_spec_text(part) in normalized_message]
    if parts and len(matched_parts) == len(parts):
        return 3
    if matched_parts:
        return len(matched_parts)
    numeric_units = re.findall(r"\d+(?:\.\d+)?(?:ml|g|kg|l|gb|tb|cm|mm|寸|英寸|颗|片|支|瓶|盒|杯|包|双|件)", normalized_value)
    if numeric_units and all(unit in normalized_message for unit in numeric_units):
        return len(numeric_units)
    return 0


def _sku_stock(sku: ProductSku, fallback_stock: int) -> int | None:
    raw = getattr(sku, "stock", None)
    if raw is None:
        return fallback_stock
    try:
        return int(raw)
    except (TypeError, ValueError):
        return fallback_stock


def _extract_reference_terms(raw_message: str) -> list[str]:
    refs: list[str] = []
    patterns = [
        r"第[一二三四五六七八九十\d]+[个款件瓶台只双]?",
        r"刚才那[个款]",
        r"刚才加购的",
        r"刚才加到购物车的",
        r"购物车里[的那个]*",
        r"这[个款]",
        r"那[个款]",
        r"它",
    ]
    for pattern in patterns:
        refs.extend(match.group(0) for match in re.finditer(pattern, raw_message))
    return refs


def _rank_ref_to_int(ref: str) -> int | None:
    digit = re.search(r"\d+", ref)
    if digit:
        return int(digit.group(0))
    zh_map = {
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    for text, value in zh_map.items():
        if text in ref:
            return value
    return None


def _is_cart_event_reference(ref: str) -> bool:
    return any(term in ref for term in ["加购", "加到购物车", "购物车里的", "购物车里那个", "刚才买"])


def _select_cart_item_by_price(
    *,
    state: SessionState,
    product_repository: ProductRepository,
    reverse: bool,
) -> str | None:
    priced_items = []
    for item in state.cart.items:
        product = product_repository.get_product(item.sku_id)
        if product:
            priced_items.append((product.price, product.sku_id))
    if not priced_items:
        return None
    priced_items.sort(reverse=reverse)
    return priced_items[0][1]
