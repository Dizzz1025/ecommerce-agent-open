import re

from app.models.agent import ParsedQuery, PreferenceUpdateResult
from app.models.domain import SessionState


class PreferenceManager:
    """Updates long-term preferences only for explicit stable preference cues."""

    _future_markers = ["以后", "之后", "一直", "长期", "平时", "一般", "通常", "经常", "记住", "以后都"]
    _like_markers = ["喜欢", "偏好", "更爱", "比较爱", "倾向", "常买"]
    _dislike_markers = ["不喜欢", "讨厌", "以后不要", "别给我推荐", "不想要", "避开", "拉黑"]

    def update_from_query(self, parsed_query: ParsedQuery, state: SessionState) -> PreferenceUpdateResult:
        message = parsed_query.raw_message
        if not any(marker in message for marker in self._future_markers + self._like_markers + self._dislike_markers):
            return PreferenceUpdateResult(updated=False)

        preferences = state.user.global_preferences
        updates: dict[str, list[str] | str] = {}

        if any(marker in message for marker in self._like_markers):
            styles = [
                term
                for term in [
                    "清爽", "不油腻", "轻薄", "温和", "敏感肌", "保湿", "控油", "轻量", "通勤", "百搭",
                    "性价比", "学生党", "降噪", "续航", "拍照", "无糖", "低糖", "低脂", "提神",
                ]
                if term in message
            ]
            for term in styles:
                if term not in preferences.preferred_style:
                    preferences.preferred_style.append(term)
            if styles:
                updates["preferred_style"] = styles

        if any(marker in message for marker in self._dislike_markers) or "以后不要" in message:
            avoid_terms = list(parsed_query.negative_constraints)
            for term in ["酒精", "香精", "皂基", "太贵", "油腻", "厚重", "黏腻", "入耳式", "日系", "太甜", "咖啡因"]:
                if term in message:
                    avoid_terms.append(term)
            for term in sorted(set(avoid_terms)):
                if term and term not in preferences.avoid_terms:
                    preferences.avoid_terms.append(term)
            if parsed_query.brands_exclude:
                for brand in parsed_query.brands_exclude:
                    if brand not in preferences.excluded_brands:
                        preferences.excluded_brands.append(brand)
            if avoid_terms:
                updates["avoid_terms"] = sorted(set(avoid_terms))
            if parsed_query.brands_exclude:
                updates["excluded_brands"] = parsed_query.brands_exclude

        price_match = re.search(r"(?:预算|一般|通常|平时).*?(\d+(?:\.\d+)?)\s*元?\s*(?:以内|以下|左右)?", message)
        if price_match:
            preferences.price_preference = f"{float(price_match.group(1)):g}元以内"
            updates["price_preference"] = preferences.price_preference

        if parsed_query.brands_include and any(marker in message for marker in self._like_markers):
            for brand in parsed_query.brands_include:
                if brand not in preferences.preferred_brands:
                    preferences.preferred_brands.append(brand)
            updates["preferred_brands"] = parsed_query.brands_include

        if not updates:
            return PreferenceUpdateResult(updated=False)

        return PreferenceUpdateResult(
            updated=True,
            message="明白，之后帮你挑商品时我会参考这个偏好；如果你这次有明确预算或功能要求，我会优先按这次的要求来筛。",
            updates=updates,
            needs_confirmation=False,
        )
