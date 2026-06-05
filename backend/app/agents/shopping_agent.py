import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
import traceback as _traceback

from app.retrieval.fallback import RetrievalFallback, FallbackResult
from app.agents.closing_guide import ClosingGuide
from time import perf_counter

from app.agents.dialogue_flow import DialogueFlowController
from app.agents.frontend_action_planner import FrontendActionPlanner
from app.agents.frontend_event_builder import FrontendEventBuilder
from app.agents.input_preprocessor import InputPreprocessor
from app.agents.model_router import ModelRouter
from app.agents.product_qa import ProductQAModule
from app.agents.query_understanding import QueryUnderstandingModule
from app.agents.response_generator import ResponseGenerationModule
from app.agents.scene_presentation_builder import ScenePresentationBuilder
from app.agents.response_validator import ResponseValidator
from app.agents.scenario_planner import ScenarioPlanner
from app.agents.task_planner import TaskPlanner
from app.memory.preference_manager import PreferenceManager
from app.memory.cart_aware_personalization import CartAwarePersonalization
from app.memory.personalization_service import PersonalizationService
from app.memory.session_memory import SessionMemory
from app.memory.user_history_store import UserHistoryStore
from app.memory.user_profile_service import UserProfileService
from app.multimodal.multimodal_service import MultimodalService
from app.models.agent import (
    AgentTrace,
    CartAction,
    CandidateProduct,
    DialogueFlow,
    FlowDecision,
    IntentStep,
    ModelRouteDecision,
    ParsedQuery,
    PriceRange,
    PreferenceUpdateResult,
    ProductQAResult,
    ScenePlan,
    ToolExecutionResult,
    ValidationResult,
)
from app.models.domain import BehaviourRecord, IntentType, Product, ProductCard, SessionState
from app.models.events import SSEEvent
from app.progress.progress_event_builder import ProgressEventBuilder
from app.repositories.product_repository import ProductRepository
from app.retrieval.post_processor import ProductPostProcessor
from app.tools.action_executor import ActionExecutor
from app.tools.product_search_tool import ProductSearchTool
from app.utils.runtime_timer import RuntimeTimer


class ShoppingAgent:
    """Task-oriented RAG shopping agent orchestration entry point."""

    def __init__(
        self,
        input_preprocessor: InputPreprocessor,
        query_understanding: QueryUnderstandingModule,
        model_router: ModelRouter,
        flow_controller: DialogueFlowController,
        task_planner: TaskPlanner,
        session_memory: SessionMemory,
        product_repository: ProductRepository,
        product_search_tool: ProductSearchTool,
        post_processor: ProductPostProcessor,
        action_executor: ActionExecutor,
        preference_manager: PreferenceManager,
        product_qa_module: ProductQAModule,
        scenario_planner: ScenarioPlanner,
        response_generator: ResponseGenerationModule,
        response_validator: ResponseValidator,
        scene_presentation_builder: ScenePresentationBuilder,
        frontend_action_planner: FrontendActionPlanner,
        frontend_event_builder: FrontendEventBuilder,
        user_history_store: UserHistoryStore,
        user_profile_service: UserProfileService,
        personalization_service: PersonalizationService,
        multimodal_service: MultimodalService,
        progress_event_builder: ProgressEventBuilder,
        cart_aware_personalization: CartAwarePersonalization,
    ) -> None:
        self.input_preprocessor = input_preprocessor
        self.query_understanding = query_understanding
        self.model_router = model_router
        self.flow_controller = flow_controller
        self.task_planner = task_planner
        self.session_memory = session_memory
        self.product_repository = product_repository
        self.product_search_tool = product_search_tool
        self.post_processor = post_processor
        self.action_executor = action_executor
        self.preference_manager = preference_manager
        self.product_qa_module = product_qa_module
        self.scenario_planner = scenario_planner
        self.response_generator = response_generator
        self.response_validator = response_validator
        self.scene_presentation_builder = scene_presentation_builder
        self.frontend_action_planner = frontend_action_planner
        self.frontend_event_builder = frontend_event_builder
        self.user_history_store = user_history_store
        self.user_profile_service = user_profile_service
        self.personalization_service = personalization_service
        self.multimodal_service = multimodal_service
        self.progress_event_builder = progress_event_builder
        self.cart_aware_personalization = cart_aware_personalization

    async def stream_chat(
        self,
        session_id: str,
        message: str,
        user_id: str | None = None,
        input_type: str = "text",
        resume: bool = False,
        new_session: bool = False,
        metadata: dict | None = None,
    ) -> AsyncIterator[SSEEvent]:
        metadata = dict(metadata or {})
        effective_user_id = user_id or metadata.get("user_id") or session_id
        progress_plan = self.progress_event_builder.build_parallel(
            message=message,
            input_type=input_type,
            is_old_user=self._is_old_user_for_progress(
                user_id=effective_user_id,
                resume=resume,
                new_session=new_session,
            ),
        )
        metadata["_external_progress_plan"] = progress_plan
        metadata["_disable_core_progress_yield"] = True

        queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        request_start = perf_counter()

        def run_core() -> None:
            async def pump() -> None:
                try:
                    async for event in self._stream_chat_core(
                        session_id=session_id,
                        message=message,
                        user_id=user_id,
                        input_type=input_type,
                        resume=resume,
                        new_session=new_session,
                        metadata=metadata,
                    ):
                        loop.call_soon_threadsafe(queue.put_nowait, event)
                except Exception as exc:
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        SSEEvent(event="turn_result", data=_minimal_error_turn_output(session_id, effective_user_id, exc)),
                    )
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        SSEEvent(event="error", data={"message": "系统处理时遇到问题，请稍后重试。", "code": "AGENT_ERROR"}),
                    )
                    loop.call_soon_threadsafe(queue.put_nowait, SSEEvent(event="done", data={"finish_reason": "error"}))
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            asyncio.run(pump())

        core_task = asyncio.create_task(asyncio.to_thread(run_core))
        progress_events = list(progress_plan.get("events", []))
        progress_interval = max(float(progress_plan.get("progress输出间隔_ms") or 700) / 1000.0, 0.25)
        progress_index = 0
        progress_stopped = False
        next_progress_at = perf_counter()

        try:
            while True:
                now = perf_counter()
                if (
                    not progress_stopped
                    and progress_index < len(progress_events)
                    and now >= next_progress_at
                ):
                    event = progress_events[progress_index]
                    progress_index += 1
                    if progress_plan.get("首条progress输出耗时_ms") is None:
                        progress_plan["首条progress输出耗时_ms"] = round((perf_counter() - request_start) * 1000, 2)
                    progress_plan["已输出数量"] = progress_index
                    yield SSEEvent(event="progress", data=event)
                    await asyncio.sleep(0)
                    next_progress_at = perf_counter() + progress_interval

                timeout = 0.05
                if not progress_stopped and progress_index < len(progress_events):
                    timeout = max(min(next_progress_at - perf_counter(), 0.2), 0.02)
                try:
                    backend_event = await asyncio.wait_for(queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    continue

                if backend_event is None:
                    progress_plan.setdefault("停止原因", "主流程结束")
                    break

                if backend_event.event == "progress":
                    continue

                if not progress_stopped and backend_event.event != "state":
                    progress_stopped = True
                    progress_plan["停止原因"] = "正式结果已开始输出"
                    progress_plan["progress停止耗时_ms"] = round((perf_counter() - request_start) * 1000, 2)

                yield backend_event
                if backend_event.event == "done":
                    break
        finally:
            progress_plan.setdefault("停止原因", "请求结束")
            progress_plan["最终主流程耗时_ms"] = round((perf_counter() - request_start) * 1000, 2)
            if not core_task.done():
                core_task.cancel()
            try:
                await core_task
            except asyncio.CancelledError:
                pass

    async def _stream_chat_core(
        self,
        session_id: str,
        message: str,
        user_id: str | None = None,
        input_type: str = "text",
        resume: bool = False,
        new_session: bool = False,
        metadata: dict | None = None,
    ) -> AsyncIterator[SSEEvent]:
        timer = RuntimeTimer()
        metadata = metadata or {}
        effective_user_id = user_id or metadata.get("user_id") or session_id
        with timer.measure("privacy_preferences", "读取并应用隐私/个性化设置"):
            privacy_update = self.user_history_store.apply_privacy_preferences(
                user_id=effective_user_id,
                message=message,
                metadata=metadata,
            )
        privacy_only = bool(privacy_update.get("updated")) and self._is_privacy_only_message(message)
        restored_from_session_id = None
        history_restored = False
        with timer.measure("history_restore", "按需从本地历史恢复会话"):
            should_restore_history = False
            if resume and not new_session:
                if not self.session_memory.exists(session_id):
                    should_restore_history = True
                else:
                    existing_state = self.session_memory.get_or_create(session_id, user_id=effective_user_id)
                    should_restore_history = self._is_blank_resume_state(existing_state)
            if should_restore_history:
                restored_state, restored_from_session_id = self.user_history_store.restore_state(
                    user_id=effective_user_id,
                    source_session_id=metadata.get("resume_session_id"),
                    target_session_id=session_id,
                )
                if restored_state is not None:
                    self.session_memory.replace_state(restored_state)
                    history_restored = True

        with timer.measure("memory_read", "读取当前会话状态、用户画像和购物车"):
            state = self.session_memory.get_or_create(session_id, user_id=effective_user_id)
            profile = self.user_history_store.load_profile(effective_user_id)
            state = self.session_memory.attach_user_profile(
                session_id,
                user_id=effective_user_id,
                summary_text=profile.get("profile_summary_text"),
                structured_profile=profile.get("structured_profile") or {},
            )
            state_before_snapshot = self._state_debug_snapshot(state)
            query_id = self.session_memory.next_query_id(session_id)
            flow_before = state.dialogue_state_tracking.current_flow
        with timer.measure("input_preprocess", "输入预处理与简单路由"):
            preprocess = self.input_preprocessor.preprocess(
                message=message,
                input_type=input_type,
                state=state,
            )

        trace = AgentTrace(
            session_id=session_id,
            query_id=query_id,
            raw_query=message,
            normalized_query=preprocess.normalized_message,
            flow_before=flow_before,
            memory_read_keys=["recent_messages", "dialogue_state", "cart", "user_preferences"],
        )

        with timer.measure("progress_events_build_fast", "本地快速生成前端 progress events"):
            external_progress_plan = metadata.get("_external_progress_plan")
            if isinstance(external_progress_plan, dict):
                progress_plan = external_progress_plan
                progress_plan["核心流程复用外部progress"] = True
                progress_plan.setdefault("首次progress生成耗时_ms", progress_plan.get("首条progress输出耗时_ms"))
            else:
                progress_plan = self.progress_event_builder.build_fast(
                    message=preprocess.normalized_message,
                    state=state,
                    input_type=input_type,
                )
                progress_plan["首次progress生成耗时_ms"] = timer.elapsed_ms()
        trace.progress_plan = progress_plan
        if not metadata.get("_disable_core_progress_yield"):
            for progress_event in progress_plan.get("events", []):
                yield SSEEvent(event="progress", data=progress_event)
                trace.legacy_sse_events.append("progress")

        multimodal_context: dict = {}
        with timer.measure("query_understanding", "意图理解、约束抽取和 IntentPlan 解析"):
            parsed_query = self._build_simple_parsed_query(preprocess) if preprocess.simple_route else self.query_understanding.parse(
                message=preprocess.normalized_message,
                state=state,
            )
        if "doubao" in parsed_query.route_source:
            timer.mark_model_call(
                module="query_understanding",
                provider=self.response_generator.llm_client.__class__.__name__,
                purpose="intent_plan_resolution",
                duration_ms=timer.last_duration("query_understanding"),
                call_debug=self._llm_call_debug(),
            )
        with timer.measure("multimodal_processing", "多模态输入处理"):
            multimodal_context = self.multimodal_service.process(
                input_type=input_type,
                message=preprocess.normalized_message,
                metadata=metadata,
            )
            if multimodal_context.get("是否启用多模态"):
                self._apply_multimodal_context(parsed_query, multimodal_context)
        with timer.measure("context_merge", "多轮上下文与当前约束合并"):
            mixed_retrieval_step = self._last_retrieval_step(parsed_query) if self._has_mixed_intent_plan(parsed_query) else None
            if mixed_retrieval_step is not None:
                self._apply_retrieval_step_to_query(parsed_query, mixed_retrieval_step, state)
            self._merge_context_constraints(parsed_query, state)
        with timer.measure("reference_resolution", "事件记忆和旧引用缓存指代解析"):
            state, reference_resolution = self._resolve_event_references(session_id, parsed_query, state)
        trace.reference_resolution = reference_resolution
        self._promote_ellipsis_reference_intent(parsed_query)
        if parsed_query.inherit_context and parsed_query.category:
            parsed_query.need_clarification = False
            parsed_query.clarification_slots = []
        with timer.measure("flow_control", "对话流程状态机决策"):
            decision = self._simple_flow_decision(preprocess, parsed_query) if preprocess.simple_route else self.flow_controller.decide(parsed=parsed_query, state=state)
        if privacy_only:
            parsed_query.intent = IntentType.PREFERENCE.value
            parsed_query.route_source = f"{parsed_query.route_source}+privacy_control"
            decision = FlowDecision(
                flow=DialogueFlow.PREFERENCE_UPDATE,
                reason="用户更新隐私和个性化设置",
                need_retrieval=False,
                need_llm=False,
            )
        if self._multimodal_target_is_unsupported(multimodal_context):
            decision = FlowDecision(
                flow=DialogueFlow.NO_RESULT,
                reason="图片目标类目当前库存不覆盖",
                need_retrieval=False,
                need_llm=True,
            )

        # ---- 闭环引导：用户拒绝/接受结算邀请 ----
        # 拒绝信号必须优先处理；例如“先不结算，我再看看”同时包含“结算”和“先不”，
        # 不能因为命中 checkout 词就直接生成订单。
        with timer.measure("closing_accept_check", "检测用户是否接受了闭环结算引导"):
            if self._is_closing_decline(parsed_query, state):
                current_turn = len(state.recent_messages) // 2
                if not hasattr(state, 'checkout_guidance') or state.checkout_guidance is None:
                    state.checkout_guidance = {}
                state.checkout_guidance['declined_at_turn'] = current_turn
                parsed_query.intent = IntentType.CHITCHAT.value
                parsed_query.route_source = f"{parsed_query.route_source}+closing_decline"
                decision = FlowDecision(
                    flow=DialogueFlow.CHITCHAT,
                    reason="用户拒绝或延后闭环结算引导",
                    need_retrieval=False,
                    need_llm=True,
                )
            elif self._is_closing_acceptance(parsed_query, state, decision):
                parsed_query.intent = IntentType.CHECKOUT.value
                parsed_query.route_source = f"{parsed_query.route_source}+closing_accept"
                decision = FlowDecision(
                    flow=DialogueFlow.CHECKOUT,
                    reason="用户确认闭环结算引导",
                    need_retrieval=False,
                    need_llm=True,
                )

        with timer.measure("task_planning", "生成本轮任务计划"):
            task_plan = self.task_planner.plan(decision)
        with timer.measure("model_routing", "模型路由决策"):
            model_route = self.model_router.route(parsed_query, decision)
        model_route_payload = model_route.model_dump()
        model_route_payload["llm_provider"] = self.response_generator.llm_client.__class__.__name__
        with timer.measure("memory_write_model_route", "写入模型路由状态"):
            self.session_memory.update_model_route(session_id, model_route_payload)

        trace.intent = parsed_query.intent
        trace.flow_after = decision.flow.value
        trace.difficulty = model_route.difficulty
        trace.model_route = model_route_payload
        trace.parsed_query = parsed_query.model_dump()
        trace.task_plan = task_plan.task_names
        trace.llm_called = False

        yield SSEEvent(
            event="state",
            data={
                "current_flow": decision.flow.value,
                "intent": parsed_query.intent,
                "difficulty": model_route.difficulty,
                "model_route": model_route.model_dump(),
                "parsed_query": parsed_query.model_dump(),
                "task_plan": task_plan.task_names,
            },
        )
        trace.legacy_sse_events.append("state")

        with timer.measure("memory_write_user_message", "写入用户消息到短期记忆"):
            self.session_memory.append_message(session_id, role="user", content=preprocess.normalized_message)

        candidates: list[CandidateProduct] = []
        alternatives: list[CandidateProduct] = []
        products: list[Product] = []
        cards: list[ProductCard] = []
        tool_result: ToolExecutionResult | None = None
        qa_result: ProductQAResult | None = None
        scene_plan: ScenePlan | None = None
        preference_result = None
        tool_prefix_messages: list[str] = []
        personalization_context: dict = {}
        cart_personalization_context: dict = {}
        fallback_result: FallbackResult | None = None
        comparison_data = None

        try:
            with timer.measure("product_repository_load", "读取本地商品库"):
                products_by_id = {product.sku_id: product for product in self.product_repository.list_products()}
            with timer.measure("cart_personalization_analyze", "分析购物车商品侧个性化信号"):
                cart_personalization_context = self.cart_aware_personalization.build_context(
                    state=state,
                    parsed_query=parsed_query,
                )
            if cart_personalization_context.get("是否调用Doubao"):
                timer.mark_model_call(
                    module="cart_personalization",
                    provider=self.response_generator.llm_client.__class__.__name__,
                    purpose="cart_profile_analysis",
                    duration_ms=timer.last_duration("cart_personalization_analyze"),
                    call_debug=self._llm_call_debug(),
                )
            if privacy_update.get("updated"):
                preference_result = PreferenceUpdateResult(
                    updated=True,
                    message=privacy_update.get("message") or "隐私和个性化设置已更新。",
                    updates={"privacy_settings": privacy_update.get("privacy_settings", {})},
                    needs_confirmation=False,
                )
            elif parsed_query.intent == IntentType.PREFERENCE.value:
                preference_result = self.preference_manager.update_from_query(parsed_query, state)

            if preprocess.template_reply is not None:
                response_text = preprocess.template_reply
                self.response_generator.last_llm_called = False
                self.response_generator.last_response_strategy = self.response_generator._build_response_strategy(
                    decision=decision,
                    candidates=[],
                    alternatives=[],
                    personalization_context={},
                )
            elif decision.flow in {DialogueFlow.CART_ACTION, DialogueFlow.CHECKOUT}:
                if self._has_executable_intent_plan(parsed_query):
                    with timer.measure("tool_execution", "执行多步骤购物车/结算工具"):
                        tool_result, tool_calls = self._execute_intent_plan(
                            session_id=session_id,
                            query_id=query_id,
                            parsed_query=parsed_query,
                            state=state,
                        )
                    trace.tool_calls.extend(item.model_dump() for item in tool_calls)
                    if len(tool_calls) > 1:
                        tool_prefix_messages = [item.message for item in tool_calls[:-1] if item.ok and item.message]
                else:
                    with timer.measure("tool_execution", "执行确定性购物车/结算工具"):
                        tool_result = self.action_executor.execute_cart_action(
                            session_id=session_id,
                            parsed_query=parsed_query,
                            state=state,
                        )
                        trace.tool_calls.append(tool_result.model_dump())
                        self._record_cart_event_from_tool_result(
                            session_id=session_id,
                            query_id=query_id,
                            message=preprocess.normalized_message,
                            parsed_query=parsed_query,
                            tool_result=tool_result,
                        )
                if tool_result.payload:
                    yield SSEEvent(event="cart_update", data=tool_result.payload)
                    yield SSEEvent(event="cart", data={"cart": tool_result.payload})
                    trace.legacy_sse_events.extend(["cart_update", "cart"])
                personalization_context = self._build_personalization_context_timed(
                    timer=timer,
                    user_id=effective_user_id,
                    parsed_query=parsed_query,
                    state=state,
                    candidates=[],
                    cart_personalization_context=cart_personalization_context,
                )
                response_text = self._generate_response_timed(
                    timer=timer,
                    model_route=model_route,
                    parsed_query=parsed_query,
                    decision=decision,
                    state=state,
                    candidates=candidates,
                    products=products,
                    tool_result=tool_result,
                    personalization_context=personalization_context,
                    multimodal_context=multimodal_context,
                    closing_context=self._maybe_trigger_closing(state, parsed_query, preprocess),
                )
            elif decision.flow == DialogueFlow.PREFERENCE_UPDATE:
                personalization_context = self._build_personalization_context_timed(
                    timer=timer,
                    user_id=effective_user_id,
                    parsed_query=parsed_query,
                    state=state,
                    candidates=[],
                    cart_personalization_context=cart_personalization_context,
                )
                response_text = self._generate_response_timed(
                    timer=timer,
                    model_route=model_route,
                    parsed_query=parsed_query,
                    decision=decision,
                    state=state,
                    candidates=[],
                    products=[],
                    preference_result=preference_result,
                    personalization_context=personalization_context,
                    multimodal_context=multimodal_context,
                )
            elif decision.flow == DialogueFlow.SCENE_BUNDLE:
                if self._has_mixed_intent_plan(parsed_query):
                    with timer.measure("tool_execution", "执行混合意图中的购物车工具步骤"):
                        tool_result, tool_calls = self._execute_tool_steps_from_intent_plan(
                            session_id=session_id,
                            query_id=query_id,
                            parsed_query=parsed_query,
                            state=state,
                        )
                    trace.tool_calls.extend(item.model_dump() for item in tool_calls)
                    tool_prefix_messages = [item.message for item in tool_calls if item.ok and item.message]
                    if tool_result and tool_result.payload:
                        yield SSEEvent(event="cart_update", data=tool_result.payload)
                        yield SSEEvent(event="cart", data={"cart": tool_result.payload})
                        trace.legacy_sse_events.extend(["cart_update", "cart"])
                with timer.measure("scene_planning", "场景化组合拆解"):
                    scene_plan = self.scenario_planner.plan(parsed_query.raw_message)
                with timer.measure("rag_retrieval", "场景化多子查询商品检索"):
                    candidates = self._retrieve_scene_candidates(scene_plan, state)
                model_route, model_route_payload = self._refresh_local_model_status(model_route)
                trace.model_route = model_route_payload
                with timer.measure("cart_personalization_rerank", "购物车商品侧个性化重排"):
                    candidates = self.cart_aware_personalization.rerank(
                        candidates=candidates,
                        context=cart_personalization_context,
                        parsed_query=parsed_query,
                    )
                context_candidates = candidates if candidates else alternatives
                products = [products_by_id[item.sku_id] for item in context_candidates if item.sku_id in products_by_id]
                with timer.measure("product_card_build", "生成商品卡片数据"):
                    cards = self.post_processor.build_product_cards(candidates, products_by_id)
                trace.retrieved_product_ids = [item.sku_id for item in candidates]
                personalization_context = self._build_personalization_context_timed(
                    timer=timer,
                    user_id=effective_user_id,
                    parsed_query=parsed_query,
                    state=state,
                    candidates=candidates,
                    cart_personalization_context=cart_personalization_context,
                )
                response_text = self._generate_response_timed(
                    timer=timer,
                    model_route=model_route,
                    parsed_query=parsed_query,
                    decision=decision,
                    state=state,
                    candidates=candidates,
                    products=products,
                    scene_plan=scene_plan,
                    personalization_context=personalization_context,
                    multimodal_context=multimodal_context,
                )
                if tool_prefix_messages:
                    response_text = "\n".join(tool_prefix_messages) + "\n\n" + response_text
                yield SSEEvent(event="scenario", data=scene_plan.model_dump())
                trace.legacy_sse_events.append("scenario")
            elif decision.need_retrieval:
                if self._has_mixed_intent_plan(parsed_query):
                    with timer.measure("tool_execution", "执行混合意图中的购物车工具步骤"):
                        tool_result, tool_calls = self._execute_tool_steps_from_intent_plan(
                            session_id=session_id,
                            query_id=query_id,
                            parsed_query=parsed_query,
                            state=state,
                        )
                    trace.tool_calls.extend(item.model_dump() for item in tool_calls)
                    tool_prefix_messages = [item.message for item in tool_calls if item.ok and item.message]
                    if tool_result and tool_result.payload:
                        yield SSEEvent(event="cart_update", data=tool_result.payload)
                        yield SSEEvent(event="cart", data={"cart": tool_result.payload})
                        trace.legacy_sse_events.extend(["cart_update", "cart"])
                with timer.measure("rag_retrieval", "RAG/Hybrid 商品召回"):
                    raw_candidates = self._retrieve_for_flow(parsed_query, decision, state)
                model_route, model_route_payload = self._refresh_local_model_status(model_route)
                trace.model_route = model_route_payload
                with timer.measure("multimodal_candidate_boost", "多模态候选增强"):
                    raw_candidates = self.multimodal_service.boost_candidates(raw_candidates, multimodal_context)
                with timer.measure("cart_personalization_rerank", "购物车商品侧个性化重排"):
                    raw_candidates = self.cart_aware_personalization.rerank(
                        candidates=raw_candidates,
                        context=cart_personalization_context,
                        parsed_query=parsed_query,
                    )
                with timer.measure("product_postprocessing", "商品去重、过滤和最终排序"):
                    candidates = self.post_processor.finalize(
                        candidates=raw_candidates,
                        parsed_query=parsed_query,
                        limit=5 if decision.flow == DialogueFlow.COMPARISON else 3,
                    )
                if decision.flow == DialogueFlow.PRODUCT_QA and parsed_query.mentioned_products:
                    exact_candidates = self._mentioned_product_candidates(parsed_query, products_by_id)
                    if exact_candidates:
                        raw_candidates = exact_candidates
                        candidates = exact_candidates
                trace.retrieved_product_ids = [item.sku_id for item in raw_candidates if not item.filtered_out]
                trace.filtered_product_ids = [item.sku_id for item in raw_candidates if item.filtered_out]

                if not candidates:
                    with timer.measure("alternative_retrieval", "放宽条件后的备选商品检索"):
                        alternatives, fallback_result = self._retrieve_alternatives(parsed_query, state)
                        trace.fallback_result = {
                            "is_fallback": fallback_result.is_fallback,
                            "original_count": fallback_result.original_count,
                            "relaxed_steps": fallback_result.relaxed_steps,
                            "summary": fallback_result.summary_for_response(),
                        }
                        alternatives = self.cart_aware_personalization.rerank(
                            candidates=alternatives,
                            context=cart_personalization_context,
                            parsed_query=parsed_query,
                        )
                    decision = FlowDecision(
                        flow=DialogueFlow.NO_RESULT,
                        reason="检索后无完全匹配商品",
                        need_retrieval=False,
                        need_llm=model_route.need_llm,
                    )

                context_candidates = candidates if candidates else alternatives
                products = [products_by_id[item.sku_id] for item in context_candidates if item.sku_id in products_by_id]
                with timer.measure("product_card_build", "生成商品卡片数据"):
                    cards = self.post_processor.build_product_cards(candidates, products_by_id)

                if decision.flow == DialogueFlow.PRODUCT_QA:
                    with timer.measure("product_qa", "商品详情/问答事实抽取"):
                        qa_result = self.product_qa_module.answer(
                            parsed_query=parsed_query,
                            products=products,
                            candidates=candidates,
                        )
                    if products:
                        with timer.measure("memory_write_product_detail_event", "写入商品详情事件记忆"):
                            self.session_memory.record_product_detail_event(
                                session_id=session_id,
                                query_id=query_id,
                                source_message=preprocess.normalized_message,
                                sku_id=products[0].sku_id,
                                target_ref=parsed_query.referents[0] if parsed_query.referents else None,
                                source_event_id=reference_resolution.get("source_event_id"),
                            )
                        yield SSEEvent(event="product_detail", data={"product": products[0].model_dump(), "qa": qa_result.model_dump()})
                        trace.legacy_sse_events.append("product_detail")

                personalization_context = self._build_personalization_context_timed(
                    timer=timer,
                    user_id=effective_user_id,
                    parsed_query=parsed_query,
                    state=state,
                    candidates=context_candidates,
                    cart_personalization_context=cart_personalization_context,
                )
                response_text = self._generate_response_timed(
                    timer=timer,
                    model_route=model_route,
                    parsed_query=parsed_query,
                    decision=decision,
                    state=state,
                    candidates=candidates,
                    products=products,
                    qa_result=qa_result,
                    alternatives=alternatives,
                    fallback_result=fallback_result,
                    personalization_context=personalization_context,
                    multimodal_context=multimodal_context,
                )
                if tool_prefix_messages:
                    response_text = "\n".join(tool_prefix_messages) + "\n\n" + response_text
            else:
                response_text = self._generate_response_timed(
                    timer=timer,
                    model_route=model_route,
                    parsed_query=parsed_query,
                    decision=decision,
                    state=state,
                    candidates=[],
                    products=[],
                    personalization_context=personalization_context,
                    multimodal_context=multimodal_context,
                )

            validation_candidates = candidates if candidates else alternatives
            trace.llm_called = self.response_generator.last_llm_called
            if decision.flow in {
                DialogueFlow.CART_ACTION,
                DialogueFlow.CHECKOUT,
                DialogueFlow.PREFERENCE_UPDATE,
                DialogueFlow.CLARIFICATION,
                DialogueFlow.CHITCHAT,
                DialogueFlow.GREETING,
                DialogueFlow.OUT_OF_SCOPE,
                DialogueFlow.INVALID,
            }:
                validation_result = ValidationResult(ok=True)
            else:
                with timer.measure("response_validation", "回复事实校验和幻觉修复"):
                    response_text, validation_result = self.response_validator.validate_with_result(response_text, validation_candidates)
            if tool_prefix_messages and not response_text.startswith(tool_prefix_messages[0]):
                response_text = "\n".join(tool_prefix_messages) + "\n\n" + response_text
            if cards and decision.flow != DialogueFlow.PRODUCT_QA:
                with timer.measure("scene_presentation_build", "构造结构化商品展示字段"):
                    cards, comparison_data = self.scene_presentation_builder.build(
                        parsed_query=parsed_query,
                        flow=decision.flow,
                        cards=cards,
                        products=products,
                        candidates=candidates,
                        use_llm=model_route.need_llm,
                    )
                timer.mark_model_call(
                    module="scene_presentation_build",
                    provider=self.response_generator.llm_client.__class__.__name__,
                    purpose="build_scene_presentation",
                    duration_ms=timer.last_duration("scene_presentation_build"),
                    called=self.scene_presentation_builder.last_llm_called,
                    call_debug=self.scene_presentation_builder.last_call_debug,
                )
                trace.presentation = {
                    **self.scene_presentation_builder.last_debug,
                    "llm_called": self.scene_presentation_builder.last_llm_called,
                    "comparison_data": comparison_data.model_dump() if comparison_data else None,
                }
                if decision.flow == DialogueFlow.COMPARISON:
                    response_text = self.scene_presentation_builder.comparison_intro(parsed_query, cards)
                elif self.scene_presentation_builder.scene_type(decision.flow) == "recommendation":
                    response_text = self.scene_presentation_builder.recommendation_intro(parsed_query, cards)
                trace.llm_called = trace.llm_called or self.scene_presentation_builder.last_llm_called
            trace.validation_result = validation_result.model_dump()
            trace.cart_personalization = cart_personalization_context
            trace.personalization_context = personalization_context
            trace.multimodal_context = multimodal_context
            trace.response_strategy = self.response_generator.last_response_strategy
            trace.selected_product_ids = [item.sku_id for item in (candidates if candidates else alternatives)]
            trace.retrieval_scores = [
                {
                    "sku_id": item.sku_id,
                    "name": item.name,
                    "score": item.score,
                    "raw_scores": item.raw_scores,
                    "matched_reasons": item.matched_reasons,
                    "enhancement_matches": item.enhancement_matches,
                }
                for item in candidates[:5]
            ]
            trace.product_enhancement = self._product_enhancement_trace(candidates if candidates else alternatives)
            with timer.measure("memory_write_assistant_message", "写入系统回复到短期记忆"):
                self.session_memory.append_message(session_id, role="assistant", content=response_text)

            if decision.flow == DialogueFlow.CLARIFICATION:
                yield SSEEvent(event="clarification", data={"question": response_text, "missing_slots": decision.missing_slots})
                trace.legacy_sse_events.append("clarification")

            for chunk in self._chunk_text(response_text):
                yield SSEEvent(event="token", data={"text": chunk, "content": chunk})
                trace.legacy_sse_events.append("token")
                await asyncio.sleep(0)

            if cards and decision.flow != DialogueFlow.PRODUCT_QA:
                if self._should_stream_recommendation_sections(decision, cards):
                    for section_event in self._recommendation_section_events(cards, query_id):
                        yield section_event
                        trace.legacy_sse_events.append(section_event.event)
                        await asyncio.sleep(0)
                product_payload = {"products": [card.model_dump() for card in cards]}
                yield SSEEvent(event="product_cards", data=product_payload)
                yield SSEEvent(event="products", data=product_payload)
                trace.legacy_sse_events.extend(["product_cards", "products"])
                if decision.flow in {
                    DialogueFlow.RECOMMENDATION,
                    DialogueFlow.FILTERING,
                    DialogueFlow.REFINEMENT,
                    DialogueFlow.EXCLUSION,
                    DialogueFlow.SCENE_BUNDLE,
                    DialogueFlow.NO_RESULT,
                }:
                    with timer.measure("memory_write_recommendation_event", "写入推荐事件记忆"):
                        recommendations = self.post_processor.build_recommendation_records(candidates=candidates, query_id=query_id)
                        self.session_memory.record_recommendation_event(
                            session_id=session_id,
                            query_id=query_id,
                            source_message=preprocess.normalized_message,
                            recommendations=recommendations,
                            category=parsed_query.category,
                            sub_category=parsed_query.sub_category,
                            constraints=self._event_constraints(parsed_query),
                            recommendation_mode=self._recommendation_mode(candidates),
                            result_status=self._recommendation_status(candidates),
                        )
                elif decision.flow == DialogueFlow.COMPARISON and candidates:
                    with timer.measure("memory_write_comparison_event", "写入对比事件记忆"):
                        self.session_memory.record_comparison_event(
                            session_id=session_id,
                            query_id=query_id,
                            source_message=preprocess.normalized_message,
                            sku_ids=[item.sku_id for item in candidates],
                            references=parsed_query.referents or parsed_query.compare_targets,
                            resolved_references=reference_resolution.get("resolved", {}),
                            comparison_dimensions=self._comparison_dimensions(parsed_query),
                            source_event_id=reference_resolution.get("source_event_id"),
                        )

            if alternatives:
                with timer.measure("alternative_card_build", "生成备选商品卡片"):
                    alt_cards = self.post_processor.build_product_cards(alternatives[:3], products_by_id)
                    alt_cards, _ = self.scene_presentation_builder.build(
                        parsed_query=parsed_query,
                        flow=DialogueFlow.NO_RESULT,
                        cards=alt_cards,
                        products=products,
                        candidates=alternatives[:3],
                        use_llm=False,
                    )
                yield SSEEvent(event="alternatives", data={"products": [card.model_dump() for card in alt_cards]})
                trace.legacy_sse_events.append("alternatives")
                with timer.measure("memory_write_alternative_event", "写入备选推荐事件记忆"):
                    recommendations = self.post_processor.build_recommendation_records(candidates=alternatives[:3], query_id=query_id)
                    self.session_memory.record_recommendation_event(
                        session_id=session_id,
                        query_id=query_id,
                        source_message=preprocess.normalized_message,
                        recommendations=recommendations,
                        category=parsed_query.category,
                        sub_category=parsed_query.sub_category,
                        constraints=self._event_constraints(parsed_query),
                        recommendation_mode="alternative",
                        result_status="no_exact_match",
                        unmet_constraints=self._unmet_constraints(parsed_query),
                        relaxed_constraints={"price_range": "relaxed", "hard_filters": "relaxed_for_alternatives"},
                    )

            with timer.measure("frontend_action_decision", "前端动作决策"):
                frontend_action = self.frontend_action_planner.decide(
                    parsed_query=parsed_query,
                    decision=decision,
                    state=state,
                    cards=cards,
                    candidates=candidates,
                    response_text=response_text,
                    tool_result=tool_result,
                    qa_result=qa_result,
                    scene_plan=scene_plan,
                )
            timer.mark_model_call(
                module="frontend_action_decision",
                provider=self.response_generator.llm_client.__class__.__name__,
                purpose="frontend_action_decision",
                duration_ms=timer.last_duration("frontend_action_decision"),
                called=frontend_action.source == "doubao",
                call_debug=self._llm_call_debug(),
            )
            trace.frontend_action = frontend_action.model_dump()
            trace.llm_called = trace.llm_called or frontend_action.source == "doubao"
            yield SSEEvent(event="frontend_action", data=frontend_action.model_dump())
            trace.legacy_sse_events.append("frontend_action")

            with timer.measure("memory_update_dialogue_state", "更新对话状态、候选商品和行为记录"):
                self._record_turn(
                    session_id=session_id,
                    query_id=query_id,
                    message=preprocess.normalized_message,
                    flow=decision.flow.value,
                    parsed_query=parsed_query,
                    candidates=candidates,
                    task_plan=task_plan.task_names,
                    missing_slots=decision.missing_slots,
                    model_route=model_route,
                    preference_updated=bool(preference_result and preference_result.updated),
                )
            trace.memory_update_keys = ["recent_messages", "dialogue_state", "event_memory", "last_recommendations", "cart", "trace"]
            with timer.measure("memory_read_after_turn", "读取更新后的会话状态"):
                state_after = self.session_memory.get_or_create(session_id, user_id=effective_user_id)
            progress_plan["停止原因"] = progress_plan.get("停止原因") or "正式结果已生成"
            progress_plan["最终主流程耗时_ms"] = timer.elapsed_ms()
            progress_plan["主流程已完成"] = True
            trace.runtime_timings = timer.summary()
            with timer.measure("frontend_events_build", "构造 frontend_events/frontend_data/system_debug"):
                turn_output = self.frontend_event_builder.build(
                    session_id=session_id,
                    user_id=effective_user_id,
                    response_text=response_text,
                    parsed_query=parsed_query,
                    decision=decision,
                    state_before=state_before_snapshot,
                    state_after=state_after,
                    cards=cards,
                    products=products,
                    candidates=candidates,
                    alternatives=alternatives,
                    tool_result=tool_result,
                    qa_result=qa_result,
                    scene_plan=scene_plan,
                    frontend_action=frontend_action,
                    trace_payload=trace.model_dump(),
                    comparison_data=comparison_data,
                    history_restored=history_restored,
                    restored_from_session_id=restored_from_session_id,
                    legacy_sse_events=trace.legacy_sse_events,
                )
            trace.frontend_events = turn_output.frontend_events
            trace.legacy_sse_events.append("turn_result")
            with timer.measure("history_save", "保存本轮本地用户历史和 state_snapshot"):
                self.user_history_store.save_turn(
                    user_id=effective_user_id,
                    session_id=session_id,
                    user_message=preprocess.normalized_message,
                    assistant_reply=response_text,
                    state=state_after,
                    trace=trace.model_dump(),
                    frontend_output=turn_output.model_dump(),
                )
            with timer.measure("profile_refresh", "按需刷新长期用户画像"):
                refreshed_profile = self.user_profile_service.maybe_refresh_profile(
                    effective_user_id,
                    force=frontend_action.should_end_conversation,
                )
            if refreshed_profile.get("profile_summary_text"):
                with timer.measure("memory_write_profile", "写入刷新后的用户画像到会话"):
                    self.session_memory.attach_user_profile(
                        session_id,
                        user_id=effective_user_id,
                        summary_text=refreshed_profile.get("profile_summary_text"),
                        structured_profile=refreshed_profile.get("structured_profile") or {},
                    )
            trace.runtime_timings = timer.summary()
            turn_output.system_debug["运行耗时统计"] = trace.runtime_timings
            if "Progress事件" in turn_output.system_debug:
                turn_output.system_debug["Progress事件"]["实际总耗时_ms"] = trace.runtime_timings.get("total_duration_ms")
                turn_output.system_debug["Progress事件"]["最终主流程耗时_ms"] = progress_plan.get("最终主流程耗时_ms")
            if "进度事件" in turn_output.system_debug:
                turn_output.system_debug["进度事件"]["实际总耗时_ms"] = trace.runtime_timings.get("total_duration_ms")
                turn_output.system_debug["进度事件"]["最终主流程耗时_ms"] = progress_plan.get("最终主流程耗时_ms")
            trace.unified_output = turn_output.model_dump()
            with timer.measure("trace_save", "保存本轮 trace 日志"):
                self.session_memory.append_trace(session_id, trace.model_dump())
            yield SSEEvent(event="turn_result", data=turn_output.model_dump())
            yield SSEEvent(event="done", data={"finish_reason": "stop"})
        except Exception as exc:
            import sys
            print(f"[AGENT_ERROR] {exc}", file=sys.stderr)
            _traceback.print_exc(file=sys.stderr)
            trace.error_message = str(exc)
            if "progress_plan" in locals():
                progress_plan["停止原因"] = progress_plan.get("停止原因") or "主流程异常"
                progress_plan["最终主流程耗时_ms"] = timer.elapsed_ms()
                progress_plan["主流程已完成"] = False
            with timer.measure("error_state_read", "异常后读取会话状态"):
                state_after = self.session_memory.get_or_create(session_id, user_id=effective_user_id)
            trace.runtime_timings = timer.summary()
            with timer.measure("frontend_error_build", "构造错误输出"):
                error_output = self.frontend_event_builder.build_error(
                    session_id=session_id,
                    user_id=effective_user_id,
                    message=str(exc),
                    state_before=state_before_snapshot,
                    state_after=state_after,
                    trace_payload=trace.model_dump(),
                    legacy_sse_events=trace.legacy_sse_events,
                )
            error_output.system_debug["运行耗时统计"] = trace.runtime_timings
            trace.frontend_events = error_output.frontend_events
            trace.unified_output = error_output.model_dump()
            trace.legacy_sse_events.extend(["turn_result", "error"])
            self.session_memory.append_trace(session_id, trace.model_dump())
            self.user_history_store.save_turn(
                user_id=effective_user_id,
                session_id=session_id,
                user_message=message,
                assistant_reply="系统处理时遇到问题，请稍后重试。",
                state=state_after,
                trace=trace.model_dump(),
                frontend_output=error_output.model_dump(),
            )
            yield SSEEvent(event="turn_result", data=error_output.model_dump())
            yield SSEEvent(event="error", data={"message": "系统处理时遇到问题，请稍后重试。", "code": "AGENT_ERROR"})
            yield SSEEvent(event="done", data={"finish_reason": "error"})

    def _retrieve_for_flow(self, parsed_query: ParsedQuery, decision: FlowDecision, state) -> list[CandidateProduct]:
        if decision.flow in {DialogueFlow.COMPARISON, DialogueFlow.PRODUCT_QA, DialogueFlow.DETAIL}:
            return self.product_search_tool.retrieve_reference_candidates(parsed_query=parsed_query, state=state, top_k=5)
        return self.product_search_tool.retrieve_candidates(parsed_query=parsed_query, state=state, top_k=5)

    def _is_old_user_for_progress(self, *, user_id: str, resume: bool, new_session: bool) -> bool:
        if new_session:
            return False
        if resume:
            return True
        try:
            profile = self.user_history_store.load_profile(user_id)
        except Exception:
            return False
        return bool(
            profile.get("sessions")
            or profile.get("last_session_id")
            or profile.get("profile_summary_text")
            or profile.get("history_summary")
        )

    def _resolve_event_references(self, session_id: str, parsed_query: ParsedQuery, state) -> tuple[object, dict]:
        """Resolve "第一款/第二个/这款" before retrieval or cart tools run.

        The active recommendation event owns stable rank references. Detail
        events only own pronouns such as "这款/它", so opening a detail page
        does not erase the user's previous ranked recommendation list.
        """
        reference_terms = self._collect_reference_terms(parsed_query)
        memory_result = self.session_memory.resolve_reference_from_memory_events(
            state,
            parsed_query.raw_message,
            references=reference_terms,
        )
        if memory_result.resolved:
            self._apply_resolved_references_to_query(parsed_query, memory_result.resolved, reference_terms)
            parsed_query.route_source = f"{parsed_query.route_source}+memory_events_reference"
            state = self.session_memory.refresh_references(session_id)
            return state, memory_result.model_dump()

        state = self.session_memory.refresh_references(session_id)
        resolved: dict[str, str] = {}
        for ref in reference_terms:
            sku_id = state.dialogue_state_tracking.resolved_references.get(ref)
            if sku_id:
                resolved[ref] = sku_id

        if not resolved:
            return state, {
                "resolved": {},
                "product_ids": [],
                "source_event_id": None,
                "source": "failed",
                "reference_texts": reference_terms,
                "confidence": 0.0,
            }

        self._apply_resolved_references_to_query(parsed_query, resolved, reference_terms)
        parsed_query.route_source = f"{parsed_query.route_source}+resolved_references"
        return state, {
            "resolved": resolved,
            "product_ids": list(dict.fromkeys(resolved.values())),
            "source_event_id": None,
            "source": "resolved_references",
            "reference_texts": list(resolved.keys()),
            "confidence": 0.75,
        }

    def _promote_ellipsis_reference_intent(self, parsed_query: ParsedQuery) -> None:
        if parsed_query.intent not in {IntentType.CHITCHAT.value, IntentType.REFINE.value}:
            return
        if not parsed_query.mentioned_products or not parsed_query.referents:
            return
        raw = parsed_query.raw_message.strip()
        looks_like_ellipsis_followup = "呢" in raw or raw in set(parsed_query.referents) or len(raw) <= 8
        if not looks_like_ellipsis_followup:
            return
        product = self.product_repository.get_product(parsed_query.mentioned_products[0])
        parsed_query.intent = IntentType.DETAIL.value
        parsed_query.sub_intent = "ellipsis_product_detail"
        parsed_query.inherit_context = True
        parsed_query.need_clarification = False
        parsed_query.clarification_slots = []
        if product:
            parsed_query.category = product.category
            parsed_query.sub_category = product.sub_category
        parsed_query.route_source = f"{parsed_query.route_source}+ellipsis_detail_inheritance"
        if parsed_query.intent_plan and parsed_query.intent_plan.steps:
            parsed_query.intent_plan.primary_intent = IntentType.DETAIL.value
            for step in parsed_query.intent_plan.steps:
                step.intent = IntentType.DETAIL.value
                step.action = IntentType.DETAIL.value
                step.requires_retrieval = True

    def _apply_resolved_references_to_query(
        self,
        parsed_query: ParsedQuery,
        resolved: dict[str, str],
        reference_terms: list[str],
    ) -> None:
        resolved_skus = list(dict.fromkeys(resolved.values()))
        parsed_query.mentioned_products = list(dict.fromkeys([*resolved_skus, *parsed_query.mentioned_products]))
        parsed_query.referents = list(dict.fromkeys([*parsed_query.referents, *resolved.keys()]))

        if parsed_query.cart_action:
            if parsed_query.cart_action.target_ref is None and reference_terms:
                parsed_query.cart_action.target_ref = reference_terms[0]
            if parsed_query.cart_action.target_ref in resolved:
                parsed_query.cart_action.sku_id = resolved[parsed_query.cart_action.target_ref]

        if parsed_query.intent_plan:
            for step in parsed_query.intent_plan.steps:
                step_ref = step.target_ref
                if step_ref is None:
                    step_ref = self._first_reference_in_text(step.source_text)
                    if step_ref:
                        step.target_ref = step_ref
                if step_ref in resolved:
                    step.sku_id = resolved[step_ref]
                elif step_ref:
                    sku_id = resolved.get(step_ref)
                    if sku_id:
                        step.sku_id = sku_id

    def _collect_reference_terms(self, parsed_query: ParsedQuery) -> list[str]:
        refs: list[str] = []
        refs.extend(parsed_query.referents)
        if parsed_query.cart_action and parsed_query.cart_action.target_ref:
            refs.append(parsed_query.cart_action.target_ref)
        if parsed_query.intent_plan:
            for step in parsed_query.intent_plan.steps:
                if step.target_ref:
                    refs.append(step.target_ref)
                refs.extend(self._references_in_text(step.source_text))
        refs.extend(self._references_in_text(parsed_query.raw_message))
        return list(dict.fromkeys(ref for ref in refs if ref))

    def _references_in_text(self, text: str | None) -> list[str]:
        if not text:
            return []
        reference_terms = getattr(self.query_understanding, "_reference_terms", [])
        ranked = [(text.find(ref), ref) for ref in reference_terms if ref and ref in text]
        ranked.sort(key=lambda item: item[0])
        return [ref for _, ref in ranked]

    def _first_reference_in_text(self, text: str | None) -> str | None:
        refs = self._references_in_text(text)
        return refs[0] if refs else None

    def _retrieve_scene_candidates(self, scene_plan: ScenePlan, state) -> list[CandidateProduct]:
        all_candidates: list[CandidateProduct] = []
        seen: set[str] = set()
        for sub_query in scene_plan.sub_queries:
            parsed = ParsedQuery(
                raw_message=sub_query.query,
                intent=IntentType.RECOMMEND.value,
                category=sub_query.category,
                sub_category=sub_query.sub_category,
                positive_constraints=[],
                rewritten_query=sub_query.query,
                confidence=0.82,
            )
            raw = self.product_search_tool.retrieve_candidates(parsed_query=parsed, state=state, top_k=3)
            final = self.post_processor.finalize(raw, parsed, limit=1)
            for candidate in final:
                if candidate.sku_id not in seen:
                    candidate.matched_reasons = [sub_query.label, sub_query.reason, *candidate.matched_reasons]
                    candidate.score = round(min(candidate.score + 0.25, 1.0), 4)
                    all_candidates.append(candidate)
                    seen.add(candidate.sku_id)
        return all_candidates[:6]

    def _retrieve_alternatives(self, parsed_query: ParsedQuery, state) -> tuple[list[CandidateProduct], FallbackResult]:
        """Progressive fallback retrieval when strict matching yields no results.

        Replaces the old simple price-relaxation with a full 4-level progressive
        constraint relaxation: price → sub_category → negative → broad search.
        Returns (candidates, fallback_result) where fallback_result contains the
        relaxation trace for generating user-facing explanations.
        """
        fallback_result = RetrievalFallback.progressive_retrieve(
            retriever=self.product_search_tool.retriever,
            parsed_query=parsed_query,
            state=state,
            top_k=5,
        )
        # CRITICAL: Use a fully relaxed parsed_query for finalize, otherwise
        # finalize re-applies the original strict constraints (price, category,
        # negative) and filters out all the candidates we just worked hard to find.
        relaxed_query = parsed_query.model_copy(deep=True)
        relaxed_query.price_range.max = None
        relaxed_query.price_range.min = None
        relaxed_query.negative_constraints = []
        relaxed_query.brands_exclude = []
        relaxed_query.sub_category = None
        candidates = self.post_processor.finalize(
            [c for c in fallback_result.candidates if not c.filtered_out],
            relaxed_query,
            limit=3,
        )
        return candidates, fallback_result

    @staticmethod
    def _mentioned_product_candidates(
        parsed_query: ParsedQuery,
        products_by_id: dict[str, Product],
    ) -> list[CandidateProduct]:
        candidates: list[CandidateProduct] = []
        for index, sku_id in enumerate(dict.fromkeys(parsed_query.mentioned_products), start=1):
            product = products_by_id.get(sku_id)
            if not product:
                continue
            candidates.append(
                CandidateProduct(
                    candidate_id=f"mentioned_{index}",
                    product_id=product.product_id,
                    sku_id=product.sku_id,
                    name=product.name,
                    brand=product.brand,
                    category=product.category,
                    sub_category=product.sub_category,
                    price=product.price,
                    image_url=product.image_url,
                    matched_reasons=["来自上一轮推荐或用户指代"],
                    score=1.0,
                    raw_scores={"reference_memory": 1.0},
                )
            )
        return candidates

    @staticmethod
    def _event_constraints(parsed_query: ParsedQuery) -> dict:
        return {
            "price_min": parsed_query.price_range.min,
            "price_max": parsed_query.price_range.max,
            "positive_constraints": parsed_query.positive_constraints,
            "negative_constraints": parsed_query.negative_constraints,
            "brands_include": parsed_query.brands_include,
            "brands_exclude": parsed_query.brands_exclude,
            "scenario": parsed_query.scenario,
        }

    @staticmethod
    def _recommendation_mode(candidates: list[CandidateProduct]) -> str:
        if not candidates:
            return "alternative"
        if any(item.score < 0.5 or item.violated_constraints for item in candidates):
            return "mixed"
        return "exact"

    @staticmethod
    def _recommendation_status(candidates: list[CandidateProduct]) -> str:
        if not candidates:
            return "no_exact_match"
        if any(item.score < 0.5 or item.violated_constraints for item in candidates):
            return "partial_match"
        return "exact_match"

    @staticmethod
    def _unmet_constraints(parsed_query: ParsedQuery) -> dict:
        unmet: dict[str, object] = {}
        if parsed_query.price_range.min is not None or parsed_query.price_range.max is not None:
            unmet["price_range"] = parsed_query.price_range.model_dump()
        if parsed_query.positive_constraints:
            unmet["positive_constraints"] = parsed_query.positive_constraints
        if parsed_query.negative_constraints:
            unmet["negative_constraints"] = parsed_query.negative_constraints
        if parsed_query.brands_exclude:
            unmet["brands_exclude"] = parsed_query.brands_exclude
        return unmet

    @staticmethod
    def _comparison_dimensions(parsed_query: ParsedQuery) -> list[str]:
        dimensions: list[str] = []
        message = parsed_query.raw_message
        for term in ["油皮", "拍照", "续航", "性价比", "价格", "学生", "通勤", "保湿", "清爽", "降噪"]:
            if term in message or term in parsed_query.positive_constraints:
                dimensions.append(term)
        return list(dict.fromkeys(dimensions))

    def _build_personalization_context(
        self,
        *,
        user_id: str,
        parsed_query: ParsedQuery,
        state,
        candidates: list[CandidateProduct],
    ) -> dict:
        return self.personalization_service.build_context(
            user_id=user_id,
            parsed_query=parsed_query,
            state=state,
            candidates=candidates,
        )

    def _build_personalization_context_timed(
        self,
        *,
        timer: RuntimeTimer,
        user_id: str,
        parsed_query: ParsedQuery,
        state,
        candidates: list[CandidateProduct],
        cart_personalization_context: dict,
    ) -> dict:
        with timer.measure("personalization_context", "构建用户侧个性化和购物车侧软约束上下文"):
            context = self._build_personalization_context(
                user_id=user_id,
                parsed_query=parsed_query,
                state=state,
                candidates=candidates,
            )
            if cart_personalization_context.get("是否启用"):
                context["购物车商品侧个性化"] = {
                    "参考购物车商品": [
                        {
                            "sku_id": item.get("sku_id"),
                            "name": item.get("name"),
                            "brand": item.get("brand"),
                            "category": item.get("category"),
                            "sub_category": item.get("sub_category"),
                            "price": item.get("price"),
                        }
                        for item in cart_personalization_context.get("参考购物车商品", [])[:6]
                    ],
                    "商品标签": cart_personalization_context.get("商品标签", []),
                    "价格画像": cart_personalization_context.get("价格画像", {}),
                    "库存覆盖": cart_personalization_context.get("库存覆盖", {}),
                    "命中的本地规则": [
                        {
                            "rule_id": item.get("rule_id"),
                            "说明": item.get("说明"),
                        }
                        for item in cart_personalization_context.get("命中的本地规则", [])
                    ],
                    "是否调用Doubao": cart_personalization_context.get("是否调用Doubao"),
                    "Doubao分析摘要": {
                        key: value
                        for key, value in (cart_personalization_context.get("Doubao分析") or {}).items()
                        if key in {"商品标签", "推荐约束", "排序理由"}
                    },
                    "排序影响": cart_personalization_context.get("排序影响", [])[:5],
                }
            return context

    def _generate_response_timed(
        self,
        *,
        timer: RuntimeTimer,
        model_route: ModelRouteDecision,
        **kwargs,
    ) -> str:
        with timer.measure("response_generation", "Prompt 构造与回复生成"):
            response_text = self.response_generator.generate(model_route=model_route, **kwargs)
        timer.mark_model_call(
            module="response_generation",
            provider=self.response_generator.llm_client.__class__.__name__,
            purpose="generate_response",
            duration_ms=timer.last_duration("response_generation"),
            called=self.response_generator.last_llm_called,
            call_debug=self._llm_call_debug(),
        )
        return response_text

    def _refresh_local_model_status(self, model_route: ModelRouteDecision) -> tuple[ModelRouteDecision, dict]:
        if not self.model_router.local_models:
            payload = model_route.model_dump()
        else:
            model_route = model_route.model_copy(
                update={"local_model_status": self.model_router.local_models.status()}
            )
            payload = model_route.model_dump()
        payload["llm_provider"] = self.response_generator.llm_client.__class__.__name__
        return model_route, payload

    @staticmethod
    def _should_stream_recommendation_sections(decision: FlowDecision, cards: list[ProductCard]) -> bool:
        return bool(cards) and decision.flow in {
            DialogueFlow.RECOMMENDATION,
            DialogueFlow.FILTERING,
            DialogueFlow.REFINEMENT,
            DialogueFlow.EXCLUSION,
            DialogueFlow.NO_RESULT,
        }

    def _recommendation_section_events(self, cards: list[ProductCard], query_id: str) -> list[SSEEvent]:
        events: list[SSEEvent] = []
        turn_id = f"turn_{query_id}"
        for index, card in enumerate(cards, start=1):
            presentation = card.presentation
            option_label = (
                _clean_optional_text(presentation.option_label if presentation else None)
                or self._option_label(index)
            )
            reason = ((presentation.reason if presentation else None) or card.reason or "").strip()
            trade_off = _clean_optional_text(presentation.trade_off if presentation else None)
            content_source = presentation.content_source if presentation else "fallback"
            common = {
                "turn_id": turn_id,
                "section_index": index,
                "sku_id": card.sku_id,
                "option_label": option_label,
            }
            events.append(
                SSEEvent(
                    event="recommendation_section_start",
                    data={
                        **common,
                        "event_id": f"{turn_id}:{index}:start",
                        "product_name": card.name,
                        "brand": card.brand,
                    },
                )
            )
            if reason:
                for chunk_index, chunk in enumerate(self._chunk_text(reason, chunk_size=36), start=1):
                    events.append(
                        SSEEvent(
                            event="recommendation_text_delta",
                            data={
                                **common,
                                "event_id": f"{turn_id}:{index}:delta:{chunk_index}",
                                "delta": chunk,
                            },
                        )
                    )
            events.append(
                SSEEvent(
                    event="recommendation_text_done",
                    data={
                        **common,
                        "event_id": f"{turn_id}:{index}:text_done",
                        "reason": reason,
                        "trade_off": trade_off,
                        "content_source": content_source,
                    },
                )
            )
            events.append(
                SSEEvent(
                    event="product_card",
                    data={
                        **common,
                        "event_id": f"{turn_id}:{index}:product_card",
                        "product": card.model_dump(),
                    },
                )
            )
        return events

    @staticmethod
    def _option_label(index: int) -> str:
        labels = ["方案一", "方案二", "方案三", "方案四", "方案五"]
        return labels[index - 1] if index <= len(labels) else f"方案{index}"

    def _llm_call_debug(self) -> dict:
        return dict(getattr(self.response_generator.llm_client, "last_call_debug", {}) or {})

    @staticmethod
    def _is_blank_resume_state(state: SessionState) -> bool:
        """Allow resume after debug endpoints created an empty in-memory session."""
        dialogue = state.dialogue_state_tracking
        return (
            not state.recent_messages
            and not state.behaviours
            and not state.cart.items
            and not state.goods.last_recommendations
            and not state.goods.last_candidates
            and not state.trace_log
            and not dialogue.current_category
            and not dialogue.current_sub_category
        )

    @staticmethod
    def _product_enhancement_trace(candidates: list[CandidateProduct]) -> dict:
        used_fields: list[str] = []
        matched_non_standard_tags: list[str] = []
        matched_scenarios: list[str] = []
        matched_user_tags: list[str] = []
        ranking_effects: list[dict] = []
        for candidate in candidates[:8]:
            matches = candidate.enhancement_matches or {}
            used_fields.extend(matches.get("used_fields", []))
            matched_non_standard_tags.extend(matches.get("matched_non_standard_query_tags", []))
            matched_scenarios.extend(matches.get("matched_suitable_scenarios", []))
            matched_user_tags.extend(matches.get("matched_target_user_tags", []))
            enhancement_score = candidate.raw_scores.get("enhancement")
            if enhancement_score:
                ranking_effects.append(
                    {
                        "sku_id": candidate.sku_id,
                        "enhancement_score": enhancement_score,
                        "matched_reasons": candidate.matched_reasons[:5],
                        "matches": matches,
                    }
                )
        return {
            "是否启用": bool(candidates),
            "使用的增强字段": list(dict.fromkeys(used_fields)),
            "命中的非标准问题标签": list(dict.fromkeys(matched_non_standard_tags))[:10],
            "命中的适用场景": list(dict.fromkeys(matched_scenarios))[:10],
            "命中的人群标签": list(dict.fromkeys(matched_user_tags))[:10],
            "排序影响": ranking_effects[:6],
        }

    @staticmethod
    def _apply_multimodal_context(parsed_query: ParsedQuery, multimodal_context: dict) -> None:
        fused = multimodal_context.get("图文融合查询", {}) or {}
        visual = multimodal_context.get("图片理解结果", {}) or {}
        product_match = multimodal_context.get("视觉匹配商品", {}) or {}
        category = fused.get("映射商品类别")
        sub_category = fused.get("映射商品子类")
        visual_terms = [
            *visual.get("颜色", []),
            *visual.get("款式", []),
            *visual.get("材质或质感", []),
            *visual.get("图案", []),
            *visual.get("使用场景", []),
            *fused.get("视觉关键词", []),
        ]
        if category:
            parsed_query.category = category
            parsed_query.sub_category = sub_category
            parsed_query.need_clarification = False
            parsed_query.clarification_slots = []
        if parsed_query.intent in {IntentType.CHITCHAT.value, IntentType.OUT_OF_SCOPE.value, IntentType.INVALID.value}:
            parsed_query.intent = IntentType.RECOMMEND.value
        parsed_query.positive_constraints = _merge_lists(parsed_query.positive_constraints, [term for term in visual_terms if term])
        fused_text = fused.get("融合后的检索文本")
        if fused_text:
            parsed_query.rewritten_query = fused_text
        best_match = product_match.get("best_match") if product_match.get("是否启用") else None
        if best_match and best_match.get("sku_id"):
            parsed_query.mentioned_products = _merge_lists(parsed_query.mentioned_products, [best_match["sku_id"]])
        parsed_query.route_source = f"{parsed_query.route_source}+multimodal_fusion"
        if not fused.get("库存是否覆盖目标类目"):
            parsed_query.uncertain_points.append(f"multimodal_unsupported:{fused.get('目标商品类别')}")

    def _maybe_trigger_closing(self, state, parsed_query, preprocess) -> dict | None:
        """Decide whether to trigger checkout closing guidance.

        Only fires when:
        - Cart is non-empty
        - Current action is a cart operation (add/view/update)
        - User message contains NO new shopping demand signals
        - Not already offered and declined recently
        """
        cart_items = state.cart.items if state and hasattr(state, 'cart') else []
        if not cart_items:
            return None

        # Resolve product details and compute totals
        resolved_items = []
        cart_total = 0.0
        cart_count = 0
        for item in cart_items:
            product = self.product_repository.get_product(item.sku_id)
            name = product.name if product else item.sku_id
            price = product.price if product else 0
            qty = item.quantity if hasattr(item, 'quantity') else 1
            cart_total += price * qty
            cart_count += qty
            resolved_items.append({'name': name, 'price': price, 'sku_id': item.sku_id})

        # Read state tracking
        checkout_state = state.checkout_guidance or {}
        offered_count = checkout_state.get('offered_count', 0)
        declined_at_turn = checkout_state.get('declined_at_turn', -999)
        current_turn = len(state.recent_messages) // 2  # rough turn counter

        # Track current cart SKU set to detect new items
        current_cart_skus = frozenset(item.sku_id for item in cart_items)
        last_offered_skus = frozenset(checkout_state.get('offered_cart_skus', []))

        # If cart has new items since last offer, reset offered_count
        effective_offered_count = offered_count
        if current_cart_skus != last_offered_skus and last_offered_skus:
            effective_offered_count = 0

        should = ClosingGuide.should_trigger(
            cart_items=resolved_items,
            current_intent=parsed_query.intent if parsed_query else '',
            current_message=parsed_query.raw_message if parsed_query else '',
            checkout_offered_count=effective_offered_count,
            checkout_declined_recently=(current_turn - declined_at_turn) < 2,
            last_flow=state.dialogue_state_tracking.current_flow if state and hasattr(state, 'dialogue_state_tracking') else '',
        )
        if not should:
            return None

        # Update state
        state.checkout_guidance = {
            'offered_count': offered_count + 1,
            'last_offered_at_turn': current_turn,
            'declined_at_turn': declined_at_turn,
            'offered_cart_skus': list(current_cart_skus),
        }

        return ClosingGuide.build_guidance_context(
            cart_items=resolved_items,
            cart_total=cart_total,
            cart_count=cart_count,
        )

    @staticmethod
    def _is_closing_decline(parsed_query, state) -> bool:
        """Detect if user is declining a previously-offered checkout closing."""
        checkout_state = getattr(state, 'checkout_guidance', None) or {}
        if not checkout_state.get('offered_count', 0):
            return False
        msg = (parsed_query.raw_message or '').strip()
        if not ClosingGuide.is_decline_signal(msg):
            return False
        # “刚才加购的防晒不要了/清空购物车”是真实购物车动作，不是拒绝结算。
        cart_mutation_terms = [
            "清空购物车", "购物车清空", "删掉", "删除", "移除", "拿掉", "撤掉",
            "不要了", "不要这款", "不要那个", "不要刚才", "加购的", "加到购物车的",
        ]
        if any(term in msg for term in cart_mutation_terms):
            return False
        checkout_terms = ["结算", "下单", "付款", "支付", "订单"]
        short_decline = len(msg) <= 12 and not any(term in msg for term in ["推荐", "挑选", "选择", "加入购物车", "加购"])
        return short_decline or any(term in msg for term in checkout_terms)

    @staticmethod
    def _is_closing_acceptance(parsed_query, state, decision) -> bool:
        """Detect if user is accepting a previously-offered checkout closing guidance.

        Triggers when:
        - Closing guidance was offered in the previous turn
        - Current message is a short affirmative (好的/可以/行/确认/下单吧)
        - Cart is non-empty
        - Current flow is NOT already checkout (avoid double-trigger)
        """
        if decision.flow == DialogueFlow.CHECKOUT:
            return False  # Already checkout
        cart_items = state.cart.items if state and hasattr(state, 'cart') else []
        if not cart_items:
            return False
        checkout_state = getattr(state, 'checkout_guidance', None) or {}
        if not checkout_state.get('offered_count', 0):
            return False  # Closing was never offered
        msg = (parsed_query.raw_message or '').strip()
        # Short affirmative messages that suggest accepting the closing offer
        return ClosingGuide.is_accept_signal(msg) and not ClosingGuide._has_new_demand(msg)

    @staticmethod
    def _multimodal_target_is_unsupported(multimodal_context: dict) -> bool:
        if not multimodal_context.get("是否启用多模态"):
            return False
        fused = multimodal_context.get("图文融合查询", {}) or {}
        return fused.get("库存是否覆盖目标类目") is False

    @staticmethod
    def _tool_intents() -> set[str]:
        return {
            IntentType.CART_ADD.value,
            IntentType.CART_REMOVE.value,
            IntentType.CART_UPDATE.value,
            IntentType.CART_CLEAR.value,
            IntentType.CART_VIEW.value,
            IntentType.CART_KEEP_ONLY.value,
            IntentType.CHECKOUT.value,
        }

    @staticmethod
    def _retrieval_intents() -> set[str]:
        return {
            IntentType.RECOMMEND.value,
            IntentType.FILTER.value,
            IntentType.REFINE.value,
            IntentType.COMPARE.value,
            IntentType.DETAIL.value,
            IntentType.SCENE_BUNDLE.value,
        }

    @classmethod
    def _has_mixed_intent_plan(cls, parsed_query: ParsedQuery) -> bool:
        if not parsed_query.intent_plan or not parsed_query.intent_plan.steps:
            return False
        intents = [step.intent for step in parsed_query.intent_plan.steps]
        return any(intent in cls._tool_intents() for intent in intents) and any(
            intent in cls._retrieval_intents() for intent in intents
        )

    @classmethod
    def _last_retrieval_step(cls, parsed_query: ParsedQuery):
        if not parsed_query.intent_plan:
            return None
        for step in reversed(parsed_query.intent_plan.steps):
            if step.intent in cls._retrieval_intents():
                return step
        return None

    def _apply_retrieval_step_to_query(self, parsed_query: ParsedQuery, step, state) -> None:
        source_text = (step.source_text or "").strip() or parsed_query.raw_message
        parsed_query.intent = step.intent
        parsed_query.inherit_context = False
        step_price = self.query_understanding._extract_price_range(source_text)
        if step_price.min is not None or step_price.max is not None:
            parsed_query.price_range = step_price
        step_negative = self.query_understanding._extract_negative_constraints(source_text)
        step_positive = self.query_understanding._extract_positive_constraints(source_text, step_negative)
        step_category, step_sub_category = self.query_understanding._extract_category(source_text)
        if step_category:
            parsed_query.category = step_category
            parsed_query.sub_category = step_sub_category
        elif parsed_query.category == state.dialogue_state_tracking.current_category:
            parsed_query.inherit_context = True
        if step_positive:
            parsed_query.positive_constraints = step_positive
        if step_negative:
            parsed_query.negative_constraints = step_negative
        step_include, step_exclude = self.query_understanding._extract_brands(source_text)
        if step_include:
            parsed_query.brands_include = step_include
        if step_exclude:
            parsed_query.brands_exclude = step_exclude
        parsed_query.rewritten_query = self.query_understanding._rewrite_query(
            message=source_text,
            category=parsed_query.category,
            sub_category=parsed_query.sub_category,
            price_range=parsed_query.price_range,
            positive_constraints=parsed_query.positive_constraints,
            negative_constraints=parsed_query.negative_constraints,
            brands_exclude=parsed_query.brands_exclude,
        )
        parsed_query.need_clarification, parsed_query.clarification_slots = self.query_understanding._detect_clarification_need(
            intent=IntentType(step.intent),
            category=parsed_query.category,
            sub_category=parsed_query.sub_category,
            message=source_text,
            positive_constraints=parsed_query.positive_constraints,
            price_range=parsed_query.price_range,
        )
        parsed_query.route_source = f"{parsed_query.route_source}+mixed_intent_retrieval_step"

    @staticmethod
    def _has_executable_intent_plan(parsed_query: ParsedQuery) -> bool:
        if not parsed_query.intent_plan or not parsed_query.intent_plan.is_multi_intent:
            return False
        return all(step.intent in ShoppingAgent._tool_intents() for step in parsed_query.intent_plan.steps)

    def _execute_intent_plan(
        self,
        *,
        session_id: str,
        query_id: str,
        parsed_query: ParsedQuery,
        state,
    ) -> tuple[ToolExecutionResult, list[ToolExecutionResult]]:
        assert parsed_query.intent_plan is not None
        calls: list[ToolExecutionResult] = []
        last_result: ToolExecutionResult | None = None
        protected_sku_ids: set[str] = set()
        for step in parsed_query.intent_plan.steps:
            step_query = self._query_for_tool_step(parsed_query, step, protected_sku_ids)
            expected_sku_id = self.action_executor._resolve_target_sku(step_query, state, cart_first=step.intent in {"cart_remove", "cart_update"})
            last_result = self.action_executor.execute_cart_action(
                session_id=session_id,
                parsed_query=step_query,
                state=state,
            )
            calls.append(last_result)
            self._record_cart_event_from_tool_result(
                session_id=session_id,
                query_id=query_id,
                message=(step.source_text or parsed_query.raw_message),
                parsed_query=step_query,
                tool_result=last_result,
                expected_sku_id=expected_sku_id,
            )
            if last_result.ok and step.intent == IntentType.CART_ADD.value and expected_sku_id:
                protected_sku_ids.add(expected_sku_id)
            if not last_result.ok and step.intent != IntentType.CART_CLEAR.value:
                break
        if last_result is None:
            last_result = self.action_executor.execute_cart_action(
                session_id=session_id,
                parsed_query=parsed_query,
                state=state,
            )
            calls.append(last_result)
        return last_result, calls

    def _execute_tool_steps_from_intent_plan(
        self,
        *,
        session_id: str,
        query_id: str,
        parsed_query: ParsedQuery,
        state,
    ) -> tuple[ToolExecutionResult | None, list[ToolExecutionResult]]:
        if not parsed_query.intent_plan:
            return None, []
        calls: list[ToolExecutionResult] = []
        last_result: ToolExecutionResult | None = None
        protected_sku_ids: set[str] = set()
        for step in parsed_query.intent_plan.steps:
            if step.intent not in self._tool_intents():
                continue
            step_query = self._query_for_tool_step(parsed_query, step, protected_sku_ids)
            expected_sku_id = self.action_executor._resolve_target_sku(step_query, state, cart_first=step.intent in {"cart_remove", "cart_update"})
            last_result = self.action_executor.execute_cart_action(
                session_id=session_id,
                parsed_query=step_query,
                state=state,
            )
            calls.append(last_result)
            self._record_cart_event_from_tool_result(
                session_id=session_id,
                query_id=query_id,
                message=(step.source_text or parsed_query.raw_message),
                parsed_query=step_query,
                tool_result=last_result,
                expected_sku_id=expected_sku_id,
            )
            if last_result.ok and step.intent == IntentType.CART_ADD.value and expected_sku_id:
                protected_sku_ids.add(expected_sku_id)
            if not last_result.ok:
                break
        return last_result, calls

    def _record_cart_event_from_tool_result(
        self,
        *,
        session_id: str,
        query_id: str,
        message: str,
        parsed_query: ParsedQuery,
        tool_result: ToolExecutionResult | None,
        expected_sku_id: str | None = None,
    ) -> None:
        if tool_result is None or not tool_result.ok:
            return
        sku_ids: list[str] = []
        if expected_sku_id:
            sku_ids.append(expected_sku_id)
        if parsed_query.cart_action and parsed_query.cart_action.sku_id:
            sku_ids.append(parsed_query.cart_action.sku_id)
        for item in tool_result.payload.get("items", []) if isinstance(tool_result.payload, dict) else []:
            sku_id = item.get("sku_id") if isinstance(item, dict) else None
            if sku_id:
                sku_ids.append(sku_id)
        self.session_memory.record_cart_event(
            session_id=session_id,
            query_id=query_id,
            source_message=message,
            action=tool_result.tool_name,
            sku_ids=list(dict.fromkeys(sku_ids)),
            quantity=parsed_query.cart_action.quantity if parsed_query.cart_action else None,
            target_ref=parsed_query.cart_action.target_ref if parsed_query.cart_action else None,
            tool_result={
                "ok": tool_result.ok,
                "tool_name": tool_result.tool_name,
                "message": tool_result.message,
                "error_code": tool_result.error_code,
                "total_items": tool_result.payload.get("total_items") if isinstance(tool_result.payload, dict) else None,
                "total_price": tool_result.payload.get("total_price") if isinstance(tool_result.payload, dict) else None,
            },
        )

    def _query_for_tool_step(
        self,
        parsed_query: ParsedQuery,
        step: IntentStep,
        protected_sku_ids: set[str],
    ) -> ParsedQuery:
        step_text = (step.source_text or parsed_query.raw_message).strip()
        step_query = parsed_query.model_copy(deep=True)
        step_query.raw_message = step_text
        step_query.intent = step.intent
        step_query.mentioned_products = [step.sku_id] if step.sku_id else []
        step_query.referents = [step.target_ref] if step.target_ref else self._references_in_text(step_text)
        step_category, step_sub_category = self.query_understanding._extract_category(step_text)
        if step_category:
            step_query.category = step_category
            step_query.sub_category = step_sub_category
        step_negative = self.query_understanding._extract_negative_constraints(step_text)
        step_positive = self.query_understanding._extract_positive_constraints(step_text, step_negative)
        if step_negative:
            step_query.negative_constraints = step_negative
        if step_positive:
            step_query.positive_constraints = step_positive
        step_include, step_exclude = self.query_understanding._extract_brands(step_text)
        if step_include:
            step_query.brands_include = step_include
        if step_exclude:
            step_query.brands_exclude = step_exclude
        parent_action = parsed_query.cart_action
        exclude_sku_ids = list(dict.fromkeys([
            *step.exclude_sku_ids,
            *(parent_action.exclude_sku_ids if parent_action else []),
            *(protected_sku_ids if step.intent == IntentType.CART_REMOVE.value and "其他" in step_text else []),
        ]))
        keep_categories = step.keep_categories or (parent_action.keep_categories if parent_action else [])
        keep_sub_categories = step.keep_sub_categories or (parent_action.keep_sub_categories if parent_action else [])
        if not keep_categories and not keep_sub_categories:
            if step_category and not step_sub_category:
                keep_categories = [step_category]
            if step_sub_category:
                keep_sub_categories = [step_sub_category]
        step_query.cart_action = CartAction(
            action=step.intent,
            quantity=step.quantity,
            target_ref=step.target_ref,
            sku_id=step.sku_id,
            keep_categories=keep_categories,
            keep_sub_categories=keep_sub_categories,
            exclude_sku_ids=exclude_sku_ids,
        )
        return step_query

    @staticmethod
    def _build_simple_parsed_query(preprocess) -> ParsedQuery:
        intent_by_route = {
            "greeting": IntentType.CHITCHAT.value,
            "out_of_scope": IntentType.OUT_OF_SCOPE.value,
            "invalid": IntentType.INVALID.value,
        }
        return ParsedQuery(
            raw_message=preprocess.normalized_message or preprocess.raw_message,
            intent=intent_by_route.get(preprocess.simple_route, IntentType.CHITCHAT.value),
            confidence=1.0 if preprocess.valid else 0.0,
            route_source="preprocess",
        )

    @staticmethod
    def _simple_flow_decision(preprocess, parsed_query: ParsedQuery) -> FlowDecision:
        if preprocess.simple_route == "invalid":
            return FlowDecision(flow=DialogueFlow.INVALID, reason=preprocess.reason or "invalid", need_retrieval=False, need_llm=False)
        if preprocess.simple_route == "out_of_scope":
            return FlowDecision(flow=DialogueFlow.OUT_OF_SCOPE, reason="out_of_scope", need_retrieval=False, need_llm=False)
        if preprocess.simple_route == "greeting":
            return FlowDecision(flow=DialogueFlow.GREETING, reason="greeting", need_retrieval=False, need_llm=False)
        return FlowDecision(flow=DialogueFlow.CHITCHAT, reason="template", need_retrieval=False, need_llm=False)

    @staticmethod
    def _is_privacy_only_message(message: str) -> bool:
        privacy_terms = [
            "关闭个性化推荐",
            "关闭个性化",
            "不要个性化",
            "取消个性化",
            "关闭推荐记忆",
            "不要根据历史推荐",
            "隐私个性化",
            "只用匿名",
            "只用向量",
            "只用语义",
            "不要用原文历史",
            "不要读取历史聊天",
            "保护隐私但个性化",
            "开启个性化",
            "恢复个性化",
            "允许个性化",
            "可以根据历史推荐",
            "使用我的历史偏好",
            "不要保存聊天",
            "不保存聊天",
            "不要记录聊天",
            "清除原文",
            "不要保存原文",
            "可以保存聊天",
            "恢复保存聊天",
            "允许保存原文",
        ]
        shopping_terms = [
            "推荐",
            "买",
            "挑",
            "选",
            "选择",
            "看看",
            "查看",
            "详情",
            "加入购物车",
            "加购",
            "购物车",
            "下单",
            "结算",
            "付款",
            "商品",
            "产品",
            "手机",
            "耳机",
            "电脑",
            "相机",
            "洗面奶",
            "洁面",
            "防晒",
            "面霜",
            "精华",
            "眼线笔",
            "短袖",
            "T恤",
            "背包",
            "跑鞋",
            "鞋",
            "穿搭",
            "饮料",
            "零食",
            "早餐",
            "文具",
            "收纳",
            "第一个",
            "第一款",
            "第二个",
            "第二款",
            "刚才那个",
            "刚才那款",
            "这个",
            "这款",
            "它",
        ]
        if not any(term in message for term in privacy_terms):
            return False
        remaining = message
        for term in sorted(privacy_terms, key=len, reverse=True):
            remaining = remaining.replace(term, "")
        return not any(term in remaining for term in shopping_terms)

    def _record_turn(
        self,
        *,
        session_id: str,
        query_id: str,
        message: str,
        flow: str,
        parsed_query: ParsedQuery,
        candidates: list[CandidateProduct],
        task_plan: list[str],
        missing_slots: list[str],
        model_route: ModelRouteDecision,
        preference_updated: bool,
    ) -> None:
        state = self.session_memory.get_or_create(session_id)
        same_topic = False if parsed_query.intent == IntentType.SCENE_BUNDLE.value else (
            parsed_query.category is None
            or (
                parsed_query.category == state.dialogue_state_tracking.current_category
                and (
                    parsed_query.sub_category is None
                    or state.dialogue_state_tracking.current_sub_category is None
                    or parsed_query.sub_category == state.dialogue_state_tracking.current_sub_category
                )
            )
        )
        previous_constraints = state.dialogue_state_tracking.active_constraints if same_topic else {}
        active_constraints = {
            **previous_constraints,
            "price_min": parsed_query.price_range.min if parsed_query.price_range.min is not None else previous_constraints.get("price_min"),
            "price_max": parsed_query.price_range.max if parsed_query.price_range.max is not None else previous_constraints.get("price_max"),
            "features": _merge_lists(previous_constraints.get("features", []), parsed_query.positive_constraints),
            "negative_constraints": _merge_lists(previous_constraints.get("negative_constraints", []), parsed_query.negative_constraints),
            "exclude_brands": _merge_lists(previous_constraints.get("exclude_brands", []), parsed_query.brands_exclude),
            "include_brands": _merge_lists(previous_constraints.get("include_brands", []), parsed_query.brands_include),
            "scenario": parsed_query.scenario or previous_constraints.get("scenario"),
        }
        related_sku_ids = [item.sku_id for item in candidates]
        self.session_memory.append_behaviour(
            session_id=session_id,
            behaviour=BehaviourRecord(
                turn_id=len(state.behaviours) + 1,
                intent=parsed_query.intent,
                query_id=query_id,
                user_query=message,
                target_category=parsed_query.category,
                related_sku_ids=related_sku_ids,
                timestamp=datetime.now().isoformat(timespec="seconds"),
            ),
        )
        self.session_memory.update_dialogue_state(
            session_id=session_id,
            current_intent=parsed_query.intent,
            current_flow=flow,
            current_category=parsed_query.category if parsed_query.intent == IntentType.SCENE_BUNDLE.value else parsed_query.category or state.dialogue_state_tracking.current_category,
            current_sub_category=parsed_query.sub_category if parsed_query.intent == IntentType.SCENE_BUNDLE.value else parsed_query.sub_category or state.dialogue_state_tracking.current_sub_category,
            slots={
                "category": parsed_query.category,
                "sub_category": parsed_query.sub_category,
                "scenario": parsed_query.scenario,
                "target_user": parsed_query.target_user,
                "last_candidate_count": len(candidates),
                "preference_updated": preference_updated,
            },
            active_constraints=active_constraints,
            missing_slots=missing_slots,
            task_plan=task_plan,
        )

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 24) -> list[str]:
        return [text[index:index + chunk_size] for index in range(0, len(text), chunk_size)] or [""]

    @staticmethod
    def _merge_context_constraints(parsed_query: ParsedQuery, state) -> None:
        if parsed_query.intent == IntentType.SCENE_BUNDLE.value:
            return
        context_terms = ["继续", "上次", "刚才", "前面", "告诉我", "哪些", "合适", "再", "换", "更", "便宜", "贵", "只剩", "还剩", "剩下", "零花钱", "不要", "排除", "这个", "那个", "它", "一起", "分享", "配着"]
        explicit_new_scope = (
            bool(parsed_query.category or parsed_query.sub_category)
            and not parsed_query.inherit_context
            and not any(
                term in parsed_query.raw_message
                for term in ["继续", "上次", "刚才", "前面", "这个", "那个", "它", "第", "哪些", "合适", "再", "换", "更", "便宜", "贵了", "太贵"]
            )
        )
        if explicit_new_scope:
            return
        same_topic = (
            parsed_query.category is None
            or state.dialogue_state_tracking.current_category is None
            or (
                parsed_query.category == state.dialogue_state_tracking.current_category
                and (
                    parsed_query.sub_category is None
                    or state.dialogue_state_tracking.current_sub_category is None
                    or parsed_query.sub_category == state.dialogue_state_tracking.current_sub_category
                )
            )
        )
        should_inherit = (
            parsed_query.inherit_context
            or parsed_query.intent == IntentType.REFINE.value
            or any(term in parsed_query.raw_message for term in context_terms)
        )
        if not should_inherit or not same_topic:
            return
        parsed_query.inherit_context = True
        constraints = state.dialogue_state_tracking.active_constraints
        if parsed_query.price_range.min is None:
            parsed_query.price_range.min = constraints.get("price_min")
        if parsed_query.price_range.max is None:
            parsed_query.price_range.max = constraints.get("price_max")
        parsed_query.positive_constraints = _merge_lists(constraints.get("features", []), parsed_query.positive_constraints)
        parsed_query.negative_constraints = _merge_lists(constraints.get("negative_constraints", []), parsed_query.negative_constraints)
        parsed_query.brands_exclude = _merge_lists(constraints.get("exclude_brands", []), parsed_query.brands_exclude)
        parsed_query.brands_include = _merge_lists(constraints.get("include_brands", []), parsed_query.brands_include)

    @staticmethod
    def _state_debug_snapshot(state) -> dict:
        dialogue = state.dialogue_state_tracking
        return {
            "当前流程": dialogue.current_flow,
            "当前意图": dialogue.current_intent,
            "当前类别": dialogue.current_category,
            "当前子类": dialogue.current_sub_category,
            "活跃约束": dialogue.active_constraints,
            "缺失槽位": dialogue.missing_slots,
            "购物车数量": sum(item.quantity for item in state.cart.items),
            "最近推荐商品": [item.sku_id for item in state.goods.last_recommendations],
            "用户画像摘要": state.user_profile_summary_text,
        }


def _merge_lists(old: list, new: list) -> list:
    return list(dict.fromkeys([*old, *new]))


def _clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    return text


def _minimal_error_turn_output(session_id: str, user_id: str, exc: Exception) -> dict:
    return {
        "frontend_events": [
            {
                "步骤": 1,
                "动作类型": "show_reply",
                "含义": "展示系统回复",
                "数据参考": "reply_message",
                "blocking": False,
            },
            {
                "步骤": 2,
                "动作类型": "show_error",
                "含义": "展示错误或无结果提示",
                "数据参考": "error_message",
                "blocking": False,
            },
        ],
        "frontend_data": {
            "reply_message": {
                "中文说明": "系统异常时展示给用户的兜底回复。",
                "text": "系统处理时遇到问题，请稍后重试。",
            },
            "error_message": {
                "中文说明": "后端异常信息，前端只需要展示 message，不需要展示内部错误。",
                "code": "AGENT_ERROR",
                "message": "系统处理时遇到问题，请稍后重试。",
            },
        },
        "system_debug": {
            "中文说明": "本部分用于后端调试，展示并行主流程逃逸异常的安全网输出。",
            "session_id": session_id,
            "user_id": user_id,
            "异常信息": {"message": str(exc)},
        },
    }
