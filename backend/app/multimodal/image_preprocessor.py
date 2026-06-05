from __future__ import annotations

from pathlib import Path
from typing import Any


class ImagePreprocessor:
    """Validate basic image properties for a stable demo pipeline."""

    allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    def preprocess(self, image_input: dict[str, Any]) -> dict[str, Any]:
        if not image_input.get("ok"):
            return image_input
        if image_input.get("source_type") == "url":
            return {
                **image_input,
                "preprocessed": True,
                "format": "remote",
                "size_bytes": None,
                "message": "远程图片将在视觉分析阶段直接使用。",
            }
        image_path = image_input.get("image_path")
        if not image_path:
            return {"ok": False, "error_code": "IMAGE_PATH_MISSING", "message": "缺少本地图片路径。"}
        path = Path(str(image_path))
        suffix = path.suffix.lower()
        if suffix not in self.allowed_suffixes:
            return {"ok": False, "error_code": "IMAGE_FORMAT_UNSUPPORTED", "message": f"暂不支持的图片格式：{suffix}"}
        size = path.stat().st_size
        if size <= 0:
            return {"ok": False, "error_code": "IMAGE_EMPTY", "message": "图片文件为空。"}
        if size > 8 * 1024 * 1024:
            return {"ok": False, "error_code": "IMAGE_TOO_LARGE", "message": "图片超过8MB，请压缩后再上传。"}
        return {
            **image_input,
            "preprocessed": True,
            "format": suffix.lstrip("."),
            "size_bytes": size,
            "message": "图片基础校验通过。",
        }

