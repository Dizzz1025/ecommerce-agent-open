from __future__ import annotations

import re
from typing import Any

from app.memory.user_history_store import UserHistoryStore
from app.ml.local_models import LocalModelManager
from app.models.agent import CandidateProduct, ParsedQuery
from app.models.domain import SessionState


class PersonalizationService:
    """Select concise, relevant personalization context for one response turn."""

    def __init__(self, history_store: UserHistoryStore, local_models: LocalModelManager | None = None) -> None:
        self.history_store = history_store
        self.local_models = local_models

    def build_context(
        self,
        *,
        user_id: str,
        parsed_query: ParsedQuery,
        state: SessionState,
        candidates: list[CandidateProduct],
        max_evidence: int = 5,
        max_few_shots: int = 3,
    ) -> dict[str, Any]:
        profile = self.history_store.load_profile(user_id)
        privacy = profile.get("privacy_settings") or {}
        mode = privacy.get("personalization_mode", "full")
        domain_style = self._domain_style(parsed_query.category, parsed_query.sub_category)
        if mode == "off" or privacy.get("personalization_enabled") is False:
            return {
                "中文说明": "用户已关闭个性化。本轮回复只使用当前明确需求和检索商品。",
                "是否启用个性化": False,
                "领域导购风格": domain_style,
                "隐私设置": privacy,
                "用户画像摘要": None,
                "结构化用户画像": {},
                "显式长期偏好": {},
                "本轮相关历史证据": [],
                "few_shot示例": [],
                "相似人群参考": {},
                "个性化生成策略": "个性化已关闭，只按本轮需求生成回复。",
                "用户画像更新候选": {"是否更新": False, "新增观察": []},
                "当前购物车摘要": self._cart_summary(state),
                "最近推荐摘要": [],
            }
        recent_turns = self.history_store.recent_turns_for_profile(user_id, max_turns=40)
        stable_profile_exists = bool(
            profile.get("profile_summary_text")
            or profile.get("structured_profile")
            or _has_non_empty_preferences(profile.get("explicit_preferences") or {})
        )
        if not stable_profile_exists and len(recent_turns) < 3:
            return self._cold_start_context(
                privacy=privacy,
                state=state,
                turn_count=len(recent_turns),
                domain_style=domain_style,
            )
        if mode == "semantic" or privacy.get("use_raw_history_for_personalization") is False:
            return self._build_semantic_context(
                user_id=user_id,
                profile=profile,
                recent_turns=recent_turns,
                parsed_query=parsed_query,
                state=state,
                candidates=candidates,
                domain_style=domain_style,
            )
        evidence = self._select_evidence(
            turns=recent_turns,
            parsed_query=parsed_query,
            candidates=candidates,
            max_items=max_evidence,
        )
        few_shots = self._build_few_shots(evidence, max_items=max_few_shots)
        cohort = self._similar_cohort_preference(parsed_query, state, candidates)
        collaborative = self._collaborative_style_reference(
            user_id=user_id,
            profile=profile,
            recent_turns=recent_turns,
            parsed_query=parsed_query,
            candidates=candidates,
            allow_current_raw=True,
        )
        strategy = self._generation_strategy(profile, parsed_query, evidence, cohort, collaborative, domain_style)
        profile_update = self._profile_update_observation(parsed_query)
        enabled = bool(
            profile.get("profile_summary_text")
            or evidence
            or few_shots
            or cohort.get("参考偏好")
            or collaborative.get("是否启用")
        )

        return {
            "中文说明": "本轮回复生成可使用的个性化上下文。当前用户明确需求是硬约束，以下内容只作为软参考。",
            "是否启用个性化": enabled,
            "领域导购风格": domain_style,
            "隐私设置": privacy,
            "用户画像摘要": profile.get("profile_summary_text"),
            "结构化用户画像": profile.get("structured_profile") or {},
            "显式长期偏好": profile.get("explicit_preferences") or {},
            "本轮相关历史证据": evidence,
            "few_shot示例": few_shots,
            "相似人群参考": cohort,
            "相似历史用户协同过滤": collaborative,
            "个性化生成策略": strategy,
            "用户画像更新候选": profile_update,
            "当前购物车摘要": self._cart_summary(state),
            "最近推荐摘要": [
                {
                    "sku_id": item.sku_id,
                    "name": item.name,
                    "category": item.category,
                    "price": item.price,
                    "reason": item.reason,
                }
                for item in state.goods.last_recommendations[:5]
            ],
        }

    def _cold_start_context(
        self,
        *,
        privacy: dict[str, Any],
        state: SessionState,
        turn_count: int,
        domain_style: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "中文说明": "从零开始的新用户前三轮只积累历史，不启用用户侧个性化；购物车侧同类商品个性化仍由独立模块判断。",
            "是否启用个性化": False,
            "领域导购风格": domain_style,
            "隐私设置": privacy,
            "用户画像摘要": None,
            "结构化用户画像": {},
            "显式长期偏好": {},
            "本轮相关历史证据": [],
            "few_shot示例": [],
            "相似人群参考": {},
            "个性化生成策略": f"新用户历史积累中：已有{turn_count}轮，满3轮后从下一轮开始启用对话个性化。",
            "用户画像更新候选": {"是否更新": False, "新增观察": []},
            "当前购物车摘要": self._cart_summary(state),
            "最近推荐摘要": [],
            "新用户冷启动": {
                "是否冷启动": True,
                "已积累轮数": turn_count,
                "启用阈值": 3,
                "本轮是否启用": False,
            },
        }

    def _build_semantic_context(
        self,
        *,
        user_id: str,
        profile: dict[str, Any],
        recent_turns: list[dict[str, Any]],
        parsed_query: ParsedQuery,
        state: SessionState,
        candidates: list[CandidateProduct],
        domain_style: dict[str, Any],
    ) -> dict[str, Any]:
        semantic_memory = profile.get("semantic_memory") or {}
        semantic_evidence = self._semantic_evidence(semantic_memory, parsed_query)
        cohort = self._similar_cohort_preference(parsed_query, state, candidates)
        collaborative = self._collaborative_style_reference(
            user_id=user_id,
            profile=profile,
            recent_turns=recent_turns,
            parsed_query=parsed_query,
            candidates=candidates,
            allow_current_raw=False,
        )
        strategy = (
            "用户启用了隐私个性化：只参考结构化偏好、类目计数、价格信号和匿名语义标签，"
            "不使用历史自然语言原文和历史回复 few-shot。回复仍然先给结论，再给简短理由。"
        )
        if domain_style.get("风格指令"):
            strategy += f" 领域风格：{domain_style['风格指令']}"
        if collaborative.get("是否启用"):
            strategy += " 可参考相似历史用户的导购节奏，但不使用当前用户历史原文。"
        profile_update = self._profile_update_observation(parsed_query)
        return {
            "中文说明": "隐私个性化模式下的语义化上下文。不包含历史原文。",
            "是否启用个性化": True,
            "领域导购风格": domain_style,
            "隐私设置": profile.get("privacy_settings") or {},
            "用户画像摘要": profile.get("profile_summary_text"),
            "结构化用户画像": profile.get("structured_profile") or {},
            "显式长期偏好": profile.get("explicit_preferences") or {},
            "本轮相关历史证据": semantic_evidence,
            "few_shot示例": [],
            "相似人群参考": cohort,
            "相似历史用户协同过滤": collaborative,
            "个性化生成策略": strategy,
            "用户画像更新候选": profile_update,
            "当前购物车摘要": self._cart_summary(state),
            "最近推荐摘要": [
                {
                    "sku_id": item.sku_id,
                    "category": item.category,
                    "price": item.price,
                }
                for item in state.goods.last_recommendations[:5]
            ],
        }

    def _select_evidence(
        self,
        *,
        turns: list[dict[str, Any]],
        parsed_query: ParsedQuery,
        candidates: list[CandidateProduct],
        max_items: int,
    ) -> list[dict[str, Any]]:
        current_terms = _terms(
            " ".join(
                [
                    parsed_query.raw_message,
                    parsed_query.category or "",
                    parsed_query.sub_category or "",
                    " ".join(parsed_query.positive_constraints),
                    " ".join(parsed_query.negative_constraints),
                ]
            )
        )
        candidate_categories = {item.category for item in candidates}
        candidate_sub_categories = {item.sub_category for item in candidates if item.sub_category}
        scored: list[tuple[float, dict[str, Any]]] = []
        for turn in turns:
            score = 0.0
            user_input = str(turn.get("user_input") or "")
            assistant_reply = str(turn.get("assistant_reply") or "")
            turn_text = f"{user_input} {assistant_reply}"
            turn_terms = _terms(turn_text)
            if parsed_query.category and parsed_query.category in turn_text:
                score += 3.0
            if parsed_query.sub_category and parsed_query.sub_category in turn_text:
                score += 3.0
            for product in turn.get("recommended_products", [])[:5]:
                if product.get("category") == parsed_query.category:
                    score += 2.0
                if product.get("category") in candidate_categories:
                    score += 1.0
                if product.get("sub_category") in candidate_sub_categories:
                    score += 1.5
            overlap = len(current_terms & turn_terms)
            score += min(overlap, 5) * 0.45
            if turn.get("cart_change"):
                score += 1.2
            if any(term in user_input for term in ["喜欢", "不喜欢", "太贵", "便宜", "记住", "以后", "一直"]):
                score += 1.0
            if score <= 0:
                continue
            scored.append(
                (
                    score,
                    {
                        "turn_id": turn.get("turn_id"),
                        "用户输入": user_input,
                        "系统回复摘要": _truncate(assistant_reply, 160),
                        "推荐商品摘要": [
                            {
                                "sku_id": item.get("sku_id"),
                                "name": item.get("name"),
                                "category": item.get("category"),
                                "price": item.get("price"),
                            }
                            for item in turn.get("recommended_products", [])[:3]
                        ],
                        "购物车变化": turn.get("cart_change", []),
                        "相关性理由": self._evidence_reason(parsed_query, turn_text, score),
                        "score": round(score, 3),
                    },
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in scored[:max_items]]

    @staticmethod
    def _build_few_shots(evidence: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
        shots: list[dict[str, Any]] = []
        for item in evidence:
            user_input = item.get("用户输入")
            reply = item.get("系统回复摘要")
            if not user_input or not reply:
                continue
            shots.append(
                {
                    "历史用户输入": user_input,
                    "历史系统回复风格摘要": reply,
                    "可迁移个性化经验": item.get("相关性理由") or "保留用户偏好的表达节奏和决策重点。",
                }
            )
            if len(shots) >= max_items:
                break
        return shots

    @staticmethod
    def _semantic_evidence(semantic_memory: dict[str, Any], parsed_query: ParsedQuery) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for label, key in [
            ("类目兴趣", "category_counts"),
            ("子类兴趣", "sub_category_counts"),
            ("功能偏好", "feature_counts"),
            ("排除偏好", "negative_constraint_counts"),
            ("风格偏好", "style_signals"),
        ]:
            top = _top_counter_items(semantic_memory.get(key, {}), 5)
            if top:
                evidence.append(
                    {
                        "证据类型": label,
                        "语义摘要": top,
                        "是否包含历史原文": False,
                        "相关性理由": "来自隐私模式下的结构化偏好计数。",
                    }
                )
        price_signals = semantic_memory.get("price_signals", [])[-3:]
        if price_signals:
            evidence.append(
                {
                    "证据类型": "价格偏好",
                    "语义摘要": [
                        {
                            "category": item.get("category"),
                            "sub_category": item.get("sub_category"),
                            "min": item.get("min"),
                            "max": item.get("max"),
                        }
                        for item in price_signals
                    ],
                    "是否包含历史原文": False,
                    "相关性理由": "来自历史预算信号的结构化摘要。",
                }
            )
        return evidence[:5]

    @staticmethod
    def _similar_cohort_preference(
        parsed_query: ParsedQuery,
        state: SessionState,
        candidates: list[CandidateProduct],
    ) -> dict[str, Any]:
        text = parsed_query.raw_message
        constraints = set(parsed_query.positive_constraints)
        target = parsed_query.target_user or ""
        refs: list[str] = []
        if target == "小朋友" or any(term in text for term in ["小朋友", "4岁", "四岁", "孩子"]):
            refs.append("儿童饮食场景优先少糖、小包装、不含咖啡因，并用更简单温和的语言解释。")
        if any(term in text for term in ["职场", "上班", "通勤", "入职"]):
            refs.append("通勤/职场人群通常重视实用、低调、耐用和省心，回复适合先给结论再补充场景理由。")
        if parsed_query.category == "数码电子":
            refs.append("数码商品决策通常关注预算、核心功能、使用场景和明显短板。")
        if parsed_query.category == "美妆护肤":
            refs.append("护肤彩妆决策应优先说明适用肤质、质地、成分或妆效，不夸大功效。")
        if parsed_query.category == "食品饮料":
            refs.append("食品饮料推荐应说明口味、包装规格、价格和是否适合作为日常/分享场景。")
        if "性价比" in constraints or any(term in text for term in ["便宜", "预算", "别太贵", "划算"]):
            refs.append("价格敏感用户更需要明确预算内选择和超预算备选的差异。")
        if not refs and candidates:
            refs.append("同类购买者通常希望先看到最适合的一款，再看简短理由和可选备选。")
        return {
            "中文说明": "相似购买场景的通用偏好，只作为软参考，不覆盖当前明确需求。",
            "参考偏好": refs[:4],
        }

    def _collaborative_style_reference(
        self,
        *,
        user_id: str,
        profile: dict[str, Any],
        recent_turns: list[dict[str, Any]],
        parsed_query: ParsedQuery,
        candidates: list[CandidateProduct],
        allow_current_raw: bool,
    ) -> dict[str, Any]:
        turn_count = len(recent_turns)
        if turn_count <= 4 and not profile.get("profile_summary_text"):
            return {
                "中文说明": "当前用户历史轮次不足，暂不启用相似历史用户协同过滤。",
                "是否启用": False,
                "当前用户有效轮数": turn_count,
                "启用阈值": ">4轮或已有稳定画像",
                "匹配方法": "not_started",
                "相似用户": [],
                "few_shot示例": [],
            }

        current_doc = self._style_document(
            profile=profile,
            turns=recent_turns[-10:] if allow_current_raw else [],
            parsed_query=parsed_query,
            candidates=candidates,
            include_raw=allow_current_raw,
        )
        if not current_doc.strip():
            return {
                "中文说明": "当前用户没有可用于风格匹配的摘要。",
                "是否启用": False,
                "当前用户有效轮数": turn_count,
                "匹配方法": "empty_current_document",
                "相似用户": [],
                "few_shot示例": [],
            }

        user_ids = self._candidate_reference_user_ids(user_id)
        docs: list[str] = []
        metas: list[dict[str, Any]] = []
        for other_user_id in user_ids:
            other_profile = self.history_store.load_profile(other_user_id)
            other_turns = self.history_store.recent_turns_for_profile(other_user_id, max_turns=12)
            if not other_turns and not other_profile.get("profile_summary_text") and not other_profile.get("history_summary"):
                continue
            doc = self._style_document(
                profile=other_profile,
                turns=other_turns,
                parsed_query=parsed_query,
                candidates=[],
                include_raw=True,
            )
            if not doc.strip():
                continue
            docs.append(doc)
            metas.append(
                {
                    "user_id": other_user_id,
                    "profile": other_profile,
                    "turns": other_turns,
                    "doc": doc,
                }
            )
            if len(docs) >= 36:
                break

        if not docs:
            return {
                "中文说明": "没有可用的历史用户作为协同过滤参考。",
                "是否启用": False,
                "当前用户有效轮数": turn_count,
                "匹配方法": "no_reference_users",
                "相似用户": [],
                "few_shot示例": [],
            }

        semantic_scores = self._semantic_similarity_scores(current_doc, docs)
        scored: list[tuple[float, dict[str, Any]]] = []
        for index, meta in enumerate(metas):
            semantic_score = semantic_scores[index] if index < len(semantic_scores) else 0.0
            fallback_score = _lexical_similarity(current_doc, meta["doc"])
            category_score = self._category_overlap_score(parsed_query, meta["profile"], meta["turns"])
            score = max(semantic_score, fallback_score * 0.88) * 0.72 + category_score * 0.28
            scored.append((round(min(score, 1.0), 4), meta))
        scored.sort(key=lambda item: item[0], reverse=True)
        threshold = 0.38 if semantic_scores else 0.28
        selected = [(score, meta) for score, meta in scored[:3] if score >= threshold]
        if not selected:
            selected = scored[:1]

        similar_users = [
            {
                "user_id": meta["user_id"],
                "相似度": score,
                "画像摘要": _truncate(str(meta["profile"].get("profile_summary_text") or meta["profile"].get("history_summary") or ""), 140),
                "结构化风格": {
                    key: value
                    for key, value in (meta["profile"].get("structured_profile") or {}).items()
                    if key in {"说话风格", "语言风格", "决策风格", "信息关注点", "客服交互偏好"}
                },
                "参考理由": self._collaborative_reason(parsed_query, meta["profile"], meta["turns"], score),
            }
            for score, meta in selected
        ]
        few_shots = self._collaborative_few_shots(selected[0][1]["turns"] if selected else [], parsed_query)
        enabled = bool(similar_users and selected[0][0] >= threshold)
        return {
            "中文说明": "基于本地历史用户的相似语言/购买风格协同过滤。只作为回复风格和解释重点参考，不改变当前商品事实和硬约束。",
            "是否启用": enabled,
            "当前用户有效轮数": turn_count,
            "启用阈值": ">4轮或已有稳定画像",
            "本轮相似度阈值": threshold,
            "匹配方法": "text2vec/bge语义相似度 + 关键词fallback + 类目偏好重合",
            "相似用户": similar_users,
            "few_shot示例": few_shots,
            "风格使用方式": "参考相似用户收到的回复节奏、解释详细度和导购语气；不要复制原句，不要暴露相似用户身份。",
        }

    def _semantic_similarity_scores(self, query: str, documents: list[str]) -> list[float]:
        if not self.local_models or not documents:
            return []
        scores = self.local_models.semantic_scores(query, documents)
        if not scores:
            return []
        result: list[float] = []
        for index in range(len(documents)):
            values = [
                score_list[index]
                for score_list in scores.values()
                if index < len(score_list)
            ]
            result.append(sum(values) / len(values) if values else 0.0)
        return result

    def _candidate_reference_user_ids(self, current_user_id: str) -> list[str]:
        priority = [
            "alex_sports",
            "xiaomei_beauty",
            "lily_beauty_pro",
            "xiaoming_digital",
            "zhanggong_digital",
            "xiaoya_clothing",
            "daliu_sports",
            "xiaochihuo_food",
            "wangjingli_food",
            "sophia_digital",
            "victoria_beauty",
            "beauty_lily",
            "digital_tony",
            "sports_mike",
            "food_emma",
        ]
        all_ids = self.history_store.list_user_ids()
        ordered = [item for item in priority if item in all_ids and item != current_user_id]
        extras = [
            item
            for item in all_ids
            if item != current_user_id
            and item not in ordered
            and not item.startswith(("test-", "test_", "restore-event-user", "debug", "dbg-", "tmp-"))
        ]
        return [*ordered, *extras]

    @staticmethod
    def _style_document(
        *,
        profile: dict[str, Any],
        turns: list[dict[str, Any]],
        parsed_query: ParsedQuery,
        candidates: list[CandidateProduct],
        include_raw: bool,
    ) -> str:
        structured = profile.get("structured_profile") or {}
        semantic = profile.get("semantic_memory") or {}
        parts: list[str] = [
            str(profile.get("profile_summary_text") or ""),
            str(profile.get("history_summary") or ""),
            " ".join(str(value) for value in structured.values() if value),
            " ".join(_top_keys(semantic.get("category_counts", {}), 5)),
            " ".join(_top_keys(semantic.get("feature_counts", {}), 8)),
            " ".join(_top_keys(semantic.get("style_signals", {}), 8)),
            parsed_query.category or "",
            parsed_query.sub_category or "",
            " ".join(parsed_query.positive_constraints),
            " ".join(parsed_query.negative_constraints),
            " ".join(item.category for item in candidates[:5]),
        ]
        if include_raw:
            for turn in turns[-8:]:
                if not turn.get("raw_text_hidden"):
                    parts.append(str(turn.get("user_input") or ""))
                    parts.append(str(turn.get("assistant_reply") or ""))
        return " ".join(item for item in parts if item).strip()

    @staticmethod
    def _category_overlap_score(parsed_query: ParsedQuery, profile: dict[str, Any], turns: list[dict[str, Any]]) -> float:
        if not parsed_query.category:
            return 0.0
        score = 0.0
        semantic = profile.get("semantic_memory") or {}
        category_counts = semantic.get("category_counts") or {}
        if parsed_query.category in category_counts:
            score += 0.55
        sub_counts = semantic.get("sub_category_counts") or {}
        if parsed_query.sub_category and parsed_query.sub_category in sub_counts:
            score += 0.25
        turn_text = " ".join(
            f"{turn.get('user_input', '')} {turn.get('assistant_reply', '')}"
            for turn in turns[-8:]
            if not turn.get("raw_text_hidden")
        )
        if parsed_query.category in turn_text:
            score += 0.2
        return min(score, 1.0)

    @staticmethod
    def _collaborative_reason(
        parsed_query: ParsedQuery,
        profile: dict[str, Any],
        turns: list[dict[str, Any]],
        score: float,
    ) -> str:
        reasons: list[str] = []
        semantic = profile.get("semantic_memory") or {}
        if parsed_query.category and parsed_query.category in (semantic.get("category_counts") or {}):
            reasons.append("历史关注类目相同")
        if parsed_query.sub_category and parsed_query.sub_category in (semantic.get("sub_category_counts") or {}):
            reasons.append("历史关注子类相同")
        structured = profile.get("structured_profile") or {}
        if structured.get("语言风格") or structured.get("说话风格"):
            reasons.append("可迁移回复风格明确")
        if turns:
            reasons.append("存在可参考历史对话")
        reasons.append(f"综合相似度{score:.2f}")
        return "、".join(reasons[:4])

    @staticmethod
    def _collaborative_few_shots(turns: list[dict[str, Any]], parsed_query: ParsedQuery) -> list[dict[str, Any]]:
        if not turns:
            return []
        scored: list[tuple[int, dict[str, Any]]] = []
        for turn in turns[-12:]:
            if turn.get("raw_text_hidden"):
                continue
            text = f"{turn.get('user_input', '')} {turn.get('assistant_reply', '')}"
            score = 0
            if parsed_query.category and parsed_query.category in text:
                score += 3
            if parsed_query.sub_category and parsed_query.sub_category in text:
                score += 2
            if any(term in text for term in parsed_query.positive_constraints):
                score += 1
            scored.append((score, turn))
        scored.sort(key=lambda item: item[0], reverse=True)
        shots: list[dict[str, Any]] = []
        for _, turn in scored[:2]:
            user_input = str(turn.get("user_input") or "")
            assistant_reply = str(turn.get("assistant_reply") or "")
            if not user_input or not assistant_reply:
                continue
            shots.append(
                {
                    "相似用户输入": _truncate(user_input, 90),
                    "相似用户收到的回复风格摘要": _truncate(assistant_reply, 180),
                    "迁移要求": "只学习表达节奏和解释重点，不复制原句，不引入该用户的商品事实。",
                }
            )
        return shots

    @staticmethod
    def _domain_style(category: str | None, sub_category: str | None) -> dict[str, Any]:
        styles = {
            "美妆护肤": {
                "导购角色": "美妆护肤导购小姐姐",
                "风格指令": "温柔细腻、少夸大功效，优先说肤质/质地/成分或妆效，再给简短购买建议。",
                "解释重点": ["肤质适配", "质地肤感", "成分/功效边界", "使用场景"],
                "禁忌": ["不要承诺医学疗效", "不要用过度绝对化功效词"],
            },
            "数码电子": {
                "导购角色": "数码电子导购小哥",
                "风格指令": "清晰理性、先给预算内结论，再讲核心参数、使用体验和明显短板。",
                "解释重点": ["预算", "核心功能", "参数/体验", "适合人群", "短板"],
                "禁忌": ["不要堆太多参数", "不要推荐超预算商品作为主推"],
            },
            "服饰运动": {
                "导购角色": "服饰运动搭配顾问",
                "风格指令": "场景感强、自然亲切，优先说版型/材质/舒适度/搭配场景。",
                "解释重点": ["场景", "版型", "材质", "舒适度", "搭配性"],
                "禁忌": ["不要忽略尺码/风格差异", "不要混入无关类目"],
            },
            "食品饮料": {
                "导购角色": "食品饮料导购",
                "风格指令": "轻松亲切，优先说口味、甜度、规格、价格和是否适合分享/儿童场景。",
                "解释重点": ["口味", "甜度", "包装规格", "价格", "分享场景"],
                "禁忌": ["儿童场景避免咖啡因/高糖表达", "不要编造成分或健康功效"],
            },
        }
        payload = styles.get(category) or {
            "导购角色": "电商导购",
            "风格指令": "简洁专业，先给结论，再说明与当前需求最相关的1-2个理由。",
            "解释重点": ["预算", "使用场景", "核心优势"],
            "禁忌": ["不要编造商品事实"],
        }
        return {
            "中文说明": "领域导购风格只影响表达方式和解释重点，不改变当前硬约束和商品事实。",
            "商品类别": category,
            "商品子类": sub_category,
            **payload,
        }

    @staticmethod
    def _generation_strategy(
        profile: dict[str, Any],
        parsed_query: ParsedQuery,
        evidence: list[dict[str, Any]],
        cohort: dict[str, Any],
        collaborative: dict[str, Any],
        domain_style: dict[str, Any],
    ) -> str:
        structured = profile.get("structured_profile") or {}
        style = structured.get("语言风格") or structured.get("说话风格") or "简洁自然"
        focus = structured.get("信息关注点") or []
        focus_text = "、".join(focus[:4]) if isinstance(focus, list) else str(focus)
        base = f"回复采用{style}风格，先给结论，再给1-3句理由。"
        if domain_style.get("风格指令"):
            base += f" 领域导购风格：{domain_style['风格指令']}"
        if focus_text:
            base += f" 解释时优先覆盖用户长期关注的{focus_text}。"
        if evidence:
            base += " 参考相似历史轮次的表达节奏，但不能复述历史内容。"
        if cohort.get("参考偏好"):
            base += " 同时吸收相似购买场景的决策关注点。"
        if collaborative.get("是否启用"):
            top_user = (collaborative.get("相似用户") or [{}])[0].get("user_id")
            base += f" 协同过滤提示：当前用户与历史用户{top_user}的表达/购买风格相近，可参考其回复节奏和解释重点。"
        if parsed_query.negative_constraints or parsed_query.brands_exclude:
            base += " 本轮否定约束必须明确遵守。"
        return base

    @staticmethod
    def _profile_update_observation(parsed_query: ParsedQuery) -> dict[str, Any]:
        observations: list[str] = []
        text = parsed_query.raw_message
        if any(term in text for term in ["一直", "以后", "记住", "长期", "通常", "平时"]):
            observations.append("用户本轮可能表达了可进入长期画像的稳定偏好，需要画像服务后续确认。")
        if parsed_query.price_range.max is not None or any(term in text for term in ["预算", "便宜", "性价比", "划算"]):
            observations.append("用户本轮继续体现价格/性价比关注，可作为价格偏好证据。")
        if parsed_query.negative_constraints or parsed_query.brands_exclude:
            observations.append("用户本轮表达了排除条件；若包含“以后/一直”等长期词，才应写入长期排斥。")
        return {
            "是否更新": bool(observations),
            "新增观察": observations,
        }

    @staticmethod
    def _cart_summary(state: SessionState) -> dict[str, Any]:
        return {
            "total_items": sum(item.quantity for item in state.cart.items),
            "items": [
                {
                    "sku_id": item.sku_id,
                    "quantity": item.quantity,
                }
                for item in state.cart.items
            ],
        }

    @staticmethod
    def _evidence_reason(parsed_query: ParsedQuery, text: str, score: float) -> str:
        reasons = []
        if parsed_query.category and parsed_query.category in text:
            reasons.append("商品大类相同")
        if parsed_query.sub_category and parsed_query.sub_category in text:
            reasons.append("商品子类相同")
        if any(term in text for term in parsed_query.positive_constraints):
            reasons.append("功能偏好相似")
        if any(term in text for term in ["喜欢", "不喜欢", "太贵", "便宜", "记住"]):
            reasons.append("包含用户反馈或稳定偏好表达")
        if not reasons:
            reasons.append(f"文本相似度较高，相关分 {score:.1f}")
        return "、".join(reasons[:3])


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[\u4e00-\u9fff]{2,8}|[a-zA-Z0-9]+", text.lower()))


def _top_counter_items(counter: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    if not isinstance(counter, dict):
        return []
    return [
        {"term": key, "count": value}
        for key, value in sorted(counter.items(), key=lambda item: item[1], reverse=True)
        if key
    ][:limit]


def _top_keys(counter: dict[str, Any], limit: int) -> list[str]:
    if not isinstance(counter, dict):
        return []
    return [
        str(key)
        for key, value in sorted(counter.items(), key=lambda item: item[1], reverse=True)
        if key and value
    ][:limit]


def _lexical_similarity(left: str, right: str) -> float:
    left_terms = _terms(left)
    right_terms = _terms(right)
    if not left_terms or not right_terms:
        return 0.0
    overlap = len(left_terms & right_terms)
    union = len(left_terms | right_terms)
    return overlap / union if union else 0.0


def _has_non_empty_preferences(preferences: dict[str, Any]) -> bool:
    return any(value not in (None, "", [], {}, 0) for value in preferences.values())


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
