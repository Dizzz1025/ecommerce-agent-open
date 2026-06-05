from __future__ import annotations

from typing import Any

from app.llm.base import BaseLLMClient
from app.memory.user_history_store import UserHistoryStore


class UserProfileService:
    """Summarize user history into a stable, non-sensitive shopping profile."""

    def __init__(self, history_store: UserHistoryStore, llm_client: BaseLLMClient) -> None:
        self.history_store = history_store
        self.llm_client = llm_client

    def maybe_refresh_profile(self, user_id: str, *, force: bool = False) -> dict[str, Any]:
        existing_profile = self.history_store.load_profile(user_id)
        privacy = existing_profile.get("privacy_settings") or {}
        if privacy.get("personalization_mode") == "off" or privacy.get("personalization_enabled") is False:
            return existing_profile
        if privacy.get("personalization_mode") == "semantic":
            natural, structured = self._semantic_profile(existing_profile.get("semantic_memory") or {})
            return self.history_store.save_profile_summary(
                user_id=user_id,
                natural_summary=natural,
                structured_profile=structured,
                history_summary=natural,
            )

        turns = self.history_store.recent_turns_for_profile(user_id, max_turns=20)
        if not turns:
            return existing_profile
        if not force:
            return existing_profile

        compact_turns = [
            {
                "用户输入": turn.get("user_input"),
                "系统回复": turn.get("assistant_reply"),
                "推荐商品": [
                    {
                        "sku_id": item.get("sku_id"),
                        "name": item.get("name"),
                        "price": item.get("price"),
                        "category": item.get("category"),
                    }
                    for item in turn.get("recommended_products", [])[:3]
                ],
                "购物车变化": turn.get("cart_change", []),
            }
            for turn in turns[-12:]
        ]
        profile = self.llm_client.analyze_user_profile(
            {
                "任务说明": USER_PROFILE_SUMMARY_PROMPT,
                "最近对话": compact_turns,
                "输出格式": {
                    "自然语言用户画像": "string",
                    "结构化用户画像": {
                        "说话风格": "string",
                        "语言风格": "string",
                        "价格偏好": "string",
                        "商品类别偏好": ["string"],
                        "品牌偏好": ["string"],
                        "排斥条件": ["string"],
                        "决策风格": "string",
                        "信息关注点": ["string"],
                        "客服交互偏好": "string",
                        "用户自述信息": ["string"],
                    },
                },
            }
        )
        natural = str(profile.get("自然语言用户画像") or "").strip()
        structured = profile.get("结构化用户画像") if isinstance(profile.get("结构化用户画像"), dict) else {}
        if not natural:
            natural, structured = self._local_fallback(compact_turns)
        return self.history_store.save_profile_summary(
            user_id=user_id,
            natural_summary=natural,
            structured_profile=structured,
            history_summary=natural,
        )

    @staticmethod
    def _semantic_profile(semantic_memory: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        categories = _top_keys(semantic_memory.get("category_counts", {}), 4)
        features = _top_keys(semantic_memory.get("feature_counts", {}), 8)
        avoids = _top_keys(semantic_memory.get("negative_constraint_counts", {}), 8)
        styles = _top_keys(semantic_memory.get("style_signals", {}), 6)
        price_signals = semantic_memory.get("price_signals", [])[-5:]
        price_text = "暂无稳定价格偏好"
        if price_signals:
            latest = price_signals[-1]
            if latest.get("max") is not None:
                price_text = f"近期在{latest.get('category') or '部分商品'}上关注{latest.get('max'):g}元以内"
        summary_parts = ["用户开启了隐私个性化模式，系统仅使用结构化偏好摘要，不使用历史原文。"]
        if categories:
            summary_parts.append(f"近期关注类别：{'、'.join(categories)}。")
        if features or styles:
            summary_parts.append(f"常见偏好标签：{'、'.join(list(dict.fromkeys([*features, *styles]))[:8])}。")
        if avoids:
            summary_parts.append(f"常见排除标签：{'、'.join(avoids)}。")
        structured = {
            "说话风格": "隐私模式下不使用历史原文推断",
            "语言风格": "默认简洁自然",
            "价格偏好": price_text,
            "商品类别偏好": categories,
            "品牌偏好": _top_keys(semantic_memory.get("brand_counts", {}), 5),
            "排斥条件": avoids,
            "决策风格": "根据结构化偏好先给结论，再给少量理由",
            "信息关注点": list(dict.fromkeys([*features, *styles]))[:8],
            "客服交互偏好": "默认少问问题，优先给可选商品",
            "用户自述信息": [],
        }
        return "".join(summary_parts), structured

    @staticmethod
    def _local_fallback(turns: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        categories: list[str] = []
        focus_terms: list[str] = []
        price_words = []
        user_self_info: list[str] = []
        for turn in turns:
            text = f"{turn.get('用户输入', '')} {turn.get('系统回复', '')}"
            if any(term in text for term in ["我是4岁", "我四岁", "4岁小朋友", "四岁小朋友", "小朋友"]):
                user_self_info.append("用户自述/扮演为小朋友，儿童场景推荐需更谨慎")
            if any(term in text for term in ["女生", "女性", "女孩子"]):
                user_self_info.append("用户明确提到女性使用场景")
            for product in turn.get("推荐商品", []):
                category = product.get("category")
                if category:
                    categories.append(category)
            for term in ["性价比", "便宜", "预算", "拍照", "续航", "清爽", "轻量", "保湿", "降噪", "通勤"]:
                if term in text:
                    focus_terms.append(term)
            if any(term in text for term in ["预算", "以内", "便宜", "性价比"]):
                price_words.append("关注价格和性价比")
        summary = "用户表达较直接，倾向于通过多轮补充条件完成筛选。"
        if price_words:
            summary += "购物时较关注预算和性价比。"
        if categories:
            summary += f"近期关注较多的类别包括：{'、'.join(list(dict.fromkeys(categories))[:4])}。"
        if focus_terms:
            summary += f"常提到的信息关注点包括：{'、'.join(list(dict.fromkeys(focus_terms))[:6])}。"
        if user_self_info:
            summary += f"明确上下文：{'、'.join(list(dict.fromkeys(user_self_info))[:2])}。"
        structured = {
            "说话风格": "直接、口语化",
            "语言风格": "偏简洁",
            "价格偏好": "关注预算和性价比" if price_words else "暂无稳定价格偏好",
            "商品类别偏好": list(dict.fromkeys(categories))[:5],
            "品牌偏好": [],
            "排斥条件": [],
            "决策风格": "倾向先看结论，再补充条件细化",
            "信息关注点": list(dict.fromkeys(focus_terms))[:8],
            "客服交互偏好": "可以接受系统主动澄清，但问题不宜过多",
            "用户自述信息": list(dict.fromkeys(user_self_info))[:5],
        }
        return summary, structured


def _top_keys(counter: dict[str, Any], limit: int) -> list[str]:
    if not isinstance(counter, dict):
        return []
    return [
        key
        for key, _ in sorted(counter.items(), key=lambda item: item[1], reverse=True)
        if key
    ][:limit]


USER_PROFILE_SUMMARY_PROMPT = """
你是电商导购系统的用户历史分析器。请根据用户明确说过的话和真实交互记录，总结可用于后续推荐的非敏感购物画像。

必须遵守：
1. 不要强行推断敏感身份信息，包括性别、年龄、职业、收入、健康状况等。
2. 只有用户明确说“我是女生/男生”“给女朋友买”“送爸爸”等，才可写入“用户自述信息”或“送礼对象信息”。
3. 当前任务中的临时条件不要误写成长期偏好；只有“以后都不要”“我一直不喜欢”“记住我喜欢”等明确长期表达才写入长期偏好或排斥条件。
4. 输出必须是 JSON，不要输出解释文本。
5. 自然语言用户画像要简短，适合放入后续 Doubao 回复生成 prompt 作为软约束。
6. 结构化用户画像中的字段缺少依据时，用空数组或“暂无稳定偏好”。
"""
