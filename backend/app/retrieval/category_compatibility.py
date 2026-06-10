"""Small, explicit category compatibility rules for inventory retrieval.

The dataset contains fine-grained sub-categories such as "男士洁面" and
"防晒喷雾". User queries are often broader ("洁面", "防晒霜"). These helpers
keep hard filters strict at the main-category level while allowing safe
same-family sub-category matches.
"""

from __future__ import annotations


_SUB_CATEGORY_FAMILIES: tuple[set[str], ...] = (
    {"洁面", "男士洁面"},
    {"防晒", "防晒喷雾"},
    {"精华", "祛痘精华", "精华油", "安瓶"},
    {"底妆", "粉底液", "BB霜", "素颜霜", "隔离霜", "蜜粉"},
    {"短袖T恤", "速干T恤"},
    {"外套", "冲锋衣", "羽绒服", "防晒衣", "卫衣", "休闲衬衫"},
    {"运动鞋", "跑步鞋", "篮球鞋", "徒步鞋", "板鞋"},
    {"裤子", "运动长裤", "瑜伽裤", "骑行裤", "运动短裤", "户外裤", "牛仔裤"},
    {"饮料", "茶饮", "碳酸饮料", "功能饮料", "牛奶", "酸奶", "咖啡", "乳酸菌饮品", "矿泉水", "纯果汁"},
    {"早餐", "方便食品", "即食麦片", "牛奶", "酸奶", "咖啡", "苏打饼干"},
    {"健身补给", "蛋白粉", "能量棒", "牛奶", "酸奶", "功能饮料"},
    {"办公设备", "笔记本电脑", "平板电脑", "家用打印机", "显示器"},
)

_SAFE_CONTAINMENT_ROOTS = ("洁面", "防晒", "精华", "T恤", "外套", "运动鞋", "裤", "饮料", "早餐")


def sub_category_matches(query_sub_category: str | None, product_sub_category: str | None) -> bool:
    """Return whether a product sub-category can satisfy a query sub-category.

    This is intentionally conservative: it only relaxes exact equality for
    families where the broader user wording is clearly a parent concept.
    """

    if not query_sub_category:
        return True
    if not product_sub_category:
        return False
    query_sub_category = query_sub_category.strip()
    product_sub_category = product_sub_category.strip()
    if query_sub_category == product_sub_category:
        return True
    for family in _SUB_CATEGORY_FAMILIES:
        if query_sub_category in family and product_sub_category in family:
            return True
    return any(root in query_sub_category and root in product_sub_category for root in _SAFE_CONTAINMENT_ROOTS)


def sub_category_match_level(query_sub_category: str | None, product_sub_category: str | None) -> str:
    if not query_sub_category:
        return "not_requested"
    if not product_sub_category:
        return "missing"
    if query_sub_category == product_sub_category:
        return "exact"
    if sub_category_matches(query_sub_category, product_sub_category):
        return "compatible"
    return "mismatch"
