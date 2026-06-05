"""检索容错层 (Retrieval Robustness Layer).

当严格过滤导致 0 结果时，按层级逐步放宽约束：
  1. 放宽价格约束 → 取价格最接近的商品
  2. 放宽子类目约束 → 在同类目中宽泛搜索
  3. 移除否定硬过滤 → 仅通过软评分降权
  4. 彻底放宽 → 全库存中找关键词最匹配的

每一步都会记录放松了什么，以便在回复中告知用户。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.agent import CandidateProduct, ParsedQuery


@dataclass
class FallbackResult:
    """检索容错结果，包含原始结果和容错尝试的完整记录。"""

    candidates: list[CandidateProduct]
    """最终推荐的候选商品（可能是放宽约束后的结果）。"""

    original_count: int = 0
    """首次严格检索的候选数量。"""

    relaxed_steps: list[str] = field(default_factory=list)
    """已执行的放宽步骤，如 ['relaxed_price', 'relaxed_sub_category']。"""

    relaxed_details: dict[str, Any] = field(default_factory=dict)
    """每步放宽的详细信息，供回复生成时使用。"""

    is_fallback: bool = False
    """是否触发了容错机制。"""

    def to_dict(self) -> dict:
        """Serializable representation for trace/debug."""
        return {
            "is_fallback": self.is_fallback,
            "original_count": self.original_count,
            "relaxed_steps": self.relaxed_steps,
            "summary": self.summary_for_response(),
        }

    def summary_for_response(self) -> str:
        """生成面向用户的简短说明（中文）。"""
        if not self.is_fallback or not self.relaxed_steps:
            return ""
        parts: list[str] = []
        if "relaxed_price" in self.relaxed_steps:
            parts.append("适当放宽了价格范围")
        if "relaxed_sub_category" in self.relaxed_steps:
            parts.append("扩大了同类商品的检索范围")
        if "relaxed_negative" in self.relaxed_steps:
            parts.append("减少了排除条件的严格限制")
        if "broad_search" in self.relaxed_steps:
            parts.append("进行了全类目宽泛匹配")
        if not parts:
            return ""
        return "、".join(parts) + "，为你找到了以下相近选择。"


class RetrievalFallback:
    """渐进式检索容错。"""

    @staticmethod
    def progressive_retrieve(
        *,
        retriever: Any,
        parsed_query: ParsedQuery,
        state: Any,
        top_k: int = 5,
    ) -> FallbackResult:
        """按层级尝试检索，直到找到至少 1 个候选。"""

        # Step 0: 严格检索
        candidates = retriever.retrieve(parsed_query=parsed_query, state=state, top_k=top_k, broad=False)
        valid = [c for c in candidates if not c.filtered_out]
        if valid and len(valid) >= 1:
            return FallbackResult(
                candidates=candidates,
                original_count=len(valid),
                is_fallback=False,
            )

        result = FallbackResult(
            candidates=candidates,
            original_count=len(valid),
            is_fallback=True,
        )

        # Step 1: 放宽价格约束
        price_relaxed_query = parsed_query.model_copy(deep=True)
        price_range_relaxed = False
        if parsed_query.price_range.max is not None or parsed_query.price_range.min is not None:
            price_relaxed_query.price_range.max = None
            price_relaxed_query.price_range.min = None
            price_range_relaxed = True
        if price_range_relaxed:
            candidates = retriever.retrieve(parsed_query=price_relaxed_query, state=state, top_k=top_k, broad=False)
            valid = [c for c in candidates if not c.filtered_out]
            if valid:
                result.relaxed_steps.append("relaxed_price")
                result.relaxed_details["relaxed_price"] = {
                    "original_max": parsed_query.price_range.max,
                    "original_min": parsed_query.price_range.min,
                    "found_count": len(valid),
                }
                # 标记最接近原预算的商品
                if parsed_query.price_range.max is not None:
                    sorted_by_price = sorted(valid, key=lambda c: abs(c.price - parsed_query.price_range.max))
                    result.candidates = sorted_by_price[: top_k * 3]
                    result.relaxed_details["relaxed_price"]["closest_match_price"] = sorted_by_price[0].price if sorted_by_price else None
                else:
                    result.candidates = candidates
                return result

        # Step 2: 放宽子类目，但保留大类目
        broad_query = parsed_query.model_copy(deep=True)
        if parsed_query.sub_category:
            candidates = retriever.retrieve(parsed_query=broad_query, state=state, top_k=top_k, broad=True)
        else:
            candidates = retriever.retrieve(parsed_query=broad_query, state=state, top_k=top_k, broad=True)
        valid = [c for c in candidates if not c.filtered_out]
        if valid:
            result.relaxed_steps.append("relaxed_sub_category")
            result.relaxed_details["relaxed_sub_category"] = {
                "original_sub_category": parsed_query.sub_category,
                "found_count": len(valid),
            }
            result.candidates = candidates
            return result

        # Step 3: 移除否定硬过滤，仅保留软评分降权
        relaxed_neg_query = parsed_query.model_copy(deep=True)
        relaxed_neg_query.price_range.max = None
        relaxed_neg_query.price_range.min = None
        relaxed_neg_query.negative_constraints = []
        relaxed_neg_query.brands_exclude = []
        candidates = retriever.retrieve(parsed_query=relaxed_neg_query, state=state, top_k=top_k, broad=True)
        valid = [c for c in candidates if not c.filtered_out]
        if valid:
            result.relaxed_steps.append("relaxed_negative")
            result.relaxed_details["relaxed_negative"] = {
                "found_count": len(valid),
            }
            result.candidates = candidates
            return result

        # Step 4: 全类目宽泛搜索 — 只用关键词
        broad_query = parsed_query.model_copy(deep=True)
        broad_query.category = None
        broad_query.sub_category = None
        broad_query.price_range.max = None
        broad_query.price_range.min = None
        broad_query.negative_constraints = []
        broad_query.brands_exclude = []
        broad_query.brands_include = []
        candidates = retriever.retrieve(parsed_query=broad_query, state=state, top_k=top_k, broad=True)
        valid = [c for c in candidates if not c.filtered_out]
        if valid:
            result.relaxed_steps.append("broad_search")
            result.relaxed_details["broad_search"] = {
                "original_category": parsed_query.category,
                "found_count": len(valid),
            }
            result.candidates = candidates
        else:
            result.relaxed_steps.append("no_results_at_all")
            result.candidates = []

        return result
