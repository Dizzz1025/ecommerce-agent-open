from __future__ import annotations

from typing import Any


class VisualQueryBuilder:
    """Fuse visual attributes with user text into retrieval-friendly query fields."""

    inventory_map = {
        # ---- 美妆护肤 ----
        "化妆品": ("美妆护肤", None, True, "按美妆护肤类商品检索"),
        "护肤品": ("美妆护肤", None, True, "按美妆护肤类商品检索"),
        "彩妆": ("美妆护肤", None, True, "按美妆护肤/彩妆相关库存检索"),
        "精华": ("美妆护肤", "精华", True, "精华"),
        "精华液": ("美妆护肤", "精华", True, "精华"),
        "面霜": ("美妆护肤", "面霜", True, "面霜"),
        "乳霜": ("美妆护肤", "面霜", True, "面霜"),
        "爽肤水": ("美妆护肤", "化妆水", True, "化妆水/爽肤水"),
        "化妆水": ("美妆护肤", "化妆水", True, "化妆水"),
        "洁面": ("美妆护肤", "洁面", True, "洁面"),
        "洗面奶": ("美妆护肤", "洁面", True, "洁面"),
        "防晒": ("美妆护肤", "防晒", True, "防晒"),
        "防晒霜": ("美妆护肤", "防晒", True, "防晒"),
        "眼霜": ("美妆护肤", "眼霜", True, "眼霜"),
        "粉底液": ("美妆护肤", "粉底液", True, "粉底液"),
        "粉底": ("美妆护肤", "粉底液", True, "粉底液"),
        "面膜": ("美妆护肤", "面膜", True, "面膜"),
        "卸妆": ("美妆护肤", "卸妆", True, "卸妆"),
        "卸妆油": ("美妆护肤", "卸妆", True, "卸妆"),
        "唇釉": ("美妆护肤", "唇釉", True, "唇釉"),
        "口红": ("美妆护肤", "唇釉", True, "唇釉"),
        "眉笔": ("美妆护肤", "眉笔", True, "眉笔"),
        "蜜粉": ("美妆护肤", "蜜粉", True, "蜜粉"),
        "散粉": ("美妆护肤", "蜜粉", True, "蜜粉"),
        "眼线笔": ("美妆护肤", "眼线笔", True, "眼线笔"),
        # ---- 数码电子 ----
        "手机": ("数码电子", "智能手机", True, "手机"),
        "智能手机": ("数码电子", "智能手机", True, "手机"),
        "电脑": ("数码电子", "笔记本电脑", True, "笔记本电脑"),
        "笔记本": ("数码电子", "笔记本电脑", True, "笔记本电脑"),
        "笔记本电脑": ("数码电子", "笔记本电脑", True, "笔记本电脑"),
        "平板": ("数码电子", "平板电脑", True, "平板电脑"),
        "平板电脑": ("数码电子", "平板电脑", True, "平板电脑"),
        "耳机": ("数码电子", "真无线耳机", True, "耳机"),
        "蓝牙耳机": ("数码电子", "真无线耳机", True, "耳机"),
        "无线耳机": ("数码电子", "真无线耳机", True, "耳机"),
        "相机": ("数码电子", None, True, "数码电子类商品"),
        # ---- 服饰运动：上衣/外套 ----
        "上衣": ("服饰运动", "短袖T恤", True, "按上衣/短袖T恤库存检索"),
        "短袖": ("服饰运动", "短袖T恤", True, "短袖T恤"),
        "T恤": ("服饰运动", "短袖T恤", True, "短袖T恤"),
        "t恤": ("服饰运动", "短袖T恤", True, "短袖T恤"),
        "速干衣": ("服饰运动", "速干T恤", True, "速干T恤"),
        "外套": ("服饰运动", None, True, "按服饰运动外套类库存检索"),
        "夹克": ("服饰运动", None, True, "按服饰运动外套类库存检索"),
        "休闲外套": ("服饰运动", None, True, "按服饰运动外套类库存检索"),
        "冲锋衣": ("服饰运动", "冲锋衣", True, "冲锋衣/硬壳夹克"),
        "羽绒服": ("服饰运动", "羽绒服", True, "羽绒服"),
        "防晒衣": ("服饰运动", "防晒衣", True, "防晒衣/防晒外套"),
        "卫衣": ("服饰运动", "卫衣", True, "卫衣/套头衫"),
        "衬衫": ("服饰运动", "休闲衬衫", True, "休闲衬衫"),
        "衣服": ("服饰运动", None, True, "按服饰运动类库存检索"),
        "穿搭": ("服饰运动", None, True, "按服饰运动类库存检索"),
        # ---- 服饰运动：下装 ----
        "运动裤": ("服饰运动", "运动长裤", True, "运动长裤"),
        "长裤": ("服饰运动", "运动长裤", True, "运动长裤"),
        "短裤": ("服饰运动", "运动短裤", True, "运动短裤"),
        "运动短裤": ("服饰运动", "运动短裤", True, "运动短裤"),
        "牛仔裤": ("服饰运动", "牛仔裤", True, "牛仔裤"),
        "瑜伽裤": ("服饰运动", "瑜伽裤", True, "瑜伽裤"),
        "骑行裤": ("服饰运动", "骑行裤", True, "骑行裤"),
        "户外裤": ("服饰运动", "户外裤", True, "户外裤"),
        # ---- 服饰运动：鞋类 ----
        "跑鞋": ("服饰运动", "跑步鞋", True, "跑步鞋"),
        "跑步鞋": ("服饰运动", "跑步鞋", True, "跑步鞋"),
        "运动鞋": ("服饰运动", "跑步鞋", True, "按相似运动鞋/跑步鞋检索"),
        "老爹鞋": ("服饰运动", "跑步鞋", True, "当前库没有老爹鞋专门子类，按相似运动休闲鞋检索"),
        "鞋子": ("服饰运动", "跑步鞋", True, "按相似运动鞋/跑步鞋检索"),
        "篮球鞋": ("服饰运动", "篮球鞋", True, "篮球鞋"),
        "徒步鞋": ("服饰运动", "徒步鞋", True, "徒步鞋"),
        "板鞋": ("服饰运动", "板鞋", True, "板鞋/帆布鞋"),
        "帆布鞋": ("服饰运动", "板鞋", True, "板鞋/帆布鞋"),
        "拖鞋": ("服饰运动", "沙滩拖鞋", True, "沙滩拖鞋"),
        # ---- 服饰运动：配饰装备 ----
        "背包": ("服饰运动", "背包", True, "背包"),
        "双肩包": ("服饰运动", "背包", True, "背包"),
        "帽子": ("服饰运动", "帽子", True, "帽子"),
        "运动帽": ("服饰运动", "帽子", True, "帽子"),
        "棒球帽": ("服饰运动", "帽子", True, "帽子"),
        "运动袜": ("服饰运动", "运动袜", True, "运动袜"),
        "袜子": ("服饰运动", "运动袜", True, "运动袜"),
        "泳衣": ("服饰运动", "泳衣", True, "泳衣"),
        "泳装": ("服饰运动", "泳衣", True, "泳衣"),
        "运动内衣": ("服饰运动", "运动内衣", True, "运动内衣"),
        "登山杖": ("服饰运动", "登山杖", True, "登山杖"),
        # ---- 食品饮料 ----
        "饮料": ("食品饮料", None, True, "饮料"),
        "咖啡": ("食品饮料", "咖啡", True, "咖啡"),
        "茶": ("食品饮料", "茶饮", True, "茶饮"),
        "茶饮": ("食品饮料", "茶饮", True, "茶饮"),
        "牛奶": ("食品饮料", "牛奶", True, "牛奶"),
        "酸奶": ("食品饮料", "酸奶", True, "酸奶"),
        "零食": ("食品饮料", "坚果/零食", True, "坚果/零食"),
        "坚果": ("食品饮料", "坚果/零食", True, "坚果/零食"),
        "方便面": ("食品饮料", "方便食品", True, "方便食品"),
        "泡面": ("食品饮料", "方便食品", True, "方便食品"),
        "碳酸饮料": ("食品饮料", "碳酸饮料", True, "碳酸饮料"),
        "功能饮料": ("食品饮料", "功能饮料", True, "功能饮料"),
        "调味品": ("食品饮料", "调味品", True, "调味品"),
        "酱油": ("食品饮料", "调味品", True, "调味品"),
        # ---- 日用百货 ----
        "发圈": ("日用百货", "发圈", True, "发圈"),
        "头绳": ("日用百货", "发圈", True, "发圈"),
        "办公文具": ("日用百货", "办公文具", True, "办公文具"),
        "文具": ("日用百货", "办公文具", True, "办公文具"),
        "桌面收纳": ("日用百货", "桌面收纳", True, "桌面收纳"),
        "通勤小物": ("日用百货", "通勤小物", True, "通勤小物"),
        # ---- 库存不覆盖的商品类型 ----
        "连衣裙": (None, None, False, "当前商品库暂时没有连衣裙/裙装类库存"),
        "裙子": (None, None, False, "当前商品库暂时没有裙装类库存"),
        "毛绒玩偶": (None, None, False, "当前商品库暂时没有毛绒玩偶类库存"),
        "玩具": (None, None, False, "当前商品库暂时没有玩具类库存"),
        "家具": (None, None, False, "当前商品库暂时没有家具类库存"),
        "家电": (None, None, False, "当前商品库暂时没有家电类库存"),
    }

    def build(self, *, message: str, visual_result: dict[str, Any]) -> dict[str, Any]:
        target = visual_result.get("主要商品类别")
        category, sub_category, supported, inventory_note = self._match_target(target)
        visual_terms = _unique(
            [
                target,
                *visual_result.get("候选商品类别", []),
                *visual_result.get("颜色", []),
                *visual_result.get("款式", []),
                *visual_result.get("材质或质感", []),
                *visual_result.get("图案", []),
                *visual_result.get("使用场景", []),
                *visual_result.get("相似检索关键词", []),
            ]
        )
        fused = " ".join([message, category or "", sub_category or "", *visual_terms]).strip()
        return {
            "中文说明": "把图片属性和用户文本融合后的结构化检索查询。",
            "融合后的检索文本": fused,
            "视觉关键词": visual_terms,
            "映射商品类别": category,
            "映射商品子类": sub_category,
            "库存匹配说明": inventory_note,
            "库存是否覆盖目标类目": supported,
            "目标商品类别": target,
        }

    @classmethod
    def _match_target(cls, target: str | None) -> tuple[str | None, str | None, bool, str]:
        """Match VLM output to inventory map with fuzzy fallback.

        VLM outputs like "雅诗兰黛小棕瓶面部精华" or "女士休闲街头风穿搭套装"
        don't exactly match our inventory_map keys. This method tries:
        1. Exact match against inventory_map keys
        2. Substring match (longest key found in target)
        3. Keyword-based heuristic for common category terms
        """
        if not target:
            return None, None, False, "未识别到图片中的商品类别"
        # 1. Exact match
        if target in cls.inventory_map:
            return cls.inventory_map[target]
        # 2. Substring match: find the longest inventory_map key that appears in target
        best_key = ""
        for key in cls.inventory_map:
            if key in target and len(key) > len(best_key):
                best_key = key
        if best_key:
            return cls.inventory_map[best_key]
        # 3. Keyword heuristic: scan target for known category-indicating terms
        _keyword_map = {
            "精华": ("美妆护肤", "精华", True, "精华类商品"),
            "面霜": ("美妆护肤", "面霜", True, "面霜类商品"),
            "防晒": ("美妆护肤", "防晒", True, "防晒类商品"),
            "洁面": ("美妆护肤", "洁面", True, "洁面类商品"),
            "眼霜": ("美妆护肤", "眼霜", True, "眼霜类商品"),
            "面膜": ("美妆护肤", "面膜", True, "面膜类商品"),
            "粉底": ("美妆护肤", "粉底液", True, "粉底液类商品"),
            "口红": ("美妆护肤", "唇釉", True, "唇釉/口红类商品"),
            "唇釉": ("美妆护肤", "唇釉", True, "唇釉/口红类商品"),
            "穿搭": ("服饰运动", None, True, "按服饰运动类库存检索"),
            "套装": ("服饰运动", None, True, "按服饰运动搭配检索"),
            "上衣": ("服饰运动", "短袖T恤", True, "上衣类商品"),
            "T恤": ("服饰运动", "短袖T恤", True, "短袖T恤"),
            "外套": ("服饰运动", None, True, "外套类商品"),
            "夹克": ("服饰运动", None, True, "外套类商品"),
            "跑鞋": ("服饰运动", "跑步鞋", True, "跑步鞋"),
            "运动鞋": ("服饰运动", "跑步鞋", True, "跑步鞋"),
            "鞋": ("服饰运动", "跑步鞋", True, "鞋类商品"),
            "裤": ("服饰运动", "运动长裤", True, "裤装类商品"),
            "背包": ("服饰运动", "背包", True, "背包"),
            "手机": ("数码电子", "智能手机", True, "手机"),
            "耳机": ("数码电子", "真无线耳机", True, "耳机"),
            "平板": ("数码电子", "平板电脑", True, "平板电脑"),
            "电脑": ("数码电子", "笔记本电脑", True, "笔记本电脑"),
            "笔记本": ("数码电子", "笔记本电脑", True, "笔记本电脑"),
            "咖啡": ("食品饮料", "咖啡", True, "咖啡"),
            "茶": ("食品饮料", "茶饮", True, "茶饮"),
            "牛奶": ("食品饮料", "牛奶", True, "牛奶"),
            "零食": ("食品饮料", "坚果/零食", True, "零食"),
            "饮料": ("食品饮料", None, True, "饮料"),
        }
        for keyword, entry in sorted(_keyword_map.items(), key=lambda x: len(x[0]), reverse=True):
            if keyword in target:
                return entry
        return None, None, False, f"当前商品库暂时没有「{target}」对应的明确库存类目"


def _unique(items: list[Any]) -> list[str]:
    result: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result
