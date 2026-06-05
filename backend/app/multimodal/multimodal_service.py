from __future__ import annotations

from typing import Any

from app.multimodal.image_loader import ImageLoader
from app.multimodal.image_preprocessor import ImagePreprocessor
from app.multimodal.vision_analyzer import VisionAnalyzer
from app.multimodal.visual_query_builder import VisualQueryBuilder
from app.multimodal.visual_product_matcher import VisualProductMatcher
from app.multimodal.visual_retriever import VisualRetriever
from app.models.agent import CandidateProduct


class MultimodalService:
    """End-to-end image + text query processor."""

    def __init__(
        self,
        *,
        enabled: bool,
        image_loader: ImageLoader,
        image_preprocessor: ImagePreprocessor,
        vision_analyzer: VisionAnalyzer,
        visual_query_builder: VisualQueryBuilder,
        visual_product_matcher: VisualProductMatcher,
        visual_retriever: VisualRetriever,
    ) -> None:
        self.enabled = enabled
        self.image_loader = image_loader
        self.image_preprocessor = image_preprocessor
        self.vision_analyzer = vision_analyzer
        self.visual_query_builder = visual_query_builder
        self.visual_product_matcher = visual_product_matcher
        self.visual_retriever = visual_retriever

    def process(self, *, input_type: str, message: str, metadata: dict[str, Any]) -> dict[str, Any]:
        wants_image = input_type in {"image", "image_text", "multimodal"} or any(
            key in metadata for key in ["image_url", "image_path", "image_base64"]
        )
        if not wants_image:
            return {"是否启用多模态": False}
        if not self.enabled:
            return {
                "是否启用多模态": False,
                "错误": {"code": "MULTIMODAL_DISABLED", "message": "多模态能力未启用。"},
            }
        loaded = self.image_loader.load(metadata)
        preprocessed = self.image_preprocessor.preprocess(loaded)
        visual = self.vision_analyzer.analyze(image_input=preprocessed, message=message)
        fused = self.visual_query_builder.build(message=message, visual_result=visual)
        product_match = self.visual_product_matcher.match(
            image_input=preprocessed,
            visual_result=visual,
            message=message,
        )
        self._apply_product_match_to_fusion(fused=fused, visual=visual, product_match=product_match)
        return {
            "中文说明": "多模态输入处理结果，包含图片加载、视觉理解和图文融合查询。",
            "是否启用多模态": True,
            "图片输入": preprocessed,
            "图片理解结果": visual,
            "图文融合查询": fused,
            "视觉匹配商品": product_match,
            "库存匹配判断": {
                "库存是否覆盖目标类目": fused.get("库存是否覆盖目标类目"),
                "映射商品类别": fused.get("映射商品类别"),
                "映射商品子类": fused.get("映射商品子类"),
                "说明": fused.get("库存匹配说明"),
            },
        }

    def boost_candidates(self, candidates: list[CandidateProduct], multimodal_context: dict[str, Any]) -> list[CandidateProduct]:
        if not multimodal_context.get("是否启用多模态"):
            return candidates
        terms = (multimodal_context.get("图文融合查询", {}) or {}).get("视觉关键词", [])
        product_match = multimodal_context.get("视觉匹配商品", {}) or {}
        candidates = self._inject_best_visual_match(candidates, product_match)
        return self.visual_retriever.boost_visual_matches(candidates, terms, product_match=product_match)

    def _inject_best_visual_match(
        self,
        candidates: list[CandidateProduct],
        product_match: dict[str, Any],
    ) -> list[CandidateProduct]:
        best = product_match.get("best_match") if product_match.get("是否启用") else None
        sku_id = best.get("sku_id") if isinstance(best, dict) else None
        if not sku_id or any(item.sku_id == sku_id for item in candidates):
            return candidates
        product = self.visual_product_matcher.product_repository.get_product(sku_id)
        if not product:
            return candidates
        visual_candidate = CandidateProduct(
            candidate_id=f"visual_match_{product.sku_id}",
            product_id=product.product_id or product.sku_id,
            sku_id=product.sku_id,
            name=product.name,
            brand=product.brand,
            category=product.category,
            sub_category=product.sub_category,
            price=product.price,
            image_url=product.image_url,
            matched_reasons=["图片最相近库存商品", *best.get("matched_terms", [])[:3]],
            score=min(0.92, 0.72 + float(best.get("confidence") or 0) * 0.2),
            raw_scores={"visual_product_match": float(best.get("confidence") or 0)},
        )
        return [visual_candidate, *candidates]

    @staticmethod
    def _apply_product_match_to_fusion(*, fused: dict[str, Any], visual: dict[str, Any], product_match: dict[str, Any]) -> None:
        best = product_match.get("best_match") if product_match.get("是否启用") else None
        if not best:
            return
        category = best.get("category")
        sub_category = best.get("sub_category")
        fused["映射商品类别"] = category
        fused["映射商品子类"] = sub_category
        fused["库存是否覆盖目标类目"] = True
        fused["库存匹配说明"] = f"图片最相近库存商品：{best.get('name')}"
        keywords = [
            best.get("brand"),
            best.get("sub_category"),
            best.get("name"),
            *best.get("matched_terms", []),
        ]
        visual_keywords = fused.setdefault("视觉关键词", [])
        for item in keywords:
            text = str(item or "").strip()
            if text and text not in visual_keywords:
                visual_keywords.append(text)
        visual["视觉匹配sku_id"] = best.get("sku_id")
        visual["视觉匹配商品名"] = best.get("name")
        fused["视觉匹配sku_id"] = best.get("sku_id")
        fused["融合后的检索文本"] = " ".join(
            str(item or "").strip()
            for item in [
                fused.get("融合后的检索文本"),
                best.get("brand"),
                best.get("sub_category"),
                best.get("name"),
                *best.get("matched_terms", []),
            ]
            if str(item or "").strip()
        )
