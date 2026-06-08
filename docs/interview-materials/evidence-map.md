# 证据映射表

每个核心结论标注确认程度：
- **【代码确认】**：可由具体代码直接证明
- **【文档确认】**：只在文档中有描述
- **【合理推断】**：从代码结构推断，但没有直接证据
- **【需要用户确认】**：涉及个人贡献、业务效果或项目背景

---

## 系统架构

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 1 | 系统采用 FastAPI + SSE 流式架构 | `backend/app/main.py:1-30` | `app = FastAPI()` | 代码中存在 FastAPI 应用实例化和路由挂载 | 【代码确认】 |
| 2 | Agent 通过依赖注入组合 20+ 个模块 | `backend/app/core/dependencies.py:294-320` | `get_shopping_agent()` | 函数内构造 ShoppingAgent 并传入 20 个依赖参数 | 【代码确认】 |
| 3 | 所有依赖使用 @lru_cache 单例模式 | `backend/app/core/dependencies.py:53-320` | 各 `get_*()` 函数 | 每个函数都有 `@lru_cache` 装饰器 | 【代码确认】 |
| 4 | 后端共 50+ 个 Python 源文件 | `backend/app/` 目录 | — | Glob 扫描 backend/app/**/*.py | 【代码确认】 |
| 5 | 前端共 37 个 Kotlin 源文件 | `android/app/src/main/java/` 目录 | — | Glob 扫描 | 【代码确认】 |
| 6 | 无 Docker 化部署 | 项目根目录 | — | 全局搜索无 Dockerfile | 【代码确认】 |

## Agent 工作流

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 7 | ShoppingAgent 是核心编排器（2715行） | `backend/app/agents/shopping_agent.py:64` | `class ShoppingAgent` | 类定义 + `stream_chat()` + `_stream_chat_core()` | 【代码确认】 |
| 8 | Agent 使用 asyncio.to_thread 分离主协程和工作线程 | `shopping_agent.py:143-175` | `stream_chat()` | `loop.run_in_executor(None, run_core)` + `asyncio.Queue` | 【代码确认】 |
| 9 | 意图理解采用三阶架构（模板→LLM→规则） | `backend/app/agents/query_understanding.py` | `parse()` | 方法内调用 `_parse_strict_template()` → `_parse_with_llm()` → `_parse_legacy_rule()` | 【代码确认】 |
| 10 | 支持 16 种意图类型 | `backend/app/models/domain.py` | `class IntentType(StrEnum)` | 枚举定义 16 个成员 | 【代码确认】 |
| 11 | 对话流有 17 种状态 | `backend/app/agents/dialogue_flow.py` | `class DialogueFlow` | `DialogueFlowController.decide()` 的决策逻辑 | 【代码确认】 |
| 12 | 18 种任务类型 | `backend/app/models/agent.py` | `class TaskType(StrEnum)` | 枚举定义 | 【代码确认】 |
| 13 | 模型路由决定用模板/本地模型/LLM | `backend/app/agents/model_router.py` | `ModelRouter.route()` | 优先级链决定 primary_handler | 【代码确认】 |
| 14 | 进度事件使用 700ms 间隔交错发送 | `shopping_agent.py:143-228` | `stream_chat()` | `progress_interval = 0.7` | 【代码确认】 |

## RAG 检索

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 15 | 混合检索使用 5 阶段管线 | `backend/app/retrieval/hybrid_retriever.py` | `HybridRetriever.retrieve()` | 硬过滤→七维打分→模型打分→加权融合→排序 | 【代码确认】 |
| 16 | 七维轻量打分（关键词/语义/约束/增强/偏好/价格/风险） | `hybrid_retriever.py` | 各 `_*_score()` 方法 | 7 个独立打分函数 | 【代码确认】 |
| 17 | 最终融合权重：keyword 0.24, semantic 0.28, constraint 0.22 等 | `hybrid_retriever.py` | `retrieve()` | 代码中硬编码的权重计算公式 | 【代码确认】 |
| 18 | 有 Reranker 时使用不同权重（含 reranker 0.10） | `hybrid_retriever.py` | `retrieve()` | `if self.local_models and self.local_models.has_reranker:` 分支 | 【代码确认】 |
| 19 | 使用 BGE-reranker-base 重排序 | `backend/app/ml/local_models.py` | `LocalModelManager.rerank_scores()` | 模型路径 `backend/models/bge-reranker-base/` | 【代码确认】 |
| 20 | 4 级渐进式检索容错 | `backend/app/retrieval/fallback.py` | `RetrievalFallback.progressive_retrieve()` | 4 步松弛（价格→子类目→否定→全类目） | 【代码确认】 |
| 21 | 否定词安全处理（"不要酒精" 不排除 "不含酒精"） | `hybrid_retriever.py` | `_negative_satisfied_by_safe_word()` | 9 种否定词映射 | 【代码确认】 |
| 22 | 后处理器去重并再次硬过滤 | `backend/app/retrieval/post_processor.py` | `ProductPostProcessor.finalize()` | 去重→硬过滤→否定词安全→排序 | 【代码确认】 |
| 23 | LLM IntentPlan 包含 14 条核心原则的 system prompt | `backend/app/llm/doubao_client.py` | `resolve_user_intent()` | 方法内 50+ 行 system prompt | 【代码确认】 |
| 24 | 规则回退有 200+ 条类别别名 | `backend/app/agents/query_understanding.py` | `_category_aliases` | 字典定义 | 【代码确认】 |

## LLM 集成

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 25 | 使用 Doubao Seed 2.0 (ep-20260514111645-lmgt2) | `.env` + `backend/app/core/config.py:27` | `doubao_model` | 环境变量 `DOUBAO_MODEL` | 【代码确认】 |
| 26 | DoubaoClient 支持 5 种 LLM 调用模式 | `backend/app/llm/doubao_client.py` | `class DoubaoClient` | generate_response, stream_generate_response, resolve_user_intent, analyze_image, analyze_user_profile | 【代码确认】 |
| 27 | JSON 提取有重试机制（最多 2 次） | `doubao_client.py` | `_chat_json()` | `retries` 参数 + for 循环 | 【代码确认】 |
| 28 | JSON 提取失败时尝试截取 `{...}` | `doubao_client.py` | `_extract_json_with_debug()` | 找第一个 `{` 和最后一个 `}` | 【代码确认】 |
| 29 | MockLLMClient 有 200+ 行规则意图解析 | `backend/app/llm/mock_llm.py` | `_resolve_user_intent_internal()` | 200+ 行关键词匹配逻辑 | 【代码确认】 |
| 30 | LLM Client 使用抽象基类 | `backend/app/llm/base.py` | `class BaseLLMClient(ABC)` | ABC 定义 6 个方法 | 【代码确认】 |

## Memory 系统

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 31 | 三层记忆架构（会话/事件/历史） | `backend/app/memory/session_memory.py` + `user_history_store.py` | `SessionMemory` + `UserHistoryStore` | 两个独立的存储系统 | 【代码确认】 |
| 32 | 用户历史持久化到文件系统 JSON | `backend/app/memory/user_history_store.py` | `UserHistoryStore.save_turn()` | 写入 `{root_dir}/{user_id}/sessions/{sid}.json` | 【代码确认】 |
| 33 | 每轮对话自动持久化 | `shopping_agent.py` — 阶段 8 | `_stream_chat_core()` | 调用 `user_history_store.save_turn()` | 【代码确认】 |
| 34 | 引用消解为每个排名生成 8 个别名 | `backend/app/memory/session_memory.py` | `record_recommendation_event()` | `["第{rank}个", "第{rank}款", ...]` | 【代码确认】 |
| 35 | 保留最近 20 条记忆事件 | `session_memory.py` | `record_recommendation_event()` | `event_memory.recommendations[-20:]` | 【代码确认】 |
| 36 | 语义记忆维护类别/特征/品牌计数 | `user_history_store.py` | `_promote_turn_memory()` | 增量更新 category_counts, feature_counts 等 | 【代码确认】 |
| 37 | 记忆卡片最多 50 条 | `user_history_store.py` | `_promote_turn_memory()` | `memory_cards[-50:]` | 【代码确认】 |
| 38 | 用户画像支持 3 种生成模式 | `backend/app/memory/user_profile_service.py` | `maybe_refresh_profile()` | semantic/LLM/local_fallback 三个分支 | 【代码确认】 |

## Tool Calling

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 39 | 5 个工具封装（检索/购物车/结账/订单/RAG） | `backend/app/tools/` | 各 Tool 类 | 5 个工具文件 | 【代码确认】 |
| 40 | ActionExecutor 支持 7 种购物车动作 | `backend/app/tools/action_executor.py` | `execute_cart_action()` | 方法内的动作分支 | 【代码确认】 |
| 41 | SKU 解析有 8 级优先级链 | `action_executor.py` | `_resolve_target_sku()` | 价格选取→intent_plan→记忆引用→提及→resolved_references→语义匹配→唯一商品→推荐首项 | 【代码确认】 |
| 42 | 支持多步骤意图计划（混合意图） | `action_executor.py` | `execute_cart_action()` | 检测 `intent_plan.steps` 并逐个执行 | 【代码确认】 |
| 43 | 规格变体解析有打分机制 | `action_executor.py` | `_resolve_variant_from_query()` | token/bigram/多部分值/数值单位匹配 | 【代码确认】 |

## 流式输出

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 44 | SSE 使用标准 event/data 双行格式 | `backend/app/utils/sse.py` | `format_sse()` | `event: {}\ndata: {}\n\n` 格式 | 【代码确认】 |
| 45 | 前端原生解析 SSE（不使用 EventSource） | `android/.../ShoppingRepository.kt:289-350` | `readSseStream()` | 逐行读取输入流解析 | 【代码确认】 |
| 46 | `toChatStreamEvent()` 支持 20+ 种 SSE 事件类型 | `ShoppingRepository.kt:352-523` | `toChatStreamEvent()` | 大 when 表达式 | 【代码确认】 |
| 47 | 推荐流式使用 `[[SECTION:N]]` 标记 | `backend/app/agents/recommendation_streaming.py` | `RecommendationPresentationParser` | 解析 `[[SECTION:` 和 `[[END_SECTION]]` | 【代码确认】 |
| 48 | 前端有打字机效果 | `ChatViewModel.kt:935-1003` | 协程打字机 | 步长和延迟的动态调整 | 【代码确认】 |
| 49 | 进度阶段映射为 6 个规范阶段 | `ChatViewModel.kt` | `defaultProcessStages()` + `mapProgressStage()` | 6 个规范阶段常量 | 【代码确认】 |

## 个性化

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 50 | 五层个性化机制 | `backend/app/memory/personalization_service.py` | `build_context()` | 硬约束→画像→购物车→领域风格→隐私 逐层叠加 | 【代码确认】 |
| 51 | 证据选择按 7 个维度打分 | `personalization_service.py` | `_select_evidence()` | 类别+3.0, 子类别+3.0, term_overlap×0.45 等 | 【代码确认】 |
| 52 | 协同过滤使用语义相似度+词汇回退 | `personalization_service.py` | `_collaborative_style_reference()` | semantic_scores + _lexical_similarity 融合公式 | 【代码确认】 |
| 53 | 最终 CF 得分 = max(语义, 回退×0.88) × 0.72 + 类别重叠×0.28 | `personalization_service.py` | `_collaborative_style_reference()` | 代码中的公式 | 【代码确认】 |
| 54 | 4 种领域导购风格 | `personalization_service.py` | `_domain_style()` | 返回 per-category 角色和风格指令 | 【代码确认】 |
| 55 | 40+ 条购物车配对规则 | `backend/app/memory/cart_aware_personalization.py` | `_match_rules()` | 规则列表 | 【代码确认】 |
| 56 | 购物车重排序有 7 个加分维度 | `cart_aware_personalization.py` | `rerank()` | 品牌+0.08, 类别+0.05, 子类别+0.12 等 | 【代码确认】 |

## 业务闭环

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 57 | 六步购买转化链路 | 多个文件 | — | 推荐(hybrid_retriever)→加购(action_executor)→规格(spec_selection)→购物车(cart_service)→结账引导(closing_guide)→订单(order_service) | 【代码确认】 |
| 58 | 结账引导有 20+ 接受/拒绝信号词汇 | `backend/app/agents/closing_guide.py` | `is_accept_signal()` / `is_decline_signal()` | `_CHECKOUT_ACCEPT_SIGNALS` / `_CHECKOUT_DECLINE_SIGNALS` 集合 | 【代码确认】 |
| 59 | 结账引导有 2 轮冷却期 | `closing_guide.py` | `should_trigger()` | `checkout_declined_recently` 参数 | 【代码确认】 |
| 60 | 导航只响应用户明确请求 | `backend/app/agents/frontend_action_planner.py` | `_enforce_navigation_policy()` | 未验证的 target_page 覆盖为 "chat" | 【代码确认】 |

## 异常处理和降级

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 61 | 回复验证检查产品名和价格幻觉 | `backend/app/agents/response_validator.py` | `validate_with_result()` | 产品名在已知库但不在允许列表中 → 触发回退 | 【代码确认】 |
| 62 | 价格检查有 8 个预算上下文 token 豁免 | `response_validator.py:37-39` | `validate_with_result()` | "以内", "以下", "预算", "不超过" 等 | 【代码确认】 |
| 63 | MockLLMClient 作为 LLM 降级存在 | `backend/app/llm/mock_llm.py` | `class MockLLMClient` | 完整的意图解析+回复生成实现 | 【代码确认】 |
| 64 | 全局 try/except 包装整个 turn | `shopping_agent.py:1083-1121` | `_stream_chat_core()` | except 块逐个 yield 错误 SSE 事件 | 【代码确认】 |
| 65 | 错误时仍输出 turn_result + error + done 三个事件 | `shopping_agent.py:1083-1121` | `_stream_chat_core()` | yield 序列 | 【代码确认】 |

## 前端

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 66 | 6 个页面（聊天/图片搜索/商品详情/购物车/结账/地址） | `android/.../navigation/Routes.kt` | `Routes` sealed class | 7 条路由（含订单结果） | 【代码确认】 |
| 67 | ChatViewModel 同时服务于 ChatScreen 和 ImageSearchScreen | `ImageSearchScreen.kt` + `ChatScreen.kt` | 两者均创建 `ChatViewModel` | 共享 ViewModel | 【代码确认】 |
| 68 | 商品有 36 个字段的 ProductUiModel | `android/.../data/model/UiModels.kt` | `ProductUiModel` data class | 36 个字段 | 【代码确认】 |
| 69 | 购物车支持多 SKU 规格选择 | `backend/app/services/cart_service.py` | `CartService.add()` | 多 SKU 检测 + variant 解析 | 【代码确认】 |
| 70 | 无单元测试/UI 测试 | `android/` 目录 | — | 全局搜索无 test 相关文件 | 【代码确认】 |

## 数据和商品

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 71 | 商品从 JSON 文件加载（双源） | `backend/app/repositories/product_repository.py` | `ProductRepository.__init__()` | `_load_competition_dataset()` + `_load_legacy()` | 【代码确认】 |
| 72 | 商品数据标准化的 searchable_text 拼接所有字段 | `product_repository.py` | `_normalize_dataset_item()` | 拼接 name, brand, category, SKU 属性, spotlight 等 | 【代码确认】 |
| 73 | Windows 文件名乱码特殊处理（mojibake） | `product_repository.py` | `_normalize_dataset_item()` | rglob 回退匹配 | 【代码确认】 |
| 74 | 151 件商品，4 大类 | `docs/综合测试报告.md:20` | — | 文档描述 | 【文档确认】 |
| 75 | 构造了 8 个测试用户人设 | `storage/user_history/` | — | 目录下存在 8+ 个用户子目录的 profile.json | 【代码确认】 |

## 测试

| # | 结论 | 文件路径 | 类/函数/模块 | 代码证据 | 确认程度 |
|---|------|---------|-------------|---------|---------|
| 76 | 有 API 流程测试（产品/购物车/多SKU） | `backend/tests/test_api_flow.py` | 多个 test 函数 | test_products_api, test_cart_api_flow, test_multi_sku_cart_api 等 | 【代码确认】 |
| 77 | 有 ScenePresentationBuilder 单元测试 | `backend/tests/test_scene_presentation_builder.py` | 多个 test 函数 | 使用 StaticLLMClient/RawLLMClient 模拟 LLM | 【代码确认】 |
| 78 | 有菜菜验收测试 | `backend/tests/test_caicai_acceptance.py` | — | 文件存在 | 【代码确认】 |
| 79 | MockLLMClient 用于测试 | `tests/test_scene_presentation_builder.py:9-20` | `StaticLLMClient` / `RawLLMClient` | 继承 BaseLLMClient 的测试替身 | 【代码确认】 |

## 不能从代码确认的结论

| # | 需要用户确认的问题 |
|---|-------------------|
| Q1 | 哪些模块由你本人独立开发，哪些由团队协作？ |
| Q2 | 系统设计的核心决策（如三阶意图理解、5 层个性化）是你提出的还是团队共识？ |
| Q3 | 项目经历了哪些迭代阶段？v1→v8 的每次提交对应什么功能增量？ |
| Q4 | 是否做过性能测试？端到端延迟（从用户提问到首 token）是多少？ |
| Q5 | 是否有真实用户反馈或测试结果？ |
| Q6 | 购物车配对规则的 40+ 条是谁维护的？基于什么数据来源？ |
| Q7 | 协同过滤的相似用户数据是如何构造的？ |
| Q8 | 是否有生产环境部署？ |
| Q9 | 项目是否是为了答辩/面试专门开发的，还是有实际应用场景？ |
| Q10 | 前端 UI 设计是你自己做的还是有设计师协助？ |
