import json

from app.models.domain import Product
from app.models.domain import SessionState


class PromptBuilder:
    def build(
        self,
        message: str,
        product_facts: str,
        products: list[Product],
        state: SessionState | None = None,
        personalization_context: dict | None = None,
        multimodal_context: dict | None = None,
    ) -> str:
        product_names = ", ".join(product.name for product in products)
        memory_line = ""
        if state is not None:
            memory_line = (
                "Previous session state for reference only; do not treat it as this turn's hard constraint unless the user clearly continues the previous topic:\n"
                f"previous_category: {state.dialogue_state_tracking.current_category}; "
                f"previous_active_constraints: {state.dialogue_state_tracking.active_constraints}\n"
            )
            if state.user_profile_summary_text:
                memory_line += (
                    "User long-term shopping profile summary, as soft preference only. "
                    "Current explicit request has higher priority:\n"
                    f"{state.user_profile_summary_text}\n"
                    f"Structured profile: {state.user_profile_structured}\n"
                )
        personalization_block = ""
        has_cart_personalization = bool(
            personalization_context and personalization_context.get("购物车商品侧个性化")
        )
        has_domain_style = bool(personalization_context and personalization_context.get("领域导购风格"))
        has_collaborative = bool(
            personalization_context
            and (personalization_context.get("相似历史用户协同过滤") or {}).get("是否启用")
        )
        if personalization_context and (
            personalization_context.get("是否启用个性化")
            or has_cart_personalization
            or has_domain_style
            or has_collaborative
        ):
            personalization_block = (
                "\nPersonalized response context, soft preference only. Do not expose this section to the user:\n"
                f"{json.dumps(_compact_personalization(personalization_context), ensure_ascii=False, indent=2)}\n"
                "Domain style: reflect the category-specific shopping assistant style, but keep facts grounded.\n"
                "Collaborative filtering: if similar historical users are provided, learn only the reply rhythm, explanation granularity and decision focus. Do not copy sentences, do not mention similar users, and do not import their product facts.\n"
                "How to use personalization: learn the user's preferred explanation style and stable shopping concerns. "
                "If cart-side personalization exists, naturally use the cart products' pairing, compatibility, price tier, brand ecosystem and routine signals as soft ranking/explanation hints. "
                "You may say a product can pair with an item already in the cart when that relation is supported by the context. "
                "Do not copy historical replies, do not mention user profile, and never override current explicit constraints. "
                "Never import historical budgets, brands, quantities or old constraints as this turn's requirements unless the current user message explicitly repeats them. "
                "Do not say 'your budget' or 'you specified' for a budget/brand that only appears in history or few-shot examples.\n"
            )
        multimodal_block = ""
        if multimodal_context and multimodal_context.get("是否启用多模态"):
            multimodal_block = (
                "\nMultimodal image understanding context. Use it only as query evidence; do not infer identity or sensitive attributes:\n"
                f"{json.dumps(_compact_multimodal(multimodal_context), ensure_ascii=False, indent=2)}\n"
                "If the image target category is not available in inventory, say so honestly and only recommend real similar products when available.\n"
            )
        return (
            "你是一个电商智能导购，请用一位有礼貌、温柔、专业的客服女士语气回复。你的目标是用最少轮次帮助用户选到合适商品并推进购买决策。\n"
            "硬性规则：只能基于 Verified product facts 中的商品回答；不得编造商品、价格、品牌、库存、优惠券、功效或参数。\n"
            "Verified product facts 里的 highlight_short、suitable_scenarios、target_user_tags、non_standard_query_tags 和 enhancement_matches 都是数据库增强字段，可以作为推荐理由、场景适配和详情介绍依据。\n"
            "当前用户明确说出的需求是硬约束，用户画像只是软参考；两者冲突时必须服从当前需求。\n"
            "不要在用户回复中提到你使用了用户画像。\n"
            "严禁在用户回复中出现这些后端/开发者术语：对话状态、短期记忆、长期记忆、memory、RAG、检索、状态机、向量、rerank、prompt。\n"
            "积极导购回复策略：只要 Verified product facts 中有候选商品、备选商品或相近商品，就用正面、肯定、主动的语气给出推荐。\n"
            "有候选商品时，禁止以“抱歉”“没有找到”“没有符合”“没有明确信息”等否定句开头；应该说“我为你挑了…”“这几款更接近…”“优先看…”这类推进式表达。\n"
            "如果没有完全匹配但有相近商品，应先说“我先为你挑了几款更接近需求的选择”，再简短说明差异，不要把“没有完全匹配”放在第一句。\n"
            "如果候选商品 match_score < 0.5 或 match_level=partial，要说它更适合作为备选，并点出可取之处和差异；不要笼统说所有商品都不符合。\n"
            "只有需求完全超出商品库或没有任何可推荐方向时，才明确说明限制，并马上给出调整预算、放宽条件、换类目或补充需求的引导。\n"
            "推荐理由必须写成完整自然的一句话，不要写成“理由：轻量”“优势：拍照”这类机械标签。\n"
            "长度控制：普通推荐 2-4 句，比较最多 5 句，澄清最多问 1-2 个关键问题，购物车反馈 1-2 句；商品细节主要交给商品卡片，不要长篇解释。\n"
            "个性化只自然影响排序、语气、解释重点和回复长度；不要生硬说“根据你的用户画像”。\n"
            f"用户本轮需求：{message}\n"
            f"{memory_line}"
            f"{personalization_block}"
            f"{multimodal_block}"
            f"候选商品名称：{product_names}\n"
            f"Verified product facts:\n{product_facts}\n"
            "请直接生成给用户看的中文回复。"
        )


def _compact_personalization(context: dict) -> dict:
    return {
        "领域导购风格": context.get("领域导购风格"),
        "用户画像摘要": context.get("用户画像摘要"),
        "结构化用户画像": context.get("结构化用户画像"),
        "显式长期偏好": context.get("显式长期偏好"),
        "本轮相关历史证据": context.get("本轮相关历史证据", [])[:5],
        "few_shot示例": context.get("few_shot示例", [])[:3],
        "相似人群参考": context.get("相似人群参考"),
        "相似历史用户协同过滤": _compact_collaborative(context.get("相似历史用户协同过滤") or {}),
        "个性化生成策略": context.get("个性化生成策略"),
        "当前购物车摘要": context.get("当前购物车摘要"),
        "购物车商品侧个性化": context.get("购物车商品侧个性化"),
    }


def _compact_collaborative(context: dict) -> dict:
    return {
        "是否启用": context.get("是否启用"),
        "当前用户有效轮数": context.get("当前用户有效轮数"),
        "匹配方法": context.get("匹配方法"),
        "相似用户": context.get("相似用户", [])[:3],
        "few_shot示例": context.get("few_shot示例", [])[:2],
        "风格使用方式": context.get("风格使用方式"),
    }


def _compact_multimodal(context: dict) -> dict:
    return {
        "图片理解结果": context.get("图片理解结果"),
        "图文融合查询": context.get("图文融合查询"),
        "库存匹配判断": context.get("库存匹配判断"),
    }
