from app.models.domain import Product
from app.models.agent import CandidateProduct


class KnowledgeFormatter:
    def format_products(
        self,
        products: list[Product],
        candidates: list[CandidateProduct] | None = None,
    ) -> str:
        candidate_map = {item.sku_id: item for item in candidates or []}
        lines = []
        for product in products:
            candidate = candidate_map.get(product.sku_id)
            reasons = "、".join(candidate.matched_reasons[:4]) if candidate else "商品库匹配"
            risk_notes = "、".join(candidate.risk_notes[:2]) if candidate else ""
            score_text = f"{candidate.score:.4f}" if candidate else "unknown"
            match_level = _match_level(candidate.score) if candidate else "unknown"
            tags = _safe_tags(product, candidate)
            enhancement = _format_enhancement(product, candidate)
            lines.append(
                f"- product_id={product.sku_id} | name={product.name} | brand={product.brand} | "
                f"category={product.category}/{product.sub_category or ''} | price={product.price:g} | "
                f"match_score={score_text} | match_level={match_level} | reasons={reasons} | "
                f"tags={'、'.join(tags)} | "
                f"highlight_short={product.highlight_short} | suitable_scenarios={'、'.join(product.suitable_scenarios[:5])} | "
                f"target_user_tags={'、'.join(product.target_user_tags[:5])} | "
                f"non_standard_query_tags={'、'.join(product.non_standard_query_tags[:5])} | "
                f"enhancement_matches={enhancement} | review_summary={product.reviews_summary} | risks={risk_notes}"
            )
        return "\n".join(lines)


def _safe_tags(product: Product, candidate: CandidateProduct | None) -> list[str]:
    if candidate is None:
        return list(dict.fromkeys([product.category, product.sub_category or "", *product.tags[:4]]))
    blocked = {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选"}
    tags = [
        item.removeprefix("匹配")
        for item in candidate.matched_reasons
        if item and item not in blocked
    ]
    tags.extend([product.category, product.sub_category or ""])
    return [item for item in dict.fromkeys(tags) if item][:8]


def _match_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "partial"


def _format_enhancement(product: Product, candidate: CandidateProduct | None) -> str:
    if candidate and candidate.enhancement_matches:
        matches = candidate.enhancement_matches
        parts = []
        for key in ["matched_non_standard_query_tags", "matched_suitable_scenarios", "matched_target_user_tags", "matched_highlight_fields"]:
            values = matches.get(key) or []
            if values:
                parts.append(f"{key}={','.join(values[:3])}")
        if parts:
            return "; ".join(parts)
    if product.highlight_short:
        return product.highlight_short
    return ""
