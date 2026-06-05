from __future__ import annotations

import re
from typing import Any

from app.llm.base import BaseLLMClient


class VisionAnalyzer:
    """Analyze product attributes from an uploaded image with VLM fallback."""

    def __init__(self, llm_client: BaseLLMClient, vision_model: str | None = None) -> None:
        self.llm_client = llm_client
        self.vision_model = vision_model

    def analyze(self, *, image_input: dict[str, Any], message: str) -> dict[str, Any]:
        if not image_input.get("ok"):
            return self._wrap({}, source="none", error=image_input)
        llm_result = self.llm_client.analyze_image(
            {
                "message": message,
                "image_url": image_input.get("image_url"),
                "image_path": image_input.get("image_path"),
                "vision_model": self.vision_model,
            }
        )
        if llm_result:
            return self._wrap(self._normalize(llm_result, message), source=self.llm_client.__class__.__name__, error=None)
        return self._wrap(self._local_fallback(message, image_input), source="local_heuristic", error=None)

    @staticmethod
    def _wrap(payload: dict[str, Any], *, source: str, error: dict[str, Any] | None) -> dict[str, Any]:
        result = {
            "中文说明": "从用户上传图片中识别出的商品和视觉属性。",
            "主要商品类别": payload.get("主要商品类别"),
            "候选商品类别": payload.get("候选商品类别", []),
            "颜色": payload.get("颜色", []),
            "款式": payload.get("款式", []),
            "材质或质感": payload.get("材质或质感", []),
            "图案": payload.get("图案", []),
            "使用场景": payload.get("使用场景", []),
            "相似检索关键词": payload.get("相似检索关键词", []),
            "置信度": float(payload.get("置信度") or 0.0),
            "不确定点": payload.get("不确定点", []),
            "分析来源": source,
        }
        if error:
            result["错误"] = error
        return result

    @staticmethod
    def _normalize(payload: dict[str, Any], message: str) -> dict[str, Any]:
        category = payload.get("主要商品类别") or _category_from_text(message)
        if category in {"商品", "物品", "产品", "不确定"}:
            category = _category_from_text(message) or category
        keywords = payload.get("相似检索关键词") or []
        if category and not keywords:
            keywords = [f"{' '.join(payload.get('颜色', []))} {' '.join(payload.get('款式', []))} {category}".strip()]
        return {
            "主要商品类别": category,
            "候选商品类别": _list(payload.get("候选商品类别")) or ([category] if category else []),
            "颜色": _list(payload.get("颜色")),
            "款式": _list(payload.get("款式")),
            "材质或质感": _list(payload.get("材质或质感")),
            "图案": _list(payload.get("图案")),
            "使用场景": _list(payload.get("使用场景")),
            "相似检索关键词": _list(keywords),
            "置信度": payload.get("置信度") or 0.65,
            "不确定点": _list(payload.get("不确定点")),
        }

    @staticmethod
    def _local_fallback(message: str, image_input: dict[str, Any]) -> dict[str, Any]:
        source = f"{message} {image_input.get('image_path') or image_input.get('image_url') or ''}"
        category = _category_from_text(source)
        colors = [term for term in ["黑色", "白色", "蓝色", "浅蓝色", "红色", "粉色", "灰色", "绿色", "米色", "棕色"] if term in source]
        styles = [term for term in ["通勤", "旅行", "户外", "厚底", "收腰", "长款", "大号", "简约", "休闲", "同款", "相似风格"] if term in source]
        scenes = [term for term in ["通勤", "旅行", "户外", "日常出街", "海边", "学生", "职场"] if term in source]
        keywords = [" ".join([*colors, *styles, category or "相似商品"]).strip()]
        return {
            "主要商品类别": category,
            "候选商品类别": [category] if category else [],
            "颜色": colors,
            "款式": styles,
            "材质或质感": [],
            "图案": [],
            "使用场景": scenes,
            "相似检索关键词": [item for item in keywords if item],
            "置信度": 0.48 if category else 0.25,
            "不确定点": ["未调用可用视觉模型，当前结果来自文本和图片文件名的保守推断。"],
        }


def _category_from_text(text: str) -> str | None:
    rules = [
        # 美妆护肤
        ("化妆品", ["化妆品", "彩妆", "cosmetic", "makeup"]),
        ("护肤品", ["护肤品", "护肤", "skincare"]),
        ("精华", ["精华", "精华液", "serum"]),
        ("面霜", ["面霜", "乳霜", "cream"]),
        ("爽肤水", ["爽肤水", "化妆水", "toner"]),
        ("洁面", ["洁面", "洗面奶", "cleanser"]),
        ("防晒", ["防晒"]),
        ("眼霜", ["眼霜"]),
        ("粉底液", ["粉底液", "粉底"]),
        ("面膜", ["面膜"]),
        ("卸妆", ["卸妆", "卸妆油", "卸妆水"]),
        ("唇釉", ["唇釉", "口红"]),
        ("眉笔", ["眉笔"]),
        ("蜜粉", ["蜜粉", "散粉"]),
        ("眼线笔", ["眼线笔"]),
        # 服饰运动 — 上衣外套
        ("冲锋衣", ["冲锋衣", "硬壳", "jacket"]),
        ("羽绒服", ["羽绒服", "棉服"]),
        ("防晒衣", ["防晒衣"]),
        ("卫衣", ["卫衣"]),
        ("短袖", ["短袖", "t恤", "T恤", "tee", "t-shirt"]),
        ("速干T恤", ["速干衣", "速干T恤", "速干t恤"]),
        ("休闲衬衫", ["衬衫"]),
        ("外套", ["外套", "夹克", "休闲外套"]),
        ("上衣", ["上衣", "衣服", "穿搭", "街拍", "top", "outfit"]),
        # 服饰运动 — 下装
        ("运动长裤", ["运动裤", "长裤"]),
        ("运动短裤", ["短裤"]),
        ("牛仔裤", ["牛仔裤"]),
        ("瑜伽裤", ["瑜伽裤"]),
        ("骑行裤", ["骑行裤"]),
        ("户外裤", ["户外裤"]),
        # 服饰运动 — 鞋
        ("跑步鞋", ["跑鞋", "跑步鞋", "老爹鞋", "鞋子", "运动鞋", "sneaker", "shoe"]),
        ("篮球鞋", ["篮球鞋"]),
        ("徒步鞋", ["徒步鞋"]),
        ("板鞋", ["板鞋", "帆布鞋"]),
        ("沙滩拖鞋", ["拖鞋", "凉拖"]),
        # 服饰运动 — 配饰
        ("背包", ["背包", "双肩包", "书包", "backpack"]),
        ("帽子", ["帽子", "鸭舌帽", "棒球帽"]),
        ("运动袜", ["运动袜", "袜子"]),
        ("泳衣", ["泳衣", "泳装"]),
        ("运动内衣", ["运动内衣"]),
        ("登山杖", ["登山杖"]),
        # 数码电子
        ("手机", ["手机", "智能手机"]),
        ("笔记本电脑", ["电脑", "笔记本", "笔记本电脑"]),
        ("平板电脑", ["平板", "平板电脑"]),
        ("真无线耳机", ["耳机"]),
        # 食品饮料
        ("咖啡", ["咖啡"]),
        ("茶饮", ["茶", "茶饮"]),
        ("牛奶", ["牛奶"]),
        ("酸奶", ["酸奶"]),
        ("坚果/零食", ["坚果", "零食"]),
        ("碳酸饮料", ["碳酸饮料", "气泡水"]),
        ("功能饮料", ["功能饮料"]),
        ("方便食品", ["方便面", "泡面", "方便食品"]),
        ("调味品", ["调味品", "酱油"]),
        ("饮料", ["饮料", "喝的"]),
        # 日用百货
        ("发圈", ["发圈", "头绳"]),
        ("办公文具", ["办公文具", "文具"]),
        ("桌面收纳", ["桌面收纳", "收纳盒"]),
        # 库存不支持
        ("连衣裙", ["连衣裙", "裙子", "长裙", "dress"]),
        ("毛绒玩偶", ["毛绒", "玩偶", "公仔", "toy", "doll"]),
    ]
    lower = text.lower()
    for category, terms in rules:
        if any(term in lower or term in text for term in terms):
            return category
    cjk = re.findall(r"[一-鿿]{2,6}", text)
    return cjk[0] if cjk else None


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []
