from __future__ import annotations

import json
from typing import Any

from app.llm.base import BaseLLMClient
from app.models.agent import CandidateProduct, ParsedQuery
from app.models.domain import IntentType, Product, SessionState
from app.repositories.product_repository import ProductRepository


class CartAwarePersonalization:
    """Product-side personalization from current cart contents."""

    def __init__(
        self,
        *,
        product_repository: ProductRepository,
        llm_client: BaseLLMClient,
    ) -> None:
        self.product_repository = product_repository
        self.llm_client = llm_client

    def build_context(self, *, state: SessionState, parsed_query: ParsedQuery) -> dict[str, Any]:
        all_products = [
            product for item in state.cart.items
            if (product := self.product_repository.get_product(item.sku_id)) is not None
        ]
        if not all_products:
            return {
                "是否启用": False,
                "参考购物车商品": [],
                "商品标签": [],
                "命中的本地规则": [],
                "是否调用Doubao": False,
                "排序影响": [],
                "禁用原因": "购物车为空或购物车商品已不在商品库中",
            }
        target_category = parsed_query.category or state.dialogue_state_tracking.current_category
        if not target_category:
            return {
                "是否启用": False,
                "参考购物车商品": [],
                "购物车全部商品": [_brief_product(item) for item in all_products],
                "商品标签": [],
                "命中的本地规则": [],
                "是否调用Doubao": False,
                "排序影响": [],
                "禁用原因": "当前目标商品类目尚不明确，不使用购物车商品侧个性化",
            }
        products = [item for item in all_products if item.category == target_category]
        ignored_products = [item for item in all_products if item.category != target_category]
        if not products:
            return {
                "是否启用": False,
                "参考购物车商品": [],
                "购物车全部商品": [_brief_product(item) for item in all_products],
                "忽略的非同类购物车商品": [_brief_product(item) for item in ignored_products],
                "目标类目": target_category,
                "商品标签": [],
                "命中的本地规则": [],
                "是否调用Doubao": False,
                "排序影响": [],
                "禁用原因": f"购物车中没有{target_category}类目的商品，本轮不使用跨类目购物车个性化",
            }

        tags = self._derive_tags(products)
        rules = self._match_rules(products, parsed_query)
        inventory_coverage = self._inventory_coverage(products, parsed_query)
        needs_llm = self._needs_llm(products, parsed_query, rules)
        llm_payload: dict[str, Any] = {}

        return {
            "是否启用": True,
            "目标类目": target_category,
            "参考购物车商品": [_brief_product(item) for item in products],
            "购物车全部商品": [_brief_product(item) for item in all_products],
            "忽略的非同类购物车商品": [_brief_product(item) for item in ignored_products],
            "商品标签": tags,
            "价格画像": _price_profile(products),
            "库存覆盖": inventory_coverage,
            "命中的本地规则": rules,
            "是否调用Doubao": False,
            "是否需要复杂搭配分析": needs_llm,
            "复杂搭配分析处理方式": "并入回复生成Doubao调用" if needs_llm else "本地规则足够",
            "Doubao分析": llm_payload,
            "排序影响": [],
        }

    def rerank(
        self,
        *,
        candidates: list[CandidateProduct],
        context: dict[str, Any],
        parsed_query: ParsedQuery,
    ) -> list[CandidateProduct]:
        if not context.get("是否启用") or not candidates:
            return candidates
        rules = context.get("命中的本地规则", [])
        tags = set(context.get("商品标签", []))
        price_profile = context.get("价格画像", {})
        high_end_cart = "高端护肤" in tags or float(price_profile.get("avg") or 0) >= 500
        explicit_price = parsed_query.price_range.min is not None or parsed_query.price_range.max is not None
        effects: list[dict[str, Any]] = []
        reranked: list[CandidateProduct] = []
        for candidate in candidates:
            item = candidate.model_copy(deep=True)
            boost = 0.0
            reasons: list[str] = []
            text = f"{item.name} {item.brand} {item.category} {item.sub_category or ''} {' '.join(item.matched_reasons)}"
            for rule in rules:
                if rule.get("debug_only"):
                    continue
                target_brands = set(rule.get("boost_brands", []))
                target_categories = set(rule.get("boost_categories", []))
                target_sub_categories = set(rule.get("boost_sub_categories", []))
                target_tags = set(rule.get("boost_tags", []))
                if item.brand in target_brands:
                    boost += 0.08
                    reasons.append(f"品牌搭配:{item.brand}")
                if item.category in target_categories:
                    boost += 0.05
                    reasons.append(f"类目搭配:{item.category}")
                if item.sub_category and item.sub_category in target_sub_categories:
                    boost += 0.12
                    reasons.append(f"子类搭配:{item.sub_category}")
                if any(tag and tag in text for tag in target_tags):
                    boost += 0.04
                    reasons.append("标签相近")
                soft_price_max = rule.get("soft_price_max")
                if soft_price_max and item.price <= float(soft_price_max):
                    boost += 0.05
                    reasons.append(f"价格带友好:不高于{float(soft_price_max):g}元")
                if rule.get("prefer_high_price") and (
                    high_end_cart
                    or any(term in parsed_query.raw_message for term in ["高端", "贵一点", "最贵", "最昂贵", "预算够"])
                ):
                    boost += min(item.price / 5000, 0.12)
                    reasons.append("延续高端价位偏好")
            if not explicit_price:
                price_boost = _price_fit_boost(item.price, price_profile)
                if price_boost:
                    boost += price_boost
                    reasons.append("价格带接近购物车偏好")
            if tags and any(tag in text for tag in tags):
                boost += 0.03
                reasons.append("延续购物车商品风格")
            if boost:
                item.raw_scores["cart_personalization"] = round(boost, 4)
                item.score = round(min(item.score + boost, 1.0), 4)
                item.matched_reasons = list(dict.fromkeys([*item.matched_reasons, *[f"购物车偏好:{r}" for r in reasons[:2]]]))
                effects.append(
                    {
                        "sku_id": item.sku_id,
                        "boost": round(boost, 4),
                        "reasons": reasons[:4],
                    }
                )
            reranked.append(item)
        reranked.sort(
            key=lambda item: (
                item.score,
                float(item.raw_scores.get("cart_personalization", 0.0)),
            ),
            reverse=True,
        )
        context["排序影响"] = effects[:8]
        return reranked

    @staticmethod
    def _derive_tags(products: list[Product]) -> list[str]:
        tags: list[str] = []
        prices = [item.price for item in products]
        avg_price = sum(prices) / len(prices) if prices else 0
        if avg_price <= 150:
            tags.append("价格敏感")
        elif avg_price >= 5000:
            tags.append("高端消费")
        elif avg_price >= 3000:
            tags.append("接受中高价")
        elif avg_price >= 800:
            tags.append("中端消费")

        brands = {item.brand for item in products}
        categories = {item.category for item in products}
        subs = {item.sub_category for item in products}

        # Brand ecosystem signals
        if any("Apple" in b or "苹果" in b for b in brands):
            tags.extend(["Apple生态", "数码生态", "办公生产力"])
        if any(b in brands for b in ["华为", "小米", "OPPO", "vivo"]):
            tags.append("国产数码生态")
        if any(b in brands for b in ["兰蔻", "雅诗兰黛", "SK-II", "资生堂", "娇韵诗"]) or avg_price >= 500:
            tags.extend(["高端护肤", "成分功效"])

        # Category-level signals
        if "美妆护肤" in categories:
            makeup_subs = {"素颜霜", "BB霜", "隔离霜", "粉底液", "蜜粉", "眉笔", "眼影盘", "唇釉"}
            skincare_subs = {"精华", "面霜", "化妆水", "眼霜", "洁面", "安瓶", "精华油", "面膜"}
            body_subs = {"身体乳", "洗发水", "防晒", "防晒喷雾", "香水"}
            cart_makeup = bool(subs & makeup_subs)
            cart_skincare = bool(subs & skincare_subs)
            cart_body = bool(subs & body_subs)
            if cart_skincare:
                tags.append("护肤流程完整")
                if any(s in subs for s in ["精华", "安瓶", "精华油"]):
                    tags.extend(["成分党", "功效护肤", "抗初老"])
                if any(s in subs for s in ["洁面", "防晒"]):
                    tags.append("基础护肤")
            if cart_makeup:
                tags.extend(["彩妆用户", "底妆需求", "日常通勤妆"])
            if cart_body:
                tags.extend(["身体护理", "全身精致护理"])

        if "数码电子" in categories:
            if subs & {"智能手机", "真无线耳机", "平板电脑", "智能手表", "笔记本电脑"}:
                tags.append("数码生态用户")
            if subs & {"游戏鼠标", "游戏手柄", "手机散热器"}:
                tags.extend(["游戏玩家", "电竞装备"])
            if subs & {"显示器", "家用打印机", "移动硬盘"}:
                tags.extend(["办公效率", "居家办公"])
            if subs & {"微单相机", "移动硬盘"}:
                tags.append("创作者/摄影")

        if "服饰运动" in categories:
            sport_subs = {"跑步鞋", "速干T恤", "短袖T恤", "运动袜", "运动短裤", "运动长裤", "运动内衣", "骑行裤"}
            outdoor_subs = {"冲锋衣", "徒步鞋", "登山杖", "户外裤", "防晒衣", "背包"}
            casual_subs = {"板鞋", "牛仔裤", "休闲衬衫", "卫衣", "沙滩拖鞋"}
            if subs & sport_subs:
                tags.extend(["运动训练", "透气速干", "健身爱好者"])
            if subs & outdoor_subs:
                tags.extend(["户外运动", "旅行装备", "防晒防护"])
            if subs & casual_subs:
                tags.append("日常休闲穿搭")
            if any(s in subs for s in ["羽绒服", "冲锋衣"]):
                tags.append("冬季保暖")

        if "食品饮料" in categories:
            if subs & {"咖啡", "茶叶", "功能饮料"}:
                tags.append("提神需求")
            if subs & {"蛋白粉", "能量棒", "即食麦片", "牛奶", "酸奶"}:
                tags.extend(["健康营养", "健身补给"])
            if subs & {"方便食品", "午餐肉罐头", "辣条", "苏打饼干"}:
                tags.append("速食便捷")
            if subs & {"巧克力", "蒟蒻果冻", "坚果/零食", "蜂蜜"}:
                tags.append("零食甜食")
            if subs & {"矿泉水", "纯果汁", "碳酸饮料", "茶饮"}:
                tags.append("饮品需求")
            if subs & {"茶叶", "蜂蜜", "黑巧克力"}:
                tags.append("送礼品质")

        # Collect product-level tags
        for product in products:
            tags.extend(product.tags[:6])
        return list(dict.fromkeys(tag for tag in tags if tag))[:12]

    @staticmethod
    def _match_rules(products: list[Product], parsed_query: ParsedQuery) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = []
        brands = {item.brand for item in products}
        categories = {item.category for item in products}
        subs = {item.sub_category for item in products}

        for product in products:
            text = f"{product.name} {product.brand} {product.category} {product.sub_category or ''} {' '.join(product.tags)}"
            brand = product.brand
            sub = product.sub_category or ""
            cat = product.category

            # ===== 数码电子 配对规则 =====
            if "MacBook" in text or (brand == "Apple 苹果" and sub == "笔记本电脑"):
                rules.append({
                    "rule_id": "apple_macbook_ecosystem",
                    "说明": "购物车里有 MacBook，优先考虑 Apple 生态、办公协同和便携配件。",
                    "boost_brands": ["Apple 苹果", "苹果"],
                    "boost_categories": ["数码电子"],
                    "boost_sub_categories": ["真无线耳机", "智能手机", "平板电脑", "智能手表", "显示器"],
                    "boost_tags": ["办公", "续航", "降噪", "便携", "学习", "影音", "创作"],
                })
            if sub in {"智能手机"}:
                rules.append({
                    "rule_id": "phone_accessory_ecosystem",
                    "说明": "购物车里有手机，优先推荐同品牌耳机、手表、充电宝和平板。",
                    "boost_brands": [brand],
                    "boost_categories": ["数码电子"],
                    "boost_sub_categories": ["真无线耳机", "智能手表", "智能手环", "充电宝", "平板电脑", "手机散热器"],
                    "boost_tags": ["降噪", "续航", "通勤", "快充", "便携"],
                })
                if brand in {"Apple 苹果", "苹果", "华为", "小米"}:
                    rules.append({
                        "rule_id": f"brand_ecosystem_{brand}",
                        "说明": f"购物车里有{brand}手机，强化同品牌生态配件推荐。",
                        "boost_brands": [brand],
                        "boost_categories": ["数码电子"],
                        "boost_sub_categories": ["真无线耳机", "智能手表", "平板电脑", "笔记本电脑", "智能手环"],
                        "boost_tags": ["降噪", "办公", "续航", "影音", "学习", "协同"],
                    })
            if sub in {"真无线耳机", "蓝牙音箱"}:
                rules.append({
                    "rule_id": "audio_to_phone_watch",
                    "说明": "购物车里有音频设备，优先搭配手机、手表和充电配件。",
                    "boost_brands": [brand] if brand in {"Apple 苹果", "苹果", "华为", "索尼"} else [],
                    "boost_categories": ["数码电子"],
                    "boost_sub_categories": ["智能手机", "智能手表", "充电宝", "智能手环"],
                    "boost_tags": ["降噪", "续航", "便携", "运动"],
                })
            if sub in {"平板电脑", "电子书阅读器"}:
                rules.append({
                    "rule_id": "tablet_study_bundle",
                    "说明": "购物车里有平板/电子书，优先搭配耳机、触控笔相关和轻便配件。",
                    "boost_brands": [brand],
                    "boost_categories": ["数码电子"],
                    "boost_sub_categories": ["真无线耳机", "充电宝", "智能手环"],
                    "boost_tags": ["学习", "便携", "续航", "护眼", "影音"],
                    "soft_price_max": 2500,
                })
            if sub in {"游戏鼠标", "游戏手柄", "手机散热器"}:
                rules.append({
                    "rule_id": "gaming_gear_bundle",
                    "说明": "购物车里有电竞外设，优先搭配高性能手机、散热器和高刷屏配件。",
                    "boost_brands": ["罗技", "索尼", "黑鲨", "小米"],
                    "boost_categories": ["数码电子"],
                    "boost_sub_categories": ["智能手机", "手机散热器", "游戏手柄", "游戏鼠标", "显示器"],
                    "boost_tags": ["游戏", "高性能", "高刷", "快充"],
                })
            if sub in {"显示器", "移动硬盘", "家用打印机"}:
                rules.append({
                    "rule_id": "productivity_office_bundle",
                    "说明": "购物车里有办公设备，优先搭配笔记本电脑、键鼠和充电配件。",
                    "boost_brands": ["戴尔", "华为", "联想", "西部数据"],
                    "boost_categories": ["数码电子"],
                    "boost_sub_categories": ["笔记本电脑", "移动硬盘", "充电宝", "显示器"],
                    "boost_tags": ["办公", "商务", "便携", "生产力"],
                })
            if sub in {"微单相机"}:
                rules.append({
                    "rule_id": "photography_kit",
                    "说明": "购物车里有微单相机，优先搭配存储、充电和便携配件。",
                    "boost_brands": ["佳能", "索尼", "西部数据"],
                    "boost_categories": ["数码电子"],
                    "boost_sub_categories": ["移动硬盘", "充电宝", "智能手机"],
                    "boost_tags": ["便携", "大容量", "快充", "创作"],
                })
            if sub in {"智能手表", "智能手环"}:
                rules.append({
                    "rule_id": "wearable_fitness_bundle",
                    "说明": "购物车里有穿戴设备，优先搭配运动耳机和轻便配件。",
                    "boost_brands": [brand],
                    "boost_categories": ["数码电子", "服饰运动"],
                    "boost_sub_categories": ["真无线耳机", "速干T恤", "跑步鞋", "运动袜"],
                    "boost_tags": ["运动", "跑步", "防水", "轻量", "续航"],
                })

            # ===== 美妆护肤 配对规则 =====
            if sub in {"精华", "安瓶", "精华油"}:
                rules.append({
                    "rule_id": "serum_to_routine",
                    "说明": "购物车里有高功效精华，优先搭配同品牌面霜、眼霜和面膜完善护理流程。",
                    "boost_brands": [brand],
                    "boost_categories": ["美妆护肤"],
                    "boost_sub_categories": ["面霜", "眼霜", "面膜", "化妆水"],
                    "boost_tags": ["修护", "抗初老", "保湿", "提亮", "紧致"],
                    "prefer_high_price": product.price >= 500,
                })
                if product.price >= 500 or brand in {"兰蔻", "SK-II", "雅诗兰黛", "资生堂", "娇韵诗"}:
                    rules.append({
                        "rule_id": "premium_skincare_routine",
                        "说明": "购物车里有高端功效护肤品，优先搭配同价位、同功效链路的面霜/眼霜/面膜。",
                        "boost_brands": ["兰蔻", "SK-II", "雅诗兰黛", "资生堂", "娇韵诗", "科颜氏", "修丽可"],
                        "boost_categories": ["美妆护肤"],
                        "boost_sub_categories": ["面霜", "眼霜", "面膜", "精华", "化妆水"],
                        "boost_tags": ["高端", "修护", "抗初老", "保湿", "提亮", "成分"],
                        "prefer_high_price": True,
                    })
            if sub in {"面霜", "眼霜"}:
                rules.append({
                    "rule_id": "moisturizer_to_cleanser_sunscreen",
                    "说明": "购物车里有面霜/眼霜，优先搭配同品牌洁面和防晒完成日常护肤闭环。",
                    "boost_brands": [brand],
                    "boost_categories": ["美妆护肤"],
                    "boost_sub_categories": ["洁面", "防晒", "精华", "化妆水"],
                    "boost_tags": ["保湿", "修护", "温和", "防晒", "清洁"],
                })
            if sub in {"洁面", "卸妆"}:
                rules.append({
                    "rule_id": "cleanser_to_moisturize_protect",
                    "说明": "购物车里有清洁产品，优先搭配保湿修护和防晒产品形成完整流程。",
                    "boost_brands": [brand] if brand in {"珊珂", "芳珂", "碧欧泉"} else [],
                    "boost_categories": ["美妆护肤"],
                    "boost_sub_categories": ["面霜", "精华", "防晒", "化妆水"],
                    "boost_tags": ["保湿", "修护", "温和", "敏感肌", "防晒"],
                    "soft_price_max": 500,
                })
            if sub in {"防晒", "防晒喷雾"}:
                rules.append({
                    "rule_id": "sunscreen_to_repair",
                    "说明": "购物车里有防晒产品，优先搭配晒后修护、洁面和补水产品。",
                    "boost_brands": [brand],
                    "boost_categories": ["美妆护肤"],
                    "boost_sub_categories": ["洁面", "面膜", "面霜", "卸妆", "精华"],
                    "boost_tags": ["修护", "保湿", "舒缓", "清洁", "补水"],
                })
            if sub in {"粉底液", "BB霜", "素颜霜", "隔离霜"}:
                rules.append({
                    "rule_id": "base_makeup_bundle",
                    "说明": "购物车里有底妆产品，优先搭配定妆、卸妆和妆前护理。",
                    "boost_brands": [brand] if brand in {"雅诗兰黛", "谜尚", "苏菲娜", "蒂佳婷"} else [],
                    "boost_categories": ["美妆护肤"],
                    "boost_sub_categories": ["蜜粉", "卸妆", "隔离霜", "洁面", "精华"],
                    "boost_tags": ["定妆", "清洁", "持妆", "控油", "保湿"],
                    "soft_price_max": 300,
                })
            if sub in {"眉笔", "眼影盘", "唇釉"}:
                rules.append({
                    "rule_id": "color_cosmetics_bundle",
                    "说明": "购物车里有彩妆单品，优先搭配其他彩妆品类和卸妆产品补全妆容。",
                    "boost_brands": ["花西子", "完美日记", "方里"],
                    "boost_categories": ["美妆护肤"],
                    "boost_sub_categories": ["眉笔", "眼影盘", "唇釉", "蜜粉", "卸妆", "粉底液"],
                    "boost_tags": ["定妆", "持久", "日常", "自然", "不晕染"],
                    "soft_price_max": 200,
                })
            if sub in {"洗发水", "身体乳"}:
                rules.append({
                    "rule_id": "body_hair_care_bundle",
                    "说明": "购物车里有身体/头发护理，优先搭配面部护理和香氛完善精致日常。",
                    "boost_brands": [brand],
                    "boost_categories": ["美妆护肤"],
                    "boost_sub_categories": ["洁面", "面霜", "香水", "防晒", "精华"],
                    "boost_tags": ["保湿", "修护", "温和", "清爽", "精致"],
                })
            if sub in {"香水"}:
                rules.append({
                    "rule_id": "fragrance_to_skincare",
                    "说明": "购物车里有香水，优先搭配同品牌护肤品和沐浴护理提升整体精致度。",
                    "boost_brands": [brand],
                    "boost_categories": ["美妆护肤"],
                    "boost_sub_categories": ["身体乳", "洁面", "精华", "面霜", "洗发水"],
                    "boost_tags": ["精致", "保湿", "高端", "清爽"],
                    "prefer_high_price": True,
                })
            if sub in {"祛痘精华"}:
                rules.append({
                    "rule_id": "acne_care_routine",
                    "说明": "购物车里有祛痘产品，优先搭配温和洁面、无油保湿和不致痘防晒。",
                    "boost_brands": [],
                    "boost_categories": ["美妆护肤"],
                    "boost_sub_categories": ["洁面", "面霜", "防晒", "面膜"],
                    "boost_tags": ["控油", "温和", "敏感肌", "清爽", "不黏", "水杨酸"],
                    "soft_price_max": 350,
                })

            # ===== 服饰运动 配对规则 =====
            if sub in {"跑步鞋", "篮球鞋"}:
                rules.append({
                    "rule_id": "shoes_to_apparel",
                    "说明": "购物车里有运动鞋，优先搭配速干服饰、运动袜和运动下装。",
                    "boost_brands": [brand] if brand in {"耐克", "Nike", "阿迪达斯", "阿迪达斯", "李宁", "安踏"} else [],
                    "boost_categories": ["服饰运动"],
                    "boost_sub_categories": ["速干T恤", "短袖T恤", "运动袜", "运动短裤", "运动长裤", "帽子"],
                    "boost_tags": ["运动", "跑步", "透气", "速干", "轻量"],
                })
            if sub in {"速干T恤", "短袖T恤", "运动长裤", "运动短裤", "运动内衣", "运动袜"}:
                rules.append({
                    "rule_id": "apparel_to_shoes",
                    "说明": "购物车里有运动服饰，优先搭配同品牌运动鞋和帽子完善运动穿搭。",
                    "boost_brands": [brand] if brand in {"耐克", "Nike", "阿迪达斯", "阿迪达斯", "安德玛", "优衣库", "安踏"} else [],
                    "boost_categories": ["服饰运动"],
                    "boost_sub_categories": ["跑步鞋", "篮球鞋", "徒步鞋", "帽子", "运动袜", "板鞋"],
                    "boost_tags": ["运动", "跑步", "透气", "缓震", "轻量", "速干"],
                    "soft_price_max": 1200,
                })
                rules.append({
                    "rule_id": "training_apparel_to_shoes",
                    "说明": "购物车里有训练服饰，推荐运动鞋时优先考虑训练/跑步场景的缓震、透气和性价比。",
                    "debug_only": True,
                })
            if sub in {"冲锋衣", "徒步鞋", "登山杖", "户外裤", "防晒衣"}:
                rules.append({
                    "rule_id": "outdoor_adventure_bundle",
                    "说明": "购物车里有户外装备，优先搭配背包、帽子、防晒和速干服饰。",
                    "boost_brands": ["始祖鸟", "萨洛蒙", "The North Face", "北面", "探路者", "迈乐"],
                    "boost_categories": ["服饰运动", "美妆护肤"],
                    "boost_sub_categories": ["背包", "帽子", "防晒", "防晒衣", "速干T恤", "户外裤"],
                    "boost_tags": ["防水", "透气", "轻量", "防晒", "速干", "耐磨"],
                })
            if sub in {"羽绒服", "冲锋衣"}:
                rules.append({
                    "rule_id": "winter_warm_bundle",
                    "说明": "购物车里有冬季保暖外套，优先搭配卫衣、手套和保暖配件。",
                    "boost_brands": ["波司登", "始祖鸟", "The North Face", "北面"],
                    "boost_categories": ["服饰运动"],
                    "boost_sub_categories": ["卫衣", "帽子", "运动长裤", "围巾"] if "围巾" in [p.sub_category for p in products] else ["卫衣", "运动长裤"],
                    "boost_tags": ["保暖", "防风", "加厚", "日常"],
                })
            if sub in {"泳衣", "沙滩拖鞋"}:
                rules.append({
                    "rule_id": "beach_summer_bundle",
                    "说明": "购物车里有泳衣/拖鞋，优先搭配防晒、帽子和轻便背包打造度假装备。",
                    "boost_brands": [],
                    "boost_categories": ["服饰运动", "美妆护肤"],
                    "boost_sub_categories": ["防晒", "防晒衣", "帽子", "背包", "短袖T恤"],
                    "boost_tags": ["防晒", "轻量", "透气", "便携", "速干"],
                    "soft_price_max": 500,
                })
            if sub in {"运动内衣", "瑜伽裤", "骑行裤"}:
                rules.append({
                    "rule_id": "womens_activewear_bundle",
                    "说明": "购物车里有女性运动紧身服饰，优先搭配速干上衣、运动鞋和轻便外套。",
                    "boost_brands": ["露露乐蒙", "Lululemon", "安德玛", "Under Armour", "耐克", "Nike"],
                    "boost_categories": ["服饰运动"],
                    "boost_sub_categories": ["速干T恤", "短袖T恤", "跑步鞋", "运动袜", "防晒衣"],
                    "boost_tags": ["运动", "跑步", "透气", "速干", "轻量", "弹力"],
                })
            if sub in {"牛仔裤", "休闲衬衫", "板鞋", "卫衣"}:
                rules.append({
                    "rule_id": "casual_daily_bundle",
                    "说明": "购物车里有休闲服饰，优先搭配百搭鞋款和基础单品完善日常穿搭。",
                    "boost_brands": [brand] if brand in {"优衣库", "Levi's", "匡威", "李宁"} else [],
                    "boost_categories": ["服饰运动"],
                    "boost_sub_categories": ["板鞋", "短袖T恤", "帽子", "背包", "卫衣"],
                    "boost_tags": ["百搭", "日常", "通勤", "基础款", "休闲"],
                    "soft_price_max": 800,
                })
            if sub in {"背包"}:
                rules.append({
                    "rule_id": "backpack_travel_bundle",
                    "说明": "购物车里有背包，优先搭配防晒、帽子、速干服饰和轻便出行装备。",
                    "boost_brands": ["The North Face", "Osprey", "北面", "始祖鸟"],
                    "boost_categories": ["服饰运动", "美妆护肤", "食品饮料"],
                    "boost_sub_categories": ["防晒", "帽子", "速干T恤", "防晒衣", "徒步鞋", "矿泉水"],
                    "boost_tags": ["旅行", "轻量", "便携", "防晒", "透气", "收纳"],
                })

            # ===== 食品饮料 配对规则 =====
            if sub in {"咖啡", "茶叶"}:
                rules.append({
                    "rule_id": "beverage_to_snack",
                    "说明": "购物车里有咖啡/茶叶，优先搭配饼干、零食和蜂蜜作为下午茶组合。",
                    "boost_brands": [],
                    "boost_categories": ["食品饮料"],
                    "boost_sub_categories": ["苏打饼干", "黑巧克力", "蜂蜜", "坚果/零食", "蒟蒻果冻"],
                    "boost_tags": ["下午茶", "零食", "健康", "低糖", "办公室"],
                    "soft_price_max": 150,
                })
            if sub in {"蛋白粉", "能量棒"}:
                rules.append({
                    "rule_id": "fitness_nutrition_bundle",
                    "说明": "购物车里有运动营养品，优先搭配矿泉水、即食麦片和健康零食完善补给方案。",
                    "boost_brands": ["Swisse", "康比特", "桂格"],
                    "boost_categories": ["食品饮料", "服饰运动"],
                    "boost_sub_categories": ["矿泉水", "即食麦片", "牛奶", "功能饮料", "运动袜"],
                    "boost_tags": ["健康", "运动", "高蛋白", "补给", "低脂"],
                    "soft_price_max": 250,
                })
            if sub in {"即食麦片", "牛奶", "酸奶"}:
                rules.append({
                    "rule_id": "breakfast_bundle",
                    "说明": "购物车里有早餐食品，优先搭配蜂蜜、饼干和饮品丰富早餐选择。",
                    "boost_brands": ["桂格", "伊利", "蒙牛", "金典", "纯甄"],
                    "boost_categories": ["食品饮料"],
                    "boost_sub_categories": ["蜂蜜", "苏打饼干", "纯果汁", "咖啡", "坚果/零食"],
                    "boost_tags": ["早餐", "健康", "方便", "营养", "即食"],
                    "soft_price_max": 100,
                })
            if sub in {"方便食品", "午餐肉罐头"}:
                rules.append({
                    "rule_id": "instant_meal_bundle",
                    "说明": "购物车里有方便食品/午餐肉，优先搭配饮料、零食和调味品打造宿舍/加班补给。",
                    "boost_brands": ["康师傅", "统一", "梅林", "日清"],
                    "boost_categories": ["食品饮料"],
                    "boost_sub_categories": ["功能饮料", "碳酸饮料", "辣条", "茶饮", "调味品", "矿泉水"],
                    "boost_tags": ["速食", "方便", "办公室", "宿舍", "加班"],
                    "soft_price_max": 80,
                })
            if sub in {"黑巧克力", "蒟蒻果冻", "辣条", "苏打饼干", "坚果/零食"}:
                rules.append({
                    "rule_id": "snack_mix_bundle",
                    "说明": "购物车里有零食，优先搭配饮品和其他零食品类丰富选择。",
                    "boost_brands": [],
                    "boost_categories": ["食品饮料"],
                    "boost_sub_categories": ["茶饮", "碳酸饮料", "咖啡", "纯果汁", "蒟蒻果冻", "黑巧克力"],
                    "boost_tags": ["零食", "下午茶", "办公室", "便携", "低糖"],
                    "soft_price_max": 120,
                })
            if sub in {"蜂蜜", "茶叶"}:
                rules.append({
                    "rule_id": "gift_quality_bundle",
                    "说明": "购物车里有高品质蜂蜜/茶叶，优先搭配巧克力、坚果礼盒组成送礼方案。",
                    "boost_brands": ["西湖牌", "北大荒", "歌帝梵", "三只松鼠"],
                    "boost_categories": ["食品饮料"],
                    "boost_sub_categories": ["黑巧克力", "坚果/零食", "茶叶", "蜂蜜"],
                    "boost_tags": ["送礼", "品质", "健康", "精致"],
                    "prefer_high_price": True,
                })
            if sub in {"矿泉水", "纯果汁", "碳酸饮料"}:
                rules.append({
                    "rule_id": "drink_to_snack",
                    "说明": "购物车里有饮品，优先搭配饼干、零食和方便食品。",
                    "boost_brands": [],
                    "boost_categories": ["食品饮料"],
                    "boost_sub_categories": ["苏打饼干", "坚果/零食", "辣条", "方便食品", "蒟蒻果冻"],
                    "boost_tags": ["零食", "便携", "办公室", "出游", "下午茶"],
                    "soft_price_max": 80,
                })

            # ===== 跨类目搭配规则 =====
            if cat == "食品饮料" and "服饰运动" in categories:
                if sub in {"蛋白粉", "能量棒", "功能饮料"}:
                    rules.append({
                        "rule_id": "cross_fitness_food_fashion",
                        "说明": "购物车同时有运动服饰和运动补给，优先推荐运动配件和更多健康食品。",
                        "boost_brands": [],
                        "boost_categories": ["服饰运动", "食品饮料"],
                        "boost_sub_categories": ["运动袜", "速干T恤", "跑步鞋", "即食麦片", "矿泉水", "蛋白粉"],
                        "boost_tags": ["运动", "健身", "健康", "补给", "高蛋白"],
                    })
            if cat == "美妆护肤" and "服饰运动" in categories:
                if sub in {"防晒", "防晒喷雾"}:
                    rules.append({
                        "rule_id": "cross_sunscreen_outdoor",
                        "说明": "购物车同时有防晒和户外服饰，优先推荐更多户外防护和便携装备。",
                        "boost_brands": [],
                        "boost_categories": ["美妆护肤", "服饰运动"],
                        "boost_sub_categories": ["防晒衣", "帽子", "背包", "徒步鞋", "冲锋衣"],
                        "boost_tags": ["防晒", "户外", "防水", "透气", "轻量"],
                    })

        # Deduplicate by rule_id
        unique: dict[str, dict[str, Any]] = {}
        for rule in rules:
            unique.setdefault(rule["rule_id"], rule)
        return list(unique.values())

    def _inventory_coverage(self, products: list[Product], parsed_query: ParsedQuery) -> dict[str, Any]:
        cart_brands = list(dict.fromkeys(item.brand for item in products if item.brand))
        premium_brands = [
            brand for brand in cart_brands
            if brand in {"兰蔻", "SK-II", "雅诗兰黛", "资生堂", "娇韵诗", "科颜氏", "修丽可"}
        ]
        if not parsed_query.category:
            return {
                "目标类目": None,
                "购物车高端/同品牌": premium_brands,
                "目标库存品牌": [],
                "缺少同品牌目标商品": [],
                "可用同品牌相邻商品": [],
            }
        target_products = [
            item for item in self.product_repository.list_products()
            if item.category == parsed_query.category
            and (not parsed_query.sub_category or item.sub_category == parsed_query.sub_category)
        ]
        target_brands = sorted({item.brand for item in target_products if item.brand})
        missing = [
            brand for brand in premium_brands
            if not any(brand == target_brand or brand in target_brand or target_brand in brand for target_brand in target_brands)
        ]
        adjacent = [
            {
                "sku_id": item.sku_id,
                "name": item.name,
                "brand": item.brand,
                "sub_category": item.sub_category,
                "price": item.price,
            }
            for item in self.product_repository.list_products()
            if item.category == parsed_query.category
            and item.brand in premium_brands
            and (parsed_query.sub_category and item.sub_category != parsed_query.sub_category)
        ][:6]
        return {
            "目标类目": parsed_query.category,
            "目标子类": parsed_query.sub_category,
            "购物车高端/同品牌": premium_brands,
            "目标库存品牌": target_brands,
            "缺少同品牌目标商品": missing,
            "可用同品牌相邻商品": adjacent,
            "说明": (
                "当前目标子类没有购物车同品牌商品，不能强行推荐不存在商品。"
                if missing and parsed_query.sub_category else ""
            ),
        }

    @staticmethod
    def _needs_llm(products: list[Product], parsed_query: ParsedQuery, rules: list[dict[str, Any]]) -> bool:
        message = parsed_query.raw_message or ""
        relationship_signal = any(
            term in message
            for term in [
                "搭配",
                "兼容",
                "配套",
                "一整套",
                "一起买",
                "一起用",
                "一起吃",
                "同系列",
                "同品牌",
                "补齐",
                "还缺",
                "组合",
                "配着",
                "购物车",
                "加购的",
            ]
        )
        if not relationship_signal:
            return False
        if rules:
            return False
        categories = {item.category for item in products if item.category}
        cart_subs = {item.sub_category for item in products if item.sub_category}
        if len(categories) >= 2:
            return True
        if parsed_query.category and parsed_query.category in categories:
            return True
        if parsed_query.sub_category and parsed_query.sub_category not in cart_subs:
            return True
        return True

    def _doubao_analysis(self, products: list[Product], parsed_query: ParsedQuery) -> dict[str, Any]:
        context = {
            "任务": "请基于购物车商品输出结构化商品侧画像、搭配建议、推荐约束和排序理由。只输出JSON。",
            "当前用户需求": parsed_query.raw_message,
            "购物车商品": [
                {
                    "sku_id": item.sku_id,
                    "name": item.name,
                    "brand": item.brand,
                    "category": item.category,
                    "sub_category": item.sub_category,
                    "price": item.price,
                    "tags": item.tags,
                    "reviews_summary": item.reviews_summary,
                }
                for item in products
            ],
            "输出schema": {
                "商品标签": ["价格敏感/通勤风/数码生态等"],
                "搭配建议": [{"说明": "", "boost_categories": [], "boost_sub_categories": [], "boost_brands": [], "boost_tags": []}],
                "推荐约束": {"soft_constraints": []},
                "排序理由": [],
            },
        }
        raw = self.llm_client.generate_response(
            intent=IntentType.RECOMMEND,
            message=parsed_query.raw_message,
            context=json.dumps(context, ensure_ascii=False),
            product_names=[item.name for item in products[:3]],
        )
        return _extract_json(raw)


def _price_profile(products: list[Product]) -> dict[str, Any]:
    prices = [item.price for item in products]
    avg = sum(prices) / len(prices)
    return {
        "min": min(prices),
        "max": max(prices),
        "avg": round(avg, 2),
        "tier": "low" if avg <= 150 else "high" if avg >= 3000 else "mid",
    }


def _price_fit_boost(price: float, profile: dict[str, Any]) -> float:
    avg = profile.get("avg")
    tier = profile.get("tier")
    if not avg:
        return 0.0
    if tier == "low" and price <= max(float(avg) * 1.5, 200):
        return 0.06
    if tier == "high" and price >= float(avg) * 0.35:
        return 0.05
    if tier == "mid" and abs(price - float(avg)) / max(float(avg), 1) <= 0.45:
        return 0.04
    return 0.0


def _brief_product(item: Product) -> dict[str, Any]:
    return {
        "sku_id": item.sku_id,
        "name": item.name,
        "brand": item.brand,
        "category": item.category,
        "sub_category": item.sub_category,
        "price": item.price,
        "tags": item.tags[:6],
    }


def _extract_json(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(content[start:end + 1])
                return payload if isinstance(payload, dict) else {}
            except Exception:
                return {}
    return {}
