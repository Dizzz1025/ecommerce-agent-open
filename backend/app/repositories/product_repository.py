import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit

from app.models.domain import Product, ProductSpotlight
from app.utils.json_loader import load_json_file


class ProductRepository:
    """Loads either the old normalized products.json or the competition dataset.

    Public APIs keep using `sku_id` for Android compatibility. For the real
    dataset, `sku_id` is the original `product_id`.
    """

    def __init__(self, source_path: Path, dataset_dir: Path | None = None) -> None:
        self.source_path = source_path
        self.dataset_dir = dataset_dir
        self._cache: list[Product] | None = None
        self._by_id: dict[str, Product] = {}
        self._display_titles: dict[str, str] | None = None

    def list_products(self) -> list[Product]:
        if self._cache is None:
            self._cache = self._load_products()
            self._by_id = {item.sku_id: item for item in self._cache}
            for item in self._cache:
                if item.product_id:
                    self._by_id[item.product_id] = item
        return self._cache

    def get_product(self, sku_id: str) -> Product | None:
        self.list_products()
        return self._by_id.get(sku_id)

    def list_brands(self) -> list[str]:
        return sorted({item.brand for item in self.list_products() if item.brand})

    def list_categories(self) -> list[str]:
        values = set()
        for item in self.list_products():
            values.add(item.category)
            if item.sub_category:
                values.add(item.sub_category)
        return sorted(values)

    def find_by_text_reference(self, text: str) -> Product | None:
        normalized = _normalize_text(text)
        if not normalized:
            return None
        exact = self.get_product(text)
        if exact:
            return exact
        products = self.list_products()
        for product in products:
            if _normalize_text(product.name) == normalized:
                return product
        for product in products:
            haystack = _normalize_text(" ".join([product.name, product.brand, product.category, product.sub_category or ""]))
            if normalized in haystack or haystack in normalized:
                return product
        return None

    def _load_products(self) -> list[Product]:
        if self.dataset_dir and self.dataset_dir.exists():
            return self._load_competition_dataset(self.dataset_dir)

        if self.source_path.exists() and self.source_path.is_file():
            payload = load_json_file(self.source_path)
            return [Product.model_validate(self._normalize_legacy_item(item)) for item in payload]

        raise FileNotFoundError(
            "No product data found. Set PRODUCT_DATA_PATH or PRODUCT_DATASET_DIR in .env."
        )

    def _load_competition_dataset(self, dataset_dir: Path) -> list[Product]:
        products: list[Product] = []
        for path in sorted(dataset_dir.glob("*/data/*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            products.append(Product.model_validate(self._normalize_dataset_item(raw)))
        return products

    def _normalize_legacy_item(self, raw: dict[str, Any]) -> dict[str, Any]:
        sku_id = str(raw.get("sku_id") or raw.get("product_id"))
        name = raw.get("name") or raw.get("title") or sku_id
        price = float(raw.get("price") or raw.get("base_price") or 0)
        image_url = raw.get("image_url") or raw.get("image_path") or ""
        detail_image_url = raw.get("detail_image_url") or raw.get("detailImageUrl")
        spotlight = raw.get("spotlight") or {}
        searchable_text = self._build_searchable_text(
            title=name,
            brand=raw.get("brand", ""),
            category=raw.get("category", ""),
            sub_category=raw.get("sub_category", ""),
            rag_knowledge=raw.get("rag_knowledge", {}),
            skus=raw.get("skus", []),
            spotlight=spotlight,
            enhancement=_enhancement_payload(raw),
        )
        display_tag_text = self._build_display_tag_text(
            title=name,
            brand=raw.get("brand", ""),
            category=raw.get("category", ""),
            sub_category=raw.get("sub_category", ""),
            skus=raw.get("skus", []),
            spotlight=spotlight,
            enhancement=_enhancement_payload(raw),
        )
        return {
            "sku_id": sku_id,
            "product_id": raw.get("product_id") or sku_id,
            "name": name,
            "title": raw.get("title") or name,
            "display_title": self._display_title(raw.get("product_id") or sku_id),
            "category": raw.get("category", ""),
            "sub_category": raw.get("sub_category"),
            "brand": raw.get("brand", ""),
            "price": price,
            "base_price": raw.get("base_price") or price,
            "stock": int(raw.get("stock") or 999),
            "image_url": image_url,
            "detail_image_url": detail_image_url,
            "image_path": raw.get("image_path"),
            "skus": raw.get("skus", []),
            "spotlight": spotlight,
            "reviews_summary": raw.get("reviews_summary") or self._summarize_reviews(raw.get("rag_knowledge", {})),
            "rag_knowledge": raw.get("rag_knowledge", {}),
            **_enhancement_payload(raw),
            "searchable_text": searchable_text,
            "tags": self._extract_tags(display_tag_text),
        }

    def _normalize_dataset_item(self, raw: dict[str, Any]) -> dict[str, Any]:
        product_id = str(raw["product_id"])
        title = raw["title"]
        skus = raw.get("skus", [])
        sku_prices = [float(item.get("price", raw.get("base_price", 0))) for item in skus]
        min_price = min(sku_prices) if sku_prices else float(raw.get("base_price", 0))
        image_path = self._resolve_dataset_image_path(raw.get("image_path", ""))
        image_url = f"/static/dataset/{quote(image_path, safe='/')}" if image_path else ""
        detail_image_path = self._resolve_dataset_detail_image_path(image_path)
        detail_image_url = f"/static/dataset/{quote(detail_image_path, safe='/')}" if detail_image_path else None
        rag_knowledge = raw.get("rag_knowledge", {})
        searchable_text = self._build_searchable_text(
            title=title,
            brand=raw.get("brand", ""),
            category=raw.get("category", ""),
            sub_category=raw.get("sub_category", ""),
            rag_knowledge=rag_knowledge,
            skus=skus,
            spotlight={},
            enhancement=_enhancement_payload(raw),
        )
        display_tag_text = self._build_display_tag_text(
            title=title,
            brand=raw.get("brand", ""),
            category=raw.get("category", ""),
            sub_category=raw.get("sub_category", ""),
            skus=skus,
            spotlight={},
            enhancement=_enhancement_payload(raw),
        )
        tags = self._extract_tags(display_tag_text)
        spotlight = ProductSpotlight(
            skin_type=[term for term in ["油皮", "混油皮", "干皮", "敏感肌"] if term in searchable_text],
            features=tags[:8],
            exclude=[],
            description=self._shorten(rag_knowledge.get("marketing_description", ""), max_len=90),
        )
        return {
            "sku_id": product_id,
            "product_id": product_id,
            "name": title,
            "title": title,
            "display_title": self._display_title(product_id),
            "category": raw.get("category", ""),
            "sub_category": raw.get("sub_category"),
            "brand": raw.get("brand", ""),
            "price": min_price,
            "base_price": raw.get("base_price") or min_price,
            "stock": 999,
            "image_url": image_url,
            "detail_image_url": detail_image_url,
            "image_path": image_path,
            "skus": skus,
            "spotlight": spotlight.model_dump(),
            "reviews_summary": self._summarize_reviews(rag_knowledge),
            "rag_knowledge": rag_knowledge,
            **_enhancement_payload(raw),
            "searchable_text": searchable_text,
            "tags": tags,
        }

    def _build_searchable_text(
        self,
        *,
        title: str,
        brand: str,
        category: str,
        sub_category: str | None,
        rag_knowledge: dict[str, Any],
        skus: list[dict[str, Any]],
        spotlight: dict[str, Any],
        enhancement: dict[str, Any] | None = None,
    ) -> str:
        parts: list[str] = [title, brand, category, sub_category or ""]
        for sku in skus:
            parts.extend(str(value) for value in sku.get("properties", {}).values())
        parts.extend(str(value) for value in spotlight.values() if not isinstance(value, list))
        for value in spotlight.values():
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
        enhancement = enhancement or {}
        parts.extend(
            str(enhancement.get(key, ""))
            for key in ["product_highlight", "highlight_short", "highlight_detail"]
        )
        for key in ["suitable_scenarios", "target_user_tags", "non_standard_query_tags"]:
            parts.extend(str(item) for item in enhancement.get(key, []) if item)
        parts.append(str(rag_knowledge.get("marketing_description", "")))
        for faq in rag_knowledge.get("official_faq", []):
            parts.extend([str(faq.get("question", "")), str(faq.get("answer", ""))])
        for review in rag_knowledge.get("user_reviews", []):
            parts.append(str(review.get("content", "")))
        return " ".join(part for part in parts if part).strip()

    @staticmethod
    def _build_display_tag_text(
        *,
        title: str,
        brand: str,
        category: str,
        sub_category: str | None,
        skus: list[dict[str, Any]],
        spotlight: dict[str, Any],
        enhancement: dict[str, Any] | None = None,
    ) -> str:
        """Return curated product facts used only for display tag extraction.

        Full searchable text intentionally includes FAQ/reviews/marketing copy.
        Display tags are shown on product cards, so they must not be inferred
        from support phrases like "联系客服拍照反馈" or unrelated long-form text.
        """
        parts: list[str] = [title, brand, category, sub_category or ""]
        for sku in skus:
            parts.extend(str(value) for value in sku.get("properties", {}).values())
        for key in ["features", "skin_type", "exclude"]:
            value = spotlight.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value if item)
        enhancement = enhancement or {}
        parts.extend(
            str(enhancement.get(key, ""))
            for key in ["product_highlight", "highlight_short", "highlight_detail"]
        )
        for key in ["suitable_scenarios", "target_user_tags", "non_standard_query_tags"]:
            parts.extend(str(item) for item in enhancement.get(key, []) if item)
        return " ".join(part for part in parts if part).strip()

    @staticmethod
    def _summarize_reviews(rag_knowledge: dict[str, Any]) -> str:
        reviews = rag_knowledge.get("user_reviews", [])
        if not reviews:
            return ""
        ratings = [float(item.get("rating", 0)) for item in reviews if item.get("rating") is not None]
        avg = sum(ratings) / len(ratings) if ratings else 0
        positive = next((item.get("content", "") for item in reviews if float(item.get("rating", 0)) >= 4), "")
        negative = next((item.get("content", "") for item in reviews if float(item.get("rating", 0)) <= 2), "")
        parts = [f"用户评分约{avg:.1f}/5"]
        if positive:
            parts.append(f"好评提到：{ProductRepository._shorten(positive, 45)}")
        if negative:
            parts.append(f"差评提醒：{ProductRepository._shorten(negative, 45)}")
        return "；".join(parts)

    @staticmethod
    def _extract_tags(text: str) -> list[str]:
        candidates = [
            "控油", "保湿", "温和", "敏感肌", "油皮", "干皮", "抗初老", "淡纹",
            "防晒", "修护", "轻量", "缓震", "透气", "通勤", "运动", "跑步",
            "续航", "拍照", "快充", "降噪", "便携", "办公", "游戏", "高性能",
            "无糖", "低脂", "提神", "速溶", "礼盒", "百搭", "凉感", "速干",
            "低糖", "无油", "非油炸", "不甜", "小包装", "儿童", "亲子", "分享",
            "咸味", "发圈", "批量", "细头", "不防水", "文具", "收纳", "桌面",
            "苹果生态", "数码生态", "平板", "学习", "影音", "创作", "高端",
            "成分", "维稳", "提亮", "屏障", "角质", "急救", "低卡", "入门",
        ]
        return [term for term in candidates if term in text]

    @staticmethod
    def _shorten(text: str, max_len: int) -> str:
        compact = re.sub(r"\s+", "", text)
        if len(compact) <= max_len:
            return compact
        return compact[:max_len] + "..."

    def _resolve_dataset_image_path(self, image_path: str) -> str:
        """Return the actual relative path served by StaticFiles.

        Some Windows-extracted dataset folders are mojibake while JSON keeps
        the intended Chinese folder name. Match by image filename so API image
        URLs always point to files that really exist under product_dataset_dir.
        """
        if not image_path or not self.dataset_dir:
            return image_path

        normalized = _safe_relative_image_reference(image_path) or ""
        is_detail_reference = _is_detail_image_reference(normalized)
        direct_path = self.dataset_dir / normalized
        if (
            normalized
            and not is_detail_reference
            and _is_within_directory(direct_path, self.dataset_dir)
            and direct_path.is_file()
        ):
            return normalized

        filename = _safe_image_filename(image_path)
        if not filename:
            return normalized

        for image_dir in self.dataset_dir.glob("*/images"):
            candidate = image_dir / filename
            if candidate.is_file() and not candidate.name.startswith("._"):
                return candidate.relative_to(self.dataset_dir).as_posix()

        for candidate in self.dataset_dir.rglob("*"):
            if (
                candidate.is_file()
                and candidate.name == filename
                and candidate.parent.name != "images_android"
                and not candidate.name.startswith("._")
            ):
                return candidate.relative_to(self.dataset_dir).as_posix()

        return "" if is_detail_reference else normalized

    def _resolve_dataset_detail_image_path(self, original_image_path: str) -> str | None:
        if not original_image_path or not self.dataset_dir:
            return None

        filename = _safe_image_filename(original_image_path)
        if not filename:
            return None

        detail_filenames = _detail_image_filename_candidates(filename)
        normalized = _safe_relative_image_reference(original_image_path) or ""
        if normalized:
            parts = normalized.split("/")
            for index in range(len(parts) - 2, -1, -1):
                if parts[index] == "images":
                    for detail_filename in detail_filenames:
                        detail_parts = [*parts[:index], "images_android", detail_filename]
                        detail_relative = "/".join(detail_parts)
                        detail_path = self.dataset_dir / detail_relative
                        if _is_within_directory(detail_path, self.dataset_dir) and detail_path.is_file():
                            return detail_relative
                    break

        for detail_dir in self.dataset_dir.glob("*/images_android"):
            for detail_filename in detail_filenames:
                candidate = detail_dir / detail_filename
                if candidate.is_file() and not candidate.name.startswith("._"):
                    return candidate.relative_to(self.dataset_dir).as_posix()

        return None

    def _display_title(self, product_id: str | None) -> str | None:
        if not product_id:
            return None
        if self._display_titles is None:
            self._display_titles = self._load_display_titles()
        return self._display_titles.get(str(product_id))

    def _load_display_titles(self) -> dict[str, str]:
        path = self._resolve_display_title_report_path()
        if path is None or not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        items = payload.get("items") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return {}
        titles: dict[str, str] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            product_id = str(item.get("product_id") or "").strip()
            display_title = str(item.get("display_title") or "").strip()
            if product_id and display_title:
                titles[product_id] = display_title
        return titles

    def _resolve_display_title_report_path(self) -> Path | None:
        env_path = os.getenv("PRODUCT_SLOGAN_REPORT_PATH")
        candidates: list[Path] = []
        if env_path:
            path = Path(env_path)
            candidates.append(path if path.is_absolute() else self.source_path.parent / path)
        if self.dataset_dir:
            candidates.append(self.dataset_dir / "slogan_generation_report.json")
        base_dirs = []
        if self.dataset_dir:
            base_dirs.extend([self.dataset_dir.parent, self.dataset_dir.parent.parent])
        base_dirs.extend([self.source_path.parent, self.source_path.parent.parent])
        for base in base_dirs:
            candidates.append(base / "ecommerce_dataset_with_slogans" / "slogan_generation_report.json")
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None



def _safe_image_filename(image_reference: str | None) -> str | None:
    if not image_reference:
        return None
    raw_path = urlsplit(str(image_reference).strip()).path
    normalized = unquote(raw_path).replace("\\", "/")
    filename = Path(normalized).name
    if not filename or filename in {".", ".."} or filename.startswith("._"):
        return None
    if "/" in filename or "\\" in filename:
        return None
    return filename


def _safe_relative_image_reference(image_reference: str | None) -> str | None:
    if not image_reference:
        return None
    raw_path = urlsplit(str(image_reference).strip()).path
    normalized = unquote(raw_path).replace("\\", "/").lstrip("/")
    dataset_prefix = "static/dataset/"
    if normalized.startswith(dataset_prefix):
        normalized = normalized[len(dataset_prefix):]
    parts = [part for part in normalized.split("/") if part and part != "."]
    if not parts or any(part == ".." for part in parts):
        return None
    return "/".join(parts)


def _is_within_directory(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def _is_detail_image_reference(relative_path: str) -> bool:
    return any(part == "images_android" for part in relative_path.replace("\\", "/").split("/"))


def _detail_image_filename_candidates(filename: str) -> list[str]:
    path = Path(filename)
    stem = path.stem
    suffix = path.suffix.lower()
    candidates = [filename]
    for extension in [".jpg", ".jpeg", ".png", ".webp"]:
        if extension != suffix:
            candidates.append(f"{stem}{extension}")
    return list(dict.fromkeys(candidates))


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


_QUESTION_PATTERN = re.compile(
    r"[?？]|吗|能不能|适不适合|为什么|怎么办|怎么|用什么|哪个|"
    r"有没有|会不会|可以不|行不行|值不值得|需不需要|能不能够|"
    r"如何|怎样|哪里|哪些|什么|谁|哪款|怎么样|好不好|多少|几时"
)


def _clean_display_tags(tags: list[str]) -> list[str]:
    """Remove question-like strings and long sentences from display tags."""
    cleaned: list[str] = []
    for tag in tags:
        tag_str = str(tag).strip()
        if not tag_str:
            continue
        if len(tag_str) > 12:
            continue
        if _QUESTION_PATTERN.search(tag_str):
            continue
        if re.search(r"[。，！…、；：]", tag_str):
            continue
        if tag_str not in cleaned:
            cleaned.append(tag_str)
    return cleaned


def _enhancement_payload(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_highlight": str(raw.get("product_highlight") or ""),
        "highlight_short": str(raw.get("highlight_short") or ""),
        "highlight_detail": str(raw.get("highlight_detail") or ""),
        "suitable_scenarios": _clean_display_tags(
            [str(item) for item in raw.get("suitable_scenarios", []) if item]
        ),
        "target_user_tags": _clean_display_tags(
            [str(item) for item in raw.get("target_user_tags", []) if item]
        ),
        "non_standard_query_tags": _clean_display_tags(
            [str(item) for item in raw.get("non_standard_query_tags", []) if item]
        ),
    }
