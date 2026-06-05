import re

from app.models.agent import InputPreprocessResult
from app.models.domain import SessionState


class InputPreprocessor:
    """Cheap request gate before any retrieval or LLM work."""

    _greeting_tokens = ["你好", "您好", "hello", "hi", "在吗", "你是谁", "你能做什么", "你能干嘛", "谢谢", "多谢", "辛苦了", "好的", "ok"]
    _out_of_scope_tokens = [
        "天气", "作文", "论文", "写代码", "讲个笑话", "新闻", "股票", "基金",
        "作业", "翻译", "算命", "星座", "租房", "招聘", "简历", "看病", "医生",
        "法律", "律师", "贷款", "保险", "彩票", "赌博", "政治", "宗教",
        "今天几号", "几点了", "现在几点", "你是谁发明的", "你的底层模型",
    ]
    _unsupported_product_tokens = ["汽车", "买车", "一辆车", "房子", "机票", "酒店", "优惠券", "券码", "电影票", "外卖", "药", "处方"]

    def preprocess(
        self,
        *,
        message: str,
        input_type: str = "text",
        state: SessionState | None = None,
    ) -> InputPreprocessResult:
        normalized = self._normalize(message)
        if not normalized:
            return InputPreprocessResult(
                raw_message=message,
                normalized_message="",
                input_type=input_type,
                valid=False,
                reason="empty_input",
                simple_route="invalid",
                template_reply="我还没有收到具体需求，可以告诉我想买什么或想比较哪几款商品。",
            )

        is_repeated = bool(
            state
            and state.recent_messages
            and state.recent_messages[-1].role == "user"
            and self._normalize(state.recent_messages[-1].content) == normalized
        )

        if self._is_greeting(normalized):
            return InputPreprocessResult(
                raw_message=message,
                normalized_message=normalized,
                input_type=input_type,
                is_repeated=is_repeated,
                simple_route="greeting",
                template_reply="你好，我是你的智能导购助手，可以帮你推荐商品、比较商品、回答商品细节，也能管理购物车。",
            )

        if any(token in normalized for token in self._unsupported_product_tokens):
            return InputPreprocessResult(
                raw_message=message,
                normalized_message=normalized,
                input_type=input_type,
                is_repeated=is_repeated,
                simple_route="out_of_scope",
                template_reply="这个需求超出了当前商品库范围。我现在主要支持美妆护肤、数码电子、服饰运动和食品饮料，可以在这些范围里帮你推荐或比较。",
            )

        if any(token in normalized for token in self._out_of_scope_tokens):
            return InputPreprocessResult(
                raw_message=message,
                normalized_message=normalized,
                input_type=input_type,
                is_repeated=is_repeated,
                simple_route="out_of_scope",
                template_reply=(
                    "这个问题暂时不属于我的商品导购任务专长范围哦～我主要专注于帮你做商品推荐、筛选对比、"
                    "详情问答和购物车管理。目前覆盖美妆护肤、数码电子、服饰运动、食品饮料四个领域，"
                    "都是经过精挑细选的真实商品。你可以告诉我你想找什么类型的商品，或者把你的需求"
                    "告诉我，我来帮你做最合适的个性化推荐和搭配建议！"
                ),
            )

        return InputPreprocessResult(
            raw_message=message,
            normalized_message=normalized,
            input_type=input_type,
            is_repeated=is_repeated,
        )

    @staticmethod
    def _normalize(message: str) -> str:
        text = message.strip()
        text = re.sub(r"\s+", " ", text)
        text = text.replace("块钱", "元").replace("块", "元")
        text = text.replace("以内", "以内").replace("之内", "以内")
        text = text.replace("蓝牙 耳机", "蓝牙耳机")
        text = text.replace("不粘", "不黏").replace("黏腻", "油腻").replace("粘腻", "油腻")
        text = text.replace("有啥", "有什么").replace("咋样", "怎么样").replace("哪一个", "哪个")
        return text

    @staticmethod
    def _is_greeting(normalized: str) -> bool:
        """Detect pure greetings without catching shopping phrases.

        The old substring check treated “拍照好的手机” as a greeting because it
        contains “好的”. Greetings must be standalone short utterances or clear
        greeting prefixes without product-intent words.
        """
        text = normalized.strip()
        lower = text.lower()
        product_intent_terms = [
            "推荐", "想要", "想买", "买", "选", "挑", "看看", "介绍", "比较",
            "对比", "手机", "耳机", "护肤", "防晒", "面霜", "精华", "跑鞋",
            "鞋", "衣", "包", "零食", "饮料", "咖啡",
        ]
        if any(term in text for term in product_intent_terms):
            return False
        exact_greetings = {"你好", "您好", "hello", "hi", "在吗", "谢谢", "多谢", "辛苦了", "好的", "好", "ok"}
        if lower in exact_greetings:
            return True
        prefix_greetings = ("你好呀", "您好呀", "你好啊", "您好啊", "hello ", "hi ")
        if lower.startswith(prefix_greetings) and len(text) <= 12:
            return True
        if any(text.startswith(term) for term in ["你是谁", "你能做什么", "你能干嘛"]) and len(text) <= 14:
            return True
        return False
