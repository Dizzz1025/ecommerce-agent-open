from app.models.agent import CandidateProduct, ParsedQuery
from app.models.domain import Product, ProductCard, RecommendationRecord
from app.retrieval.category_compatibility import sub_category_matches


class ProductPostProcessor:
    def finalize(
        self,
        candidates: list[CandidateProduct],
        parsed_query: ParsedQuery,
        limit: int,
    ) -> list[CandidateProduct]:
        deduped: dict[str, CandidateProduct] = {}
        for candidate in candidates:
            existing = deduped.get(candidate.product_id)
            if existing is None or candidate.score > existing.score:
                deduped[candidate.product_id] = candidate

        filtered = []
        for candidate in deduped.values():
            if candidate.filtered_out:
                continue
            if parsed_query.category and candidate.category != parsed_query.category:
                continue
            if parsed_query.sub_category and not sub_category_matches(parsed_query.sub_category, candidate.sub_category):
                continue
            if parsed_query.price_range.min is not None and candidate.price < parsed_query.price_range.min:
                continue
            if parsed_query.price_range.max is not None and candidate.price > parsed_query.price_range.max:
                continue
            if parsed_query.brands_exclude and any(brand in candidate.brand for brand in parsed_query.brands_exclude):
                continue
            if parsed_query.brands_include and not any(brand in candidate.brand for brand in parsed_query.brands_include):
                continue
            violations = []
            if parsed_query.negative_constraints:
                for term in parsed_query.negative_constraints:
                    if term in {"太贵", "贵"}:
                        continue
                    if _negative_satisfied_by_safe_word(term, f"{candidate.name} {' '.join(candidate.matched_reasons)}"):
                        continue
                    if term and (term in candidate.name or term in " ".join(candidate.matched_reasons)):
                        violations.append(term)
            if violations:
                candidate.violated_constraints = violations
                candidate.displayable = False
                continue
            filtered.append(candidate)

        filtered.sort(key=lambda item: item.score, reverse=True)
        return filtered[:limit]

    def build_product_cards(self, candidates: list[CandidateProduct], products_by_id: dict[str, Product]) -> list[ProductCard]:
        cards: list[ProductCard] = []
        for candidate in candidates:
            product = products_by_id.get(candidate.sku_id)
            if product is None:
                continue
            matched_reasons = list(candidate.matched_reasons)
            if candidate.score < 0.5 and "匹配度一般，作为备选" not in matched_reasons:
                matched_reasons.insert(0, "匹配度一般，作为备选")
            reason = _build_card_reason(product, matched_reasons, candidate.score)
            cards.append(
                ProductCard(
                    sku_id=product.sku_id,
                    product_id=product.product_id,
                    name=product.name,
                    display_title=product.display_title,
                    category=product.category,
                    sub_category=product.sub_category,
                    brand=product.brand,
                    price=product.price,
                    stock=product.stock,
                    image_url=product.image_url,
                    reason=reason,
                    recommend_reason=reason,
                    highlight_short=product.highlight_short,
                    suitable_scenarios=product.suitable_scenarios[:5],
                    target_user_tags=product.target_user_tags[:5],
                    non_standard_query_tags=product.non_standard_query_tags[:5],
                    matched_reasons=matched_reasons,
                    tags=product.tags[:6],
                    score=round(candidate.score, 4),
                )
            )
        return cards

    def build_recommendation_records(
        self,
        candidates: list[CandidateProduct],
        query_id: str,
    ) -> list[RecommendationRecord]:
        records = []
        for index, candidate in enumerate(candidates, start=1):
            records.append(
                RecommendationRecord(
                    rank=index,
                    sku_id=candidate.sku_id,
                    name=candidate.name,
                    category=candidate.category,
                    query_id=query_id,
                    reason="、".join(candidate.matched_reasons[:3]),
                    price=candidate.price,
                )
            )
        return records


def _negative_satisfied_by_safe_word(term: str, text: str) -> bool:
    if term in {"酒精", "乙醇", "酒精成分", "含酒精", "有酒精"} and any(safe in text for safe in ["不含酒精", "无酒精", "不添加酒精", "不含乙醇", "无乙醇"]):
        return True
    if term in {"糖", "甜", "甜味", "太甜", "含糖", "有糖"} and any(safe in text for safe in ["无糖", "0糖", "零糖", "低糖", "不甜", "非甜味"]):
        return True
    if term in {"油", "油腻", "太油", "黏腻", "粘腻"} and any(safe in text for safe in ["不油腻", "不黏腻", "不粘腻", "清爽", "轻薄", "控油", "油皮"]):
        return True
    if term == "防水" and any(safe in text for safe in ["不防水", "非防水"]):
        return True
    if term in {"紧身", "紧身款"} and any(safe in text for safe in ["不紧身", "不会太紧身", "宽松", "微宽松", "不紧绷"]):
        return True
    if term in {"印花", "印花图案", "大logo", "大Logo", "大Logo印花", "大logo印花"} and any(safe in text for safe in ["无印花", "没有夸张的大logo", "极简", "纯色", "基础纯色"]):
        return True
    if term in {"大包装", "包装太大", "太大"} and "小包装" in text:
        return True
    if term in {"糕点", "糕点和谷物类"} and any(safe in text for safe in ["非糕点", "不是糕点"]):
        return True
    if term in {"谷物", "糕点和谷物类"} and any(safe in text for safe in ["非谷物", "不是谷物"]):
        return True
    return False


def _build_card_reason(product: Product, matched_reasons: list[str], score: float) -> str:
    meaningful = [
        _clean_reason(item) for item in matched_reasons
        if item and item not in {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选"}
    ][:3]
    need_text = "、".join(meaningful) if meaningful else (product.sub_category or product.category or "当前需求")
    selling_point = _selling_point(product)
    if not meaningful and product.highlight_short:
        return _join_two_sentences(
            f"这款比较贴合你当前想看的{product.sub_category or product.category or '商品'}方向，适合先放进候选里。",
            f"它的{selling_point}比较突出，前端卡片里可以继续查看具体名称、价格和图片。",
        )
    if score < 0.5:
        if meaningful:
            return _join_two_sentences(
                f"这款是更接近需求的备选，主要贴合你对{need_text}的方向。",
                f"它的{selling_point}仍有参考价值，但和你的部分条件可能略有差异，建议点开卡片确认。",
            )
        return _join_two_sentences(
            "这款来自当前相关类目，更适合作为备选参考。",
            f"它的{selling_point}可以作为补充选择，建议点开确认细节后再决定。",
        )
    if meaningful:
        return _join_two_sentences(
            f"这款比较贴合你对{need_text}的要求，适合优先查看。",
            f"它的{selling_point}比较突出，适合在{_scenario_text(product)}这类场景下使用。",
        )
    if product.sub_category:
        return _join_two_sentences(
            f"这款属于{product.sub_category}类目，和你当前想看的方向比较接近。",
            f"它的{selling_point}比较突出，可以先点开商品卡片看细节。",
        )
    return _join_two_sentences(
        "这款来自当前商品库的匹配结果，适合进一步查看详情。",
        f"它的{selling_point}可以作为本轮推荐的参考点。",
    )


def _selling_point(product: Product) -> str:
    for value in [
        product.highlight_short,
        product.product_highlight,
        *(product.target_user_tags or []),
        *(product.suitable_scenarios or []),
        *(product.tags or []),
    ]:
        text = _clean_reason(str(value or ""))
        if text:
            return text[:36]
    return product.brand or product.name[:18]


def _scenario_text(product: Product) -> str:
    values = [*product.suitable_scenarios, *product.target_user_tags, product.sub_category or ""]
    return "、".join(list(dict.fromkeys(item for item in values if item))[:2]) or "日常"


def _join_two_sentences(first: str, second: str) -> str:
    return f"{first.rstrip('。！？；;，,') }。{second.rstrip('。！？；;，,') }。"


def _clean_reason(reason: str) -> str:
    return (
        reason.removeprefix("匹配")
        .removeprefix("贴合问题标签:")
        .removeprefix("购物车偏好:")
    )
