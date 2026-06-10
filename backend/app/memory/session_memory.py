from app.memory.in_memory_store import InMemoryStore
from app.memory.memory_store import MemoryStore
from datetime import datetime
from typing import Any

from app.models.domain import (
    BehaviourRecord,
    CartStateItem,
    CartEvent,
    ComparisonEvent,
    ConversationTurn,
    MemoryEventRecord,
    ProductBriefRecord,
    ProductDetailEvent,
    ReferenceResolveResult,
    RecommendationRecord,
    RecommendationEvent,
    SessionState,
)


class SessionMemory:
    _rank_aliases = ["一", "二", "三", "四", "五"]

    _PRONOUN_REFS = frozenset({
        "这个", "这款", "这一款", "它", "那个", "那款", "刚才那个", "刚才那款",
    })

    def __init__(self, store: MemoryStore[SessionState] | None = None) -> None:
        self.store = store or InMemoryStore()

    def exists(self, session_id: str) -> bool:
        return self.store.get(session_id) is not None

    def get_or_create(self, session_id: str, user_id: str | None = None) -> SessionState:
        state = self.store.get(session_id)
        if state is None:
            state = SessionState(session_id=session_id, user_id=user_id)
            self.store.save(session_id, state)
        elif user_id and not state.user_id:
            state.user_id = user_id
            self.store.save(session_id, state)
        return state

    def save(self, state: SessionState) -> SessionState:
        self.store.save(state.session_id, state)
        return state

    def replace_state(self, state: SessionState) -> SessionState:
        return self.save(state)

    def attach_user_profile(
        self,
        session_id: str,
        *,
        user_id: str,
        summary_text: str | None,
        structured_profile: dict[str, Any] | None,
    ) -> SessionState:
        state = self.get_or_create(session_id, user_id=user_id)
        state.user_id = user_id
        state.user_profile_summary_text = summary_text
        state.user_profile_structured = structured_profile or {}
        return self.save(state)

    def next_query_id(self, session_id: str) -> str:
        state = self.get_or_create(session_id)
        return f"q{len(state.behaviours) + 1:03d}"

    def append_behaviour(self, session_id: str, behaviour: BehaviourRecord) -> SessionState:
        state = self.get_or_create(session_id)
        state.behaviours.append(behaviour)
        return self.save(state)

    def set_last_recommendations(
        self,
        session_id: str,
        recommendations: list[RecommendationRecord],
    ) -> SessionState:
        return self.record_recommendation_event(
            session_id=session_id,
            query_id=recommendations[0].query_id if recommendations else "unknown",
            source_message="",
            recommendations=recommendations,
        )

    def record_recommendation_event(
        self,
        *,
        session_id: str,
        query_id: str,
        source_message: str,
        recommendations: list[RecommendationRecord],
        category: str | None = None,
        sub_category: str | None = None,
        constraints: dict[str, Any] | None = None,
        recommendation_mode: str = "exact",
        result_status: str = "exact_match",
        unmet_constraints: dict[str, Any] | None = None,
        relaxed_constraints: dict[str, Any] | None = None,
    ) -> SessionState:
        state = self.get_or_create(session_id)
        state.goods.last_recommendations = recommendations
        state.goods.last_candidates = recommendations
        event_id = f"rec_{len(state.event_memory.recommendation_events) + 1:03d}"
        rank_to_sku = self._build_rank_to_sku(recommendations)
        products = [
            ProductBriefRecord(
                rank=item.rank,
                sku_id=item.sku_id,
                name=item.name,
                category=item.category,
                price=item.price,
                reason=item.reason,
            )
            for item in recommendations
        ]
        event = RecommendationEvent(
            event_id=event_id,
            query_id=query_id,
            turn_id=len(state.behaviours) + 1,
            source_message=source_message,
            category=category,
            sub_category=sub_category,
            rank_to_sku=rank_to_sku,
            products=products,
            recommendation_mode=recommendation_mode,
            result_status=result_status,
            unmet_constraints=unmet_constraints or {},
            relaxed_constraints=relaxed_constraints or {},
            constraints=constraints or {},
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        state.event_memory.recommendation_events.append(event)
        state.event_memory.recommendation_events = state.event_memory.recommendation_events[-20:]
        state.event_memory.active_recommendation_event_id = event_id
        state.event_memory.active_detail_sku_id = None
        self._append_memory_event_to_state(
            state,
            MemoryEventRecord(
                event_id=event_id,
                event_type="recommendation",
                turn_id=event.turn_id,
                timestamp=event.created_at,
                user_query=source_message,
                category=category,
                constraints=constraints or {},
                related_product_ids=[item.sku_id for item in recommendations],
                payload={
                    "recommendation_mode": recommendation_mode,
                    "result_status": result_status,
                    "unmet_constraints": unmet_constraints or {},
                    "relaxed_constraints": relaxed_constraints or {},
                    "products": [item.model_dump() for item in products],
                    "rank_to_sku": self._numeric_rank_to_sku(recommendations),
                    "reference_alias_to_sku": rank_to_sku,
                },
            ),
        )
        state.dialogue_state_tracking.resolved_references = self.build_reference_map(state)
        return self.save(state)

    def record_product_detail_event(
        self,
        *,
        session_id: str,
        query_id: str,
        source_message: str,
        sku_id: str,
        target_ref: str | None = None,
        source_event_id: str | None = None,
        source_rank: int | None = None,
    ) -> SessionState:
        state = self.get_or_create(session_id)
        source_event = self.find_source_recommendation_event(state, source_event_id)
        source_event_id = source_event_id or (source_event.event_id if source_event else None)
        source_rank = source_rank if source_rank is not None else self._rank_for_sku(source_event, sku_id)
        event_id = f"detail_{len(state.event_memory.product_detail_events) + 1:03d}"
        created_at = datetime.now().isoformat(timespec="seconds")
        state.event_memory.product_detail_events.append(
            ProductDetailEvent(
                event_id=event_id,
                query_id=query_id,
                turn_id=len(state.behaviours) + 1,
                source_message=source_message,
                sku_id=sku_id,
                target_ref=target_ref,
                source_event_id=source_event_id,
                source_rank=source_rank,
                created_at=created_at,
            )
        )
        state.event_memory.product_detail_events = state.event_memory.product_detail_events[-30:]
        state.event_memory.active_detail_sku_id = sku_id
        if sku_id not in state.goods.viewed_skus:
            state.goods.viewed_skus.append(sku_id)
            state.goods.viewed_skus = state.goods.viewed_skus[-50:]
        self._append_memory_event_to_state(
            state,
            MemoryEventRecord(
                event_id=event_id,
                event_type="product_detail",
                turn_id=len(state.behaviours) + 1,
                timestamp=created_at,
                user_query=source_message,
                source_event_id=source_event_id,
                category=source_event.category if source_event else None,
                related_product_ids=[sku_id],
                payload={
                    "sku_id": sku_id,
                    "source_rank": source_rank,
                    "target_ref": target_ref,
                },
            ),
        )
        state.dialogue_state_tracking.resolved_references = self.build_reference_map(state)
        return self.save(state)

    def record_comparison_event(
        self,
        *,
        session_id: str,
        query_id: str,
        source_message: str,
        sku_ids: list[str],
        references: list[str] | None = None,
        resolved_references: dict[str, str] | None = None,
        comparison_dimensions: list[str] | None = None,
        source_event_id: str | None = None,
    ) -> SessionState:
        state = self.get_or_create(session_id)
        if not sku_ids:
            return self.save(state)
        event_id = f"cmp_{len(state.event_memory.comparison_events) + 1:03d}"
        unique_skus = list(dict.fromkeys(sku_ids))
        source_event = self.find_source_recommendation_event(state, source_event_id)
        source_event_id = source_event_id or (source_event.event_id if source_event else None)
        created_at = datetime.now().isoformat(timespec="seconds")
        state.event_memory.comparison_events.append(
            ComparisonEvent(
                event_id=event_id,
                query_id=query_id,
                turn_id=len(state.behaviours) + 1,
                source_message=source_message,
                sku_ids=unique_skus,
                references=references or [],
                resolved_references=resolved_references or {},
                comparison_dimensions=comparison_dimensions or [],
                source_event_id=source_event_id,
                created_at=created_at,
            )
        )
        state.event_memory.comparison_events = state.event_memory.comparison_events[-20:]
        state.event_memory.active_comparison_event_id = event_id
        state.goods.compared_skus = unique_skus
        self._append_memory_event_to_state(
            state,
            MemoryEventRecord(
                event_id=event_id,
                event_type="comparison",
                turn_id=len(state.behaviours) + 1,
                timestamp=created_at,
                user_query=source_message,
                source_event_id=source_event_id,
                category=source_event.category if source_event else None,
                related_product_ids=unique_skus,
                payload={
                    "references": references or [],
                    "resolved_references": resolved_references or {},
                    "comparison_dimensions": comparison_dimensions or [],
                },
            ),
        )
        state.dialogue_state_tracking.resolved_references = self.build_reference_map(state)
        return self.save(state)

    def record_cart_event(
        self,
        *,
        session_id: str,
        query_id: str,
        source_message: str,
        action: str,
        sku_ids: list[str],
        quantity: int | None = None,
        target_ref: str | None = None,
        source_event_id: str | None = None,
        tool_result: dict[str, Any] | None = None,
    ) -> SessionState:
        state = self.get_or_create(session_id)
        event_id = f"cart_{len(state.event_memory.cart_events) + 1:03d}"
        unique_skus = list(dict.fromkeys(sku_ids))
        source_event = self.find_source_recommendation_event(state, source_event_id)
        source_event_id = source_event_id or (source_event.event_id if source_event else None)
        created_at = datetime.now().isoformat(timespec="seconds")
        state.event_memory.cart_events.append(
            CartEvent(
                event_id=event_id,
                query_id=query_id,
                turn_id=len(state.behaviours) + 1,
                source_message=source_message,
                action=action,
                sku_ids=unique_skus,
                quantity=quantity,
                target_ref=target_ref,
                source_event_id=source_event_id,
                tool_result=tool_result or {},
                created_at=created_at,
            )
        )
        state.event_memory.cart_events = state.event_memory.cart_events[-30:]
        if unique_skus:
            state.event_memory.active_cart_sku_id = unique_skus[0]
        self._append_memory_event_to_state(
            state,
            MemoryEventRecord(
                event_id=event_id,
                event_type="cart_action",
                turn_id=len(state.behaviours) + 1,
                timestamp=created_at,
                user_query=source_message,
                source_event_id=source_event_id,
                category=source_event.category if source_event else None,
                related_product_ids=unique_skus,
                payload={
                    "action": action,
                    "sku_ids": unique_skus,
                    "quantity": quantity,
                    "target_ref": target_ref,
                    "tool_result": tool_result or {},
                },
            ),
        )
        state.dialogue_state_tracking.resolved_references = self.build_reference_map(state)
        return self.save(state)

    def update_dialogue_state(
        self,
        session_id: str,
        *,
        current_intent: str,
        current_category: str | None,
        slots: dict,
        missing_slots: list[str],
        current_flow: str | None = None,
        current_sub_category: str | None = None,
        active_constraints: dict[str, Any] | None = None,
        task_plan: list[str] | None = None,
    ) -> SessionState:
        state = self.get_or_create(session_id)
        state.dialogue_state_tracking.current_intent = current_intent
        if current_flow is not None:
            state.dialogue_state_tracking.current_flow = current_flow
        state.dialogue_state_tracking.current_category = current_category
        state.dialogue_state_tracking.current_sub_category = current_sub_category
        state.dialogue_state_tracking.slots = slots
        if active_constraints is not None:
            state.dialogue_state_tracking.active_constraints = active_constraints
        state.dialogue_state_tracking.missing_slots = missing_slots
        if task_plan is not None:
            state.dialogue_state_tracking.last_task_plan = task_plan
        return self.save(state)

    def append_message(self, session_id: str, role: str, content: str) -> SessionState:
        state = self.get_or_create(session_id)
        state.recent_messages.append(
            ConversationTurn(
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(timespec="seconds"),
            )
        )
        state.recent_messages = state.recent_messages[-12:]
        return self.save(state)

    def sync_cart(
        self,
        session_id: str,
        *,
        items: list[CartStateItem],
        last_updated_by: str,
    ) -> SessionState:
        state = self.get_or_create(session_id)
        state.cart.items = items
        state.cart.last_updated_by = last_updated_by
        return self.save(state)

    def append_trace(self, session_id: str, trace: dict) -> SessionState:
        state = self.get_or_create(session_id)
        state.dialogue_state_tracking.last_trace = trace
        state.trace_log.append(trace)
        state.trace_log = state.trace_log[-30:]
        return self.save(state)

    def update_model_route(self, session_id: str, route: dict) -> SessionState:
        state = self.get_or_create(session_id)
        state.dialogue_state_tracking.last_model_route = route
        return self.save(state)

    def append_memory_event(
        self,
        session_id: str,
        event: MemoryEventRecord,
        max_events: int = 50,
    ) -> SessionState:
        state = self.get_or_create(session_id)
        self._append_memory_event_to_state(state, event, max_events=max_events)
        return self.save(state)

    @staticmethod
    def get_event_by_id(state: SessionState, event_id: str | None) -> MemoryEventRecord | None:
        if not event_id:
            return None
        for event in reversed(state.memory_events):
            if event.event_id == event_id:
                return event
        return None

    @staticmethod
    def latest_event(state: SessionState, event_type: str | None = None) -> MemoryEventRecord | None:
        for event in reversed(state.memory_events):
            if event_type is None or event.event_type == event_type:
                return event
        return None

    def _iter_recommendation_events(
        self, state: SessionState, max_events: int = 10,
    ) -> list[MemoryEventRecord]:
        """Return recommendation events from memory_events, newest first."""
        return [
            ev for ev in reversed(state.memory_events)
            if ev.event_type == "recommendation"
        ][:max_events]

    @staticmethod
    def _event_products_match_query(event: MemoryEventRecord, query: str) -> bool:
        """Check whether *query* contains Chinese text that appears in any product name."""
        products = (event.payload or {}).get("products", [])
        if not products:
            return False
        for product in products:
            if isinstance(product, dict):
                name = product.get("name", "")
                if not name:
                    continue
                if name in query:
                    return True
                chinese_chars = "".join(c for c in name if "一" <= c <= "鿿")
                if chinese_chars and len(chinese_chars) >= 2 and chinese_chars in query:
                    return True
        return False

    def latest_recommendation_event(self, state: SessionState) -> MemoryEventRecord | None:
        event = self.latest_event(state, "recommendation")
        if event is not None:
            return event
        typed = self._active_recommendation_event(state)
        if typed is None:
            return None
        return self._memory_event_from_typed_recommendation(typed)

    def find_source_recommendation_event(
        self,
        state: SessionState,
        source_event_id: str | None = None,
    ) -> MemoryEventRecord | None:
        if source_event_id:
            event = self.get_event_by_id(state, source_event_id)
            if event and event.event_type == "recommendation":
                return event
        return self.latest_recommendation_event(state)

    def resolve_reference_from_memory_events(
        self,
        state: SessionState,
        user_query: str,
        references: list[str] | None = None,
    ) -> ReferenceResolveResult:
        reference_texts = references or self._references_in_text(user_query)
        resolved: dict[str, str] = {}
        source_event_id: str | None = None

        all_rec_events = self._iter_recommendation_events(state)
        if not all_rec_events:
            return ReferenceResolveResult(reference_texts=reference_texts, source="failed")

        # Separate events into those whose product names match the user query
        # and those that do not.  "刚才第二款面霜" will match an event whose
        # products contain "面霜" and will be tried first.
        matched: list[MemoryEventRecord] = []
        unmatched: list[MemoryEventRecord] = []
        for event in all_rec_events:
            if self._event_products_match_query(event, user_query):
                matched.append(event)
            else:
                unmatched.append(event)

        # Try rank references against matching events first, then all others.
        for events_batch in [matched, unmatched]:
            if not events_batch:
                continue
            for rec_event in events_batch:
                rank_map = self._rank_map_from_memory_event(rec_event)
                for ref in reference_texts:
                    if ref in resolved:
                        continue
                    sku_id = self._resolve_rank_reference(ref, rank_map)
                    if sku_id:
                        resolved[ref] = sku_id
                        source_event_id = rec_event.event_id
                if resolved:
                    break
            if resolved:
                break

        if resolved:
            return ReferenceResolveResult(
                resolved=resolved,
                product_ids=list(dict.fromkeys(resolved.values())),
                source_event_id=source_event_id,
                source="memory_events",
                reference_texts=list(resolved.keys()),
                confidence=0.98,
            )

        pronoun_refs = [ref for ref in reference_texts if ref in self._PRONOUN_REFS]
        if pronoun_refs:
            sku_id = state.event_memory.active_detail_sku_id
            if sku_id:
                for ref in pronoun_refs:
                    resolved[ref] = sku_id
                return ReferenceResolveResult(
                    resolved=resolved,
                    product_ids=[sku_id],
                    source_event_id=None,
                    source="memory_events",
                    reference_texts=pronoun_refs,
                    confidence=0.86,
                )
            for event in reversed(state.memory_events):
                if event.related_product_ids:
                    sku_id = event.related_product_ids[0]
                    for ref in pronoun_refs:
                        resolved[ref] = sku_id
                    return ReferenceResolveResult(
                        resolved=resolved,
                        product_ids=[sku_id],
                        source_event_id=event.event_id,
                        source="memory_events",
                        reference_texts=pronoun_refs,
                        confidence=0.86,
                    )

        return ReferenceResolveResult(reference_texts=reference_texts, source="failed")

    def _build_resolved_references(
        self,
        recommendations: list[RecommendationRecord],
    ) -> dict[str, str]:
        references: dict[str, str] = {}
        for recommendation in recommendations:
            rank = recommendation.rank
            chinese_rank = self._rank_aliases[rank - 1] if 0 < rank <= len(self._rank_aliases) else str(rank)
            references[f"第{rank}个"] = recommendation.sku_id
            references[f"第{rank}款"] = recommendation.sku_id
            references[f"第{chinese_rank}个"] = recommendation.sku_id
            references[f"第{chinese_rank}款"] = recommendation.sku_id

        if recommendations:
            latest = recommendations[0]
            references["刚才那款"] = latest.sku_id
            references["刚才那个"] = latest.sku_id
            references["这个"] = latest.sku_id
            references["这款"] = latest.sku_id
            references["它"] = latest.sku_id

        return references

    def refresh_references(self, session_id: str) -> SessionState:
        state = self.get_or_create(session_id)
        state.dialogue_state_tracking.resolved_references = self.build_reference_map(state)
        return self.save(state)

    def resolve_reference(self, session_id: str, ref: str | None) -> str | None:
        if not ref:
            return None
        state = self.get_or_create(session_id)
        state.dialogue_state_tracking.resolved_references = self.build_reference_map(state)
        sku_id = state.dialogue_state_tracking.resolved_references.get(ref)
        if sku_id is None:
            sku_id = state.dialogue_state_tracking.resolved_references.get(ref.strip())
        self.save(state)
        return sku_id

    def build_reference_map(self, state: SessionState) -> dict[str, str]:
        references: dict[str, str] = {}

        # Accumulate rank aliases from multiple recent recommendation events.
        # Newer events take priority via setdefault; older events fill gaps.
        for rec_event in self._iter_recommendation_events(state, max_events=5):
            rank_map = self._rank_map_from_memory_event(rec_event)
            for alias, sku_id in rank_map.items():
                references.setdefault(alias, sku_id)

        active_recommendation = self._active_recommendation_event(state)
        if active_recommendation is not None:
            for key, sku_id in active_recommendation.rank_to_sku.items():
                references.setdefault(key, sku_id)
            for product in active_recommendation.products:
                if product.rank is None:
                    continue
                for alias in self._rank_reference_aliases(product.rank):
                    references.setdefault(alias, product.sku_id)
                    references.setdefault(f"刚才推荐的{alias}", product.sku_id)
                    references.setdefault(f"上次推荐的{alias}", product.sku_id)
                    references.setdefault(f"推荐列表{alias}", product.sku_id)
                    references.setdefault(f"备选里的{alias}", product.sku_id)

        if not references and state.goods.last_recommendations:
            references.update(self._build_resolved_references(state.goods.last_recommendations))

        detail_sku = state.event_memory.active_detail_sku_id
        cart_sku = state.event_memory.active_cart_sku_id
        first_recommended_sku = None
        if active_recommendation and active_recommendation.products:
            first_recommended_sku = active_recommendation.products[0].sku_id
        elif state.goods.last_recommendations:
            first_recommended_sku = state.goods.last_recommendations[0].sku_id

        if detail_sku:
            for alias in ["这个", "这款", "这一款", "它", "当前这个", "当前这款", "刚才介绍的", "刚才看的", "刚才这款"]:
                references[alias] = detail_sku
        elif first_recommended_sku:
            for alias in ["这个", "这款", "这一款", "它", "刚才那款", "刚才那个", "前面那款", "前面那个"]:
                references[alias] = first_recommended_sku

        if cart_sku:
            for alias in ["刚才加购的", "刚才加到购物车的", "购物车里的那个", "购物车里那个", "刚才买的"]:
                references[alias] = cart_sku

        if state.goods.compared_skus:
            for index, sku_id in enumerate(state.goods.compared_skus, start=1):
                for alias in self._rank_reference_aliases(index):
                    references[f"对比的{alias}"] = sku_id
                    references[f"刚才对比的{alias}"] = sku_id
            if len(state.goods.compared_skus) == 1:
                references["刚才对比的那款"] = state.goods.compared_skus[0]

        return references

    @staticmethod
    def _append_memory_event_to_state(
        state: SessionState,
        event: MemoryEventRecord,
        max_events: int = 50,
    ) -> None:
        state.memory_events = [item for item in state.memory_events if item.event_id != event.event_id]
        state.memory_events.append(event)
        state.memory_events = state.memory_events[-max_events:]

    def _active_recommendation_event(self, state: SessionState) -> RecommendationEvent | None:
        active_id = state.event_memory.active_recommendation_event_id
        if active_id:
            for event in reversed(state.event_memory.recommendation_events):
                if event.event_id == active_id:
                    return event
        return state.event_memory.recommendation_events[-1] if state.event_memory.recommendation_events else None

    def _build_rank_to_sku(self, recommendations: list[RecommendationRecord]) -> dict[str, str]:
        rank_to_sku: dict[str, str] = {}
        for recommendation in recommendations:
            for alias in self._rank_reference_aliases(recommendation.rank):
                rank_to_sku[alias] = recommendation.sku_id
        return rank_to_sku

    @staticmethod
    def _numeric_rank_to_sku(recommendations: list[RecommendationRecord]) -> dict[str, str]:
        return {str(item.rank): item.sku_id for item in recommendations}

    def _memory_event_from_typed_recommendation(self, event: RecommendationEvent) -> MemoryEventRecord:
        return MemoryEventRecord(
            event_id=event.event_id,
            event_type="recommendation",
            turn_id=event.turn_id,
            timestamp=event.created_at,
            user_query=event.source_message,
            category=event.category,
            constraints=event.constraints,
            related_product_ids=[item.sku_id for item in event.products],
            payload={
                "recommendation_mode": event.recommendation_mode,
                "result_status": event.result_status,
                "unmet_constraints": event.unmet_constraints,
                "relaxed_constraints": event.relaxed_constraints,
                "products": [item.model_dump() for item in event.products],
                "rank_to_sku": {str(item.rank): item.sku_id for item in event.products if item.rank is not None},
                "reference_alias_to_sku": event.rank_to_sku,
            },
        )

    def _rank_map_from_memory_event(self, event: MemoryEventRecord | None) -> dict[str, str]:
        if event is None:
            return {}
        payload = event.payload or {}
        rank_map: dict[str, str] = {}
        raw_rank_map = payload.get("rank_to_sku") or payload.get("rank_to_product_id") or {}
        if isinstance(raw_rank_map, dict):
            for rank_text, sku_id in raw_rank_map.items():
                if not sku_id:
                    continue
                rank = _rank_to_int(str(rank_text))
                if rank is not None:
                    for alias in self._rank_reference_aliases(rank):
                        rank_map[alias] = str(sku_id)
                        rank_map[f"备选里的{alias}"] = str(sku_id)
                        rank_map[f"推荐里的{alias}"] = str(sku_id)
                rank_map[str(rank_text)] = str(sku_id)
        alias_map = payload.get("reference_alias_to_sku") or {}
        if isinstance(alias_map, dict):
            rank_map.update({str(key): str(value) for key, value in alias_map.items() if value})
        return rank_map

    @staticmethod
    def _resolve_rank_reference(ref: str, rank_map: dict[str, str]) -> str | None:
        if ref in rank_map:
            return rank_map[ref]
        compact = ref.replace(" ", "")
        if compact in rank_map:
            return rank_map[compact]
        match = _rank_reference_pattern(compact)
        if match and match in rank_map:
            return rank_map[match]
        return None

    @staticmethod
    def _rank_for_sku(event: MemoryEventRecord | None, sku_id: str) -> int | None:
        if event is None:
            return None
        rank_to_sku = event.payload.get("rank_to_sku", {}) if isinstance(event.payload, dict) else {}
        if not isinstance(rank_to_sku, dict):
            return None
        for rank, event_sku in rank_to_sku.items():
            if event_sku == sku_id:
                return _rank_to_int(str(rank))
        return None

    def _references_in_text(self, text: str) -> list[str]:
        refs: list[tuple[int, str]] = []
        compact = text.replace(" ", "")
        for rank in range(1, 10):
            for alias in self._rank_reference_aliases(rank):
                for candidate in [alias, f"备选里的{alias}", f"推荐里的{alias}"]:
                    position = compact.find(candidate)
                    if position >= 0:
                        refs.append((position, candidate))
        for alias in ["这个", "这款", "这一款", "它", "那个", "那款", "刚才那个", "刚才那款"]:
            position = compact.find(alias)
            if position >= 0:
                refs.append((position, alias))
        refs.sort(key=lambda item: item[0])
        return list(dict.fromkeys(ref for _, ref in refs))

    def _rank_reference_aliases(self, rank: int) -> list[str]:
        chinese_rank = self._rank_aliases[rank - 1] if 0 < rank <= len(self._rank_aliases) else str(rank)
        return [
            f"第{rank}个",
            f"第{rank}款",
            f"第{rank}件",
            f"第{chinese_rank}个",
            f"第{chinese_rank}款",
            f"第{chinese_rank}件",
            f"{chinese_rank}号",
            f"{rank}号",
        ]


def _rank_to_int(text: str) -> int | None:
    compact = text.strip().replace("第", "").replace("个", "").replace("款", "").replace("件", "").replace("号", "")
    if compact.isdigit():
        return int(compact)
    mapping = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    return mapping.get(compact)


def _rank_reference_pattern(text: str) -> str | None:
    for rank in range(1, 10):
        chinese = SessionMemory._rank_aliases[rank - 1] if rank <= len(SessionMemory._rank_aliases) else str(rank)
        candidates = {
            f"第{rank}个",
            f"第{rank}款",
            f"第{rank}件",
            f"第{chinese}个",
            f"第{chinese}款",
            f"第{chinese}件",
            f"备选里的第{rank}个",
            f"备选里的第{rank}款",
            f"备选里的第{chinese}个",
            f"备选里的第{chinese}款",
            f"推荐里的第{rank}个",
            f"推荐里的第{chinese}个",
        }
        if text in candidates:
            return f"第{rank}个"
    return None
