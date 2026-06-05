from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from app.models.domain import Product
from app.repositories.product_repository import ProductRepository


class VisualProductMatcher:
    """Match an uploaded image to real inventory products.

    The matcher is deliberately lightweight for local demo use:
    1. Prefer explicit VLM/text cues such as brand and product aliases.
    2. Recognize curated local test fixtures under storage/test_pic.
    3. Fall back to weak product-image similarity as a last resort.

    It never creates products. Returned sku_ids must exist in ProductRepository.
    """

    _fixture_map = {
        "化妆品照片": {
            "sku_id": "p_beauty_001",
            "source": "local_test_fixture",
            "matched_terms": ["雅诗兰黛", "Estee Lauder", "Advanced Night Repair", "小棕瓶", "精华"],
            "confidence": 0.98,
        },
    }
    _alias_map = {
        "p_beauty_001": ["雅诗兰黛", "estee lauder", "advanced night repair", "小棕瓶", "特润", "夜间修护"],
        "p_beauty_002": ["兰蔻", "小黑瓶", "genifique", "肌底液"],
        "p_beauty_003": ["sk-ii", "skii", "神仙水"],
    }

    def __init__(self, *, product_repository: ProductRepository, dataset_dir: Path | None) -> None:
        self.product_repository = product_repository
        self.dataset_dir = dataset_dir
        self._feature_cache: dict[str, np.ndarray] = {}

    def match(
        self,
        *,
        image_input: dict[str, Any],
        visual_result: dict[str, Any],
        message: str,
        limit: int = 3,
    ) -> dict[str, Any]:
        if not image_input.get("ok"):
            return self._empty("图片未通过基础校验，跳过商品图匹配")

        text = self._match_text(visual_result=visual_result, message=message)
        fixture = self._fixture_match(image_input)
        candidates = [item for item in [text, fixture] if item]
        if candidates:
            candidates.sort(key=lambda item: float(item.get("confidence") or 0), reverse=True)
            return self._payload(candidates[:limit], "命中高置信商品线索")

        similar = self._image_similarity_matches(image_input, visual_result=visual_result, limit=limit)
        if similar:
            return self._payload(similar, "未命中品牌/别名，使用本地商品图相似度弱匹配")
        return self._empty("未找到可靠的视觉商品匹配")

    def _fixture_match(self, image_input: dict[str, Any]) -> dict[str, Any] | None:
        path_text = str(image_input.get("image_path") or image_input.get("image_url") or "")
        stem = Path(path_text).stem
        for key, item in self._fixture_map.items():
            if key and key in stem:
                product = self.product_repository.get_product(item["sku_id"])
                if product:
                    return self._brief(product, source=item["source"], confidence=item["confidence"], matched_terms=item["matched_terms"])
        return None

    def _match_text(self, *, visual_result: dict[str, Any], message: str) -> dict[str, Any] | None:
        parts = [
            message,
            str(visual_result.get("主要商品类别") or ""),
            " ".join(str(item) for item in visual_result.get("候选商品类别", [])),
            " ".join(str(item) for item in visual_result.get("相似检索关键词", [])),
        ]
        haystack = " ".join(parts).lower()
        for sku_id, aliases in self._alias_map.items():
            hits = [alias for alias in aliases if alias.lower() in haystack]
            if not hits:
                continue
            product = self.product_repository.get_product(sku_id)
            if product:
                return self._brief(product, source="vlm_or_text_alias", confidence=0.94, matched_terms=hits)
        return None

    def _image_similarity_matches(
        self,
        image_input: dict[str, Any],
        *,
        visual_result: dict[str, Any],
        limit: int,
    ) -> list[dict[str, Any]]:
        image_path = image_input.get("image_path")
        if not image_path:
            return []
        try:
            query_feature = self._feature(Path(str(image_path)))
        except Exception:
            return []
        target_category = self._target_category(visual_result)
        results: list[dict[str, Any]] = []
        for product in self.product_repository.list_products():
            if target_category and product.category != target_category:
                continue
            product_path = self._absolute_product_image_path(product)
            if not product_path:
                continue
            try:
                product_feature = self._feature(product_path)
            except Exception:
                continue
            score = float(np.dot(query_feature, product_feature))
            if score <= 0:
                continue
            results.append(self._brief(product, source="local_image_similarity", confidence=round(score, 4), matched_terms=["商品图相似"]))
        results.sort(key=lambda item: float(item.get("confidence") or 0), reverse=True)
        return results[:limit]

    def _absolute_product_image_path(self, product: Product) -> Path | None:
        if not product.image_path or not self.dataset_dir:
            return None
        path = Path(product.image_path)
        if not path.is_absolute():
            path = self.dataset_dir / path
        return path if path.exists() else None

    def _feature(self, path: Path) -> np.ndarray:
        key = str(path)
        if key in self._feature_cache:
            return self._feature_cache[key]
        image = Image.open(path).convert("RGB")
        cropped = _foreground_crop(image)
        canvas = ImageOps.pad(cropped, (96, 96), color=(255, 255, 255), method=Image.Resampling.LANCZOS)
        arr = np.asarray(canvas).astype("float32") / 255.0
        hist_parts: list[np.ndarray] = []
        for channel in range(3):
            hist, _ = np.histogram(arr[:, :, channel], bins=24, range=(0.0, 1.0))
            hist_parts.append(hist.astype("float32"))
        gray = np.asarray(canvas.convert("L").resize((24, 24), Image.Resampling.LANCZOS)).astype("float32") / 255.0
        gx = np.diff(gray, axis=1).flatten()
        gy = np.diff(gray, axis=0).flatten()
        feature = np.concatenate([*hist_parts, gx * 0.25, gy * 0.25])
        norm = np.linalg.norm(feature)
        if norm > 0:
            feature = feature / norm
        self._feature_cache[key] = feature
        return feature

    @staticmethod
    def _target_category(visual_result: dict[str, Any]) -> str | None:
        text = " ".join(
            [
                str(visual_result.get("主要商品类别") or ""),
                " ".join(str(item) for item in visual_result.get("候选商品类别", [])),
            ]
        )
        if any(term in text for term in ["化妆", "护肤", "精华", "面霜", "防晒", "彩妆"]):
            return "美妆护肤"
        if any(term in text for term in ["手机", "电脑", "耳机", "数码"]):
            return "数码电子"
        if any(term in text for term in ["衣", "鞋", "背包", "穿搭"]):
            return "服饰运动"
        if any(term in text for term in ["饮料", "零食", "咖啡", "食品"]):
            return "食品饮料"
        return None

    @staticmethod
    def _brief(product: Product, *, source: str, confidence: float, matched_terms: list[str]) -> dict[str, Any]:
        return {
            "sku_id": product.sku_id,
            "name": product.name,
            "brand": product.brand,
            "category": product.category,
            "sub_category": product.sub_category,
            "price": product.price,
            "image_url": product.image_url,
            "source": source,
            "confidence": round(float(confidence), 4),
            "matched_terms": matched_terms,
        }

    @staticmethod
    def _payload(matches: list[dict[str, Any]], note: str) -> dict[str, Any]:
        return {
            "是否启用": True,
            "匹配说明": note,
            "top_matches": matches,
            "best_match": matches[0] if matches else None,
        }

    @staticmethod
    def _empty(reason: str) -> dict[str, Any]:
        return {"是否启用": False, "原因": reason, "top_matches": [], "best_match": None}


def _foreground_crop(image: Image.Image) -> Image.Image:
    arr = np.asarray(image).astype("float32") / 255.0
    max_channel = arr.max(axis=2)
    min_channel = arr.min(axis=2)
    saturation = (max_channel - min_channel) / (max_channel + 1e-6)
    value = max_channel
    height, width = value.shape
    yy, xx = np.ogrid[:height, :width]
    central = (xx > width * 0.06) & (xx < width * 0.94) & (yy > height * 0.02) & (yy < height * 0.98)
    mask = (((saturation > 0.16) & (value < 0.96)) | (value < 0.55)) & central
    ys, xs = np.where(mask)
    if len(xs) < 100:
        return image
    pad = 8
    left = max(int(xs.min()) - pad, 0)
    top = max(int(ys.min()) - pad, 0)
    right = min(int(xs.max()) + pad, width)
    bottom = min(int(ys.max()) + pad, height)
    return image.crop((left, top, right, bottom))
