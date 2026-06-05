from __future__ import annotations

import json
from typing import Any

from app.llm.base import BaseLLMClient
from app.models.agent import CandidateProduct, DialogueFlow, ParsedQuery
from app.models.domain import (
    ComparisonConclusion,
    ComparisonData,
    ComparisonDimension,
    ComparisonDimensionItem,
    IntentType,
    Product,
    ProductCard,
    ProductPresentation,
)


class ScenePresentationBuilder:
    """Build per-product presentation fields without changing ranking or product facts."""

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self.llm_client = llm_client
        self.last_llm_called = False
        self.last_call_debug: dict[str, Any] = {}
        self.last_debug: dict[str, Any] = {}

    def build(
        self,
        *,
        parsed_query: ParsedQuery,
        flow: DialogueFlow,
        cards: list[ProductCard],
        products: list[Product],
        candidates: list[CandidateProduct],
        use_llm: bool,
    ) -> tuple[list[ProductCard], ComparisonData | None]:
        self.last_llm_called = False
        self.last_call_debug = {}
        scene_type = self.scene_type(flow)
        self.last_debug = {
            "scene_type": scene_type,
            "llm_required": use_llm,
            "llm_call_attempted": False,
            "llm_is_mock": self.llm_client.__class__.__name__ == "MockLLMClient",
            "http_request_sent": False,
            "http_request_succeeded": False,
            "duration_ms": 0,
            "raw_llm_output": None,
            "json_parse_succeeded": False,
            "parsed_items": [],
            "candidate_sku_ids": [card.sku_id for card in cards],
            "valid_sku_ids": [],
            "invalid_sku_ids": [],
            "missing_sku_ids": [],
            "validation_errors": [],
            "fallback_reason": None,
            "content_source_by_sku": {},
            "issues": [],
        }
        if not cards:
            return cards, None
        if flow == DialogueFlow.COMPARISON:
            return self._build_comparison(
                parsed_query=parsed_query,
                cards=cards,
                products=products,
                candidates=candidates,
                use_llm=use_llm,
            )
        if flow in {
            DialogueFlow.RECOMMENDATION,
            DialogueFlow.FILTERING,
            DialogueFlow.REFINEMENT,
            DialogueFlow.EXCLUSION,
            DialogueFlow.NO_RESULT,
        }:
            return self._build_recommendation(
                parsed_query=parsed_query,
                cards=cards,
                products=products,
                candidates=candidates,
                use_llm=use_llm,
            ), None
        return cards, None

    @staticmethod
    def scene_type(flow: DialogueFlow) -> str | None:
        if flow == DialogueFlow.COMPARISON:
            return "comparison"
        if flow in {
            DialogueFlow.RECOMMENDATION,
            DialogueFlow.FILTERING,
            DialogueFlow.REFINEMENT,
            DialogueFlow.EXCLUSION,
            DialogueFlow.NO_RESULT,
        }:
            return "recommendation"
        if flow == DialogueFlow.PRODUCT_QA:
            return "detail"
        if flow == DialogueFlow.SCENE_BUNDLE:
            return "bundle"
        return None

    def recommendation_intro(self, parsed_query: ParsedQuery, cards: list[ProductCard]) -> str:
        count = len(cards)
        category = parsed_query.sub_category or parsed_query.category or (cards[0].sub_category or cards[0].category)
        constraints = []
        if parsed_query.price_range.max is not None:
            constraints.append(f"{parsed_query.price_range.max:g}元以内")
        if parsed_query.positive_constraints:
            constraints.extend(parsed_query.positive_constraints[:2])
        if parsed_query.brands_include:
            constraints.extend(parsed_query.brands_include[:2])
        if constraints:
            return f"结合你的{ '、'.join(constraints) }需求，为你筛选了 {count} 款{category}："
        return f"根据你的需求，为你筛选了 {count} 款{category}："

    def comparison_intro(self, parsed_query: ParsedQuery, cards: list[ProductCard]) -> str:
        dimensions = _comparison_dimensions(parsed_query)
        if dimensions:
            return f"这 {len(cards)} 款商品各有侧重，我从{'、'.join(dimensions[:3])}几个方面做了对比："
        return f"这 {len(cards)} 款商品各有侧重，我按价格、亮点和适用需求做了对比："

    def _build_recommendation(
        self,
        *,
        parsed_query: ParsedQuery,
        cards: list[ProductCard],
        products: list[Product],
        candidates: list[CandidateProduct],
        use_llm: bool,
    ) -> list[ProductCard]:
        llm_items = self._generate_recommendation_items(parsed_query, cards, products, candidates) if use_llm else {}
        cards_by_sku = {card.sku_id: card for card in cards}
        merged: list[ProductCard] = []
        for index, card in enumerate(cards, start=1):
            item = llm_items.get(card.sku_id)
            if item and _nullable_text(item.get("reason")):
                presentation = ProductPresentation(
                    type="recommendation",
                    option_label=_option_label(index),
                    reason=str(item.get("reason", "")).strip(),
                    trade_off=_nullable_text(item.get("trade_off")),
                    content_source="llm",
                )
            else:
                if item is None and llm_items:
                    self.last_debug["issues"].append(f"missing_llm_item:{card.sku_id}")
                elif item is not None:
                    self.last_debug["validation_errors"].append(f"empty_reason:{card.sku_id}")
                presentation = self._recommendation_fallback(card=card, index=index, parsed_query=parsed_query)
            self.last_debug["content_source_by_sku"][card.sku_id] = presentation.content_source
            merged.append(cards_by_sku[card.sku_id].model_copy(update={"presentation": presentation}))
        self.last_debug["missing_sku_ids"] = [card.sku_id for card in cards if card.sku_id not in llm_items]
        if not llm_items and not self.last_debug.get("fallback_reason"):
            self.last_debug["fallback_reason"] = "llm_not_required" if not use_llm else "no_valid_llm_items"
        return merged

    def _build_comparison(
        self,
        *,
        parsed_query: ParsedQuery,
        cards: list[ProductCard],
        products: list[Product],
        candidates: list[CandidateProduct],
        use_llm: bool,
    ) -> tuple[list[ProductCard], ComparisonData]:
        payload = self._generate_comparison_payload(parsed_query, cards, products, candidates) if use_llm else {}
        item_payloads = payload.get("items") if isinstance(payload.get("items"), list) else []
        allowed = {card.sku_id for card in cards}
        by_sku = self._valid_item_map(item_payloads, allowed)
        merged = []
        for card in cards:
            item = by_sku.get(card.sku_id)
            if item and item.get("summary"):
                presentation = ProductPresentation(
                    type="comparison",
                    summary=str(item.get("summary", "")).strip(),
                    advantages=_string_list(item.get("advantages"))[:4],
                    trade_off=_nullable_text(item.get("trade_off")),
                    suitable_for=_nullable_text(item.get("suitable_for")),
                    content_source="llm",
                )
            else:
                presentation = self._comparison_fallback(card)
            self.last_debug["content_source_by_sku"][card.sku_id] = presentation.content_source
            merged.append(card.model_copy(update={"presentation": presentation}))
        self.last_debug["missing_sku_ids"] = [card.sku_id for card in cards if card.sku_id not in by_sku]
        if not by_sku and not self.last_debug.get("fallback_reason"):
            self.last_debug["fallback_reason"] = "llm_not_required" if not use_llm else "no_valid_llm_items"
        comparison_data = self._comparison_data(payload, parsed_query, merged)
        return merged, comparison_data

    def _generate_recommendation_items(
        self,
        parsed_query: ParsedQuery,
        cards: list[ProductCard],
        products: list[Product],
        candidates: list[CandidateProduct],
    ) -> dict[str, dict[str, Any]]:
        raw = self._call_llm(
            intent=IntentType.RECOMMEND,
            message=parsed_query.raw_message,
            context=self._recommendation_prompt(parsed_query, cards, products, candidates),
            product_names=[card.name for card in cards],
        )
        payload = self._parse_llm_json(raw)
        if not payload:
            self.last_debug["issues"].append("recommendation_json_parse_failed")
            return {}
        items = payload.get("items")
        if not isinstance(items, list):
            self.last_debug["issues"].append("recommendation_items_missing")
            self.last_debug["validation_errors"].append("items_missing_or_not_list")
            return {}
        self.last_debug["parsed_items"] = _debug_items(items)
        return self._valid_item_map(items, {card.sku_id for card in cards})

    def _generate_comparison_payload(
        self,
        parsed_query: ParsedQuery,
        cards: list[ProductCard],
        products: list[Product],
        candidates: list[CandidateProduct],
    ) -> dict[str, Any]:
        raw = self._call_llm(
            intent=IntentType.COMPARE,
            message=parsed_query.raw_message,
            context=self._comparison_prompt(parsed_query, cards, products, candidates),
            product_names=[card.name for card in cards],
        )
        payload = self._parse_llm_json(raw)
        if not payload:
            self.last_debug["issues"].append("comparison_json_parse_failed")
            return {}
        items = payload.get("items")
        if isinstance(items, list):
            self.last_debug["parsed_items"] = _debug_items(items)
        return payload

    def _call_llm(self, *, intent: IntentType, message: str, context: str, product_names: list[str]) -> str:
        try:
            self.last_llm_called = True
            raw = self.llm_client.generate_response(
                intent=intent,
                message=message,
                context=context,
                product_names=product_names,
            )
            self.last_call_debug = dict(getattr(self.llm_client, "last_call_debug", {}) or {})
            self.last_debug.update(_llm_debug_summary(self.last_call_debug))
            self.last_debug["raw_llm_output"] = _truncate(raw)
            return raw
        except Exception as exc:
            self.last_debug["issues"].append(f"llm_exception:{exc.__class__.__name__}")
            self.last_debug["validation_errors"].append(f"llm_exception:{exc.__class__.__name__}")
            self.last_debug["fallback_reason"] = "llm_exception"
            return ""

    def _valid_item_map(self, items: list[Any], allowed: set[str]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                self.last_debug["issues"].append("invalid_item_type")
                self.last_debug["validation_errors"].append("invalid_item_type")
                continue
            sku_id = str(item.get("sku_id") or "").strip()
            if sku_id not in allowed:
                self.last_debug["issues"].append(f"illegal_sku_id:{sku_id}")
                self.last_debug["invalid_sku_ids"].append(sku_id)
                self.last_debug["validation_errors"].append(f"illegal_sku_id:{sku_id}")
                continue
            if sku_id in result:
                self.last_debug["issues"].append(f"duplicate_sku_id:{sku_id}")
                self.last_debug["validation_errors"].append(f"duplicate_sku_id:{sku_id}")
                continue
            result[sku_id] = item
        self.last_debug["valid_sku_ids"] = list(result)
        return result

    def _parse_llm_json(self, raw: str) -> dict[str, Any]:
        payload, parse_debug = _loads_json_object_with_debug(raw)
        self.last_debug["cleaned_llm_output"] = parse_debug.get("cleaned_text")
        self.last_debug["json_parse_succeeded"] = bool(payload)
        if parse_debug.get("error_type"):
            self.last_debug["json_parse_error"] = parse_debug
            self.last_debug["validation_errors"].append(f"json_parse:{parse_debug['error_type']}")
            self.last_debug.setdefault("fallback_reason", "json_parse_failed")
            if self.last_debug.get("fallback_reason") is None:
                self.last_debug["fallback_reason"] = "json_parse_failed"
        return payload

    def _comparison_data(self, payload: dict[str, Any], parsed_query: ParsedQuery, cards: list[ProductCard]) -> ComparisonData:
        allowed = {card.sku_id for card in cards}
        raw_dimensions = payload.get("comparison_data", {}).get("dimensions") if isinstance(payload.get("comparison_data"), dict) else payload.get("dimensions")
        dimensions: list[ComparisonDimension] = []
        if isinstance(raw_dimensions, list):
            for raw in raw_dimensions[:5]:
                if not isinstance(raw, dict):
                    continue
                name = str(raw.get("name") or "").strip()
                if not name:
                    continue
                items = []
                for raw_item in raw.get("items") or []:
                    if not isinstance(raw_item, dict):
                        continue
                    sku_id = str(raw_item.get("sku_id") or "").strip()
                    if sku_id in allowed:
                        items.append(ComparisonDimensionItem(sku_id=sku_id, value=str(raw_item.get("value") or "").strip()))
                better = str(raw.get("better_sku_id") or "").strip() or None
                if better not in allowed:
                    if better:
                        self.last_debug["issues"].append(f"illegal_better_sku_id:{better}")
                    better = None
                if items:
                    dimensions.append(ComparisonDimension(name=name, items=items, better_sku_id=better))
        if not dimensions:
            dimensions = self._fallback_dimensions(parsed_query, cards)
        conclusion = self._comparison_conclusion(payload, cards)
        return ComparisonData(dimensions=dimensions, conclusion=conclusion)

    def _comparison_conclusion(self, payload: dict[str, Any], cards: list[ProductCard]) -> ComparisonConclusion:
        allowed = {card.sku_id for card in cards}
        raw = payload.get("comparison_data", {}).get("conclusion") if isinstance(payload.get("comparison_data"), dict) else payload.get("conclusion")
        if isinstance(raw, dict):
            recommended = str(raw.get("recommended_sku_id") or "").strip() or None
            alternative = str(raw.get("alternative_sku_id") or "").strip() or None
            if recommended not in allowed:
                if recommended:
                    self.last_debug["issues"].append(f"illegal_recommended_sku_id:{recommended}")
                recommended = None
            if alternative not in allowed:
                if alternative:
                    self.last_debug["issues"].append(f"illegal_alternative_sku_id:{alternative}")
                alternative = None
            if recommended:
                return ComparisonConclusion(
                    recommended_sku_id=recommended,
                    reason=str(raw.get("reason") or "").strip() or self._default_conclusion_reason(cards[0]),
                    alternative_sku_id=alternative,
                    alternative_reason=_nullable_text(raw.get("alternative_reason")),
                )
        best = cards[0]
        alt = cards[1] if len(cards) > 1 else None
        return ComparisonConclusion(
            recommended_sku_id=best.sku_id,
            reason=self._default_conclusion_reason(best),
            alternative_sku_id=alt.sku_id if alt else None,
            alternative_reason=f"{alt.name}也可以作为对照选择，价格和亮点可结合卡片继续看。" if alt else None,
        )

    def _fallback_dimensions(self, parsed_query: ParsedQuery, cards: list[ProductCard]) -> list[ComparisonDimension]:
        dimensions = []
        dimensions.append(
            ComparisonDimension(
                name="价格",
                items=[ComparisonDimensionItem(sku_id=card.sku_id, value=f"¥{card.price:g}") for card in cards],
                better_sku_id=min(cards, key=lambda item: item.price).sku_id if cards else None,
            )
        )
        dimensions.append(
            ComparisonDimension(
                name="匹配理由",
                items=[ComparisonDimensionItem(sku_id=card.sku_id, value=_short_text(card.reason, 80)) for card in cards],
                better_sku_id=None,
            )
        )
        if any(card.highlight_short for card in cards):
            dimensions.append(
                ComparisonDimension(
                    name="商品亮点",
                    items=[ComparisonDimensionItem(sku_id=card.sku_id, value=card.highlight_short or _tags_text(card)) for card in cards],
                    better_sku_id=None,
                )
            )
        return dimensions[:5]

    def _recommendation_prompt(
        self,
        parsed_query: ParsedQuery,
        cards: list[ProductCard],
        products: list[Product],
        candidates: list[CandidateProduct],
    ) -> str:
        return (
            "STRUCTURED_PRESENTATION_JSON\n"
            "Task: recommendation_presentation\n"
            "Return only JSON: {\"items\":[{\"sku_id\":\"...\",\"reason\":\"...\",\"trade_off\":null}]}.\n"
            "Rules: use only candidate sku_id values; do not return option_label, ranking, price, stock, image, or recommendation grade; "
            "reason must connect current user need with verified facts; trade_off must be fact-based or null.\n"
            f"User need: {parsed_query.raw_message}\n"
            f"Candidate facts:\n{self._fact_lines(cards, products, candidates)}"
        )

    def _comparison_prompt(
        self,
        parsed_query: ParsedQuery,
        cards: list[ProductCard],
        products: list[Product],
        candidates: list[CandidateProduct],
    ) -> str:
        return (
            "STRUCTURED_PRESENTATION_JSON\n"
            "Task: comparison_presentation\n"
            "Return only JSON with items and comparison_data. "
            "items fields: sku_id, summary, advantages array, trade_off null/string, suitable_for string. "
            "comparison_data fields: dimensions[{name,items[{sku_id,value}],better_sku_id}], conclusion{recommended_sku_id,reason,alternative_sku_id,alternative_reason}. "
            "All sku_id values must be from candidate facts; better_sku_id may be null if no clear winner.\n"
            f"User need: {parsed_query.raw_message}\n"
            f"Candidate facts:\n{self._fact_lines(cards, products, candidates)}"
        )

    @staticmethod
    def _fact_lines(cards: list[ProductCard], products: list[Product], candidates: list[CandidateProduct]) -> str:
        products_by_sku = {product.sku_id: product for product in products}
        candidates_by_sku = {candidate.sku_id: candidate for candidate in candidates}
        lines = []
        for card in cards:
            product = products_by_sku.get(card.sku_id)
            candidate = candidates_by_sku.get(card.sku_id)
            facts = [
                f"sku_id={card.sku_id}",
                f"name={card.name}",
                f"brand={card.brand}",
                f"category={card.category}/{card.sub_category or ''}",
                f"price={card.price:g}",
                f"stock={card.stock}",
                f"reason={card.reason}",
                f"highlight_short={card.highlight_short}",
                f"suitable_scenarios={','.join(card.suitable_scenarios[:5])}",
                f"target_user_tags={','.join(card.target_user_tags[:5])}",
                f"tags={','.join(card.tags[:6])}",
                f"matched_reasons={','.join(card.matched_reasons[:5])}",
                f"score={card.score}",
            ]
            if product:
                facts.append(f"reviews_summary={product.reviews_summary}")
                facts.append(f"highlight_detail={product.highlight_detail}")
            if candidate:
                facts.append(f"risk_notes={','.join(candidate.risk_notes[:3])}")
            lines.append("- " + " | ".join(facts))
        return "\n".join(lines)

    def _recommendation_fallback(self, *, card: ProductCard, index: int, parsed_query: ParsedQuery) -> ProductPresentation:
        reason = _recommendation_fallback_reason(card=card, parsed_query=parsed_query)
        return ProductPresentation(
            type="recommendation",
            option_label=_option_label(index),
            reason=reason,
            trade_off=None,
            content_source="fallback",
        )

    @staticmethod
    def _comparison_fallback(card: ProductCard) -> ProductPresentation:
        return ProductPresentation(
            type="comparison",
            summary=card.reason or card.highlight_short or f"{card.name}来自当前对比范围。",
            advantages=[item for item in [card.highlight_short, *_clean_list(card.matched_reasons), *_clean_list(card.tags)] if item][:3],
            trade_off=None,
            suitable_for=_tags_text(card) or None,
            content_source="fallback",
        )

    @staticmethod
    def _default_conclusion_reason(card: ProductCard) -> str:
        return f"结合当前需求和商品排序，可以先重点看{card.name}；它的匹配理由和基础信息都在商品卡片中。"


def _loads_json_object(raw: str) -> dict[str, Any]:
    return _loads_json_object_with_debug(raw)[0]


def _loads_json_object_with_debug(raw: str) -> tuple[dict[str, Any], dict[str, Any]]:
    debug: dict[str, Any] = {
        "raw_text": _truncate(raw),
        "cleaned_text": None,
        "error_type": None,
        "error_message": None,
        "error_position": None,
    }
    if not raw:
        debug["error_type"] = "empty_output"
        return {}, debug
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            text = text[start:end + 1]
    debug["cleaned_text"] = _truncate(text)
    if not text.startswith("{"):
        debug["error_type"] = "json_object_not_found"
        return {}, debug
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        debug["error_type"] = "json_decode_error"
        debug["error_message"] = exc.msg
        debug["error_position"] = exc.pos
        return {}, debug
    except Exception as exc:
        debug["error_type"] = exc.__class__.__name__
        debug["error_message"] = str(exc)
        return {}, debug
    if not isinstance(data, dict):
        debug["error_type"] = "json_root_not_object"
        return {}, debug
    return data, debug


def _option_label(index: int) -> str:
    labels = ["方案一", "方案二", "方案三", "方案四", "方案五"]
    return labels[index - 1] if index <= len(labels) else f"方案{index}"


def _nullable_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    return text


def _llm_debug_summary(call_debug: dict[str, Any]) -> dict[str, Any]:
    if not call_debug:
        return {
            "llm_call_attempted": True,
            "llm_is_mock": False,
            "http_request_sent": False,
            "http_request_succeeded": False,
            "duration_ms": 0,
        }
    return {
        "llm_call_attempted": bool(call_debug.get("llm_call_attempted", True)),
        "llm_provider": call_debug.get("llm_provider"),
        "llm_is_mock": bool(call_debug.get("llm_is_mock")),
        "http_request_sent": bool(call_debug.get("http_request_sent")),
        "http_request_succeeded": bool(call_debug.get("http_request_succeeded")),
        "http_status_code": call_debug.get("http_status_code"),
        "raw_output_received": bool(call_debug.get("raw_output_received")),
        "duration_ms": call_debug.get("duration_ms", 0),
        "llm_fallback_triggered": bool(call_debug.get("fallback_triggered")),
        "llm_fallback_reason": call_debug.get("fallback_reason"),
    }


def _debug_items(items: list[Any]) -> list[dict[str, Any]]:
    debug_items = []
    for item in items[:10]:
        if not isinstance(item, dict):
            debug_items.append({"type": type(item).__name__})
            continue
        debug_items.append(
            {
                "sku_id": item.get("sku_id"),
                "has_reason": bool(_nullable_text(item.get("reason"))),
                "has_summary": bool(_nullable_text(item.get("summary"))),
                "trade_off": _nullable_text(item.get("trade_off")),
            }
        )
    return debug_items


def _recommendation_fallback_reason(*, card: ProductCard, parsed_query: ParsedQuery) -> str:
    need_text = _need_text(parsed_query)
    facts = _product_fact_parts(card)
    fact_text = "，".join(facts[:3])
    price_text = f"¥{card.price:g}"
    brand_name = f"{card.brand} {card.name}".strip()
    if fact_text:
        return f"{brand_name} 当前价格 {price_text}，可取点是{fact_text}；结合你关注的{need_text}，可以作为一个具体方案查看。"
    if card.reason:
        return f"{brand_name} 当前价格 {price_text}，检索理由是{_short_text(card.reason, 70)}；结合你关注的{need_text}，可以继续看卡片细节。"
    return f"{brand_name} 当前价格 {price_text}，和你当前想看的{parsed_query.sub_category or parsed_query.category or '商品'}方向比较接近。"


def _need_text(parsed_query: ParsedQuery) -> str:
    needs = []
    if parsed_query.price_range.max is not None:
        needs.append(f"{parsed_query.price_range.max:g}元以内")
    needs.extend(parsed_query.positive_constraints[:3])
    if parsed_query.brands_include:
        needs.extend(parsed_query.brands_include[:2])
    return "、".join(list(dict.fromkeys(item for item in needs if item))) or parsed_query.sub_category or parsed_query.category or "当前需求"


def _product_fact_parts(card: ProductCard) -> list[str]:
    parts = []
    for value in [
        card.highlight_short,
        *_clean_list(card.matched_reasons),
        *card.suitable_scenarios,
        *card.target_user_tags,
        *card.non_standard_query_tags,
        *card.tags,
    ]:
        text = _clean_fact_text(value)
        if text and text not in parts:
            parts.append(text)
    return parts


def _clean_fact_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if not text or text in {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选"}:
        return ""
    return text.removeprefix("匹配").removeprefix("贴合问题标签:").removeprefix("购物车偏好:")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _clean_list(values: list[str]) -> list[str]:
    blocked = {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选"}
    return [
        item.removeprefix("匹配").removeprefix("贴合问题标签:").removeprefix("购物车偏好:")
        for item in values
        if item and item not in blocked
    ]


def _tags_text(card: ProductCard) -> str:
    values = [*card.suitable_scenarios, *card.target_user_tags, *card.tags, *_clean_list(card.matched_reasons)]
    return "、".join(list(dict.fromkeys(item for item in values if item))[:3])


def _short_text(text: str | None, limit: int) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _truncate(text: str | None, limit: int = 2000) -> str | None:
    if text is None:
        return None
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _comparison_dimensions(parsed_query: ParsedQuery) -> list[str]:
    dimensions = []
    text = parsed_query.raw_message
    for token, label in [
        ("拍照", "拍照"),
        ("影像", "拍照"),
        ("续航", "续航"),
        ("价格", "价格"),
        ("预算", "价格"),
        ("轻薄", "轻薄"),
        ("性能", "性能"),
        ("通勤", "通勤"),
    ]:
        if token in text and label not in dimensions:
            dimensions.append(label)
    if parsed_query.price_range.max is not None and "价格" not in dimensions:
        dimensions.append("价格")
    return dimensions
