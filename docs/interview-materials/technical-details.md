# 技术细节

## 1. Agent 工作流 【代码确认】

### 1.1 状态机设计

对话流程由 `DialogueFlowController` 控制（`backend/app/agents/dialogue_flow.py`）。

**17 种对话流（DialogueFlow 枚举）**：

```
GREETING, RECOMMENDATION, FILTERING, REFINEMENT, CLARIFICATION,
COMPARISON, PRODUCT_QA, SCENE_BUNDLE, CART_ACTION, CHECKOUT,
PREFERENCE_UPDATE, NO_RESULT, CHITCHAT, OUT_OF_SCOPE, INVALID, DETAIL
```

**决策优先级链**：
```
INVALID → OUT_OF_SCOPE → Cart操作 → CHECKOUT → PREFERENCE →
CHITCHAT → COMPARE → DETAIL → SCENE_BUNDLE →
need_clarification → EXCLUSION → REFINEMENT → FILTERING →
RECOMMENDATION (默认)
```

### 1.2 任务规划

`TaskPlanner.plan()` 将每个 FlowDecision 展开为具体任务步骤。

以 **RECOMMENDATION 流程**为例：
```
MERGE_CONTEXT → EXTRACT_CONSTRAINTS → REWRITE_QUERY →
RETRIEVE_PRODUCTS → FILTER_PRODUCTS → RERANK_PRODUCTS →
GENERATE_RESPONSE (LLM) → VALIDATE_RESPONSE →
UPDATE_MEMORY → DISPATCH_FRONTEND_EVENTS
```

以 **CART_ACTION 流程**为例：
```
RESOLVE_REFERENCE → EXECUTE_CART_ACTION →
GENERATE_RESPONSE → UPDATE_MEMORY → DISPATCH_FRONTEND_EVENTS
```

### 1.3 模型路由

`ModelRouter.route()` 根据流程类型决定谁处理（`backend/app/agents/model_router.py`）：

| 条件 | primary_handler | need_llm |
|------|----------------|----------|
| GREETING/CHITCHAT/OUT_OF_SCOPE/INVALID | "template" | False |
| CART_ACTION/CHECKOUT/PREFERENCE_UPDATE | "tool_or_memory" | False |
| CLARIFICATION | "clarification_template" | False |
| COMPARISON/PRODUCT_QA/DETAIL | "retrieval_plus_llm" | True |
| SCENE_BUNDLE | "scene_planner_plus_llm" | True |
| 低置信度 (<0.68) | "llm_fallback" | True |
| 有价格/品牌约束 | "retrieval_plus_llm" | True |
| 默认 | "retrieval_plus_llm" | True |

### 1.4 进度事件

`ProgressEventBuilder` 在 LLM/检索完成之前就给前端发送进度事件（`backend/app/progress/progress_event_builder.py`）。

三种构建模式：
- `build_parallel()`：模板驱动，快速，不依赖 Agent 结果
- `build_fast()`：加入会话上下文
- `build()`：完整版，基于 FlowDecision + ModelRouteDecision

三种延迟级别：
- Fast：1-2 事件，500ms 间隔
- Medium：3-5 事件，700ms 间隔
- Slow：4-7 事件，850ms 间隔

前端映射为 6 个规范阶段：
```
need_understanding → constraint_confirmation → product_filtering →
candidate_matching → recommendation_plan → response_generation
```

## 2. RAG 检索 【代码确认】

### 2.1 意图理解（三阶架构）

**第一阶：严格模板匹配**
- 路径：`backend/app/agents/query_understanding.py` — `_parse_strict_template()`
- 使用正则匹配简单模式：`"推荐一款{target}"`、`"想要一款{target}"`
- 拒绝复杂信号（多动词、"不要"、"购物车"、逗号等）
- 时间：<1ms，本地完成

**第二阶：LLM IntentPlan**
- 路径：`backend/app/llm/doubao_client.py` — `resolve_user_intent()`
- 通过 Doubao API 解析为结构化 JSON
- System prompt 包含 14 条核心原则 + few-shot 示例
- 输出包含 primary_intent、intent_plan（支持多步骤排序）、category、sub_category、price_range、constraints、brands、referents 等
- 时间：~2s

**第三阶：规则回退**
- 路径：`backend/app/agents/query_understanding.py` — `_parse_legacy_rule()`
- 关键词优先级链匹配意图
- 200+ 条类别别名映射
- 40+ 条语义类别示例（用于 text2vec 推断）
- 可选小模型辅助（text2vec 意图推断）
- 时间：~50ms

### 2.2 混合检索（5 阶段管线）

路径：`backend/app/retrieval/hybrid_retriever.py` — `retrieve()`

**阶段 1：硬过滤 (`_hard_filter`)**
- 类别不匹配 → 剔除
- 子类目不匹配 → 剔除
- 饮料专项检测（食品饮料类下非饮料排除）
- 儿童安全检测（含咖啡因/能量饮料/大包装 → 剔除）
- 价格范围违规 → 剔除
- 品牌包含/排除 → 剔除
- 负面约束（否定词安全处理："不要酒精" 不排除写着"不含酒精"的商品）

**阶段 2：七维轻量打分**
每个存活商品计算 7 个分数：

| 分数维度 | 方法 | 算法 |
|---------|------|------|
| keyword_score | `_keyword_score()` | 查询词元在商品文档中的命中比例 |
| semantic_score | `_semantic_score()` | 字符 bigram Jaccard × 包含度几何平均 × 2.2 |
| constraint_score | `_constraint_score()` | 正面约束在文档中的命中数 / 约束总数 |
| enhancement_score | `_enhancement_score()` | 商品标签与查询的直接/语义匹配得分 |
| preference_score | `_preference_score()` | 品牌偏好 (+0.7) / 排除 (-1.0) / 风格 (+0.3) |
| price_fit_score | `_price_fit_score()` | 商品价格接近 75% 预算上限的程度 |
| risk_notes | `_risk_notes()` | 差评提取 |

**阶段 3：模型打分（可选）**
- `LocalModelManager.semantic_scores()`：BGE-small-zh-v1.5 或 text2vec-base-chinese embedding
- `LocalModelManager.rerank_scores()`：BGE-reranker-base 交叉编码器重排序

**阶段 4：加权融合**

有 Reranker 时的权重：
```
0.18×keyword + 0.24×semantic + 0.22×constraint + 0.08×enhancement
+ 0.10×price_fit + 0.08×preference + 0.10×reranker
```

无 Reranker 时的权重：
```
0.24×keyword + 0.28×semantic + 0.22×constraint + 0.12×enhancement
+ 0.10×price_fit + 0.04×preference
```

额外加分：类别精确匹配 +0.15，子类别精确匹配 +0.18，品牌命中 +0.08，性价比调整。

**阶段 5：排序输出**
- score ≤ 0 的商品被丢弃（broad=True 时保留）
- 返回 top `3*top_k` 个商品

### 2.3 检索后处理

路径：`backend/app/retrieval/post_processor.py` — `finalize()`

1. 按 product_id 去重（保留最高分）
2. 再次硬过滤（类别、子类别、价格、品牌、负面约束）
3. 否定词安全处理（9 种常见否定模式）
4. 标记违规商品为 `displayable=False`
5. 按分数降序排列，截断

### 2.4 4 级渐进式检索容错

路径：`backend/app/retrieval/fallback.py` — `progressive_retrieve()`

当严格检索返回 0 结果时：

| 级别 | 松弛策略 | 操作 |
|------|---------|------|
| 1 | 严格检索 | 全部约束生效 |
| 2 | 放宽价格 | 移除价格 min/max，按价格接近度排序 |
| 3 | 放宽子类目 | 保留主类目，移除子类目，broad 搜索 |
| 4 | 移除否定过滤 | 清除负面约束和品牌排除，broad 搜索 |
| 5 | 全库存宽搜 | 清除所有约束（类目、价格、否定、品牌） |

每步记录松弛内容，用于生成面向用户的解释（如"适当放宽了价格范围，扩大了同类商品的检索范围"）。

## 3. Memory 系统 【代码确认】

### 3.1 三层记忆架构

```
┌───────────────────────────────────────────────┐
│ Layer 1: Session Memory (短记忆)              │
│ - 位置: SessionMemory (内存)                   │
│ - 内容: 对话状态、事件记忆、引用图谱            │
│ - 生命周期: 服务重启丢失                        │
│ - 大小: 当前会话的所有轮次                      │
├───────────────────────────────────────────────┤
│ Layer 2: Event Memory (事件记忆)               │
│ - 位置: SessionMemory.memory_events            │
│ - 内容: RecommendationEvent, DetailEvent,      │
│         ComparisonEvent, CartEvent             │
│ - 特性: rank_to_sku 映射、引用消解别名           │
│         source_event_id 事件链追踪              │
│ - 保留: 最近 20 条事件                          │
├───────────────────────────────────────────────┤
│ Layer 3: User History (长记忆)                 │
│ - 位置: UserHistoryStore (文件系统 JSON)         │
│ - 路径: storage/user_history/{user_id}/         │
│ - 内容: profile.json + sessions/{sid}.json      │
│ - 特性: semantic_memory (类别/特征/品牌计数),   │
│         memory_cards (前50), style_signals      │
│ - 持久化: 每轮写入磁盘                           │
└───────────────────────────────────────────────┘
```

### 3.2 会话记忆（SessionMemory）

路径：`backend/app/memory/session_memory.py`

核心能力：
1. **引用消解**：为每个推荐排名构建 8 个别名（`"第1个"`, `"第一款"`, `"第一件"`, `"第1款"`, `"壹号"`, `"1号"` 等）
2. **代词绑定**：`"这个"`, `"这款"`, `"它"` 指向 `active_detail_sku_id` 或第一个推荐 SKU
3. **购物车代词**：`"刚才加购的"` → `active_cart_sku_id`
4. **对比引用**：`"前两个"` → 推荐事件中的 SKU 列表
5. **事件链追踪**：每个事件记录 `source_event_id`，可追溯推荐来源

### 3.3 用户历史持久化（UserHistoryStore）

路径：`backend/app/memory/user_history_store.py`

存储目录结构：
```
storage/user_history/{user_id}/
  profile.json          # 用户画像（偏好、语义记忆、记忆卡片）
  sessions/
    {session_id}.json   # 每会话的完整对话轮次 + 状态快照
```

**Profile 结构**（关键字段）：
- `structured_profile`：结构化画像（LLM 生成的摘要）
- `explicit_preferences`：显式偏好（品牌、价格、风格）
- `semantic_memory`：语义统计（category_counts, feature_counts, brand_counts, price_signals, style_signals）
- `memory_cards`：记忆卡片（前 50 条，按 confidence × last_seen_at 排序）
- `privacy_settings`：隐私设置（personalization_mode, store_raw_history 等）

**每轮保存流程** (`save_turn()`)：
1. 构建 turn 记录（用户输入 + 助手回复 + 推荐商品 + 检索摘要 + 购物车变化 + 对话状态）
2. 隐私检查：如果 `store_raw_history` 为 false，明文替换为 `[已按隐私设置隐藏...]`
3. 写入 session JSON（含 state_snapshot 用于恢复）
4. 更新 profile 元数据
5. 调用 `_promote_turn_memory()` 更新语义记忆计数器

**语义记忆升级** (`_promote_turn_memory()`)：
- 累加 category_counts, sub_category_counts, feature_counts, negative_constraint_counts, brand_counts
- 维护 price_signals（最近 20 条）
- 追踪 recommended_skus, cart_skus, purchased_skus
- 创建/更新 memory_cards（最多 50 条，按 confidence × last_seen_at 排序）
- 写入 memory_promotion_log（最近 30 条）

### 3.4 用户画像服务（UserProfileService）

路径：`backend/app/memory/user_profile_service.py`

三种画像生成模式：

| 模式 | 条件 | 方法 |
|------|------|------|
| Semantic | 隐私模式下 | 从语义计数器直接生成（无 LLM） |
| LLM | 全模式 + force=True | llm_client.analyze_user_profile() |
| Local fallback | LLM 失败或无输出 | 关键词匹配生成 |

## 4. Tool Calling 【代码确认】

### 4.1 工具体系

5 个工具封装：

| 工具 | 类 | 路径 |
|------|-----|------|
| ProductSearchTool | 检索工具 | `tools/product_search_tool.py` |
| CartTool | 购物车工具 | `tools/cart_tool.py` |
| CheckoutTool | 结账工具 | `tools/checkout_tool.py` |
| OrderTool | 订单工具 | `tools/order_tool.py` |
| RagTool | RAG 工具 | `tools/rag_tool.py` |

### 4.2 ActionExecutor — 购物车动作执行器

路径：`backend/app/tools/action_executor.py`

支持的购物车动作类型（按优先级顺序）：
1. `cart_clear` — 清空购物车
2. `cart_view` — 查看购物车
3. `checkout` — 创建订单（购物车为空时报错）
4. `cart_keep_only` — 只保留指定类目的商品
5. `cart_remove` (批量) — "所有/全部/都" → 删除匹配项
6. `cart_add` (批量) — "都加入/一起加" → 添加所有指定商品
7. 单品操作 — 移除/添加/更新单个商品

**SKU 解析优先级** (`_resolve_target_sku()`)：
1. 基于价格的选取（最贵/最便宜）
2. intent_plan 中的 cart_action.sku_id
3. 记忆事件引用匹配
4. 查询中提及的商品
5. resolved_references 字典
6. 与购物车内商品的语义匹配
7. 购物车唯一商品（cart_first 模式）
8. 最新推荐中的第一个商品

**规格变体解析** (`_resolve_variant_from_query()`)：
- 精确 sku_id 匹配
- 单 SKU 商品直接返回
- 打分匹配：token 重叠 + bigram 重叠 + 多部分值匹配 + 数值单位匹配

## 5. 流式输出 【代码确认】

### 5.1 SSE 协议

路径：`backend/app/utils/sse.py` — `format_sse()`

标准 SSE 格式：
```
event: {event_name}
data: {json_payload}

```

### 5.2 SSE 事件类型（20+ 种）

路径：`android/app/.../ShoppingRepository.kt` — `toChatStreamEvent()` 完整解析

| 事件类型 | 方向 | 用途 |
|---------|------|------|
| `progress`/`process` | 后端→前端 | 处理进度更新 |
| `generation_started` | 后端→前端 | LLM 开始生成 |
| `response_delta` | 后端→前端 | 思考过程文本增量 |
| `response_completed` | 后端→前端 | 文本生成完成 |
| `token` | 后端→前端 | 逐 token 输出 |
| `recommendation_section_start` | 后端→前端 | 推荐部分开始 |
| `recommendation_text_delta` | 后端→前端 | 推荐理由增量 |
| `recommendation_text_done` | 后端→前端 | 推荐理由完成 |
| `recommendation_section_done` | 后端→前端 | 推荐部分结束 |
| `product_card` | 后端→前端 | 单个商品卡片 |
| `product_cards` | 后端→前端 | 批量商品 |
| `products` | 后端→前端 | 通用商品列表 |
| `alternatives` | 后端→前端 | 替代商品 |
| `product_detail` | 后端→前端 | 商品详情 |
| `cart_update` | 后端→前端 | 购物车更新 |
| `cart` | 后端→前端 | 购物车快照 |
| `spec_selection` | 后端→前端 | SKU 规格选择器 |
| `frontend_action` | 后端→前端 | 页面导航指令 |
| `turn_result` | 后端→前端 | 轮次完整结果（聚合） |
| `error` | 后端→前端 | 错误信息 |
| `done` | 后端→前端 | 流结束 |

### 5.3 推荐流式展示协议

路径：`backend/app/agents/recommendation_streaming.py`

使用 `[[SECTION:N]]` / `[[END_SECTION]]` 标记分割不同商品的推荐理由：
```
[[SECTION:1]]
这款精华采用...
[[END_SECTION]]
[[SECTION:2]]
如果你更看重性价比...
[[END_SECTION]]
```

`RecommendationPresentationParser` 增量解析这些标记，即使 buffer 被 token 边界切分也能正确处理。

前端打字机效果（`ChatViewModel.kt:935-1003`）：
- 已完成段落：步长 6-8 字符，延迟 6-10ms
- 流式中段落：步长 2-6 字符，延迟 8-18ms
- 去重检测：使用 `appliedSectionDeltas` 集合

### 5.4 进度事件交错发送

主协程使用 `asyncio.Queue` 和工作线程并行：
- 进度事件每 700ms 发送一次
- 一旦第一个非进度事件（如 `turn_result`）发出，停止进度事件
- 工作线程在 `asyncio.to_thread` 中运行

证据：`backend/app/agents/shopping_agent.py:143-228`

## 6. 个性化 【代码确认】

### 6.1 五层个性化机制

```
Layer 1: 硬约束 (负面向量过滤)
  ↓
Layer 2: 用户画像 (皮肤类型、偏好品牌、价格区间)
  ↓
Layer 3: 购物车感知 (配对规则、品牌生态)
  ↓
Layer 4: 领域导购风格 (美妆/数码/服饰/食品 四种角色)
  ↓
Layer 5: 隐私控制 (full / semantic / off)
```

### 6.2 PersonalizationService 核心算法

路径：`backend/app/memory/personalization_service.py` — `build_context()`

**证据选择 (`_select_evidence`)**：
对历史轮次按相关性打分：
- 类别匹配：+3.0
- 子类别匹配：+3.0
- 商品类别重叠：+2.0/商品
- 子类别重叠：+1.5/商品
- 词项重叠：min(匹配数, 5) × 0.45
- 购物车变化信号：+1.2
- 偏好信号：+1.0

**协同过滤 (`_collaborative_style_reference`)**：
1. 构建当前用户的"风格文档"（画像 + 最近轮次 + 解析查询）
2. 加载候选参考用户（优先级列表：alex_sports, xiaomei_beauty, lily_beauty_pro 等）
3. `LocalModelManager.semantic_scores()` 计算语义相似度
4. 词汇相似度作为回退（`_lexical_similarity`）
5. 类别重叠得分
6. 最终得分 = max(语义, 回退×0.88) × 0.72 + 类别重叠 × 0.28
7. 阈值：0.38（有语义分）/ 0.28（无语义分）
8. 返回 Top 3 相似用户及其 few-shot 示例

**领域导购风格**：
- 美妆护肤：温柔细腻的"美妆导购小姐姐"
- 数码电子：清晰理性的"数码导购小哥"
- 服饰运动：场景导向的"搭配顾问"
- 食品饮料：轻松随性的"食品导购"

### 6.3 购物车感知个性化

路径：`backend/app/memory/cart_aware_personalization.py`

40+ 条产品配对规则，按类别组织。例如：
- `apple_macbook_ecosystem`：购物车有 MacBook → 提升苹果品牌配件 + 办公标签
- 护肤流程完整性检测：有洁面+化妆水 → 提升面霜/精华

重排序加分：
- 品牌匹配：+0.08
- 类别匹配：+0.05
- 子类别匹配：+0.12
- 标签匹配：+0.04
- 高价位偏好：最高 +0.12

## 7. 业务闭环 【代码确认】

六步购买转化链路：

```
1. 商品推荐 (HybridRetriever + LLM)
   ↓
2. 加入购物车 (ActionExecutor.cart_add, 支持自然语言)
   ↓
3. 规格确认 (spec_selection SSE 事件, 多 SKU 商品)
   ↓
4. 购物车管理 (CartService CRUD API + 自然语言操作)
   ↓
5. 结账引导 (ClosingGuide, 基于购物车状态的智能触发)
   ↓
6. 订单创建 (OrderService.create_order, 演示订单)
```

**结账引导 (ClosingGuide)**：
- 路径：`backend/app/agents/closing_guide.py`
- 触发条件：购物车非空 + 当前意图为购物车操作 + 无新购物需求信号 + 最近未拒绝结账（2 轮冷却）
- 接受信号：20+ 短语（"结算"、"下单"、"付款"、"可以"、"好的"）
- 拒绝信号：20+ 短语（"不用"、"先不"、"等等"、"再看看"）
- 防止重复触发：`checkout_offered_this_turn` 标记

## 8. 异常处理和降级 【代码确认】

### 8.1 检索容错

路径：`backend/app/retrieval/fallback.py`

4 级渐进式松弛（见上文 2.4 节），每步记录松弛内容供用户感知。

### 8.2 LLM 降级

三层降级链：
```
DoubaoClient (真实API)
  ↓ HTTP 失败 / API Key 缺失 / 响应为空
MockLLMClient (本地规则引擎, 200+行)
  ↓ 特定场景
模板回复 (硬编码文案)
```

MockLLMClient 关键方法（`backend/app/llm/mock_llm.py`）：
- `_resolve_user_intent_internal()`：200+ 行规则意图解析
- `_generate_response_internal()`：模板回复（DETAIL/CHECKOUT/CART/推荐/回退）
- `stream_generate_response()`：17 字符分块模拟流式
- `analyze_image()`：关键词匹配模拟图片分析

### 8.3 回复验证（防幻觉）

路径：`backend/app/agents/response_validator.py`

两层检查：
1. **产品名检查**：扫描 LLM 输出中出现的所有已知商品名，如果不在 `allowed_candidates` 中 → 触发回退
2. **价格检查**：提取 `¥{数字}` 和 `{数字}元`，排除预算上下文中的价格（"以内"、"以下"、"预算"、"不超过" 等 8 个 token 检测窗口），检查是否在允许价格集合中

回退响应：使用排名第一的候选商品生成安全文案。

### 8.4 全局异常捕获

路径：`backend/app/agents/shopping_agent.py:1083-1121`

整个 `_stream_chat_core()` 被 try/except 包裹：
```python
except Exception:
    yield SSEEvent(event="turn_result", ...)  # 包含错误信息
    yield SSEEvent(event="error", ...)
    yield SSEEvent(event="done", {"finish_reason": "error"})
```

### 8.5 FrontendEventBuilder 错误处理

路径：`backend/app/agents/frontend_event_builder.py` — `build_error()`

生成消毒后的错误响应，前端显示"系统暂时遇到了问题，请重试"，同时保留完整调试信息在 `system_debug` 中。

## 9. 前后端交互协议 【代码确认】

### 9.1 统一轮次输出 (UnifiedTurnOutput)

路径：`backend/app/models/agent.py` — `UnifiedTurnOutput`

三部分结构：
```
{
  "frontend_events": [
    {"type": "show_reply", "data_ref": "reply_text"},
    {"type": "show_products", "data_ref": "recommended_products"},
    ...
  ],
  "frontend_data": {
    "reply_text": "基于你的肤质...",
    "recommended_products": [ProductCard, ...],
    "cart_state": CartSnapshot,
    "spec_selection": null,
    ...
  },
  "system_debug": {
    "intent_analysis": {...},
    "flow_decision": {...},
    "retrieval_process": {...},
    "personalization": {...},
    "model_calls": {...},
    ...
  }
}
```

### 9.2 导航策略

路径：`backend/app/agents/frontend_action_planner.py` — `_enforce_navigation_policy()`

后端只在用户明确请求时才触发页面跳转：
- `product_detail`：用户明确问了某商品详情
- `cart`：用户明确要看购物车
- `checkout`：用户明确要结账 + 工具成功执行
- 未验证的 target_page 被强制覆盖为 "chat"

### 9.3 前端 ChatStreamEvent 模型

路径：`android/app/.../data/model/UiModels.kt` — `ChatStreamEvent`

单一数据类承载所有 SSE 事件类型，20+ 个可选字段：
```kotlin
data class ChatStreamEvent(
    val event: String,           // 事件类型
    val requestId: String?,
    val text: String?,
    val products: List<ProductUiModel> = emptyList(),
    val cart: CartSnapshotUiModel?,
    val navigation: BackendNavigationUiModel?,
    val recommendationSection: RecommendationSectionUiModel?,
    val specSelection: SpecSelectionUiModel?,
    // ... 更多可选字段
)
```
