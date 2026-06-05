from __future__ import annotations

from app.models.agent import CandidateProduct


class VisualRetriever:
    """Lightweight visual re-ranking helper for the first multimodal demo."""

    def boost_visual_matches(
        self,
        candidates: list[CandidateProduct],
        visual_terms: list[str],
        *,
        product_match: dict | None = None,
    ) -> list[CandidateProduct]:
        if not visual_terms and not product_match:
            return candidates
        best_match = (product_match or {}).get("best_match") or {}
        best_sku_id = best_match.get("sku_id")
        boosted: list[CandidateProduct] = []
        for item in candidates:
            text = f"{item.name} {item.brand} {item.category} {item.sub_category or ''} {' '.join(item.matched_reasons)}"
            hits = [term for term in visual_terms if term and term in text]
            exact_visual_match = best_sku_id and item.sku_id == best_sku_id
            if hits or exact_visual_match:
                item = item.model_copy(deep=True)
                boost = 0.04 * len(hits)
                if exact_visual_match:
                    boost += 0.45
                    item.raw_scores["visual_product_match"] = float(best_match.get("confidence") or 1.0)
                    hits = [f"图片相近商品:{item.sku_id}", *hits]
                item.score = round(min(item.score + boost, 1.0), 4)
                item.matched_reasons = list(dict.fromkeys([*hits[:3], *item.matched_reasons]))
            boosted.append(item)
        boosted.sort(key=lambda product: product.score, reverse=True)
        return boosted
