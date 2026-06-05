from app.models.domain import IntentType


class IntentParser:
    """Legacy lightweight rule parser kept for backward-compatible imports."""

    def parse(self, message: str) -> IntentType:
        normalized = message.lower()
        if any(token in normalized for token in ["compare", "对比", "比较"]):
            return IntentType.COMPARE
        if any(token in normalized for token in ["clarify", "再便宜", "还有别的"]):
            return IntentType.CLARIFY
        if any(token in normalized for token in ["cart add", "add to cart", "加购", "加入购物车"]):
            return IntentType.CART_ADD
        if any(token in normalized for token in ["cart remove", "移出购物车", "删除购物车"]):
            return IntentType.CART_REMOVE
        if any(token in normalized for token in ["cart update", "修改数量", "更新购物车"]):
            return IntentType.CART_UPDATE
        if any(token in normalized for token in ["cart clear", "清空购物车"]):
            return IntentType.CART_CLEAR
        if any(token in normalized for token in ["checkout", "下单", "结算"]):
            return IntentType.CHECKOUT
        return IntentType.RECOMMEND
