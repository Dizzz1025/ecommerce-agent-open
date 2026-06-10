from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.agent import CandidateProduct, ParsedQuery
from app.models.domain import Product, ProductCard


class RecommendationPlanItem(BaseModel):
    section_id: int
    rank: int
    product_id: str | None = None
    sku_id: str
    option_label: str
    plan_type: str
    name: str
    display_title: str | None = None
    brand: str
    category: str
    sub_category: str | None = None
    price: float
    stock: int
    score: float | None = None
    facts: dict[str, Any] = Field(default_factory=dict)
    matching_points: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)
    fallback_reason: str = ""
    fallback_trade_off: str | None = None


class RecommendationPlan(BaseModel):
    request_id: str
    user_need: str
    category: str | None = None
    sub_category: str | None = None
    core_constraints: list[str] = Field(default_factory=list)
    items: list[RecommendationPlanItem] = Field(default_factory=list)


@dataclass
class ParsedPresentationEvent:
    event_type: Literal["section_start", "text_delta", "section_end"]
    section_id: int
    text: str = ""
    display_title: str | None = None


class RecommendationPresentationParser:
    """Incrementally parse SECTION markers without waiting for the full answer."""

    _start_re = re.compile(r"\[\[SECTION:(\d+)(?:\|TITLE:([^\]]+))?\]\]")
    _end_marker = "[[END_SECTION]]"

    def __init__(self) -> None:
        self._buffer = ""
        self._active_section_id: int | None = None

    def feed(self, delta: str) -> list[ParsedPresentationEvent]:
        if not delta:
            return []
        self._buffer += delta
        return self._drain(final=False)

    def finish(self) -> list[ParsedPresentationEvent]:
        return self._drain(final=True)

    def _drain(self, *, final: bool) -> list[ParsedPresentationEvent]:
        events: list[ParsedPresentationEvent] = []
        while self._buffer:
            marker = self._next_marker()
            if self._active_section_id is None:
                if marker is None:
                    self._buffer = self._possible_marker_tail(self._buffer)
                    break
                kind, start, end, section_id, display_title = marker
                if kind == "start":
                    self._buffer = self._buffer[end:]
                    self._active_section_id = section_id
                    events.append(
                        ParsedPresentationEvent(
                            "section_start",
                            section_id,
                            display_title=(display_title or "").strip() or None,
                        )
                    )
                    continue
                self._buffer = self._buffer[end:]
                continue

            if marker is None:
                text, tail = self._safe_text_and_tail(self._buffer, final=final)
                if text:
                    events.append(ParsedPresentationEvent("text_delta", self._active_section_id, text))
                self._buffer = tail
                break

            kind, start, end, section_id, display_title = marker
            if start > 0:
                text = self._buffer[:start]
                if text:
                    events.append(ParsedPresentationEvent("text_delta", self._active_section_id, text))
            if kind == "end":
                events.append(ParsedPresentationEvent("section_end", self._active_section_id))
                self._active_section_id = None
                self._buffer = self._buffer[end:]
                continue
            events.append(ParsedPresentationEvent("section_end", self._active_section_id))
            self._active_section_id = section_id
            events.append(
                ParsedPresentationEvent(
                    "section_start",
                    section_id,
                    display_title=(display_title or "").strip() or None,
                )
            )
            self._buffer = self._buffer[end:]

        if final and self._active_section_id is not None and not self._buffer:
            events.append(ParsedPresentationEvent("section_end", self._active_section_id))
            self._active_section_id = None
        return events

    def _next_marker(self) -> tuple[str, int, int, int, str | None] | None:
        start_match = self._start_re.search(self._buffer)
        end_index = self._buffer.find(self._end_marker)
        candidates: list[tuple[str, int, int, int, str | None]] = []
        if start_match is not None:
            candidates.append(
                (
                    "start",
                    start_match.start(),
                    start_match.end(),
                    int(start_match.group(1)),
                    start_match.group(2),
                )
            )
        if end_index >= 0:
            candidates.append(("end", end_index, end_index + len(self._end_marker), -1, None))
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[1])

    @staticmethod
    def _possible_marker_tail(text: str) -> str:
        marker_start = text.rfind("[[")
        if marker_start >= 0:
            return text[marker_start:]
        if text.endswith("["):
            return "["
        return ""

    @classmethod
    def _safe_text_and_tail(cls, text: str, *, final: bool) -> tuple[str, str]:
        if final:
            return text, ""
        tail = cls._possible_marker_tail(text)
        if not tail:
            return text, ""
        return text[: -len(tail)], tail


def build_recommendation_plan(
    *,
    request_id: str,
    parsed_query: ParsedQuery,
    cards: list[ProductCard],
    products: list[Product],
    candidates: list[CandidateProduct],
) -> RecommendationPlan:
    products_by_sku = {product.sku_id: product for product in products}
    candidates_by_sku = {candidate.sku_id: candidate for candidate in candidates}
    value_sku = min(cards, key=lambda card: card.price).sku_id if cards else None
    items: list[RecommendationPlanItem] = []
    for index, card in enumerate(cards, start=1):
        product = products_by_sku.get(card.sku_id)
        candidate = candidates_by_sku.get(card.sku_id)
        presentation = card.presentation
        items.append(
            RecommendationPlanItem(
                section_id=index - 1,
                rank=index,
                product_id=card.product_id,
                sku_id=card.sku_id,
                option_label=(presentation.option_label if presentation else None) or _option_label(index),
                plan_type=_plan_type(index=index, card=card, value_sku=value_sku),
                name=card.name,
                display_title=card.display_title,
                brand=card.brand,
                category=card.category,
                sub_category=card.sub_category,
                price=card.price,
                stock=card.stock,
                score=card.score,
                facts=_facts(card=card, product=product),
                matching_points=_matching_points(card=card),
                cautions=_cautions(card=card, candidate=candidate),
                fallback_reason=((presentation.reason if presentation else None) or card.reason or "").strip(),
                fallback_trade_off=(presentation.trade_off if presentation else None),
            )
        )
    return RecommendationPlan(
        request_id=request_id,
        user_need=parsed_query.raw_message,
        category=parsed_query.category,
        sub_category=parsed_query.sub_category,
        core_constraints=_core_constraints(parsed_query),
        items=items,
    )


def recommendation_plan_prompt(plan: RecommendationPlan) -> str:
    return (
        "RECOMMENDATION_PRESENTATION_STREAM\n"
        "You are only the presentation layer. The backend has already selected and ranked products.\n"
        "Write one user-visible Chinese display_title and recommend_reason for all sections in order.\n"
        "Never change, invent, omit, or contradict product IDs, ranks, prices, stock, specs, parameters, or business results.\n"
        "Use only the facts in RecommendationPlan. Do not expose hidden reasoning.\n"
        "Each section marker must include TITLE. TITLE is an 8-20 Chinese character need-oriented short title, not a bare category, tag, product name, plan number, or generic phrase.\n"
        "The section body is recommend_reason only: 2-3 concise Chinese sentences highlighting verified selling points, user fit, scene, difference, or necessary caution.\n"
        "Do not repeat TITLE in recommend_reason. Do not mention frontend card actions such as viewing card details, adding to candidates, adding to cart, or clicking cards.\n"
        "Output exactly this streaming protocol, with no text outside markers:\n"
        "[[SECTION:0|TITLE:section 0 display_title]]\n"
        "section 0 recommend_reason text\n"
        "[[END_SECTION]]\n"
        "[[SECTION:1|TITLE:section 1 display_title]]\n"
        "section 1 recommend_reason text\n"
        "[[END_SECTION]]\n"
        "Keep each section concise, natural, and grounded in the matching_points, facts, and cautions.\n"
        f"RecommendationPlan JSON:\n{json.dumps(plan.model_dump(), ensure_ascii=False, default=str)}"
    )


def _core_constraints(parsed_query: ParsedQuery) -> list[str]:
    constraints: list[str] = []
    if parsed_query.price_range.min is not None:
        constraints.append(f"price_min={parsed_query.price_range.min:g}")
    if parsed_query.price_range.max is not None:
        constraints.append(f"price_max={parsed_query.price_range.max:g}")
    constraints.extend(parsed_query.positive_constraints[:6])
    constraints.extend(f"brand={brand}" for brand in parsed_query.brands_include[:4])
    constraints.extend(f"avoid={item}" for item in parsed_query.negative_constraints[:4])
    constraints.extend(f"exclude_brand={brand}" for brand in parsed_query.brands_exclude[:4])
    return list(dict.fromkeys(item for item in constraints if item))


def _facts(*, card: ProductCard, product: Product | None) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "price": card.price,
        "stock": card.stock,
        "brand": card.brand,
        "display_title": card.display_title,
        "category": card.category,
        "sub_category": card.sub_category,
        "highlight_short": card.highlight_short,
        "suitable_scenarios": card.suitable_scenarios[:5],
        "target_user_tags": card.target_user_tags[:5],
        "tags": card.tags[:8],
        "matched_reasons": card.matched_reasons[:6],
    }
    if product is not None:
        facts.update(
            {
                "reviews_summary": product.reviews_summary,
                "product_highlight": product.product_highlight,
                "highlight_detail": product.highlight_detail,
                "spotlight": product.spotlight.model_dump(),
                "specs": [
                    {"sku_id": sku.sku_id, "properties": sku.properties, "price": sku.price}
                    for sku in product.skus[:6]
                ],
            }
        )
    return facts


def _matching_points(*, card: ProductCard) -> list[str]:
    values = [
        card.reason,
        card.highlight_short,
        *card.matched_reasons,
        *card.suitable_scenarios,
        *card.target_user_tags,
        *card.tags,
    ]
    return list(dict.fromkeys(item.strip() for item in values if item and item.strip()))[:10]


def _cautions(*, card: ProductCard, candidate: CandidateProduct | None) -> list[str]:
    values: list[str] = []
    if candidate is not None:
        values.extend(candidate.risk_notes)
        values.extend(candidate.violated_constraints)
    if card.stock <= 0:
        values.append("out_of_stock")
    return list(dict.fromkeys(item.strip() for item in values if item and item.strip()))[:6]


def _plan_type(*, index: int, card: ProductCard, value_sku: str | None) -> str:
    if index == 1:
        return "首选"
    if value_sku and card.sku_id == value_sku:
        return "性价比"
    return "备选"


def _option_label(index: int) -> str:
    labels = ["方案一", "方案二", "方案三", "方案四", "方案五"]
    return labels[index - 1] if index <= len(labels) else f"方案{index}"
