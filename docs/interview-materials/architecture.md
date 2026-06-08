# 系统架构

## 整体架构 【代码确认】

```
┌──────────────────────────────────────────────────────────────┐
│                    Android Client                            │
│  ChatScreen / ImageSearch / Cart / Checkout / ProductDetail  │
│  ChatViewModel ── SSE Parser ── ShoppingRepository           │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP POST / SSE
┌──────────────────────────▼───────────────────────────────────┐
│                   FastAPI Application                        │
│  ┌─────────────┐  ┌──────────────────────────────────────┐  │
│  │ API Routes  │  │  /api/chat/stream (text+image)       │  │
│  │             │  │  /api/products, /api/cart, /session   │  │
│  └──────┬──────┘  └──────────────────────────────────────┘  │
│         │                                                     │
│  ┌──────▼──────────────────────────────────────────────────┐ │
│  │              ShoppingAgent (核心编排器)                  │ │
│  │  stream_chat() → _stream_chat_core() (2715行)          │ │
│  │                                                        │ │
│  │  阶段1: 预处理 (InputPreprocessor)                      │ │
│  │  阶段2: 意图理解 (QueryUnderstandingModule)             │ │
│  │       ├─ 严格模板 (本地正则)                             │ │
│  │       ├─ LLM IntentPlan (Doubao JSON)                  │ │
│  │       └─ 规则回退 (legacy rule)                         │ │
│  │  阶段3: 流程决策 (DialogueFlowController)               │ │
│  │  阶段4: 任务规划 (TaskPlanner)                           │ │
│  │  阶段5: 模型路由 (ModelRouter)                           │ │
│  │  阶段6: 数据加载 + 个性化                                │ │
│  │  阶段7: 按流程分支执行                                    │ │
│  │       ├─ A. 模板回复 (greeting/out-of-scope)            │ │
│  │       ├─ B. 购物车/结账 (ActionExecutor)                │ │
│  │       ├─ C. 偏好更新 (PreferenceManager)                │ │
│  │       ├─ D. 场景捆绑 (ScenarioPlanner)                  │ │
│  │       ├─ E. 检索推荐 (HybridRetriever + LLM)            │ │
│  │       └─ F. 其他 (chitchat/clarification)              │ │
│  │  阶段8: 响应验证 (ResponseValidator)                     │ │
│  │  阶段9: 展示构建 (ScenePresentationBuilder)              │ │
│  │  阶段10: SSE事件输出 + 状态持久化                         │ │
│  └──────────────────────────────────────────────────────────┘ │
│         │                  │              │                   │
│  ┌──────▼──────┐  ┌────────▼──────┐  ┌───▼──────────────┐   │
│  │  Retrieval  │  │    Memory     │  │  Multimodal      │   │
│  │  Layer      │  │    Layer      │  │  Layer           │   │
│  │             │  │               │  │                  │   │
│  │ Hybrid      │  │ SessionMemory │  │ VisionAnalyzer   │   │
│  │ Retriever   │  │ UserHistory   │  │ VisualQuery      │   │
│  │ Keyword     │  │ Store         │  │ Builder          │   │
│  │ Vector      │  │ UserProfile   │  │ VisualProduct    │   │
│  │ Fallback    │  │ Service       │  │ Matcher          │   │
│  │ PostProc    │  │ Personalizat. │  │                  │   │
│  └─────────────┘  └───────────────┘  └──────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               Tools & Services                        │   │
│  │  CartService / CheckoutService / OrderService         │   │
│  │  ProductRepository (JSON → Product 对象)              │   │
│  │  LocalModelManager (BGE / text2vec / BGE-reranker)   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               LLM Layer                               │   │
│  │  BaseLLMClient (ABC)                                  │   │
│  │  ├─ DoubaoClient (真实API, 生产)                      │   │
│  │  └─ MockLLMClient (本地规则, 开发/测试)               │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## 模块划分 【代码确认】

### 1. Agent 编排层 (`backend/app/agents/`)

| 模块 | 文件 | 核心职责 |
|------|------|---------|
| ShoppingAgent | `shopping_agent.py` (2715行) | 主编排器，协调所有模块完成一轮对话 |
| QueryUnderstanding | `query_understanding.py` | 三阶意图理解（模板→LLM→规则） |
| IntentParser | `intent_parser.py` | 遗留规则意图解析器（已基本被 QueryUnderstanding 替代） |
| DialogueFlowController | `dialogue_flow.py` | 决定当前对话属于哪个业务流程 |
| TaskPlanner | `task_planner.py` | 将流程决策展开为具体的任务步骤列表 |
| ModelRouter | `model_router.py` | 决定使用模板/本地模型/LLM |
| InputPreprocessor | `input_preprocessor.py` | 请求前置检查（问候检测、越界检测、重复检测） |
| ResponseGenerator | `response_generator.py` | 按流程路由生成回复（模板/LLM） |
| ResponseValidator | `response_validator.py` | 校验LLM输出（防幻觉：产品名+价格检查） |
| ScenarioPlanner | `scenario_planner.py` | 场景捆绑分解（8种预设场景） |
| ProductQAModule | `product_qa.py` | 商品问答（成分、肤质、续航等） |
| FrontendActionPlanner | `frontend_action_planner.py` | 决定前端UI动作（导航、展示等） |
| FrontendEventBuilder | `frontend_event_builder.py` | 构建三部分输出（事件+数据+调试） |
| ScenePresentationBuilder | `scene_presentation_builder.py` | 构建每商品推荐理由和对比数据 |
| RecommendationStreaming | `recommendation_streaming.py` | 推荐内容流式展示（SECTION标记协议） |
| ClosingGuide | `closing_guide.py` | 结账引导触发和话术生成 |

### 2. 检索层 (`backend/app/retrieval/`)

| 模块 | 文件 | 核心职责 |
|------|------|---------|
| HybridRetriever | `hybrid_retriever.py` | 多阶段混合检索（硬过滤→7维打分→模型融合→排序） |
| KeywordRetriever | `keyword_retriever.py` | 纯关键词检索 |
| VectorRetriever | `vector_retriever.py` | 纯向量检索（基于本地 embedding） |
| PostProcessor | `post_processor.py` | 检索后处理（去重、硬过滤、否定词安全处理） |
| Fallback | `fallback.py` | 4级渐进式检索容错 |
| Base | `base.py` | 检索器抽象接口 |

### 3. 记忆层 (`backend/app/memory/`)

| 模块 | 文件 | 核心职责 |
|------|------|---------|
| SessionMemory | `session_memory.py` | 会话内状态（对话状态、事件记忆、引用消解） |
| UserHistoryStore | `user_history_store.py` | 持久化用户历史（文件系统JSON） |
| UserProfileService | `user_profile_service.py` | 用户画像生成（LLM摘要+规则回退） |
| PersonalizationService | `personalization_service.py` | 个性化上下文构建（证据选择+协同过滤+同类偏好） |
| CartAwarePersonalization | `cart_aware_personalization.py` | 购物车感知的个性化重排序 |
| PreferenceManager | `preference_manager.py` | 用户偏好管理 |
| InMemoryStore | `in_memory_store.py` | 内存键值存储 |

### 4. LLM 层 (`backend/app/llm/`)

| 模块 | 文件 | 核心职责 |
|------|------|---------|
| BaseLLMClient | `base.py` | LLM 客户端抽象接口（6个方法） |
| DoubaoClient | `doubao_client.py` | 豆包 API 客户端（HTTP + SSE 流式 + JSON 提取） |
| MockLLMClient | `mock_llm.py` | 本地规则引擎（200+行意图解析+模板回复+流式模拟） |

### 5. 多模态层 (`backend/app/multimodal/`)

| 模块 | 文件 | 核心职责 |
|------|------|---------|
| MultimodalService | `multimodal_service.py` | 端到端图片搜索编排 |
| VisionAnalyzer | `vision_analyzer.py` | 调用VLM分析图片属性 |
| VisualQueryBuilder | `visual_query_builder.py` | 视觉属性+文本查询融合 |
| VisualProductMatcher | `visual_product_matcher.py` | 图片→商品匹配（3策略：fixture/别名/特征相似度） |
| VisualRetriever | `visual_retriever.py` | 视觉候选增强 |
| ImageLoader/Preprocessor | | 图片加载和预处理 |

### 6. 工具层 (`backend/app/tools/`)

| 模块 | 文件 | 核心职责 |
|------|------|---------|
| ActionExecutor | `action_executor.py` | 购物车+结账动作执行（SKU解析+规格匹配） |
| ProductSearchTool | `product_search_tool.py` | 检索工具封装 |
| CartTool | `cart_tool.py` | 购物车操作封装 |
| CheckoutTool | `checkout_tool.py` | 结账操作封装 |
| OrderTool | `order_tool.py` | 订单操作封装 |
| RagTool | `rag_tool.py` | RAG管道封装 |

### 7. 服务层 (`backend/app/services/`)

| 模块 | 核心职责 |
|------|---------|
| CartService | 购物车CRUD（支持多SKU、规格选择） |
| CheckoutService | 结账预览 |
| OrderService | 演示订单创建 |
| ProductService | 商品查询和过滤 |

## 核心数据流 【代码确认】

### 一次完整的推荐对话

```
1. POST /api/chat/stream { session_id, message, user_id }
   → chat.py:16 → shopping_agent.stream_chat()

2. InputPreprocessor.preprocess()
   → 检查空输入/问候/越界/重复
   → 如果命中简单路由，直接返回模板回复

3. QueryUnderstandingModule.parse()
   → 严格模板匹配 (正则, 本地, <1ms)
   → 失败时: Doubao LLM IntentPlan (HTTP, ~2s)
   → 失败时: 规则回退 (本地, ~50ms)
   → 输出: ParsedQuery (25字段)

4. DialogueFlowController.decide()
   → 根据意图类型决定业务流程 (17种)
   → 输出: FlowDecision

5. TaskPlanner.plan()
   → 将流程展开为任务步骤列表
   → 输出: TaskPlan

6. ModelRouter.route()
   → 决定用模板/本地模型/LLM
   → 输出: ModelRouteDecision

7. HybridRetriever.retrieve() (如果需要检索)
   → 硬过滤 → 7维打分 → 模型embedding → 加权融合 → 排序
   → 输出: CandidateProduct[]

8. CartAwarePersonalization.rerank() (如果有购物车)
   → 根据购物车内容调整排序

9. PostProcessor.finalize()
   → 去重 → 硬过滤 → 否定词安全处理 → 截断

10. PersonalizationService.build_context()
    → 证据选择 → few-shot构建 → 协同过滤 → 策略生成

11. RagPipeline.build_context()
    → 组合商品事实 + prompt + 个性化上下文

12. ResponseGenerationModule.generate()
    → 按流程路由 → 模板或LLM生成回复

13. ResponseValidator.validate_with_result()
    → 检查LLM输出中是否出现非候选商品名/价格

14. ScenePresentationBuilder.build()
    → 为每个商品生成推荐理由和对比数据

15. FrontendActionPlanner.decide()
    → 决定前端UI动作

16. FrontendEventBuilder.build()
    → 构建三部分输出

17. SSE 事件序列输出
    → progress → token → recommendation_section_* → product_card
    → turn_result → done

18. 状态持久化
    → SessionMemory (会话状态)
    → UserHistoryStore.save_turn() (用户历史)
    → UserProfileService.maybe_refresh_profile() (画像刷新)
```

## Agent 调用链 【代码确认】

### 依赖注入关系

文件：`backend/app/core/dependencies.py`

`ShoppingAgent` 接收 **20 个** 依赖模块：

```python
ShoppingAgent(
    query_understanding,        # QueryUnderstandingModule
    input_preprocessor,         # InputPreprocessor
    model_router,               # ModelRouter
    flow_controller,            # DialogueFlowController
    task_planner,               # TaskPlanner
    session_memory,             # SessionMemory
    product_repository,         # ProductRepository
    product_search_tool,        # ProductSearchTool
    post_processor,             # ProductPostProcessor
    action_executor,            # ActionExecutor
    preference_manager,         # PreferenceManager
    product_qa_module,          # ProductQAModule
    scenario_planner,           # ScenarioPlanner
    response_generator,         # ResponseGenerationModule
    response_validator,         # ResponseValidator
    scene_presentation_builder, # ScenePresentationBuilder
    frontend_action_planner,    # FrontendActionPlanner
    frontend_event_builder,     # FrontendEventBuilder
    user_history_store,         # UserHistoryStore
    user_profile_service,       # UserProfileService
    personalization_service,    # PersonalizationService
    multimodal_service,         # MultimodalService
    progress_event_builder,     # ProgressEventBuilder
    cart_aware_personalization, # CartAwarePersonalization
)
```

所有依赖通过 `@lru_cache` 单例模式创建（`dependencies.py:53-320`）。

### 线程模型

`ShoppingAgent.stream_chat()` 使用 `asyncio.to_thread` 将核心逻辑放入独立线程：
- 主协程：管理 SSE 事件队列、进度事件交错发送（默认 700ms 间隔）
- 工作线程：执行 `_stream_chat_core()` 全部业务逻辑
- 通信：`asyncio.Queue[SSEEvent | None]`

证据：`backend/app/agents/shopping_agent.py:143-175`

## 关键类和接口

### ShoppingAgent
- 路径：`backend/app/agents/shopping_agent.py:64`
- 类型：核心编排器
- 关键方法：`stream_chat()` (L119), `_stream_chat_core()` (L232)

### QueryUnderstandingModule
- 路径：`backend/app/agents/query_understanding.py`
- 类型：意图理解
- 关键方法：`parse()` (三阶解析入口)

### HybridRetriever
- 路径：`backend/app/retrieval/hybrid_retriever.py`
- 类型：混合检索器
- 关键方法：`retrieve()`, `_hard_filter()`, `_keyword_score()`, `_semantic_score()`

### DoubaoClient
- 路径：`backend/app/llm/doubao_client.py`
- 类型：LLM 客户端
- 关键方法：`generate_response()`, `stream_generate_response()`, `resolve_user_intent()`, `analyze_image()`

### SessionMemory
- 路径：`backend/app/memory/session_memory.py`
- 类型：会话记忆
- 关键方法：`record_recommendation_event()`, `build_reference_map()`, `resolve_reference_from_memory_events()`

### UserHistoryStore
- 路径：`backend/app/memory/user_history_store.py`
- 类型：用户历史持久化
- 关键方法：`save_turn()`, `restore_state()`, `apply_privacy_preferences()`

### PersonalizationService
- 路径：`backend/app/memory/personalization_service.py`
- 类型：个性化服务
- 关键方法：`build_context()` (返回个性化上下文 dict)
