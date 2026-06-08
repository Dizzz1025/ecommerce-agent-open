# 技术难点与解决方案

本文档从源码、注释、提交记录和现有文档中提取技术难点，区分已解决的问题和仍存在的限制。

---

## 一、已解决的技术难点

### 1. LLM 意图理解的稳定性和延迟 【代码确认】

**问题**：纯 LLM 意图解析存在三个问题：
- 延迟高（~2s），影响用户体验
- 简单问候/重复输入浪费 LLM 调用
- LLM 输出不可控，可能返回无法解析的 JSON

**解决方案**：三阶意图理解架构（`backend/app/agents/query_understanding.py`）
- 第一阶：严格模板匹配（正则，<1ms），拦截简单查询和问候
- 第二阶：LLM IntentPlan（Doubao API，~2s），处理复杂意图
- 第三阶：规则回退（200+ 别名映射 + text2vec 辅助，~50ms），LLM 失败时的保底方案

**代码证据**：`query_understanding.py` — `parse()` 方法，`route_source` 字段跟踪实际使用哪条路径。

### 2. 检索结果为空时的系统行为 【代码确认】

**问题**：严格约束过滤可能导致 0 结果（如"100 元以内的 SK-II"），直接返回"没找到"用户体验差。

**解决方案**：4 级渐进式检索容错（`backend/app/retrieval/fallback.py`）
- 每级记录松弛了什么
- 生成面向用户的解释（"适当放宽了价格范围..."）
- 最终保底：全库存宽搜

**代码证据**：`fallback.py` — `progressive_retrieve()` + `summary_for_response()`

### 3. LLM 幻觉控制 【代码确认】

**问题**：LLM 可能编造商品名或价格，破坏推荐可信度。

**解决方案**：双层验证 + 事实边界隔离
- **事前隔离**：LLM 只能看到候选商品的事实信息（`Verified product facts`），不直接暴露全库存
- **事后校验**：`ResponseValidator`（`backend/app/agents/response_validator.py`）检查 LLM 输出中是否出现非候选商品名或异常价格
- **回退机制**：检测到幻觉时用安全模板替换

**代码证据**：`response_validator.py:17-62` — `validate_with_result()` 方法

### 4. 负面约束的安全处理 【代码确认】

**问题**：用户说"不要含酒精的"，但系统可能因为商品描述中有"酒精"二字而误排除"不含酒精"的商品。

**解决方案**：否定词安全词映射（`backend/app/retrieval/hybrid_retriever.py`）
- 9 种常见否定模式："酒精" → 检查是否有 "不含酒精"、"无酒精"
- "糖" → 检查 "无糖"、"低糖"
- "防水" → 检查 "不防水"
- 等等

**代码证据**：`hybrid_retriever.py` — `_negative_satisfied_by_safe_word()` 函数

### 5. 多轮对话中的指代消解 【代码确认】

**问题**：用户说"第一个"、"刚才那款"、"这个"，系统需要正确映射到具体 SKU。

**解决方案**：丰富的引用图谱（`backend/app/memory/session_memory.py`）
- 每个推荐排名生成 8 个中文别名（"第1个"、"第一款"、"壹号"、"1号"...）
- 代词绑定（"这个"→active_detail_sku_id）
- 购物车代词（"刚才加购的"→active_cart_sku_id）
- 事件链追踪（source_event_id）

**代码证据**：`session_memory.py` — `record_recommendation_event()` + `build_reference_map()`

### 6. 多 SKU 商品的购物车处理 【代码确认】

**问题**：商品有多个 SKU（如不同容量/颜色），加购时必须选择具体规格。

**解决方案**：
- 多 SKU 检测：拒绝未选规格的加购请求（400 错误）
- 规格匹配：通过 sku_id、属性匹配、或 combo 匹配找到目标 SKU
- 前端规格选择器：`spec_selection` SSE 事件触发规格选择 UI

**代码证据**：`backend/app/services/cart_service.py` — `add()` + `_find_variant()`；`backend/tests/test_api_flow.py:113-150` — 测试缺失/无效规格被正确拒绝

### 7. 多轮对话的话题切换与锁定 【代码确认】

**问题**：用户在美妆推荐中说"有便宜一点的吗"，系统需要知道"便宜一点"指上一轮的推荐结果。

**解决方案**：话题锁定机制（`backend/app/agents/query_understanding.py`）
- `_should_lock_current_topic()`：检测是否为延续话题
- `_message_suggests_topic_switch()`：检测跨类目信号词
- 上下文继承：REFINE/FILTER 意图自动继承上一轮类别
- 上下文合并：多轮约束叠加（`context_merge`）

**代码证据**：`query_understanding.py` — `_should_lock_current_topic()` + `_should_inherit_context()`

### 8. 购物车操作的安全性 【代码确认】

**问题**：自然语言"把第一个加入购物车"需要正确解析目标 SKU。

**解决方案**：8 级 SKU 解析优先级链 + 批量操作支持
- 价格选取（最贵/最便宜）
- intent_plan 中的 cart_action.sku_id
- 记忆事件引用匹配
- 语义匹配（查询文本 vs 购物车内商品）
- 批量操作（"都加入"、"删除所有"）

**代码证据**：`backend/app/tools/action_executor.py` — `_resolve_target_sku()` 方法

### 9. 前端复杂 UI 状态管理 【代码确认】

**问题**：SSE 流中有 20+ 种事件类型，前端需要正确组装为连贯的 UI。

**解决方案**：ChatViewModel 的状态驱动架构
- 6 个 StateFlow（messages, thinking, answer, products, recommendationSections, specSelections）
- 打字机效果（动态步长和延迟）
- delta 去重（`appliedSectionDeltas` 集合）
- 推荐部分的生命周期管理（start → delta* → done → section_done）

**代码证据**：`ChatViewModel.kt` — `handleStreamEvent()` (L380-481)，打字机效果 (L935-1003)

### 10. 前后端导航安全性 【代码确认】

**问题**：后端可能错误触发前端页面跳转，打断用户浏览。

**解决方案**：导航策略（`backend/app/agents/frontend_action_planner.py`）
- 允许列表：6 个合法页面
- 用户意图验证：只在用户明确请求时跳转
- 未验证的 target_page 强制覆盖为 "chat"

**代码证据**：`frontend_action_planner.py` — `_enforce_navigation_policy()` 方法

---

## 二、仍存在的技术限制

以下限制从代码和文档中确认存在。

### 1. 会话状态不持久 【代码确认】

**问题**：`SessionMemory` 使用内存 `InMemoryStore`，服务重启后所有会话状态丢失。

**代码证据**：`backend/app/memory/in_memory_store.py` — 使用 `dict` 存储，无持久化。

**已有部分缓解**：`UserHistoryStore` 保存 state_snapshot 到文件系统，支持 `restore_state()` 恢复，但需要显式调用。

### 2. 商品库规模限制 【文档确认】

**问题**：商品库仅 151 件商品，无法覆盖真实电商场景的百万级 SKU。

**来源**：`docs/综合测试报告.md:20` + `技术报告.md:444`

**影响**：硬过滤后可能只剩个位数候选商品，检索排序的实际效果在更大规模下未验证。

### 3. 本地模型 CPU 推理 【代码确认】

**问题**：3 个本地模型（BGE-small-zh-v1.5, text2vec-base-chinese, BGE-reranker-base）都在 CPU 上运行。

**代码证据**：`backend/app/core/config.py:30` — `local_model_device: str = "cpu"`；`.env` 中无 GPU 相关配置

**影响**：embedding 和 reranking 的延迟在商品量大时会显著增长。

### 4. 无真实支付集成 【代码确认】

**问题**：`OrderService.create_order()` 只生成演示订单（`demo_order_{uuid}`），无真实支付流程。

**代码证据**：`backend/app/services/order_service.py` — `create_demo_order()` 返回含 disclaimer 的演示订单。

### 5. 视觉模型能力有限 【文档确认】

**问题**：VLM 分析能力受限于 Doubao 视觉模型，且 fallback 方案（关键词语匹配）很弱。

**来源**：`技术报告.md:451` — "当前视觉模型能力有限"。

**代码证据**：`backend/app/multimodal/vision_analyzer.py` — `_local_fallback()` 使用简单的关键词匹配，confidence 仅 0.48。

### 6. 协同过滤依赖构造数据 【代码确认】

**问题**：相似用户数据是手工构造的（8 个人设 + 3 个重度使用用户），而非真实用户行为。

**代码证据**：`storage/user_history/` 目录下的 profile.json 文件 + `docs/综合测试报告.md:21`

### 7. 无分布式/水平扩展支持 【代码确认】

**问题**：所有状态存储在单进程内存中，无 Redis/数据库支持，无法水平扩展。

**代码证据**：`SessionMemory` 使用进程内 `dict`；无数据库连接配置。

### 8. 限流和并发控制缺失 【合理推断】

**问题**：代码中未发现并发请求的限流、排队或背压机制。多个用户同时查询可能导致 LLM API 过载。

### 9. LLM 输出的稳定性 【合理推断】

**问题**：虽然有 ResponseValidator，但 LLM 输出的风格、长度、质量仍受 prompt 和模型版本影响。目前采用 temperature=0.2 来控制，但没有 A/B 测试框架验证效果。

### 10. 测试覆盖不足 【代码确认】

**问题**：
- 后端测试仅覆盖 API 基础流程和 ScenePresentationBuilder
- 前端零测试
- 无集成测试覆盖完整对话流程
- 无回归测试套件

**代码证据**：`backend/tests/` 仅 3 个测试文件；`android/` 目录无测试文件。

---

## 三、代码中观察到的技术债务 【代码确认】

### 1. DoubaoClient 中有死代码
路径：`backend/app/llm/doubao_client.py:222-285`
在 `stream_generate_response()` 中，L220 的 `return` 语句之后的代码永远不会执行。

### 2. IntentParser 已被替代但未删除
路径：`backend/app/agents/intent_parser.py`
功能已被 `QueryUnderstandingModule` 完全覆盖，只保留了向后兼容导入。

### 3. 购物车 API 路径冗余
`POST /api/cart/{session_id}/clear` 和 `POST /api/cart/clear`（带 body 中的 session_id）提供相同功能。

### 4. 部分参数硬编码
- 检索 top_k 默认 5（`config.py:28`）
- 协同过滤阈值 0.38（`personalization_service.py`）
- 记忆事件上限 20 条（`session_memory.py`）
- 记忆卡片上限 50 条（`user_history_store.py`）
- 进度事件间隔 700ms（`shopping_agent.py`）

### 5. Windows 特定兼容代码
路径：`backend/app/repositories/product_repository.py` — 图片路径解析
需要处理 Windows 文件系统编码导致的文件名乱码（mojibake），通过 rglob 回退匹配解决。
