from pathlib import Path

from app.models.agent import CandidateProduct
from app.models.domain import Product
from app.repositories.product_repository import ProductRepository
from app.retrieval.post_processor import ProductPostProcessor


def test_dataset_display_tags_ignore_faq_and_review_noise() -> None:
    repo = ProductRepository(Path("missing-products.json"))
    normalized = repo._normalize_dataset_item(
        {
            "product_id": "p_food_water",
            "title": "农夫山泉 东方树叶 无糖乌龙茶饮料500ml",
            "brand": "农夫山泉",
            "category": "食品饮料",
            "sub_category": "茶饮",
            "base_price": 5,
            "image_path": "",
            "skus": [{"sku_id": "s_food_water", "price": 5, "properties": {"规格": "500ml"}}],
            "suitable_scenarios": ["日常饮用"],
            "target_user_tags": ["控糖/减脂人群"],
            "non_standard_query_tags": ["无糖茶饮料推荐"],
            "product_highlight": "东方树叶茶饮 —— 健康属性：无糖、低糖。",
            "highlight_short": "东方树叶无糖乌龙茶，0糖0卡0脂",
            "highlight_detail": "风味：乌龙。健康属性：无糖、低糖。",
            "rag_knowledge": {
                "marketing_description": "咖啡因含量比较温和，日常下午喝也合适。",
                "official_faq": [
                    {
                        "question": "运输漏液怎么办？",
                        "answer": "联系客服拍照反馈即可处理。",
                    }
                ],
                "user_reviews": [{"rating": 5, "content": "包装破损时拍照留证。"}],
            },
        }
    )

    assert "无糖" in normalized["tags"]
    assert "低糖" in normalized["tags"]
    assert "温和" not in normalized["tags"]
    assert "拍照" not in normalized["tags"]


def test_post_processor_keeps_tags_aligned_by_sku_after_rerank() -> None:
    products = {
        "water": _product("water", "农夫山泉天然饮用水", "食品饮料", "矿泉水", ["饮用水", "便携"]),
        "beauty": _product("beauty", "温和保湿面霜", "美妆护肤", "面霜", ["温和", "保湿"]),
        "phone": _product("phone", "拍照旗舰手机", "数码电子", "智能手机", ["拍照", "长续航"]),
    }
    candidates = [
        _candidate("phone", "拍照旗舰手机", "数码电子", "智能手机", 0.91),
        _candidate("water", "农夫山泉天然饮用水", "食品饮料", "矿泉水", 0.9),
        _candidate("beauty", "温和保湿面霜", "美妆护肤", "面霜", 0.89),
    ]

    cards = ProductPostProcessor().build_product_cards(candidates, products)

    assert [card.sku_id for card in cards] == ["phone", "water", "beauty"]
    water_card = next(card for card in cards if card.sku_id == "water")
    assert water_card.tags == ["饮用水", "便携"]
    assert "温和" not in water_card.tags
    assert "拍照" not in water_card.tags


def test_product_card_tag_lists_are_not_shared() -> None:
    products = {
        "water": _product("water", "农夫山泉天然饮用水", "食品饮料", "矿泉水", ["饮用水", "便携"]),
        "beauty": _product("beauty", "温和保湿面霜", "美妆护肤", "面霜", ["温和", "保湿"]),
    }
    cards = ProductPostProcessor().build_product_cards(
        [
            _candidate("water", "农夫山泉天然饮用水", "食品饮料", "矿泉水", 0.9),
            _candidate("beauty", "温和保湿面霜", "美妆护肤", "面霜", 0.89),
        ],
        products,
    )

    cards[0].tags.append("污染")

    assert "污染" in cards[0].tags
    assert "污染" not in cards[1].tags
    assert "污染" not in products["water"].tags


def _product(
    sku_id: str,
    name: str,
    category: str,
    sub_category: str,
    tags: list[str],
) -> Product:
    return Product(
        sku_id=sku_id,
        product_id=sku_id,
        name=name,
        category=category,
        sub_category=sub_category,
        brand=name[:4],
        price=10,
        stock=10,
        image_url="",
        reviews_summary="",
        tags=tags,
    )


def _candidate(
    sku_id: str,
    name: str,
    category: str,
    sub_category: str,
    score: float,
) -> CandidateProduct:
    return CandidateProduct(
        candidate_id=f"c_{sku_id}",
        product_id=sku_id,
        sku_id=sku_id,
        name=name,
        brand=name[:4],
        category=category,
        sub_category=sub_category,
        price=10,
        image_url="",
        matched_reasons=["类目一致"],
        score=score,
    )
