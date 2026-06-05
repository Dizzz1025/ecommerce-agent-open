"""智能下单闭环引导 (Checkout Closing Loop).

当用户已选定商品（加入购物车）且当前轮未表达新购物需求时，
主动引导用户完成下单闭环：确认商品、填写地址、发起结算。

触发条件（全部满足）:
  1. 购物车非空
  2. 当前轮是购物车操作（cart_add/cart_view）或上一轮刚加购
  3. 当前轮消息中无新的购物需求信号
  4. 本轮未触发过结算引导（同轮不重复）
  5. 距离上次拒绝引导已超过 2 轮

不触发条件:
  - 购物车为空
  - 用户正在表达新的推荐/筛选/比较需求
  - 用户刚拒绝了结算
  - 已经在本轮触发过
"""

from __future__ import annotations

from typing import Any


# 触发引导的购物车操作
_GUIDE_TRIGGER_ACTIONS = {"cart_add", "cart_view", "cart_update"}

# 新的购物需求信号 — 出现这些时不应引导结算
_NEW_DEMAND_SIGNALS = [
    "推荐", "想要", "想买", "帮我找", "看看", "有没有",
    "筛选", "比较", "对比", "哪个好", "还有", "再推荐",
    "换", "重新", "别的", "其他的", "另外", "另外的",
    "不要", "删除", "移除", "换个", "再帮我",
    "继续逛", "再看看", "还有什么", "其他的呢",
]

# 用户肯定结算的信号
_CHECKOUT_ACCEPT_SIGNALS = [
    "结算", "下单", "付款", "支付", "买单", "结账",
    "可以", "好的", "行", "ok", "OK", "好", "嗯",
    "是的", "对", "确认", "没问题", "行吧", "下单吧",
    "那就", "就这些", "就这个", "就这些吧",
]

# 用户拒绝/延后结算的信号
_CHECKOUT_DECLINE_SIGNALS = [
    "不用", "不要", "先不", "暂不", "暂时不", "等等",
    "再看", "再看看", "先看看", "还不想", "不急",
    "还没", "再加", "还想加", "继续加", "不着急",
    "等一下", "稍等", "再说", "下次",
]


class ClosingGuide:
    """Decide when and how to trigger checkout closing guidance."""

    @staticmethod
    def should_trigger(
        *,
        cart_items: list,
        current_intent: str,
        current_message: str,
        checkout_offered_count: int = 0,
        checkout_declined_recently: bool = False,
        last_flow: str = "",
    ) -> bool:
        """Check if now is the right moment to offer checkout guidance."""
        # 1. 购物车必须非空
        if not cart_items:
            return False

        # 2. 必须是购物车操作流
        if current_intent not in _GUIDE_TRIGGER_ACTIONS and last_flow not in {"cart_action", "checkout"}:
            return False

        # 3. 当前消息中不能有新购物需求
        if ClosingGuide._has_new_demand(current_message):
            return False

        # 4. 如果已触发过但购物车有新增商品，允许重新触发
        #    只在本轮已触发过时才跳过（避免同一轮重复）
        #    checkout_offered_count 是历史累计，购物车变化时重置为0

        # 5. 用户刚拒绝后不再追问（2轮冷却）
        if checkout_declined_recently:
            return False

        return True

    @staticmethod
    def is_accept_signal(message: str) -> bool:
        """Detect if user is accepting the checkout offer."""
        msg = message.strip().lower()
        return any(signal in msg for signal in _CHECKOUT_ACCEPT_SIGNALS) and not ClosingGuide._has_new_demand(message)

    @staticmethod
    def is_decline_signal(message: str) -> bool:
        """Detect if user is declining/postponing checkout."""
        msg = message.strip().lower()
        return any(signal in msg for signal in _CHECKOUT_DECLINE_SIGNALS)

    @staticmethod
    def _has_new_demand(message: str) -> bool:
        """Check if message contains signals of new shopping needs."""
        msg = message.strip().lower()
        return any(signal in msg for signal in _NEW_DEMAND_SIGNALS)

    @staticmethod
    def build_guidance_context(
        *,
        cart_items: list[dict],
        cart_total: float,
        cart_count: int,
        user_profile: dict | None = None,
    ) -> dict[str, Any]:
        """Build the context payload for generating closing guidance text.

        Returns a dict that the response generator can use to craft a natural
        checkout suggestion in the agent's persona.
        """
        item_names = [item.get("name", "")[:30] for item in cart_items[:3]]
        # cart_count 是数量合计，cart_items 是不同 SKU。展示“等N件”时应按
        # SKU 个数计算，否则 2 个 SKU 各 5 件会误写成“等7件”。
        more_count = max(0, len(cart_items) - len(item_names))

        return {
            "should_close": True,
            "cart_summary": {
                "total_items": cart_count,
                "total_price": cart_total,
                "item_names": item_names,
                "more_count": more_count,
            },
            "guidance_options": [
                "确认商品并结算",
                "填写收货地址和联系方式",
                "继续逛逛添加其他商品",
            ],
            "prompt_hint": (
                "用户已完成商品选购，请在回复末尾用 1-2 句自然引导用户确认订单。"
                "必须以当前导购角色风格表达，不要生硬。参考结构："
                "先确认已加购商品，再询问是否需要结算或继续添加。"
                f"购物车共有{cart_count}件商品，合计¥{cart_total:g}，"
                f"包含：{'、'.join(item_names)}"
                + (f"等{more_count}件" if more_count else "")
                + "。引导用户选择「确认并结算」或「继续添加商品」。"
            ),
        }
