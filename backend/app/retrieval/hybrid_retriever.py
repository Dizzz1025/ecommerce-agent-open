import math
import re
from collections import Counter
from typing import Any

from app.ml.local_models import LocalModelManager
from app.models.agent import CandidateProduct, ParsedQuery
from app.models.domain import Product, SessionState
from app.repositories.product_repository import ProductRepository
from app.retrieval.base import BaseRetriever
from app.retrieval.document_builder import ProductDocumentBuilder


class HybridRetriever(BaseRetriever):
    """Hybrid product retrieval for the demo.

    It combines strict metadata filtering, keyword overlap, a lightweight
    character n-gram semantic score, constraint matching, and memory
    preference boosts. It has no heavy model dependency, so the demo remains
    easy to run; a sentence-transformers backend can replace `_semantic_score`
    later.
    """

    def __init__(
        self,
        product_repository: ProductRepository,
        document_builder: ProductDocumentBuilder | None = None,
        local_models: LocalModelManager | None = None,
    ) -> None:
        self.product_repository = product_repository
        self.document_builder = document_builder or ProductDocumentBuilder()
        self.local_models = local_models
        self._doc_cache: dict[str, str] = {}

    def search(self, query: str, top_k: int = 5) -> list[Product]:
        parsed = ParsedQuery(raw_message=query, intent="recommend", rewritten_query=query)
        candidates = self.retrieve(parsed_query=parsed, state=None, top_k=top_k)
        by_id = {item.sku_id: item for item in self.product_repository.list_products()}
        return [by_id[item.sku_id] for item in candidates if item.sku_id in by_id]

    def retrieve(
        self,
        parsed_query: ParsedQuery,
        state: SessionState | None,
        top_k: int = 5,
        broad: bool = False,
    ) -> list[CandidateProduct]:
        query = parsed_query.rewritten_query or parsed_query.raw_message
        enhanced_query = self._enhanced_query(parsed_query)
        query_terms = self._tokens(enhanced_query)
        filtered_candidates: list[CandidateProduct] = []
        preliminary: list[dict[str, Any]] = []
        for product in self.product_repository.list_products():
            filter_reason = self._hard_filter(product, parsed_query, broad=broad)
            if filter_reason is not None:
                filtered_candidates.append(self._candidate(product, score=0, matched_reasons=[], raw_scores={}, filtered_out=True, filter_reason=filter_reason))
                continue

            document = self._document(product)
            keyword_score = self._keyword_score(query_terms, document)
            lexical_semantic_score = self._semantic_score(enhanced_query, document)
            constraint_score, matched_reasons = self._constraint_score(product, document, parsed_query)
            enhancement_score, enhancement_reasons, enhancement_matches = self._enhancement_score(product, parsed_query, enhanced_query)
            preference_score = self._preference_score(product, state)
            price_fit_score = self._price_fit_score(product, parsed_query)
            preliminary.append(
                {
                    "product": product,
                    "document": document,
                    "keyword_score": keyword_score,
                    "lexical_semantic_score": lexical_semantic_score,
                    "constraint_score": constraint_score,
                    "enhancement_score": enhancement_score,
                    "matched_reasons": matched_reasons,
                    "enhancement_reasons": enhancement_reasons,
                    "enhancement_matches": enhancement_matches,
                    "preference_score": preference_score,
                    "price_fit_score": price_fit_score,
                }
            )

        documents = [item["document"] for item in preliminary]
        model_scores = self.local_models.semantic_scores(enhanced_query, documents) if self.local_models else {}
        rerank_scores = self.local_models.rerank_scores(enhanced_query, documents) if self.local_models else []

        candidates: list[CandidateProduct] = []
        for index, item in enumerate(preliminary):
            product = item["product"]
            keyword_score = item["keyword_score"]
            lexical_semantic_score = item["lexical_semantic_score"]
            constraint_score = item["constraint_score"]
            enhancement_score = item["enhancement_score"]
            preference_score = item["preference_score"]
            price_fit_score = item["price_fit_score"]
            matched_reasons = list(dict.fromkeys([*item["matched_reasons"], *item["enhancement_reasons"]]))
            bge_score = _safe_score(model_scores.get("bge_embedding"), index)
            text2vec_score = _safe_score(model_scores.get("text2vec_embedding"), index)
            reranker_score = _safe_score(rerank_scores, index)
            semantic_parts = [score for score in [bge_score, text2vec_score] if score is not None]
            model_semantic_score = sum(semantic_parts) / len(semantic_parts) if semantic_parts else None
            semantic_score = max(lexical_semantic_score, model_semantic_score or 0.0)

            if reranker_score is not None:
                final_score = (
                    0.18 * keyword_score
                    + 0.24 * semantic_score
                    + 0.22 * constraint_score
                    + 0.08 * enhancement_score
                    + 0.10 * price_fit_score
                    + 0.08 * preference_score
                    + 0.10 * reranker_score
                )
            else:
                final_score = (
                    0.24 * keyword_score
                    + 0.28 * semantic_score
                    + 0.22 * constraint_score
                    + 0.12 * enhancement_score
                    + 0.10 * price_fit_score
                    + 0.04 * preference_score
                )
            if parsed_query.category and product.category == parsed_query.category:
                final_score += 0.15
            if parsed_query.sub_category and product.sub_category == parsed_query.sub_category:
                final_score += 0.18
            if parsed_query.brands_include and any(brand in product.brand for brand in parsed_query.brands_include):
                final_score += 0.08
            if "性价比" in parsed_query.positive_constraints:
                final_score += _value_price_adjustment(product)

            if final_score <= 0 and not broad:
                continue

            candidates.append(
                self._candidate(
                    product,
                    score=final_score,
                    matched_reasons=matched_reasons or self._default_reasons(product, parsed_query),
                    raw_scores={
                        "keyword": keyword_score,
                        "semantic": semantic_score,
                        "lexical_semantic": lexical_semantic_score,
                        "bge_embedding": bge_score or 0.0,
                        "text2vec_embedding": text2vec_score or 0.0,
                        "bge_reranker": reranker_score or 0.0,
                        "constraint": constraint_score,
                        "enhancement": enhancement_score,
                        "preference": preference_score,
                        "price_fit": price_fit_score,
                    },
                    enhancement_matches=item["enhancement_matches"],
                )
            )

        candidates = [item for item in candidates if not item.filtered_out]
        candidates.sort(key=lambda item: item.score, reverse=True)
        return [*candidates[: max(top_k * 3, top_k)], *filtered_candidates]

    def retrieve_by_references(
        self,
        parsed_query: ParsedQuery,
        state: SessionState,
        top_k: int = 5,
    ) -> list[CandidateProduct]:
        products: list[Product] = []
        for ref in [*parsed_query.mentioned_products, *parsed_query.compare_targets, *parsed_query.referents]:
            sku_id = state.dialogue_state_tracking.resolved_references.get(ref)
            product = self.product_repository.get_product(ref) or (self.product_repository.get_product(sku_id) if sku_id else self.product_repository.find_by_text_reference(ref))
            if product and product.sku_id not in {item.sku_id for item in products}:
                products.append(product)
        for ref in parsed_query.compare_targets:
            if "购物车" in ref:
                for cart_item in state.cart.items:
                    product = self.product_repository.get_product(cart_item.sku_id)
                    if product and product.sku_id not in {item.sku_id for item in products}:
                        products.append(product)
        if not products and state.goods.last_recommendations:
            for record in state.goods.last_recommendations[:top_k]:
                product = self.product_repository.get_product(record.sku_id)
                if not product:
                    continue
                if parsed_query.category and product.category != parsed_query.category:
                    continue
                if parsed_query.sub_category and product.sub_category != parsed_query.sub_category:
                    continue
                if product:
                    products.append(product)
        if not products:
            return self.retrieve(parsed_query=parsed_query, state=state, top_k=top_k)
        return [
            self._candidate(
                product,
                score=1.0 - index * 0.05,
                matched_reasons=["来自上一轮推荐或用户指代", *self._default_reasons(product, parsed_query)],
                raw_scores={"reference": 1.0},
            )
            for index, product in enumerate(products[:top_k])
        ]

    def _hard_filter(self, product: Product, parsed_query: ParsedQuery, *, broad: bool) -> str | None:
        if not broad and parsed_query.category and product.category != parsed_query.category:
            return "category_mismatch"
        if not broad and parsed_query.sub_category and product.sub_category != parsed_query.sub_category:
            return "sub_category_mismatch"
        if not broad and _query_is_beverage(parsed_query) and product.sub_category not in _beverage_sub_categories():
            return "not_beverage"
        if not broad and _query_is_for_child(parsed_query) and _product_is_not_child_drink(product, self._document(product)):
            return "not_child_friendly_beverage"
        if parsed_query.price_range.min is not None and product.price < parsed_query.price_range.min:
            return "price_below_min"
        if parsed_query.price_range.max is not None and product.price > parsed_query.price_range.max:
            return "price_above_max"
        if parsed_query.brands_include and not any(brand in product.brand for brand in parsed_query.brands_include):
            return "brand_not_included"
        if parsed_query.brands_exclude and any(brand in product.brand for brand in parsed_query.brands_exclude):
            return "brand_excluded"
        document = self._document(product)
        for term in parsed_query.negative_constraints:
            if term in {"太贵", "贵"}:
                continue
            if _negative_satisfied_by_safe_word(term, document):
                continue
            if term and term in document:
                return f"negative_constraint:{term}"
        return None

    def _constraint_score(self, product: Product, document: str, parsed_query: ParsedQuery) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        for term in parsed_query.positive_constraints:
            if not term:
                continue
            if term in document:
                score += 1.0
                reasons.append(term)
        if parsed_query.price_range.max is not None and product.price <= parsed_query.price_range.max:
            score += 0.8
            reasons.append(f"{parsed_query.price_range.max:g}元以内")
        if parsed_query.price_range.min is not None and parsed_query.price_range.min > 1 and product.price >= parsed_query.price_range.min:
            score += 0.5
            reasons.append(f"{parsed_query.price_range.min:g}元以上")
        if parsed_query.brands_exclude:
            reasons.append("已避开指定品牌")
        if parsed_query.negative_constraints:
            reasons.append("已排除否定条件")
        return min(score / max(len(parsed_query.positive_constraints) + 1, 1), 1.0), list(dict.fromkeys(reasons))

    def _enhancement_score(self, product: Product, parsed_query: ParsedQuery, enhanced_query: str) -> tuple[float, list[str], dict[str, Any]]:
        query_text = enhanced_query.lower()
        score = 0.0
        reasons: list[str] = []
        matched_tags: list[str] = []
        matched_scenarios: list[str] = []
        matched_users: list[str] = []
        matched_fields: list[str] = []

        for tag in product.non_standard_query_tags:
            similarity = self._semantic_score(query_text, tag.lower())
            if _direct_or_semantic_match(query_text, tag, similarity, threshold=0.34):
                score += 1.4 if tag in query_text else 1.0
                matched_tags.append(tag)
                reasons.append(f"贴合问题标签:{tag}")
        for scenario in product.suitable_scenarios:
            similarity = self._semantic_score(query_text, scenario.lower())
            if _direct_or_semantic_match(query_text, scenario, similarity, threshold=0.42):
                score += 0.7
                matched_scenarios.append(scenario)
                reasons.append(f"适合{scenario}")
        target_text = " ".join([parsed_query.target_user or "", *parsed_query.positive_constraints])
        for user_tag in product.target_user_tags:
            similarity = self._semantic_score(f"{query_text} {target_text}".lower(), user_tag.lower())
            if _direct_or_semantic_match(f"{query_text} {target_text}".lower(), user_tag, similarity, threshold=0.46):
                score += 0.6
                matched_users.append(user_tag)
                reasons.append(f"适合{user_tag}")

        field_hits = {
            "highlight_short": product.highlight_short,
            "highlight_detail": product.highlight_detail,
            "product_highlight": product.product_highlight,
        }
        query_terms = [
            term for term in [
                *parsed_query.positive_constraints,
                parsed_query.scenario or "",
                parsed_query.target_user or "",
            ]
            if term
        ]
        if not query_terms:
            query_terms = self._tokens(parsed_query.raw_message)[:8]
        for field_name, field_text in field_hits.items():
            if field_text and any(term and term in field_text for term in query_terms):
                score += 0.35
                matched_fields.append(field_name)

        matches = {
            "used_fields": _used_enhancement_fields(product),
            "matched_non_standard_query_tags": list(dict.fromkeys(matched_tags))[:5],
            "matched_suitable_scenarios": list(dict.fromkeys(matched_scenarios))[:5],
            "matched_target_user_tags": list(dict.fromkeys(matched_users))[:5],
            "matched_highlight_fields": list(dict.fromkeys(matched_fields))[:5],
            "enhancement_boost_basis": list(dict.fromkeys(reasons))[:6],
        }
        if not any(value for key, value in matches.items() if key != "used_fields"):
            matches = {"used_fields": matches["used_fields"]}
        return min(score / 3.0, 1.0), list(dict.fromkeys(reasons))[:4], matches

    @staticmethod
    def _preference_score(product: Product, state: SessionState | None) -> float:
        if not state:
            return 0.0
        score = 0.0
        preferences = state.user.global_preferences
        if any(brand in product.brand for brand in preferences.preferred_brands):
            score += 0.7
        if any(brand in product.brand for brand in preferences.excluded_brands):
            score -= 1.0
        if any(term in product.searchable_text for term in preferences.preferred_style):
            score += 0.3
        if any(term in product.searchable_text for term in preferences.avoid_terms):
            score -= 0.5
        return max(min(score, 1.0), -1.0)

    @staticmethod
    def _price_fit_score(product: Product, parsed_query: ParsedQuery) -> float:
        max_price = parsed_query.price_range.max
        if max_price is None:
            return 0.4
        if product.price > max_price:
            return 0.0
        ratio = product.price / max_price if max_price else 1
        return max(0.2, 1.0 - abs(0.75 - ratio))

    def _document(self, product: Product) -> str:
        cached = self._doc_cache.get(product.sku_id)
        if cached is None:
            cached = self.document_builder.build_text(product).lower()
            self._doc_cache[product.sku_id] = cached
        return cached

    @staticmethod
    def _keyword_score(query_terms: list[str], document: str) -> float:
        if not query_terms:
            return 0.0
        hits = sum(1 for term in query_terms if term in document)
        return min(hits / len(query_terms), 1.0)

    @staticmethod
    def _semantic_score(query: str, document: str) -> float:
        query_grams = _char_ngrams(query)
        doc_grams = _char_ngrams(document[:3000])
        if not query_grams or not doc_grams:
            return 0.0
        overlap = query_grams & doc_grams
        jaccard = len(overlap) / len(query_grams | doc_grams)
        containment = len(overlap) / len(query_grams)
        return min(math.sqrt(jaccard * containment) * 2.2, 1.0)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        compact = re.sub(r"[，。！？,.!?；;:：、]", " ", text.lower())
        raw_tokens = [item for item in compact.split() if item]
        cjk_terms = re.findall(r"[\u4e00-\u9fff]{2,6}", compact)
        tokens = raw_tokens + cjk_terms
        counter = Counter(tokens)
        return [term for term, _ in counter.most_common(20)]

    @staticmethod
    def _enhanced_query(parsed_query: ParsedQuery) -> str:
        parts = [
            parsed_query.rewritten_query or parsed_query.raw_message,
            parsed_query.raw_message,
            parsed_query.category or "",
            parsed_query.sub_category or "",
            parsed_query.scenario or "",
            parsed_query.target_user or "",
            " ".join(parsed_query.positive_constraints),
            " ".join(parsed_query.negative_constraints),
            " ".join(parsed_query.brands_include),
            " ".join(parsed_query.brands_exclude),
        ]
        raw = parsed_query.raw_message
        synonym_hints = []
        if any(term in raw for term in ["皮肤干", "有点干", "干燥", "起皮", "缺水", "拔干"]):
            synonym_hints.extend(["皮肤干燥起皮", "补水保湿推荐", "干皮"])
        if any(term in raw for term in ["屏障", "屏障修护", "屏障受损"]):
            synonym_hints.extend(["屏障修护", "修护维稳", "敏感肌修护"])
        if any(term in raw for term in ["不想黏腻", "不想粘腻", "不黏腻", "不粘腻", "不要黏腻", "不要粘腻"]):
            synonym_hints.extend(["不油腻的护肤品", "清爽肤感", "轻薄保湿"])
        if any(term in raw for term in ["送朋友", "送人", "礼物", "伴手礼"]):
            synonym_hints.extend(["送礼送什么零食合适", "礼盒", "分享"])
        if any(term in raw for term in ["通勤", "上班", "上下班"]):
            synonym_hints.extend(["上下班通勤背什么包", "通勤也能穿的运动裤", "便携", "办公"])
        if any(term in raw for term in ["健身入门", "刚开始健身", "新手健身", "健身新手"]):
            synonym_hints.extend(["健身穿什么上衣好", "运动训练者", "入门"])
        if any(term in raw for term in ["iPad", "ipad", "平板"]):
            synonym_hints.extend(["平板电脑", "适合记笔记的平板", "追剧看视频用什么平板"])
        if any(term in raw for term in ["运动鞋", "跑鞋", "跑步鞋"]):
            synonym_hints.extend(["跑步鞋推荐", "轻便不累脚的鞋", "运动训练"])
        return " ".join([*parts, *synonym_hints]).strip()

    @staticmethod
    def _default_reasons(product: Product, parsed_query: ParsedQuery) -> list[str]:
        reasons = []
        if product.sub_category:
            reasons.append(f"匹配{product.sub_category}")
        query_text = " ".join(parsed_query.positive_constraints)
        for tag in product.tags:
            if tag and tag in query_text:
                reasons.append(tag)
        if parsed_query.category:
            reasons.append("类目一致")
        return list(dict.fromkeys(reasons)) or ["来自商品库召回"]

    @staticmethod
    def _candidate(
        product: Product,
        *,
        score: float,
        matched_reasons: list[str],
        raw_scores: dict[str, float],
        filtered_out: bool = False,
        filter_reason: str | None = None,
        enhancement_matches: dict[str, Any] | None = None,
    ) -> CandidateProduct:
        return CandidateProduct(
            candidate_id=f"c_{product.sku_id}",
            product_id=product.product_id or product.sku_id,
            sku_id=product.sku_id,
            name=product.name,
            brand=product.brand,
            category=product.category,
            sub_category=product.sub_category,
            price=product.price,
            image_url=product.image_url,
            matched_reasons=list(dict.fromkeys(matched_reasons)),
            risk_notes=_risk_notes(product),
            filtered_out=filtered_out,
            filter_reason=filter_reason,
            score=round(score, 4),
            raw_scores={key: round(value, 4) for key, value in raw_scores.items()},
            enhancement_matches=enhancement_matches or {},
        )


def _char_ngrams(text: str, n: int = 2) -> set[str]:
    compact = re.sub(r"\s+", "", text.lower())
    if len(compact) < n:
        return {compact} if compact else set()
    return {compact[index:index + n] for index in range(len(compact) - n + 1)}


def _safe_score(scores: list[float] | None, index: int) -> float | None:
    if not scores or index >= len(scores):
        return None
    return float(scores[index])


def _value_price_adjustment(product: Product) -> float:
    if product.category == "数码电子" and product.sub_category == "智能手机":
        if product.price <= 4000:
            return 0.16
        if product.price <= 6000:
            return 0.06
        return -0.06
    if product.price <= 100:
        return 0.06
    if product.price <= 500:
        return 0.03
    return 0.0


def _query_is_beverage(parsed_query: ParsedQuery) -> bool:
    raw = parsed_query.raw_message
    return parsed_query.category == "食品饮料" and any(term in raw for term in ["饮料", "喝的", "喝起来", "口渴", "渴啦", "渴了", "一瓶喝"])


def _beverage_sub_categories() -> set[str]:
    return {"茶饮", "碳酸饮料", "功能饮料", "牛奶", "酸奶", "咖啡", "乳酸菌饮品"}


def _query_is_for_child(parsed_query: ParsedQuery) -> bool:
    raw = parsed_query.raw_message
    return parsed_query.target_user == "小朋友" or any(term in raw for term in ["小朋友", "4岁", "四岁", "宝宝", "孩子"]) or "儿童" in parsed_query.positive_constraints


def _product_is_not_child_drink(product: Product, document: str) -> bool:
    if product.category != "食品饮料":
        return False
    if "不含咖啡因" in document:
        return False
    if product.sub_category in {"咖啡", "功能饮料", "茶饮"}:
        return True
    if any(term in document for term in ["咖啡因", "牛磺酸", "红牛", "东鹏特饮", "可口可乐", "可乐"]):
        return True
    if _looks_like_family_pack(product.name) and product.sub_category in {"碳酸饮料", "牛奶", "酸奶"}:
        return True
    return False


def _looks_like_family_pack(text: str) -> bool:
    return bool(re.search(r"(\*|×|x)\s*\d+|\d+\s*(瓶|罐|盒|袋).*?(整箱|箱装|盒装|罐装)", text, flags=re.IGNORECASE))


def _risk_notes(product: Product) -> list[str]:
    notes = []
    summary = product.reviews_summary
    if "差评提醒" in summary:
        notes.append(summary.split("差评提醒：", 1)[-1][:60])
    return notes


def _negative_satisfied_by_safe_word(term: str, document: str) -> bool:
    if term in {"酒精", "乙醇", "酒精成分"} and any(safe in document for safe in ["不含酒精", "无酒精", "不添加酒精", "不含乙醇", "无乙醇"]):
        return True
    if term in {"糖", "甜", "甜味", "太甜"} and any(safe in document for safe in ["无糖", "0糖", "零糖", "低糖", "不甜", "非甜味"]):
        return True
    if term in {"防水"} and any(safe in document for safe in ["不防水", "非防水"]):
        return True
    if term in {"紧身", "紧身款"} and any(safe in document for safe in ["不紧身", "不会太紧身", "宽松", "微宽松", "不紧绷"]):
        return True
    if term in {"印花", "印花图案", "大logo", "大Logo", "大Logo印花", "大logo印花"} and any(safe in document for safe in ["无印花", "没有夸张的大logo", "极简", "纯色", "基础纯色"]):
        return True
    if term in {"大包装", "包装太大", "太大"} and "小包装" in document:
        return True
    if term in {"糕点", "糕点和谷物类"} and any(safe in document for safe in ["非糕点", "不是糕点"]):
        return True
    if term in {"谷物", "糕点和谷物类"} and any(safe in document for safe in ["非谷物", "不是谷物"]):
        return True
    return False


def _direct_or_semantic_match(query_text: str, label: str, similarity: float, *, threshold: float) -> bool:
    label_text = label.lower()
    if not label_text:
        return False
    if label_text in query_text or query_text in label_text:
        return True
    label_terms = set(re.findall(r"[\u4e00-\u9fff]{2,4}|[A-Za-z0-9]+", label_text))
    if label_terms and any(term in query_text for term in label_terms):
        return True
    return similarity >= threshold


def _used_enhancement_fields(product: Product) -> list[str]:
    fields: list[str] = []
    if product.product_highlight:
        fields.append("product_highlight")
    if product.highlight_short:
        fields.append("highlight_short")
    if product.highlight_detail:
        fields.append("highlight_detail")
    if product.suitable_scenarios:
        fields.append("suitable_scenarios")
    if product.target_user_tags:
        fields.append("target_user_tags")
    if product.non_standard_query_tags:
        fields.append("non_standard_query_tags")
    return fields
