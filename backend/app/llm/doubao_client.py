import base64
from datetime import datetime
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

import httpx

from app.core.logging import get_logger
from app.llm.base import BaseLLMClient
from app.models.domain import IntentType


logger = get_logger(__name__)


class DoubaoClient(BaseLLMClient):
    def __init__(self, api_key: str | None, base_url: str | None, model: str = "doubao-pro-32k") -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.last_call_debug: dict[str, Any] = {}

    def supports_response_streaming(self) -> bool:
        return bool(self.api_key and self.base_url)

    def generate_response(
        self,
        intent: IntentType,
        message: str,
        context: str,
        product_names: list[str],
    ) -> str:
        start = perf_counter()
        debug = self._new_call_debug(intent=intent, context=context, product_names=product_names)
        self.last_call_debug = debug
        if not self.api_key or not self.base_url:
            missing = []
            if not self.api_key:
                missing.append("api_key")
            if not self.base_url:
                missing.append("base_url")
            debug.update(
                {
                    "fallback_triggered": True,
                    "fallback_reason": f"missing_config:{','.join(missing)}",
                    "duration_ms": _elapsed_ms(start),
                }
            )
            return self._fallback(product_names)

        url = self.base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an ecommerce shopping assistant. Answer in Chinese. "
                        "Use only verified product facts from the user message. "
                        "Do not invent products, prices, brands, stock, specs, discounts, or effects. "
                        "Keep the reply concise and suitable for a mobile shopping UI."
                    ),
                },
                {"role": "user", "content": context},
            ],
        }
        try:
            debug["http_request_sent"] = True
            with httpx.Client(timeout=20) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                debug["http_status_code"] = response.status_code
                response.raise_for_status()
                data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            debug.update(
                {
                    "http_request_succeeded": True,
                    "raw_output_received": bool(content),
                    "raw_output_preview": _truncate(content),
                    "duration_ms": _elapsed_ms(start),
                }
            )
            if not content:
                debug.update(
                    {
                        "fallback_triggered": True,
                        "fallback_reason": "empty_model_output",
                    }
                )
                return self._fallback(product_names)
            return content
        except Exception as exc:
            debug.update(
                {
                    "exception_type": exc.__class__.__name__,
                    "error_message": _safe_error(exc),
                    "fallback_triggered": True,
                    "fallback_reason": "http_or_parse_exception",
                    "duration_ms": _elapsed_ms(start),
                }
            )
            return self._fallback(product_names)

    def stream_generate_response(
        self,
        intent: IntentType,
        message: str,
        context: str,
        product_names: list[str],
    ) -> Iterator[str]:
        start = perf_counter()
        debug = self._new_call_debug(intent=intent, context=context, product_names=product_names)
        debug["stream"] = True
        self.last_call_debug = debug
        if not self.api_key or not self.base_url:
            missing = []
            if not self.api_key:
                missing.append("api_key")
            if not self.base_url:
                missing.append("base_url")
            debug.update(
                {
                    "fallback_triggered": True,
                    "fallback_reason": f"missing_config:{','.join(missing)}",
                    "duration_ms": _elapsed_ms(start),
                }
            )
            return

        url = self.base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "stream": True,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是电商导购助手。只能基于后端提供的 Verified product facts 和 RecommendationPlan 表达。"
                        "不得编造或修改商品、价格、品牌、库存、规格、参数和业务结果。"
                        "如果用户可见文本需要分段，请严格遵守用户消息中的输出协议。"
                    ),
                },
                {"role": "user", "content": context},
            ],
        }
        collected: list[str] = []
        chunk_index = 0
        last_yield_at: float | None = None
        debug_recommendation_stream = "RECOMMENDATION_PRESENTATION_STREAM" in context
        try:
            debug["http_request_sent"] = True
            with httpx.Client(timeout=30) as client:
                with client.stream(
                    "POST",
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                ) as response:
                    debug["http_status_code"] = response.status_code
                    response.raise_for_status()
                    debug["http_request_succeeded"] = True
                    for line in response.iter_lines():
                        if not line:
                            continue
                        line = line.strip()
                        if line.startswith("data:"):
                            line = line.removeprefix("data:").strip()
                        if not line or line == "[DONE]":
                            continue
                        delta = _stream_delta_from_line(line)
                        if not delta:
                            continue
                        collected.append(delta)
                        if debug_recommendation_stream:
                            now = perf_counter()
                            interval_ms = None if last_yield_at is None else round((now - last_yield_at) * 1000, 2)
                            last_yield_at = now
                            chunk_index += 1
                            logger.info(
                                "[llm_stream_delta] path=doubao_stream chunk=%s len=%s interval_ms=%s ts=%s",
                                chunk_index,
                                len(delta),
                                interval_ms,
                                datetime.now().isoformat(timespec="milliseconds"),
                            )
                        yield delta
            content = "".join(collected)
            debug.update(
                {
                    "raw_output_received": bool(content),
                    "raw_output_preview": _truncate(content),
                    "duration_ms": _elapsed_ms(start),
                }
            )
            if not content:
                debug.update({"fallback_triggered": True, "fallback_reason": "empty_model_output"})
        except Exception as exc:
            debug.update(
                {
                    "exception_type": exc.__class__.__name__,
                    "error_message": _safe_error(exc),
                    "fallback_triggered": True,
                    "fallback_reason": "stream_http_or_parse_exception",
                    "duration_ms": _elapsed_ms(start),
                }
            )
            raise
        return

        url = self.base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是电商导购助手。只能基于用户提供的 Verified product facts 回答。"
                        "不得编造商品、价格、品牌、库存、优惠券和功效。"
                        "回答用中文，适合手机端，简洁自然。"
                        "只要有候选商品、备选商品或相近商品，就必须用积极、肯定、主动的导购语气推进选择。"
                        "有商品可说时，禁止以“抱歉”“没有找到”“没有符合”“没有明确信息”等否定表达开头。"
                        "没有完全匹配但有备选时，先说“我先为你挑了几款更接近需求的选择”，再简短说明差异。"
                        "只有完全超出商品库或没有任何可推荐方向时，才说明限制，并立即给出调整预算、放宽条件、换类目或补充需求的引导。"
                        "长度限制：普通推荐2-4句，比较最多5句，澄清只问1-2个关键问题，购物车反馈1-2句。"
                        "如果上下文中有明确历史选择、购物车同类商品或稳定偏好，可以自然说“基于你之前更关注…”或“基于你购物车里的…选择”。"
                        "禁止说“根据你的用户画像/记忆”，也不要暴露memory、RAG、检索、状态机等内部术语。"
                    ),
                },
                {"role": "user", "content": context},
            ],
        }
        try:
            debug["http_request_sent"] = True
            with httpx.Client(timeout=20) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                debug["http_status_code"] = response.status_code
                response.raise_for_status()
                data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            debug.update(
                {
                    "http_request_succeeded": True,
                    "raw_output_received": bool(content),
                    "raw_output_preview": _truncate(content),
                    "duration_ms": _elapsed_ms(start),
                }
            )
            if not content:
                debug.update(
                    {
                        "fallback_triggered": True,
                        "fallback_reason": "empty_model_output",
                    }
                )
                return self._fallback(product_names)
            return content
        except Exception as exc:
            debug.update(
                {
                    "exception_type": exc.__class__.__name__,
                    "error_message": _safe_error(exc),
                    "fallback_triggered": True,
                    "fallback_reason": "http_or_parse_exception",
                    "duration_ms": _elapsed_ms(start),
                }
            )
            return self._fallback(product_names)

    def decide_frontend_action(self, context: dict) -> dict:
        allowed_actions = [
            "stay_chat",
            "ask_clarification",
            "show_product_list",
            "show_product_detail",
            "show_cart",
            "show_checkout_preview",
            "show_scene_bundle",
            "finish_conversation",
        ]
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是电商导购后端的前端动作决策器。"
                        "只能输出 JSON，不要输出解释文本。"
                        "根据上下文从 allowed_actions 中选一个 action。默认保持在 chat 页面。"
                        "只有用户明确要求查看某个商品详情页、查看购物车页，或明确结算/下单/付款时，才允许切换页面。"
                        "商品推荐、场景方案和普通加购/删除购物车，只需要返回展示或更新动作，不要主动跳转页面。"
                        "target_page 只能是 chat/product_list/product_detail/cart/checkout/scenario。"
                        "should_end_conversation 只有在用户明确结束、感谢且无后续任务时才为 true。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "allowed_actions": allowed_actions,
                            "schema": {
                                "action": "one of allowed_actions",
                                "target_page": "chat|product_list|product_detail|cart|checkout|scenario",
                                "should_end_conversation": "boolean",
                                "reason": "short Chinese reason",
                                "confidence": "0-1 number",
                            },
                            "context": context,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        return self._chat_json(
            purpose="frontend_action_decision",
            context=context,
            payload=payload,
            timeout=25,
            retries=2,
        )

    def analyze_user_profile(self, context: dict) -> dict:
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是电商导购系统的用户画像分析器。"
                        "只能基于明确历史记录总结购物偏好，不要推断敏感身份信息。"
                        "必须输出 JSON，不要输出 Markdown 或解释文本。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
        }
        return self._chat_json(
            purpose="user_profile_analysis",
            context=context,
            payload=payload,
            timeout=18,
            retries=1,
        )

    def analyze_image(self, context: dict) -> dict:
        start = perf_counter()
        image_url = _image_url_for_api(context)
        if not image_url:
            debug = self._new_json_call_debug(purpose="image_analysis", context=context)
            debug.update(
                {
                    "llm_call_attempted": False,
                    "fallback_triggered": True,
                    "fallback_reason": "missing_or_too_large_image_input",
                    "duration_ms": _elapsed_ms(start),
                }
            )
            self.last_call_debug = debug
            return {}

        model = context.get("vision_model") or self.model
        payload = {
            "model": model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是电商导购系统的图片商品属性分析器。只能输出 JSON。"
                        "只识别与商品检索相关的信息，不要识别人脸、身份、年龄、性别、种族等敏感属性。"
                        "如果图片不清楚或无法判断，输出较低置信度和不确定点。"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "用户文本": context.get("message"),
                                    "输出格式": {
                                        "主要商品类别": "string or null",
                                        "候选商品类别": ["string"],
                                        "颜色": ["string"],
                                        "款式": ["string"],
                                        "材质或质感": ["string"],
                                        "图案": ["string"],
                                        "使用场景": ["string"],
                                        "相似检索关键词": ["string"],
                                        "置信度": "0-1 number",
                                        "不确定点": ["string"],
                                    },
                                },
                                ensure_ascii=False,
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
        }
        return self._chat_json(
            purpose="image_analysis",
            context=context,
            payload=payload,
            timeout=30,
            retries=1,
        )

    def resolve_user_intent(self, context: dict) -> dict:
        allowed_intents = list(context.get("available_intents") or [
            "recommend", "filter", "refine", "compare", "detail", "scene_bundle", "preference",
            "cart_add", "cart_remove", "cart_update", "cart_clear", "cart_view", "cart_keep_only",
            "checkout", "chitchat", "out_of_scope", "invalid",
        ])
        output_schema = {
            "primary_intent": "one of allowed_intents",
            "intent_plan": {
                "primary_intent": "same as primary_intent",
                "steps": [
                    {
                        "step": 1,
                        "intent": "one of allowed_intents",
                        "action": "same as intent",
                        "source_text": "the exact phrase that triggers this action",
                        "target_ref": "第一款/第二个/刚才那个/etc, or null",
                        "quantity": "integer quantity for cart_add/cart_update, or null",
                        "sku_id": "explicit sku id for this step, or null",
                        "keep_categories": ["categories to keep for cart_keep_only"],
                        "keep_sub_categories": ["sub-categories to keep for cart_keep_only"],
                        "exclude_sku_ids": ["sku ids that this step must not remove/update"],
                        "requires_tool": "boolean",
                        "requires_retrieval": "boolean",
                    }
                ],
                "is_multi_intent": "boolean",
                "confidence": "0-1 number",
                "reason": "short Chinese reason",
            },
            "category": "one available category or null",
            "sub_category": "one sub-category under category or null",
            "price_range": {"min": "number or null", "max": "number or null"},
            "positive_constraints": ["features the user wants"],
            "negative_constraints": ["features/ingredients/styles the user rejects"],
            "brands_include": ["brands explicitly wanted"],
            "brands_exclude": ["brands explicitly rejected"],
            "compare_targets": ["named products or references to compare"],
            "referents": ["第一款/第二个/刚才那个/购物车里的那个/etc"],
            "mentioned_products": ["sku_id or product name if explicitly mentioned"],
            "cart_action": {
                "action": "cart_add/cart_remove/cart_update/cart_clear/cart_view/cart_keep_only/checkout or null",
                "quantity": "integer or null",
                "target_ref": "reference phrase or null",
                "sku_id": "explicit sku id or null",
                "keep_categories": ["categories to keep when cart_keep_only"],
                "keep_sub_categories": ["sub-categories to keep when cart_keep_only"],
            },
            "scenario": "shopping scenario or null",
            "target_user": "explicit user/recipient, not inferred sensitive identity",
            "need_clarification": "boolean",
            "clarification_slots": ["missing slots"],
            "inherit_context": "boolean",
            "rewritten_query": "search query using current need and category",
            "confidence": "0-1 number",
            "uncertain_points": ["only if confidence is limited"],
        }
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是电商导购后端的结构化意图与动作规划器。只能输出一个 JSON 对象，禁止输出 Markdown、解释或多余文本。\n"
                        "你的任务不是写给用户看的回复，而是把用户这一轮话解析成系统可执行的 IntentPlan。\n\n"
                        "核心原则：\n"
                        "1. 只能使用 allowed_intents 中的意图；只能使用 context.available_categories 中存在的类目和子类目。\n"
                        "2. 用户本轮明确表达的需求是硬约束，历史状态只能在用户说“刚才、那款、继续、再便宜点”等上下文表达时辅助解析。\n"
                        "3. 如果用户明确说单一商品类目，例如手机、耳机、背包、防晒、短袖、饮料、零食，必须保持这个类目，不要随意扩展成组合推荐。\n"
                        "4. 只有用户明确说“一套、全套、清单、方案、搭配、组合、配齐、从A到B”等组合表达时，才允许 scene_bundle。\n"
                        "5. 区分历史描述和当前命令：“刚才加购的防晒不要了，清空购物车”表示 cart_clear 或 cart_remove+cart_clear，不是 cart_add。\n"
                        "5a. “第二个不错，介绍下/给我介绍下/第一款呢/这款怎么样/值得买吗”这类表达是 detail，需要保留 target_ref，并让后端从最近推荐事件解析具体商品。\n"
                        "6. 一句话有多个动作时，必须按真实执行顺序写入 intent_plan.steps，例如“把第一款加入购物车，然后结算”是 cart_add -> checkout。\n"
                        "7. 每个 step 必须尽量填自己的 quantity、target_ref、sku_id、keep_categories、keep_sub_categories、exclude_sku_ids，不要只填顶层 cart_action。\n"
                        "8. 购物车/下单必须使用确定性工具意图：cart_add、cart_remove、cart_update、cart_clear、cart_view、cart_keep_only、checkout。\n"
                        "9. 如果用户说“其他的X删掉”，通常表示删除购物车中匹配 X 的商品，但要保留本句刚刚加入或明确排除的商品；如能确定 sku_id 请写入 exclude_sku_ids，否则在 source_text 中保留“其他”让后端根据前一步结果保护。\n"
                        "10. “不喜欢刚才加到购物车的那个饮料了”应理解为 cart_remove，不是 preference；如果同句还有“把第二个加6瓶”，应输出 cart_remove -> cart_add，第二步 quantity=6,target_ref=第二个。\n"
                        "11. 当前库没有的商品类目不要编造；如果类目不确定，设置 need_clarification=true。\n"
                        "12. 不要从偏好推断敏感身份。只有用户明说“我是女生/给爸爸/4岁小朋友”等，才能写入 target_user。\n"
                        "13. 如果用户说价格“别太贵、便宜点、预算友好”但没有数字，把它作为 positive_constraints=性价比，不要虚构价格上限。\n"
                        "14. cart_clear 优先级高于其它购物车动作；cart_keep_only 高于 cart_remove；checkout 应排在加入/删除/保留动作之后。\n\n"
                        "必须输出完整字段。空值用 null 或 []。JSON 必须能被 json.loads 解析。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "allowed_intents": allowed_intents,
                            "schema": output_schema,
                            "examples": [
                                {
                                    "user": "刚才加购的防晒不要了，清空购物车",
                                    "primary_intent": "cart_clear",
                                    "steps": ["cart_clear"],
                                    "notes": "加购是历史描述，不是当前加入购物车命令",
                                },
                                {
                                    "user": "把第一款加入购物车，然后直接下单，用默认地址",
                                    "primary_intent": "checkout",
                                    "steps": ["cart_add", "checkout"],
                                    "referents": ["第一款"],
                                },
                                {
                                    "user": "帮我把你推荐的第一个防晒乳加到购物车，把购物车中其他的防晒乳全部删掉，再给我推荐一个200块左右的背包，也是旅游使用的",
                                    "primary_intent": "refine",
                                    "steps": ["cart_add", "cart_remove", "refine"],
                                    "notes": "先加推荐第一款，再删除购物车中其他防晒乳，最后按200元左右旅游背包重新检索",
                                },
                                {
                                    "user": "我不喜欢刚才加到购物车的那个饮料了，你帮我把现在推荐的第二个往购物车加6瓶吧",
                                    "primary_intent": "cart_add",
                                    "steps": ["cart_remove", "cart_add"],
                                    "notes": "不喜欢刚才加到购物车的饮料=删除该饮料；第二个加6瓶=cart_add quantity=6 target_ref=第二个",
                                },
                                {
                                    "user": "重新挑选一款适合通勤和旅行的背包",
                                    "primary_intent": "refine",
                                    "category": "服饰运动",
                                    "sub_category": "背包",
                                    "steps": ["refine"],
                                    "notes": "单品类背包，不是 scene_bundle",
                                },
                                {
                                    "user": "情侣一周短途海边度假，穿搭、护肤、随身好物全套搭配",
                                    "primary_intent": "scene_bundle",
                                    "steps": ["scene_bundle"],
                                    "notes": "明确全套搭配，允许跨类目",
                                },
                            ],
                            "context": context,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        return self._chat_json(
            purpose="intent_plan_resolution",
            context=context,
            payload=payload,
            timeout=25,
            retries=2,
        )

    @staticmethod
    def _fallback(product_names: list[str]) -> str:
        if not product_names:
            return "这个需求我需要再缩小一点范围。你可以补充预算、品牌或使用场景，我马上继续帮你挑。"
        names = "、".join(product_names[:3])
        return f"我先为你挑了这几款：{names}。可以根据价格、规格和适用场景再做取舍。"

    def _new_call_debug(self, *, intent: IntentType, context: str, product_names: list[str]) -> dict[str, Any]:
        return {
            "llm_provider": "doubao",
            "llm_is_mock": False,
            "llm_call_attempted": True,
            "http_request_sent": False,
            "http_request_succeeded": False,
            "http_status_code": None,
            "raw_output_received": False,
            "fallback_triggered": False,
            "fallback_reason": None,
            "intent": intent.value,
            "model": self.model,
            "base_url_configured": bool(self.base_url),
            "api_key_configured": bool(self.api_key),
            "context_length": len(context),
            "product_name_count": len(product_names),
        }

    def _chat_json(
        self,
        *,
        purpose: str,
        context: dict[str, Any],
        payload: dict[str, Any],
        timeout: float,
        retries: int,
    ) -> dict:
        start = perf_counter()
        debug = self._new_json_call_debug(purpose=purpose, context=context)
        self.last_call_debug = debug
        if not self.api_key or not self.base_url:
            missing = []
            if not self.api_key:
                missing.append("api_key")
            if not self.base_url:
                missing.append("base_url")
            debug.update(
                {
                    "fallback_triggered": True,
                    "fallback_reason": f"missing_config:{','.join(missing)}",
                    "duration_ms": _elapsed_ms(start),
                }
            )
            return {}

        url = self.base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        errors: list[dict[str, Any]] = []
        for attempt in range(1, max(1, retries) + 1):
            debug["attempt_count"] = attempt
            try:
                debug["http_request_sent"] = True
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    debug["http_status_code"] = response.status_code
                    response.raise_for_status()
                    data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                debug.update(
                    {
                        "http_request_succeeded": True,
                        "raw_output_received": bool(content),
                        "raw_output_preview": _truncate(content),
                    }
                )
                result, parse_debug = _extract_json_with_debug(content)
                debug["json_parse_succeeded"] = bool(result)
                if result:
                    debug.update(
                        {
                            "fallback_triggered": False,
                            "fallback_reason": None,
                            "duration_ms": _elapsed_ms(start),
                        }
                    )
                    return result
                errors.append({"attempt": attempt, **parse_debug})
            except Exception as exc:
                errors.append(
                    {
                        "attempt": attempt,
                        "error_type": exc.__class__.__name__,
                        "error_message": _safe_error(exc),
                    }
                )

        debug.update(
            {
                "fallback_triggered": True,
                "fallback_reason": _json_fallback_reason(errors),
                "json_parse_errors": errors[-3:],
                "duration_ms": _elapsed_ms(start),
            }
        )
        return {}

    def _new_json_call_debug(self, *, purpose: str, context: dict[str, Any]) -> dict[str, Any]:
        context_keys = list(context.keys())[:20] if isinstance(context, dict) else []
        try:
            context_length = len(json.dumps(context, ensure_ascii=False, default=str))
        except Exception:
            context_length = len(str(context))
        return {
            "llm_provider": "doubao",
            "llm_is_mock": False,
            "llm_call_attempted": True,
            "http_request_sent": False,
            "http_request_succeeded": False,
            "http_status_code": None,
            "raw_output_received": False,
            "raw_output_preview": None,
            "json_parse_succeeded": False,
            "fallback_triggered": False,
            "fallback_reason": None,
            "purpose": purpose,
            "model": self.model,
            "base_url_configured": bool(self.base_url),
            "api_key_configured": bool(self.api_key),
            "context_keys": context_keys,
            "context_length": context_length,
        }


def _extract_json(content: str) -> dict:
    return _extract_json_with_debug(content)[0]


def _stream_delta_from_line(line: str) -> str:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return ""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0] if isinstance(choices[0], dict) else {}
    delta = choice.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str):
            return content
    message = choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    text = choice.get("text")
    return text if isinstance(text, str) else ""


def _extract_json_with_debug(content: str) -> tuple[dict, dict[str, Any]]:
    debug: dict[str, Any] = {
        "error_type": None,
        "error_message": None,
        "error_position": None,
        "cleaned_text": None,
    }
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            cleaned = content[start:end + 1]
            debug["cleaned_text"] = _truncate(cleaned)
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as inner_exc:
                debug.update(
                    {
                        "error_type": "json_decode_error",
                        "error_message": inner_exc.msg,
                        "error_position": inner_exc.pos,
                    }
                )
                return {}, debug
        else:
            debug.update(
                {
                    "error_type": "json_decode_error",
                    "error_message": exc.msg,
                    "error_position": exc.pos,
                }
            )
            return {}, debug
    except Exception as exc:
        debug.update({"error_type": exc.__class__.__name__, "error_message": _safe_error(exc)})
        return {}, debug
    if not isinstance(data, dict):
        debug["error_type"] = "json_root_not_object"
        return {}, debug
    return data, debug


def _json_fallback_reason(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "empty_model_output"
    last = errors[-1]
    error_type = str(last.get("error_type") or "")
    if error_type.startswith("HTTP"):
        return "http_error"
    if error_type in {"json_decode_error", "json_root_not_object"}:
        return "json_parse_failed"
    return "http_or_parse_exception"


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 2)


def _truncate(text: str, limit: int = 2000) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _safe_error(exc: Exception, limit: int = 300) -> str:
    return _truncate(str(exc), limit)


def _image_url_for_api(context: dict) -> str | None:
    image_url = context.get("image_url")
    if isinstance(image_url, str) and image_url.startswith(("http://", "https://", "data:image/")):
        return image_url
    local_path = context.get("image_path")
    if not local_path:
        return None
    path = Path(str(local_path))
    if not path.exists() or path.stat().st_size > 5 * 1024 * 1024:
        return None
    suffix = path.suffix.lower()
    mime = "image/jpeg"
    if suffix == ".png":
        mime = "image/png"
    elif suffix == ".webp":
        mime = "image/webp"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"
