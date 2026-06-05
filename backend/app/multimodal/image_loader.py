from __future__ import annotations

import base64
from pathlib import Path
from typing import Any


class ImageLoader:
    """Load image metadata from URL, local path, or base64 without heavy dependencies."""

    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def load(self, metadata: dict[str, Any]) -> dict[str, Any]:
        image_url = metadata.get("image_url")
        image_path = metadata.get("image_path")
        image_base64 = metadata.get("image_base64")
        if isinstance(image_url, str) and image_url.strip():
            return {
                "ok": True,
                "source_type": "url",
                "image_url": image_url.strip(),
                "image_path": None,
                "message": "已接收图片URL。",
            }
        if isinstance(image_path, str) and image_path.strip():
            path = Path(image_path).expanduser()
            if not path.exists():
                return {"ok": False, "error_code": "IMAGE_NOT_FOUND", "message": f"图片文件不存在：{path}"}
            return {
                "ok": True,
                "source_type": "path",
                "image_url": None,
                "image_path": str(path),
                "message": "已接收本地图片。",
            }
        if isinstance(image_base64, str) and image_base64.strip():
            try:
                raw = image_base64.split(",", 1)[-1]
                data = base64.b64decode(raw, validate=False)
            except Exception:
                return {"ok": False, "error_code": "IMAGE_BASE64_INVALID", "message": "图片base64无法解析。"}
            suffix = ".jpg"
            if image_base64.startswith("data:image/png"):
                suffix = ".png"
            path = self.upload_dir / f"upload_{abs(hash(image_base64))}{suffix}"
            path.write_bytes(data)
            return {
                "ok": True,
                "source_type": "base64",
                "image_url": None,
                "image_path": str(path),
                "message": "已接收base64图片。",
            }
        return {"ok": False, "error_code": "IMAGE_MISSING", "message": "没有收到 image_url、image_path 或 image_base64。"}

