from __future__ import annotations

import json
from typing import Any


class MultimodalPromptBuilder:
    """Build a compact text block describing image understanding for LLM prompts."""

    def build_block(self, multimodal_context: dict[str, Any]) -> str:
        if not multimodal_context.get("是否启用多模态"):
            return ""
        return (
            "图片输入分析结果如下。只把它作为商品检索和解释依据，不要识别人物身份或敏感属性：\n"
            f"{json.dumps(multimodal_context, ensure_ascii=False, indent=2)}"
        )

