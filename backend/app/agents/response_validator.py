import re

from app.models.agent import CandidateProduct
from app.models.agent import ValidationResult
from app.models.domain import Product


class ResponseValidator:
    """Guards LLM output against product hallucination."""

    def __init__(self, known_products: list[Product]) -> None:
        self.known_products = known_products

    def validate(self, text: str, allowed_candidates: list[CandidateProduct]) -> str:
        return self.validate_with_result(text, allowed_candidates)[0]

    def validate_with_result(self, text: str, allowed_candidates: list[CandidateProduct]) -> tuple[str, ValidationResult]:
        if not text:
            return text, ValidationResult(ok=True)
        allowed_names = {item.name for item in allowed_candidates}
        allowed_prices = {int(item.price) for item in allowed_candidates}
        forbidden_names = [
            product.name
            for product in self.known_products
            if product.name not in allowed_names and product.name in text
        ]
        if forbidden_names:
            return self._fallback(allowed_candidates), ValidationResult(
                ok=False,
                issues=[f"forbidden_product:{name}" for name in forbidden_names],
                repaired=True,
            )

        mentioned_prices = set()
        for match in re.finditer(r"(?:¥|￥)\s*(\d{2,5})|(\d{2,5})\s*元", text):
            value = int(match.group(1) or match.group(2))
            context = text[max(0, match.start() - 8): match.end() + 8]
            if any(token in context for token in ["以内", "以下", "预算", "不超过", "不要超过", "别超过", "控制在", "上限", "低于", "少于"]):
                continue
            mentioned_prices.add(value)
        suspicious_prices = [
            value for value in mentioned_prices
            if allowed_prices and value not in allowed_prices and value > 20
        ]
        if suspicious_prices and allowed_candidates:
            return self._fallback(allowed_candidates), ValidationResult(
                ok=False,
                issues=[f"suspicious_price:{value}" for value in suspicious_prices],
                repaired=True,
            )
        return text, ValidationResult(ok=True)

    @staticmethod
    def _fallback(candidates: list[CandidateProduct]) -> str:
        if not candidates:
            return "这个需求我需要再缩小一点范围。你可以放宽预算、品牌或功能条件，我马上继续帮你挑。"
        best = candidates[0]
        lines = [f"我根据当前商品库为你重新整理了更稳妥的选择，优先看 {best.name}，¥{best.price:g}。{_natural_reason(best)}。"]
        if len(candidates) > 1:
            others = "、".join(item.name for item in candidates[1:3])
            lines.append(f"另外 {others} 也可以放在备选里，具体图片和参数以商品卡片为准。")
        return "\n".join(lines)


def _natural_reason(candidate: CandidateProduct) -> str:
    reasons = [
        _display_reason(item)
        for item in candidate.matched_reasons
        if item and item not in {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选"}
    ]
    if reasons:
        return f"它比较贴合你对{'、'.join(reasons[:3])}的需求"
    if candidate.sub_category:
        return f"它属于{candidate.sub_category}类目，和你当前想看的方向比较接近"
    return "它来自当前商品库的真实匹配结果"


def _display_reason(reason: str) -> str:
    return reason.removeprefix("匹配")
