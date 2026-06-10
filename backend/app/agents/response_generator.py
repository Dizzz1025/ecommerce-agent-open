from collections.abc import Iterator
from typing import Any

from app.llm.base import BaseLLMClient
from app.agents.recommendation_streaming import RecommendationPlan, recommendation_plan_prompt
from app.models.agent import (
    CandidateProduct,
    DialogueFlow,
    FlowDecision,
    ModelRouteDecision,
    ParsedQuery,
    PreferenceUpdateResult,
    ProductQAResult,
    ScenePlan,
    ToolExecutionResult,
)
from app.models.domain import IntentType, Product, SessionState
from app.rag.pipeline import RagPipeline


class ResponseGenerationModule:
    def __init__(self, rag_pipeline: RagPipeline, llm_client: BaseLLMClient) -> None:
        self.rag_pipeline = rag_pipeline
        self.llm_client = llm_client
        self.last_llm_called = False
        self.last_response_strategy: dict = {}

    def generate(
        self,
        *,
        parsed_query: ParsedQuery,
        decision: FlowDecision,
        state: SessionState,
        candidates: list[CandidateProduct],
        products: list[Product],
        model_route: ModelRouteDecision | None = None,
        tool_result: ToolExecutionResult | None = None,
        preference_result: PreferenceUpdateResult | None = None,
        qa_result: ProductQAResult | None = None,
        scene_plan: ScenePlan | None = None,
        alternatives: list[CandidateProduct] | None = None,
        personalization_context: dict | None = None,
        multimodal_context: dict | None = None,
        fallback_result: Any = None,
        closing_context: dict | None = None,
    ) -> str:
        self.last_llm_called = False
        self.last_response_strategy = self._build_response_strategy(
            decision=decision,
            candidates=candidates,
            alternatives=alternatives or [],
            personalization_context=personalization_context,
        )
        if decision.flow == DialogueFlow.CART_ACTION:
            base = self._cart_response(parsed_query, tool_result)
            if closing_context and closing_context.get("should_close"):
                guidance = self._closing_guidance_text(closing_context, parsed_query)
                return f"{base}\n\n{guidance}"
            return base
        if decision.flow == DialogueFlow.CHECKOUT:
            return self._cart_response(parsed_query, tool_result)
        if decision.flow == DialogueFlow.PREFERENCE_UPDATE:
            return preference_result.message if preference_result and preference_result.updated else "明白，我会先按你这次说的偏好来挑。你也可以继续补充预算、品牌或使用场景，我马上帮你筛。"
        if decision.flow == DialogueFlow.CLARIFICATION:
            return self._clarification_response(parsed_query)
        if decision.flow in {DialogueFlow.CHITCHAT, DialogueFlow.GREETING}:
            return "我可以帮你挑商品、做对比、筛预算，也能把你选中的商品加入购物车。你想先看哪类？"
        if decision.flow == DialogueFlow.OUT_OF_SCOPE:
            return "这个问题暂时不属于当前导购范围。我现在可以帮你挑美妆护肤、数码电子、服饰运动和食品饮料，也能做比较、详情问答和购物车操作。"
        if decision.flow == DialogueFlow.INVALID:
            return "我还没有收到具体需求，可以告诉我想买什么、预算多少，或者想比较哪几款商品。"
        if decision.flow == DialogueFlow.PRODUCT_QA:
            local_text = qa_result.answer if qa_result else "你可以告诉我想看第几款，我就能直接介绍这件商品的价格、亮点和适合场景。"
            if model_route and model_route.need_llm and products:
                evidence = "\n".join(f"- {item}" for item in (qa_result.evidence if qa_result else []))
                detail_context = self.rag_pipeline.build_context(
                    message=parsed_query.raw_message,
                    products=products,
                    candidates=candidates,
                    state=state,
                    personalization_context=personalization_context,
                    multimodal_context=multimodal_context,
                ) + (
                    "\n\n当前任务是商品详情/介绍，不是重新推荐。"
                    "\n请只介绍用户指代的这一款商品，不要扩展推荐其他商品。"
                    "\n如果用户没有指定介绍维度，请结合当前购物需求和个性化生成策略，从数据库事实中选择 2-3 个最有帮助的维度介绍。"
                    "\n如果用户指定了维度，只回答该维度及与之最接近的数据库事实。"
                    "\n必须自然地说明价格、核心亮点和一条需要注意的地方；没有事实依据就不要编造。"
                    "\n如果某个具体参数不存在，不要用消极开头；先介绍已有亮点，再简短说明该参数商品库未提供。"
                    "\n回复尽量写成 3 句左右：第一句给商品定位和价格，第二句讲 1-2 个最相关亮点，第三句讲适合谁/什么场景或注意点。"
                    f"\n本地事实提取草稿：{local_text}"
                    f"\n商品事实证据：\n{evidence}\n"
                )
                self.last_llm_called = True
                generated = self.llm_client.generate_response(
                    intent=IntentType.DETAIL,
                    message=parsed_query.raw_message,
                    context=detail_context,
                    product_names=[item.name for item in products[:1]],
                )
                return generated or local_text
            return local_text
        if decision.flow == DialogueFlow.NO_RESULT or (not candidates and decision.need_retrieval):
            local_text = self._no_result_response(
                parsed_query,
                alternatives=alternatives or [],
                multimodal_context=multimodal_context,
                fallback_result=fallback_result,
            )
            return local_text

        if decision.flow == DialogueFlow.COMPARISON:
            local_text = self._compare_response(parsed_query, candidates, state)
            if model_route and model_route.need_llm and products:
                context = self.rag_pipeline.build_context(
                    message=parsed_query.raw_message,
                    products=products,
                    candidates=candidates,
                    state=state,
                    personalization_context=personalization_context,
                    multimodal_context=multimodal_context,
                ) + f"\nDraft comparison response: {local_text}\n请最多 5 句，先给明确结论，再补充关键差异。\n"
                self.last_llm_called = True
                generated = self.llm_client.generate_response(
                    intent=IntentType.COMPARE,
                    message=parsed_query.raw_message,
                    context=context,
                    product_names=[item.name for item in candidates[:3]],
                )
                return generated or local_text
            return local_text

        if decision.flow == DialogueFlow.SCENE_BUNDLE:
            local_text = self._scene_response(scene_plan, candidates)
            if model_route and not model_route.need_llm:
                return local_text
            context = self.rag_pipeline.build_context(
                message=parsed_query.raw_message,
                products=products,
                candidates=candidates,
                state=state,
                personalization_context=personalization_context,
                multimodal_context=multimodal_context,
            ) + f"\nScene plan: {scene_plan.model_dump() if scene_plan else {}}\nDraft response: {local_text}\n请用积极搭配方案语气，优先展示已有商品，不要用缺货信息开头。"
            self.last_llm_called = True
            generated = self.llm_client.generate_response(
                intent=IntentType.SCENE_BUNDLE,
                message=parsed_query.raw_message,
                context=context,
                product_names=[item.name for item in candidates[:5]],
            )
            return generated or local_text

        if decision.flow in {
            DialogueFlow.RECOMMENDATION,
            DialogueFlow.FILTERING,
            DialogueFlow.REFINEMENT,
            DialogueFlow.EXCLUSION,
        }:
            self.last_response_strategy["推荐回复生成方式"] = "local_grounded_template"
            self.last_response_strategy["跳过Doubao原因"] = "前端会展示商品卡片，普通推荐只需要简短导购结论。"
            return self._recommendation_template(parsed_query, candidates, personalization_context)

        if model_route and not model_route.need_llm:
            return self._recommendation_template(parsed_query, candidates, personalization_context)

        context = self.rag_pipeline.build_context(
            message=parsed_query.raw_message,
            products=products,
            candidates=candidates,
            state=state,
            personalization_context=personalization_context,
            multimodal_context=multimodal_context,
        )
        product_names = [item.name for item in candidates[:3]]
        self.last_llm_called = True
        return self.llm_client.generate_response(
            intent=IntentType(parsed_query.intent) if parsed_query.intent in IntentType._value2member_map_ else IntentType.RECOMMEND,
            message=parsed_query.raw_message,
            context=context,
            product_names=product_names,
        ) or self._recommendation_template(parsed_query, candidates, personalization_context)

    def stream_recommendation_presentation(self, plan: RecommendationPlan) -> Iterator[str]:
        self.last_llm_called = True
        self.last_response_strategy = {
            "streaming_recommendation_presentation": True,
            "plan_item_count": len(plan.items),
            "fact_locked_fields": ["sku_id", "rank", "price", "stock", "specs"],
        }
        return self.llm_client.stream_generate_response(
            intent=IntentType.RECOMMEND,
            message=plan.user_need,
            context=recommendation_plan_prompt(plan),
            product_names=[item.name for item in plan.items],
        )

    @staticmethod
    def _cart_response(parsed_query: ParsedQuery, tool_result: ToolExecutionResult | None) -> str:
        if tool_result is None:
            return "你可以直接说「把第一款加入购物车」，我就按当前推荐列表帮你处理。"
        return tool_result.message

    @staticmethod
    def _closing_guidance_text(closing_context: dict, parsed_query) -> str:
        """Generate a natural checkout-closing guidance line based on cart state.

        The text is appended after the cart action confirmation.
        It guides the user toward the final step: confirming the order,
        providing delivery address, and checking out.
        """
        cart = closing_context.get("cart_summary", {})
        total = cart.get("total_price", 0)
        count = cart.get("total_items", 0)
        names = cart.get("item_names", [])

        # Build a warm, natural guidance based on cart state
        if count == 1:
            item_hint = f"「{names[0]}」"
            return (
                f"如果确定要买{item_hint}的话，告诉我收货地址和联系方式，"
                f"我就可以帮你生成订单预览啦。还想加其他商品也可以继续说哦～"
            )
        elif count <= 3:
            items = "、".join(names)
            return (
                f"你购物车里现在有{count}件商品（{items}），合计¥{total:g}。"
                f"需要我帮你汇总订单、填写收货地址吗？"
                f"如果想继续添加其他商品也完全没问题～"
            )
        else:
            more = cart.get("more_count", 0)
            items = "、".join(names)
            return (
                f"购物车里已经有{count}件商品了（{items}"
                + (f"等{more}件" if more else "")
                + f"），合计¥{total:g}。"
                f"要不要我帮你汇总一下订单信息，确认收货地址？"
                f"当然，想继续逛逛也随时可以～"
            )

    @staticmethod
    def _clarification_response(parsed_query: ParsedQuery) -> str:
        slots = set(parsed_query.clarification_slots)
        if "category" in slots:
            return "你想看哪一类商品？比如护肤、手机耳机、跑鞋穿搭，或者咖啡零食。"
        if "priority" in slots:
            return "可以，我先确认一下：你选手机更看重拍照、续航、游戏性能，还是性价比？"
        if "sub_category_or_scene" in slots:
            return "可以，我需要再缩小一点范围：你更想看具体单品，还是按使用场景来搭配？"
        return "可以，我再确认一个关键条件：你更看重预算、品牌，还是使用场景？"

    @staticmethod
    def _no_result_response(
        parsed_query: ParsedQuery,
        alternatives: list[CandidateProduct] | None = None,
        multimodal_context: dict | None = None,
        fallback_result: Any = None,
    ) -> str:
        # 多模态不支持时的引导
        if multimodal_context and multimodal_context.get("是否启用多模态"):
            fused = multimodal_context.get("图文融合查询", {}) or {}
            visual = multimodal_context.get("图片理解结果", {}) or {}
            if fused.get("库存是否覆盖目标类目") is False:
                target = fused.get("目标商品类别") or visual.get("主要商品类别") or "图片里的商品"
                note = fused.get("库存匹配说明") or "当前商品库暂时没有这个类目的库存。"
                return (
                    f"我看你的图片需求主要是在找「{target}」，这个方向商品库目前覆盖有限。"
                    f"{note} 你可以换成背包、鞋子、帽子、防晒、耳机或饮料这类库存方向，我马上继续帮你挑。"
                )
        # 构建约束条件说明
        parts = []
        if parsed_query.price_range.max is not None:
            parts.append(f"{parsed_query.price_range.max:g}元以内")
        if parsed_query.brands_exclude:
            parts.append("排除" + "、".join(parsed_query.brands_exclude))
        if parsed_query.negative_constraints:
            parts.append("不含/不要" + "、".join(parsed_query.negative_constraints))
        if parsed_query.positive_constraints:
            parts.extend(parsed_query.positive_constraints[:3])
        condition = " + ".join(parts) if parts else "这些条件"

        # 有备选方案：根据容错步骤生成智能解释
        if alternatives:
            names = "、".join(f"{item.name}（¥{item.price:g}）" for item in alternatives[:2])
            # 使用 fallback_result 生成更精确的放宽说明
            if fallback_result and hasattr(fallback_result, 'relaxed_steps') and fallback_result.relaxed_steps:
                from app.retrieval.fallback import FallbackResult
                fr: FallbackResult = fallback_result
                # 价格放宽 → 告知超预算但取最接近
                if "relaxed_price" in fr.relaxed_steps:
                    closest = fr.relaxed_details.get("relaxed_price", {}).get("closest_match_price")
                    orig_max = fr.relaxed_details.get("relaxed_price", {}).get("original_max")
                    if closest and orig_max:
                        return (
                            f"我先为你挑了几款更接近需求的选择：{names}。"
                            f"它们比你{orig_max:g}元的预算略高一些（最接近的¥{closest:g}），在功能上最贴合你的需求，你可以看看是否合适。"
                        )
                # 子类目放宽 → 告知扩大了同类范围
                if "relaxed_sub_category" in fr.relaxed_steps:
                    return (
                        f"我先为你挑了几款更接近需求的选择：{names}。"
                        f"虽然和「{condition}」不完全一样，但在同类商品中功能最接近，你可以看看是否符合预期。"
                    )
                # 否定约束放宽
                if "relaxed_negative" in fr.relaxed_steps:
                    return (
                        f"我先为你挑了几款更接近需求的选择：{names}。"
                        f"部分排除条件已适当放宽，挑出了在用途和功能上最接近的商品，你可以点进卡片看看详情。"
                    )
                # 普通fallback
                summary = fr.summary_for_response()
                if summary:
                    return f"我先为你挑了几款更接近需求的选择：{names}。{summary}"
            return f"我先为你挑了几款更接近需求的选择：{names}。它们和「{condition}」接近，部分条件可能需要你在卡片里再确认。"

        # 完全没有匹配：给出具体的引导建议
        category_name = parsed_query.category or "商品"
        category_guide = _get_category_guidance(parsed_query)
        return (
            f"很抱歉，目前商品库里暂时没有完全匹配「{condition}」的{category_name}。\n\n"
            f"{category_guide}\n\n"
            f"我还支持美妆护肤、数码电子、服饰运动、食品饮料四个领域的推荐、对比和搭配，"
            f"你可以告诉我具体想要什么类型的商品，我来帮你挑选最合适的哦。"
        )

    @staticmethod
    def _compare_response(parsed_query: ParsedQuery, candidates: list[CandidateProduct], state: SessionState) -> str:
        if len(candidates) < 2:
            return "你可以指定两款来比，比如「比较第一款和第二款」，我会直接给结论。"
        child_context = parsed_query.target_user == "小朋友" or "小朋友" in parsed_query.raw_message or "儿童" in parsed_query.positive_constraints
        if child_context:
            safe_candidates = [
                item for item in candidates
                if _child_safe_candidate_text(f"{item.name} {' '.join(item.matched_reasons)}")
            ]
            low_sugar = [
                item for item in safe_candidates
                if any(term in f"{item.name} {' '.join(item.matched_reasons)}" for term in ["低糖", "无糖", "0糖", "不甜", "儿童"])
            ]
            best = (low_sugar or safe_candidates or candidates)[0]
            lines = [
                "如果按小朋友来选，我会优先看「不太甜、别含咖啡因、单瓶别太大」。",
                f"最推荐 {best.name}，¥{best.price:g}，它更符合儿童少糖饮品需求，也比较适合作为日常小份饮用选择。",
            ]
            for index, item in enumerate(candidates[:3], start=1):
                reason = _human_reason(item)
                lines.append(f"{index}. {item.name}：¥{item.price:g}，{reason}")
            return "\n".join(lines)
        lines = ["我先给你一个清楚结论："]
        for index, item in enumerate(candidates[:3], start=1):
            lines.append(f"{index}. {item.name}：¥{item.price:g}，{_human_reason(item)}")
        cheaper = min(candidates[:3], key=lambda item: item.price)
        lines.append(f"如果你更看重价格，我会优先选 {cheaper.name}；如果更看重使用场景，我可以继续细分。")
        return "\n".join(lines)

    @staticmethod
    def _recommendation_template(
        parsed_query: ParsedQuery,
        candidates: list[CandidateProduct],
        personalization_context: dict | None = None,
    ) -> str:
        if not candidates:
            return "这个需求我需要再缩小一点范围。你可以补充预算、品牌或使用场景，我马上继续帮你挑。"
        best = candidates[0]
        other_names = "、".join(item.name for item in candidates[1:3])
        personalization_phrase = _visible_personalization_phrase(personalization_context)
        opening = f"{personalization_phrase}我为你挑了 {len(candidates[:3])} 款"
        prefix = f"{opening}，优先看 {best.name}，¥{best.price:g}。{_human_reason(best)}"
        if parsed_query.target_user == "小朋友" or "小朋友" in parsed_query.raw_message or "儿童" in parsed_query.positive_constraints:
            prefix = f"{personalization_phrase}考虑到是小朋友来买，我优先看少糖、小包装、更日常的选择；先看 {best.name}，¥{best.price:g}。{_human_reason(best)}"
        elif parsed_query.target_user in {"女性", "女生", "职场新人"} or "职场新人" in parsed_query.raw_message:
            prefix = f"{personalization_phrase}我按你的使用场景筛到了几款更稳妥的选择，优先看 {best.name}，¥{best.price:g}。{_human_reason(best)}"
        if parsed_query.brands_exclude or parsed_query.negative_constraints:
            excluded = "、".join([*parsed_query.brands_exclude, *parsed_query.negative_constraints])
            prefix += f" 我已按你的要求避开：{excluded}。"
        lines = [prefix]
        if other_names:
            lines.append(f"另外 {other_names} 也可以放在备选里，具体参数和图片我放在商品卡片中。")
        lines.append("想继续推进的话，可以点卡片看详情，或直接说「把第一款加入购物车」。")
        return "\n".join(lines)


    @staticmethod
    def _scene_response(scene_plan: ScenePlan | None, candidates: list[CandidateProduct]) -> str:
        if not scene_plan:
            return "我先按这个场景从商品库里找到了几款可搭配商品。"
        lines = [f"我把「{scene_plan.scenario}」拆成几个可购买方向，先为你配这几件真实库存商品："]
        used = set()
        for sub_query in scene_plan.sub_queries:
            match = next(
                (
                    item for item in candidates
                    if item.sku_id not in used
                    and (not sub_query.sub_category or item.sub_category == sub_query.sub_category)
                    and (not sub_query.category or item.category == sub_query.category)
                ),
                None,
            )
            if match:
                used.add(match.sku_id)
                lines.append(f"- {sub_query.label}：{match.name}，¥{match.price:g}，这款可以帮助你解决{sub_query.reason}这个需求。")
            else:
                lines.append(f"- {sub_query.label}：这个方向可以先保留，后面补充预算或品牌后再继续筛。")
        if scene_plan.unsupported_needs:
            lines.append("另外 " + "、".join(scene_plan.unsupported_needs) + " 这类商品当前库里覆盖有限，可以先用上面几件完成核心搭配。")
        return "\n".join(lines)

    @staticmethod
    def _build_response_strategy(
        *,
        decision: FlowDecision,
        candidates: list[CandidateProduct],
        alternatives: list[CandidateProduct],
        personalization_context: dict | None,
    ) -> dict:
        if decision.flow == DialogueFlow.OUT_OF_SCOPE:
            match_status = "out_of_scope"
        elif candidates:
            if any(item.score < 0.5 or item.violated_constraints for item in candidates):
                match_status = "partial_match"
            else:
                match_status = "exact_match" if all(item.score >= 0.75 for item in candidates) else "partial_match"
        elif alternatives:
            match_status = "alternative"
        elif decision.flow == DialogueFlow.NO_RESULT or decision.need_retrieval:
            match_status = "no_result"
        else:
            match_status = "exact_match"

        personalization_refs = []
        if personalization_context and (
            personalization_context.get("是否启用个性化")
            or personalization_context.get("购物车商品侧个性化")
            or personalization_context.get("领域导购风格")
            or (personalization_context.get("相似历史用户协同过滤") or {}).get("是否启用")
        ):
            if personalization_context.get("领域导购风格"):
                personalization_refs.append("领域导购风格")
            if personalization_context.get("用户画像摘要"):
                personalization_refs.append("用户画像摘要")
            if personalization_context.get("本轮相关历史证据"):
                personalization_refs.append("相关历史证据")
            if personalization_context.get("few_shot示例"):
                personalization_refs.append("few-shot风格示例")
            if personalization_context.get("相似人群参考"):
                personalization_refs.append("相似人群参考")
            if (personalization_context.get("相似历史用户协同过滤") or {}).get("是否启用"):
                personalization_refs.append("相似历史用户协同过滤")
            if personalization_context.get("购物车商品侧个性化"):
                personalization_refs.append("购物车商品侧个性化")

        return {
            "匹配状态": match_status,
            "是否启用积极回复": True,
            "是否避免否定开头": match_status not in {"no_result", "out_of_scope"} or bool(alternatives),
            "长度策略": _length_strategy(decision.flow),
            "使用的个性化参考": personalization_refs,
            "当前轮需求优先级": "当前明确需求为硬约束，用户画像和历史偏好为软约束。",
            "事实约束": "商品名、价格、品牌、库存、参数必须来自数据库/RAG。",
        }


def _child_safe_candidate_text(text: str) -> bool:
    if "不含咖啡因" in text:
        return True
    return not any(term in text for term in ["咖啡因", "功能饮料", "红牛", "东鹏", "咖啡"])


def _human_reason(item: CandidateProduct) -> str:
    reasons = [
        _clean_reason(reason) for reason in item.matched_reasons
        if reason and reason not in {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选"}
    ][:3]
    if item.score < 0.5:
        if reasons:
            return f"它更适合作为备选，主要可取点是{'、'.join(reasons)}，和核心需求仍有一定关联。"
        return "它更适合作为备选，属于当前相关类目，可以先点开确认细节。"
    if reasons:
        return f"它比较符合你对{'、'.join(reasons)}的需求，整体匹配度更高。"
    return "它和当前需求比较接近，适合先点开看看详情。"


def _visible_personalization_phrase(context: dict | None) -> str:
    """Return a short user-facing personalization cue when there is concrete evidence.

    The phrase intentionally avoids developer terms such as 用户画像、memory、RAG.
    It is only used as a soft opening; current explicit requirements remain the
    hard constraints for retrieval and ranking.
    """
    if not context:
        return ""
    privacy = context.get("隐私设置") or {}
    if privacy.get("personalization_mode") == "off" or privacy.get("personalization_enabled") is False:
        return ""

    cart_context = context.get("购物车商品侧个性化") or {}
    cart_items = cart_context.get("参考购物车商品") or []
    if cart_context and cart_items:
        brands = [str(item.get("brand")) for item in cart_items if item.get("brand")]
        categories = [str(item.get("sub_category") or item.get("category")) for item in cart_items if item.get("sub_category") or item.get("category")]
        brand_text = "、".join(list(dict.fromkeys(brands))[:2])
        category_text = "、".join(list(dict.fromkeys(categories))[:2])
        if brand_text and category_text:
            return f"基于你购物车里偏好的{brand_text}和{category_text}选择，"
        if category_text:
            return f"基于你购物车里的{category_text}选择，"
        return "基于你购物车里的同类商品选择，"

    evidence = context.get("本轮相关历史证据") or []
    if evidence:
        text_parts: list[str] = []
        for item in evidence[:2]:
            if isinstance(item, dict):
                for key in ("user_input", "summary", "偏好", "需求", "category", "sub_category"):
                    value = item.get(key)
                    if isinstance(value, str) and value and not value.startswith("[已按隐私设置隐藏"):
                        text_parts.append(value)
                        break
        joined = " ".join(text_parts)
        for term in ["性价比", "通勤", "旅行", "油皮", "干皮", "保湿", "清爽", "拍照", "续航", "降噪", "低糖", "无糖", "高端", "轻量"]:
            if term in joined:
                return f"根据你之前更关注{term}的偏好，"
        return "结合你之前的历史选择，"

    structured = context.get("结构化用户画像") or {}
    focus = _first_profile_focus(structured)
    if focus:
        return f"根据你平时更关注{focus}的偏好，"

    if context.get("用户画像摘要"):
        return "结合你之前的选择习惯，"
    return ""


def _first_profile_focus(profile: dict) -> str | None:
    for key in ("信息关注点", "功能偏好", "商品类别偏好", "价格偏好", "决策风格"):
        value = profile.get(key)
        if isinstance(value, list) and value:
            return str(value[0])
        if isinstance(value, str) and value:
            return value[:16]
    return None


def _clean_reason(reason: str) -> str:
    return (
        reason.removeprefix("匹配")
        .removeprefix("贴合问题标签:")
        .removeprefix("购物车偏好:")
    )


def _length_strategy(flow: DialogueFlow) -> str:
    if flow == DialogueFlow.COMPARISON:
        return "比较回复最多 5 句，先给结论再补关键差异。"
    if flow == DialogueFlow.CLARIFICATION:
        return "澄清回复最多问 1-2 个关键问题。"
    if flow in {DialogueFlow.CART_ACTION, DialogueFlow.CHECKOUT}:
        return "购物车和结算反馈 1-2 句。"
    if flow == DialogueFlow.PRODUCT_QA:
        return "商品详情 2-4 句，介绍 2-3 个关键维度。"
    return "普通推荐 2-4 句，商品细节主要交给商品卡片。"


def _get_category_guidance(parsed_query) -> str:
    """当检索完全无结果时，根据用户查询的类目生成引导建议。"""
    from app.models.agent import ParsedQuery
    pq: ParsedQuery = parsed_query
    category = pq.category
    if category == "美妆护肤":
        return (
            "美妆护肤是我们最全的类目，有洁面、精华、面霜、防晒、眼霜、"
            "粉底液、面膜、卸妆、唇釉、眉笔、蜜粉等几十款商品，"
            "你可以告诉我具体的品类和肤质需求，我来精准推荐。"
        )
    if category == "数码电子":
        return (
            "数码电子方面，我们有智能手机、笔记本电脑、平板电脑、真无线耳机等品类的多款商品，"
            "覆盖从入门到旗舰的各个价位，你可以告诉我具体需求和预算。"
        )
    if category == "服饰运动":
        return (
            "服饰运动类我们有跑步鞋、篮球鞋、徒步鞋、短袖T恤、卫衣、"
            "冲锋衣、羽绒服、防晒衣、运动长裤、瑜伽裤、背包、帽子等丰富选择，"
            "你可以告诉我具体想要什么类型、什么场景穿。"
        )
    if category == "食品饮料":
        return (
            "食品饮料方面，我们有咖啡、茶饮、牛奶、酸奶、坚果零食、"
            "碳酸饮料、功能饮料、方便食品、调味品等多个品类，"
            "日常自用、囤货、送礼都有合适的选择。"
        )
    if category == "日用百货":
        return (
            "日用百货有发圈、办公文具、桌面收纳、通勤小物等实用好物，"
            "你可以告诉我具体需要什么类型。"
        )
    # Unknown category — list all capabilities
    return (
        "我们目前覆盖美妆护肤、数码电子、服饰运动、食品饮料四个大类，"
        "每个类目都有几十款精挑细选的商品，你可以告诉我你想找什么类型的商品，"
        "我来帮你做精准推荐和对比。"
    )
