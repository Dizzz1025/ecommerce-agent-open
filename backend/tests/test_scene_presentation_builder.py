import json

from app.agents.scene_presentation_builder import ScenePresentationBuilder
from app.llm.base import BaseLLMClient
from app.models.agent import CandidateProduct, DialogueFlow, ParsedQuery
from app.models.domain import IntentType, ProductCard


class StaticLLMClient(BaseLLMClient):
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def generate_response(
        self,
        intent: IntentType,
        message: str,
        context: str,
        product_names: list[str],
    ) -> str:
        return json.dumps(self.payload, ensure_ascii=False)


class RawLLMClient(BaseLLMClient):
    def __init__(self, output: str) -> None:
        self.output = output

    def generate_response(
        self,
        intent: IntentType,
        message: str,
        context: str,
        product_names: list[str],
    ) -> str:
        return self.output


def _query(intent: str = "recommend") -> ParsedQuery:
    return ParsedQuery(
        raw_message="推荐三款适合通勤的背包，预算500以内",
        intent=intent,
        category="服饰运动",
        sub_category="背包",
        positive_constraints=["通勤", "500元以内"],
    )


def _cards() -> list[ProductCard]:
    return [
        ProductCard(
            sku_id=f"sku_{index}",
            product_id=f"p_{index}",
            name=f"商品{index}",
            category="服饰运动",
            sub_category="背包",
            brand="品牌",
            price=199 + index,
            stock=10,
            image_url="",
            reason=f"匹配通勤需求{index}",
            matched_reasons=["通勤", "背包"],
            score=0.9 - index * 0.01,
        )
        for index in range(1, 4)
    ]


def _candidates() -> list[CandidateProduct]:
    return [
        CandidateProduct(
            candidate_id=f"c_{index}",
            product_id=f"p_{index}",
            sku_id=f"sku_{index}",
            name=f"商品{index}",
            brand="品牌",
            category="服饰运动",
            sub_category="背包",
            price=199 + index,
            image_url="",
            matched_reasons=["通勤", "背包"],
            score=0.9 - index * 0.01,
        )
        for index in range(1, 4)
    ]


def test_recommendation_presentation_assigns_backend_labels_and_partial_fallback() -> None:
    builder = ScenePresentationBuilder(
        StaticLLMClient(
            {
                "items": [
                    {"sku_id": "sku_2", "reason": "适合通勤收纳", "trade_off": None},
                    {"sku_id": "bad_sku", "reason": "非法商品", "trade_off": None},
                    {"sku_id": "sku_1", "reason": "价格在预算内", "trade_off": "容量偏日常"},
                ]
            }
        )
    )

    cards, comparison = builder.build(
        parsed_query=_query(),
        flow=DialogueFlow.RECOMMENDATION,
        cards=_cards(),
        products=[],
        candidates=_candidates(),
        use_llm=True,
    )

    assert comparison is None
    assert [item.presentation.option_label for item in cards] == ["方案一", "方案二", "方案三"]
    assert cards[0].presentation.content_source == "llm"
    assert cards[1].presentation.content_source == "llm"
    assert cards[2].presentation.content_source == "fallback"
    assert "illegal_sku_id:bad_sku" in builder.last_debug["issues"]


def test_recommendation_presentation_accepts_markdown_json_block() -> None:
    builder = ScenePresentationBuilder(
        RawLLMClient(
            "```json\n"
            '{"items":[{"sku_id":"sku_1","reason":"商品1适合通勤","trade_off":null}]}'
            "\n```"
        )
    )

    cards, comparison = builder.build(
        parsed_query=_query(),
        flow=DialogueFlow.RECOMMENDATION,
        cards=_cards(),
        products=[],
        candidates=_candidates(),
        use_llm=True,
    )

    assert comparison is None
    assert builder.last_debug["json_parse_succeeded"] is True
    assert cards[0].presentation.content_source == "llm"
    assert cards[0].presentation.reason == "商品1适合通勤"
    assert cards[1].presentation.content_source == "fallback"


def test_recommendation_full_llm_failure_keeps_per_product_fallback_reasons() -> None:
    builder = ScenePresentationBuilder(RawLLMClient("我先为你挑了这几款，但这不是 JSON"))

    cards, comparison = builder.build(
        parsed_query=_query(),
        flow=DialogueFlow.RECOMMENDATION,
        cards=_cards(),
        products=[],
        candidates=_candidates(),
        use_llm=True,
    )

    assert comparison is None
    assert builder.last_debug["json_parse_succeeded"] is False
    assert builder.last_debug["fallback_reason"] == "json_parse_failed"
    assert all(item.presentation.content_source == "fallback" for item in cards)
    reasons = [item.presentation.reason for item in cards]
    assert len(set(reasons)) == len(cards)
    assert "商品1" in reasons[0]
    assert "商品2" in reasons[1]
    assert "商品3" in reasons[2]


def test_comparison_presentation_rejects_invalid_conclusion_sku() -> None:
    builder = ScenePresentationBuilder(
        StaticLLMClient(
            {
                "items": [
                    {
                        "sku_id": "sku_1",
                        "summary": "更便于通勤",
                        "advantages": ["轻便"],
                        "trade_off": None,
                        "suitable_for": "通勤",
                    }
                ],
                "comparison_data": {
                    "dimensions": [
                        {
                            "name": "价格",
                            "items": [
                                {"sku_id": "sku_1", "value": "¥200"},
                                {"sku_id": "sku_2", "value": "¥201"},
                            ],
                            "better_sku_id": "bad_sku",
                        }
                    ],
                    "conclusion": {
                        "recommended_sku_id": "bad_sku",
                        "reason": "非法结论",
                        "alternative_sku_id": "sku_2",
                    },
                },
            }
        )
    )

    cards, comparison = builder.build(
        parsed_query=_query(intent="compare"),
        flow=DialogueFlow.COMPARISON,
        cards=_cards()[:2],
        products=[],
        candidates=_candidates()[:2],
        use_llm=True,
    )

    assert all(item.presentation.type == "comparison" for item in cards)
    assert comparison is not None
    assert comparison.dimensions[0].better_sku_id is None
    assert comparison.conclusion.recommended_sku_id == "sku_1"
    assert comparison.conclusion.alternative_sku_id == "sku_2"
    assert "illegal_better_sku_id:bad_sku" in builder.last_debug["issues"]
    assert "illegal_recommended_sku_id:bad_sku" in builder.last_debug["issues"]
