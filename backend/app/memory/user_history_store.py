from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models.domain import SessionState


class UserHistoryStore:
    """Local JSON persistence for demo user history and session recovery."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def load_profile(self, user_id: str) -> dict[str, Any]:
        path = self._profile_path(user_id)
        if not path.exists():
            return self._default_profile(user_id)
        try:
            return self._normalize_profile(json.loads(path.read_text(encoding="utf-8")), user_id)
        except json.JSONDecodeError:
            return self._default_profile(user_id)

    def save_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        user_id = str(profile["user_id"])
        profile["updated_at"] = _now()
        path = self._profile_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        return profile

    def list_user_ids(self) -> list[str]:
        """Return local user ids that have a profile directory.

        This is used by collaborative personalization. It intentionally reads
        only lightweight profile paths and lets callers decide which histories
        are suitable as reference users.
        """

        if not self.root_dir.exists():
            return []
        result: list[str] = []
        for child in self.root_dir.iterdir():
            if child.is_dir() and (child / "profile.json").exists():
                result.append(child.name)
        return sorted(result)

    def save_profile_summary(
        self,
        *,
        user_id: str,
        natural_summary: str,
        structured_profile: dict[str, Any],
        history_summary: str | None = None,
    ) -> dict[str, Any]:
        profile = self.load_profile(user_id)
        profile["profile_summary_text"] = natural_summary
        profile["structured_profile"] = structured_profile
        if history_summary is not None:
            profile["history_summary"] = history_summary
        return self.save_profile(profile)

    def apply_privacy_preferences(
        self,
        *,
        user_id: str,
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata or {}
        profile = self.load_profile(user_id)
        current = profile.get("privacy_settings") or self._default_privacy_settings()
        requested_mode = str(metadata.get("privacy_mode") or "").strip().lower()
        requested_store_raw = metadata.get("store_raw_history")
        message_mode = self._privacy_mode_from_text(message)
        mode = requested_mode if requested_mode in {"full", "semantic", "off"} else message_mode
        if mode is None and requested_store_raw is None:
            return {"updated": False, "privacy_settings": current, "message": ""}

        updated = dict(current)
        if mode == "off":
            updated.update(
                {
                    "personalization_mode": "off",
                    "personalization_enabled": False,
                    "use_raw_history_for_personalization": False,
                    "semantic_memory_only": False,
                }
            )
        elif mode == "semantic":
            updated.update(
                {
                    "personalization_mode": "semantic",
                    "personalization_enabled": True,
                    "use_raw_history_for_personalization": False,
                    "semantic_memory_only": True,
                }
            )
        elif mode == "full":
            updated.update(
                {
                    "personalization_mode": "full",
                    "personalization_enabled": True,
                    "use_raw_history_for_personalization": True,
                    "semantic_memory_only": False,
                }
            )
        if requested_store_raw is not None:
            updated["store_raw_history"] = bool(requested_store_raw)
        if any(term in message for term in ["不要保存聊天", "不保存聊天", "不要记录聊天", "清除原文", "不要保存原文"]):
            updated["store_raw_history"] = False
        if any(term in message for term in ["可以保存聊天", "恢复保存聊天", "允许保存原文"]):
            updated["store_raw_history"] = True

        profile["privacy_settings"] = updated
        self.save_profile(profile)
        return {
            "updated": True,
            "privacy_settings": updated,
            "message": self._privacy_update_message(updated),
        }

    def latest_session_id(self, user_id: str) -> str | None:
        profile = self.load_profile(user_id)
        last_session_id = profile.get("last_session_id")
        if last_session_id:
            return str(last_session_id)
        sessions = profile.get("sessions", [])
        if not sessions:
            return None
        latest = max(sessions, key=lambda item: item.get("updated_at", ""))
        return latest.get("session_id")

    def load_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        path = self._session_path(user_id, session_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def restore_state(
        self,
        *,
        user_id: str,
        source_session_id: str | None,
        target_session_id: str,
    ) -> tuple[SessionState | None, str | None]:
        source_session_id = source_session_id or self.latest_session_id(user_id)
        if not source_session_id:
            return None, None
        session = self.load_session(user_id, source_session_id)
        if not session:
            return None, source_session_id
        snapshot = session.get("state_snapshot")
        if not snapshot:
            return None, source_session_id
        profile = self.load_profile(user_id)
        try:
            state = SessionState.model_validate(snapshot)
        except Exception:
            return None, source_session_id
        state.session_id = target_session_id
        state.user_id = user_id
        state.user_profile_summary_text = profile.get("profile_summary_text")
        state.user_profile_structured = profile.get("structured_profile") or {}
        return state, source_session_id

    def save_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        state: SessionState,
        trace: dict[str, Any],
        frontend_output: dict[str, Any],
    ) -> None:
        now = _now()
        profile = self.load_profile(user_id)
        session = self.load_session(user_id, session_id) or self._default_session(user_id, session_id)
        privacy_settings = profile.get("privacy_settings") or self._default_privacy_settings()
        store_raw = bool(privacy_settings.get("store_raw_history", True))
        turn = {
            "turn_id": len(session["turns"]) + 1,
            "timestamp": now,
            "user_input": user_message if store_raw else "[已按隐私设置隐藏原始用户输入]",
            "assistant_reply": assistant_reply if store_raw else "[已按隐私设置隐藏原始系统回复]",
            "raw_text_hidden": not store_raw,
            "recommended_products": frontend_output.get("frontend_data", {}).get("recommended_products", {}).get("products", []),
            "retrieval_summary": {
                "retrieved_product_ids": trace.get("retrieved_product_ids", []),
                "selected_product_ids": trace.get("selected_product_ids", []),
                "filtered_product_ids": trace.get("filtered_product_ids", []),
                "top_scores": trace.get("retrieval_scores", [])[:5],
            },
            "cart_change": self._tool_summary(trace),
            "dialogue_state": state.dialogue_state_tracking.model_dump(),
        }
        session["turns"].append(turn)
        session["updated_at"] = now
        session["last_dialogue_state"] = state.dialogue_state_tracking.model_dump()
        session["last_short_term_memory"] = {
            "recent_messages": [item.model_dump() for item in state.recent_messages],
            "last_recommendations": [item.model_dump() for item in state.goods.last_recommendations],
            "last_candidates": [item.model_dump() for item in state.goods.last_candidates],
            "resolved_references": state.dialogue_state_tracking.resolved_references,
            "event_memory": state.event_memory.model_dump(),
            "memory_events": [item.model_dump() for item in state.memory_events[-10:]],
        }
        session["cart"] = state.cart.model_dump()
        session["state_snapshot"] = state.model_dump()
        self._write_session(user_id, session_id, session)

        profile["last_session_id"] = session_id
        profile["sessions"] = self._upsert_session_meta(
            profile.get("sessions", []),
            {
                "session_id": session_id,
                "created_at": session.get("created_at", now),
                "updated_at": now,
                "turn_count": len(session["turns"]),
            },
        )
        profile["explicit_preferences"] = self._merge_explicit_preferences(
            existing=profile.get("explicit_preferences") or {},
            current=state.user.global_preferences.model_dump(),
            structured_profile=profile.get("structured_profile") or {},
        )
        profile["privacy_settings"] = privacy_settings
        self._promote_turn_memory(
            profile=profile,
            turn=turn,
            state=state,
            trace=trace,
            frontend_output=frontend_output,
            allow_natural_summary=bool(privacy_settings.get("personalization_mode") == "full" and privacy_settings.get("use_raw_history_for_personalization", True)),
        )
        profile["updated_at"] = now
        self.save_profile(profile)

    def recent_turns_for_profile(self, user_id: str, max_turns: int = 20) -> list[dict[str, Any]]:
        profile = self.load_profile(user_id)
        turns: list[dict[str, Any]] = []
        for session_meta in sorted(profile.get("sessions", []), key=lambda item: item.get("updated_at", "")):
            session = self.load_session(user_id, session_meta.get("session_id", ""))
            if session:
                turns.extend(session.get("turns", []))
        return turns[-max_turns:]

    def _normalize_profile(self, profile: dict[str, Any], fallback_user_id: str) -> dict[str, Any]:
        """Make hand-written/simulated user histories usable by memory and profile APIs."""
        user_id = str(profile.get("user_id") or fallback_user_id)
        default = self._default_profile(user_id)
        normalized = {**default, **profile}
        normalized["user_id"] = user_id
        normalized["privacy_settings"] = {
            **default["privacy_settings"],
            **(profile.get("privacy_settings") or {}),
        }
        semantic = {
            **default["semantic_memory"],
            **(profile.get("semantic_memory") or {}),
        }
        if not semantic.get("cart_skus"):
            derived_cart_skus = self._derive_cart_skus_from_sessions(
                user_id=user_id,
                sessions=normalized.get("sessions", []),
            )
            if derived_cart_skus:
                semantic["cart_skus"] = derived_cart_skus
        normalized["semantic_memory"] = semantic
        normalized["explicit_preferences"] = self._merge_explicit_preferences(
            existing=normalized.get("explicit_preferences") or {},
            current={},
            structured_profile=normalized.get("structured_profile") or {},
        )
        if not normalized.get("history_summary"):
            normalized["history_summary"] = self._derive_history_summary(normalized, semantic)
        return normalized

    def _derive_cart_skus_from_sessions(
        self,
        *,
        user_id: str,
        sessions: list[dict[str, Any]],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        session_ids = [str(item.get("session_id") or "") for item in sessions if item.get("session_id")]
        for session_id in session_ids[-8:]:
            session = self.load_session(user_id, session_id)
            if not session:
                continue
            cart = session.get("cart") or {}
            if not cart.get("items"):
                cart = ((session.get("state_snapshot") or {}).get("cart") or {})
            for item in cart.get("items", []) or []:
                _inc(counts, item.get("sku_id"), amount=item.get("quantity", 1))
        return counts

    @staticmethod
    def _merge_explicit_preferences(
        *,
        existing: dict[str, Any],
        current: dict[str, Any],
        structured_profile: dict[str, Any],
    ) -> dict[str, Any]:
        existing = _flatten_preferences(existing)
        current = _flatten_preferences(current)
        merged = {
            "price_preference": existing.get("price_preference") or current.get("price_preference"),
            "preferred_brands": _unique_list(
                existing.get("preferred_brands"),
                current.get("preferred_brands"),
                structured_profile.get("品牌偏好"),
                structured_profile.get("brand_preference"),
            ),
            "excluded_brands": _unique_list(
                existing.get("excluded_brands"),
                current.get("excluded_brands"),
                structured_profile.get("排斥品牌"),
                structured_profile.get("excluded_brands"),
            ),
            "preferred_style": _unique_list(
                existing.get("preferred_style"),
                current.get("preferred_style"),
                structured_profile.get("功能偏好"),
                structured_profile.get("信息关注点"),
                structured_profile.get("商品类别偏好"),
            ),
            "avoid_terms": _unique_list(
                existing.get("avoid_terms"),
                current.get("avoid_terms"),
                structured_profile.get("排斥条件"),
                structured_profile.get("avoid_terms"),
            ),
        }
        if not merged["price_preference"]:
            merged["price_preference"] = (
                structured_profile.get("价格偏好")
                or structured_profile.get("price_preference")
            )
        return merged

    @staticmethod
    def _derive_history_summary(profile: dict[str, Any], semantic: dict[str, Any]) -> str:
        parts: list[str] = []
        if profile.get("profile_summary_text"):
            parts.append(str(profile["profile_summary_text"]))
        session_count = len(profile.get("sessions", []) or [])
        if session_count:
            parts.append(f"本地历史包含 {session_count} 个会话，可用于会话恢复和个性化参考。")
        cart_skus = semantic.get("cart_skus") or {}
        if cart_skus:
            sample = "、".join(f"{sku}x{qty}" for sku, qty in list(cart_skus.items())[:6])
            parts.append(f"历史购物车记录包含 {sample}。")
        categories = semantic.get("category_counts") or {}
        if categories:
            sample = "、".join(f"{name}({count})" for name, count in list(categories.items())[:4])
            parts.append(f"历史关注类目：{sample}。")
        return " ".join(parts)

    def _write_session(self, user_id: str, session_id: str, session: dict[str, Any]) -> None:
        path = self._session_path(user_id, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")

    def _profile_path(self, user_id: str) -> Path:
        return self.root_dir / _safe_id(user_id) / "profile.json"

    def _session_path(self, user_id: str, session_id: str) -> Path:
        return self.root_dir / _safe_id(user_id) / "sessions" / f"{_safe_id(session_id)}.json"

    @staticmethod
    def _default_profile(user_id: str) -> dict[str, Any]:
        now = _now()
        return {
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "sessions": [],
            "last_session_id": None,
            "profile_summary_text": None,
            "structured_profile": {},
            "history_summary": "",
            "explicit_preferences": {},
            "explicit_rejections": {},
            "privacy_settings": UserHistoryStore._default_privacy_settings(),
            "semantic_memory": UserHistoryStore._default_semantic_memory(),
            "memory_cards": [],
            "memory_promotion_log": [],
        }

    @staticmethod
    def _default_session(user_id: str, session_id: str) -> dict[str, Any]:
        now = _now()
        return {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "turns": [],
            "last_dialogue_state": {},
            "last_short_term_memory": {},
            "cart": {},
            "state_snapshot": {},
        }

    @staticmethod
    def _upsert_session_meta(sessions: list[dict[str, Any]], meta: dict[str, Any]) -> list[dict[str, Any]]:
        by_id = {item.get("session_id"): item for item in sessions}
        existing = by_id.get(meta["session_id"], {})
        existing.update(meta)
        by_id[meta["session_id"]] = existing
        return sorted(by_id.values(), key=lambda item: item.get("updated_at", ""))

    @staticmethod
    def _tool_summary(trace: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "tool_name": item.get("tool_name"),
                "ok": item.get("ok"),
                "message": item.get("message"),
                "error_code": item.get("error_code"),
            }
            for item in trace.get("tool_calls", [])
        ]

    @staticmethod
    def _default_privacy_settings() -> dict[str, Any]:
        return {
            "personalization_mode": "full",
            "personalization_enabled": True,
            "use_raw_history_for_personalization": True,
            "semantic_memory_only": False,
            "store_raw_history": True,
            "updated_at": _now(),
        }

    @staticmethod
    def _default_semantic_memory() -> dict[str, Any]:
        return {
            "category_counts": {},
            "sub_category_counts": {},
            "feature_counts": {},
            "negative_constraint_counts": {},
            "brand_counts": {},
            "price_signals": [],
            "recommended_skus": {},
            "cart_skus": {},
            "purchased_skus": {},
            "style_signals": {},
            "last_updated_at": None,
        }

    @staticmethod
    def _privacy_mode_from_text(message: str) -> str | None:
        if any(term in message for term in ["关闭个性化", "不要个性化", "取消个性化", "关闭推荐记忆", "不要根据历史推荐"]):
            return "off"
        if any(term in message for term in ["隐私个性化", "只用匿名", "只用向量", "只用语义", "不要用原文历史", "不要读取历史聊天", "保护隐私但个性化"]):
            return "semantic"
        if any(term in message for term in ["开启个性化", "恢复个性化", "允许个性化", "可以根据历史推荐", "使用我的历史偏好"]):
            return "full"
        return None

    @staticmethod
    def _privacy_update_message(settings: dict[str, Any]) -> str:
        mode = settings.get("personalization_mode")
        if mode == "off":
            return "已为你关闭个性化推荐。后续我会只按本轮明确需求来挑选商品。"
        if mode == "semantic":
            return "已切换到隐私个性化模式。后续我只使用结构化偏好摘要来优化推荐，不把历史原文用于个性化生成。"
        return "已开启完整个性化推荐。后续我会在遵守本轮需求的前提下，参考你的历史偏好和购物习惯。"

    @staticmethod
    def _promote_turn_memory(
        *,
        profile: dict[str, Any],
        turn: dict[str, Any],
        state: SessionState,
        trace: dict[str, Any],
        frontend_output: dict[str, Any],
        allow_natural_summary: bool,
    ) -> None:
        settings = profile.get("privacy_settings") or UserHistoryStore._default_privacy_settings()
        if not settings.get("personalization_enabled", True):
            return
        semantic = profile.get("semantic_memory") or UserHistoryStore._default_semantic_memory()
        parsed = trace.get("parsed_query", {}) if isinstance(trace.get("parsed_query"), dict) else {}
        category = parsed.get("category") or state.dialogue_state_tracking.current_category
        sub_category = parsed.get("sub_category") or state.dialogue_state_tracking.current_sub_category
        _inc(semantic["category_counts"], category)
        _inc(semantic["sub_category_counts"], sub_category)
        for term in parsed.get("positive_constraints", []) or []:
            _inc(semantic["feature_counts"], term)
        for term in parsed.get("negative_constraints", []) or []:
            _inc(semantic["negative_constraint_counts"], term)
        for brand in (parsed.get("brands_include", []) or []):
            _inc(semantic["brand_counts"], brand)
        price_range = parsed.get("price_range") or {}
        if price_range.get("max") is not None or price_range.get("min") is not None:
            semantic["price_signals"].append(
                {
                    "category": category,
                    "sub_category": sub_category,
                    "min": price_range.get("min"),
                    "max": price_range.get("max"),
                    "turn_id": turn.get("turn_id"),
                    "timestamp": turn.get("timestamp"),
                }
            )
            semantic["price_signals"] = semantic["price_signals"][-20:]
        for product in turn.get("recommended_products", [])[:5]:
            _inc(semantic["recommended_skus"], product.get("sku_id"))
        for item in state.cart.items:
            _inc(semantic["cart_skus"], item.sku_id, amount=item.quantity)
        for call in trace.get("tool_calls", []):
            if call.get("tool_name") == "mock_checkout" and call.get("ok"):
                payload = call.get("payload") or {}
                for item in payload.get("items", []):
                    _inc(semantic["purchased_skus"], item.get("sku_id"), amount=item.get("quantity", 1))
        for term in state.user.global_preferences.preferred_style:
            _inc(semantic["style_signals"], term)
        semantic["last_updated_at"] = _now()
        profile["semantic_memory"] = semantic

        cards = profile.get("memory_cards") or []
        new_cards = UserHistoryStore._memory_cards_from_turn(
            turn=turn,
            parsed=parsed,
            allow_natural_summary=allow_natural_summary,
        )
        for card in new_cards:
            existing = next((item for item in cards if item.get("memory_key") == card.get("memory_key")), None)
            if existing:
                existing["evidence_count"] = int(existing.get("evidence_count", 1)) + 1
                existing["confidence"] = min(float(existing.get("confidence", 0.5)) + 0.08, 0.98)
                existing["last_seen_at"] = card["last_seen_at"]
                existing["source_turn_ids"] = list(dict.fromkeys([*existing.get("source_turn_ids", []), *card.get("source_turn_ids", [])]))[-6:]
            else:
                cards.append(card)
        profile["memory_cards"] = sorted(cards, key=lambda item: (item.get("confidence", 0), item.get("last_seen_at", "")), reverse=True)[:50]
        log = profile.get("memory_promotion_log") or []
        if new_cards or parsed.get("positive_constraints") or parsed.get("negative_constraints"):
            log.append(
                {
                    "timestamp": _now(),
                    "turn_id": turn.get("turn_id"),
                    "promoted_cards": [card.get("memory_key") for card in new_cards],
                    "semantic_updates": {
                        "category": category,
                        "sub_category": sub_category,
                        "features": parsed.get("positive_constraints", [])[:5],
                        "negative_constraints": parsed.get("negative_constraints", [])[:5],
                    },
                    "privacy_mode": settings.get("personalization_mode"),
                }
            )
        profile["memory_promotion_log"] = log[-30:]

    @staticmethod
    def _memory_cards_from_turn(
        *,
        turn: dict[str, Any],
        parsed: dict[str, Any],
        allow_natural_summary: bool,
    ) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        timestamp = turn.get("timestamp") or _now()
        category = parsed.get("category")
        sub_category = parsed.get("sub_category")
        for term in parsed.get("positive_constraints", []) or []:
            key = f"feature::{category or 'global'}::{term}"
            summary = f"用户在{category or '全局'}场景关注“{term}”。" if allow_natural_summary else f"semantic_feature:{category or 'global'}:{term}"
            cards.append(_memory_card(key, "preference", category, sub_category, summary, turn, timestamp, confidence=0.62))
        for term in parsed.get("negative_constraints", []) or []:
            key = f"avoid::{category or 'global'}::{term}"
            summary = f"用户在{category or '全局'}场景排除“{term}”。" if allow_natural_summary else f"semantic_avoid:{category or 'global'}:{term}"
            cards.append(_memory_card(key, "avoidance", category, sub_category, summary, turn, timestamp, confidence=0.66))
        price_range = parsed.get("price_range") or {}
        if price_range.get("max") is not None:
            key = f"price::{category or 'global'}::{price_range.get('max')}"
            summary = f"用户在{category or '当前类目'}倾向预算不超过{price_range.get('max'):g}元。" if allow_natural_summary else f"semantic_price:{category or 'global'}:max={price_range.get('max')}"
            cards.append(_memory_card(key, "price_preference", category, sub_category, summary, turn, timestamp, confidence=0.58))
        return cards


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-.]+", "_", value).strip("_") or "unknown"


def _flatten_preferences(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("global_preferences"), dict):
        return payload.get("global_preferences") or {}
    return payload


def _unique_list(*values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        if value in (None, "", []):
            continue
        items = value if isinstance(value, list) else [value]
        for item in items:
            if item in (None, ""):
                continue
            text = str(item)
            if text not in result:
                result.append(text)
    return result


def _inc(counter: dict[str, Any], key: Any, amount: int | float = 1) -> None:
    if key in (None, "", []):
        return
    text = str(key)
    counter[text] = counter.get(text, 0) + amount


def _memory_card(
    key: str,
    card_type: str,
    category: str | None,
    sub_category: str | None,
    summary: str,
    turn: dict[str, Any],
    timestamp: str,
    *,
    confidence: float,
) -> dict[str, Any]:
    return {
        "memory_key": key,
        "type": card_type,
        "scope": {
            "category": category,
            "sub_category": sub_category,
        },
        "summary": summary,
        "confidence": confidence,
        "evidence_count": 1,
        "source_turn_ids": [turn.get("turn_id")],
        "created_at": timestamp,
        "last_seen_at": timestamp,
    }


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
