# 多轮对话 Agent 记忆系统 — 代码级分析

## 1. 一句话总览

从代码组件看，系统包含 `SessionState`、`EventMemory`、`UserHistoryStore` 和 `semantic_memory` 四类实现；但从功能和时间尺度看，可以归纳为**三层记忆架构**。第一层是短期会话状态，第二层是近期事件记忆，第三层是长期用户记忆。长期用户记忆又包含完整历史及状态快照，以及由历史行为累计形成的语义计数画像。

核心设计原则是**本轮需求优先于历史状态**——`parsed_query` 中本轮明确的约束不会被历史覆盖。

---

## 2. 逻辑分层与代码组件对照

```
┌─────────────────────────────────────────────────────────────┐
│ 逻辑分层                    │ 代码组件                       │
├─────────────────────────────┼───────────────────────────────┤
│ Layer 1: 短期会话状态记忆    │ SessionState                  │
│   (当前会话，内存)           │  · DialogueStateTracking      │
│                             │  · GoodsContext               │
│                             │  · CartState                  │
│                             │  · recent_messages            │
├─────────────────────────────┼───────────────────────────────┤
│ Layer 2: 近期结构化事件记忆  │ EventMemory                   │
│   (当前会话，内存)           │  · RecommendationEvent        │
│                             │  · ProductDetailEvent         │
│                             │  · ComparisonEvent            │
│                             │  · CartEvent                  │
│                             │ MemoryEventRecord (统一记录)   │
├─────────────────────────────┼───────────────────────────────┤
│ Layer 3: 长期用户记忆        │                               │
│   (跨会话，文件持久化)       │                               │
│  ┌───────────────────────┐  │                               │
│  │ 3a. 原始历史记忆       │  │ UserHistoryStore              │
│  │  · 完整 turn 记录      │  │  · profile.json              │
│  │  · state_snapshot     │  │  · sessions/{id}.json         │
│  │  · 会话恢复           │  │                               │
│  ├───────────────────────┤  │                               │
│  │ 3b. 语义用户画像       │  │ semantic_memory 字段           │
│  │  · category_counts   │  │  · category_counts            │
│  │  · feature_counts    │  │  · feature_counts             │
│  │  · brand_counts      │  │  · brand_counts               │
│  │  · price_signals     │  │  · price_signals              │
│  └───────────────────────┘  │                               │
└─────────────────────────────────────────────────────────────┘
```

**关键区分**: `UserHistoryStore` 是长期记忆的持久化载体——负责把完整 turn、状态快照写入 JSON 文件；`semantic_memory` 是根据长期历史行为形成的结构化用户画像。二者不是并列的两层，而是长期用户记忆内部的两个子部分：一个存原始事实，一个存聚合统计。

---

## 3. 记忆系统架构表

| 逻辑层 | 时间尺度 | 主要数据 | 写入时机 | 读取时机 | 存储位置 | 对应代码 |
|--------|----------|----------|----------|----------|----------|----------|
| **Layer 1: 会话状态** | 当前会话（服务重启丢失） | current_flow, current_category, active_constraints, 购物车, recent_messages | 每轮结束后 `_record_turn()` | 每轮开始时 `get_or_create()` | 内存 dict (`InMemoryStore`) | `domain.py:331 SessionState` / `session_memory.py` |
| **Layer 2: 事件记忆** | 当前会话（最多20-50条） | 推荐/比较/详情/购物车事件，rank→SKU 映射，source_event_id 事件链 | 业务动作成功后 | 指代消解、引用解析 | SessionState.memory_events / event_memory | `domain.py:154 MemoryEventRecord` / `session_memory.py:83-330` |
| **Layer 3a: 原始历史** | 跨会话长期保存 | 每轮 turn 记录、state_snapshot、profile.json | 每轮结束 `save_turn()` | 会话恢复、协同过滤 | `storage/user_history/{user_id}/` JSON 文件 | `user_history_store.py` |
| **Layer 3b: 语义画像** | 跨会话长期保存 | category_counts, feature_counts, brand_counts, price_signals 等计数器 | 每轮结束 `_promote_turn_memory()`（在 `save_turn()` 内部） | 个性化上下文构建、隐私模式画像生成 | profile.json 的 semantic_memory 字段 | `user_history_store.py:481-565` / `user_profile_service.py` |

---

## 4. 完整生命周期

### 读取顺序（每轮开始）

```
1. SessionMemory.get_or_create(session_id)
   → 从 InMemoryStore 读取 SessionState（无则新建）
   → 若传了 user_id 且历史存在，从 JSON 文件恢复 state snapshot

2. UserHistoryStore.load_profile(user_id)
   → 读取 profile.json，获取 profile_summary_text, structured_profile, semantic_memory

3. SessionMemory.attach_user_profile()
   → 将用户画像文本注入 SessionState.user_profile_summary_text

4. flow_before = state.dialogue_state_tracking.current_flow
   → 记录上轮流程，用于话题切换判定
```

### 写入顺序（每轮结束）

```
1. SessionMemory.append_message(role="user", ...)          ← 写入用户消息
2. [各业务分支执行: 检索、LLM 生成、卡片构建]
3. SessionMemory.record_recommendation_event()              ← 推荐事件（含 rank→SKU）
   / record_comparison_event()                              ← 比较事件
   / record_cart_event()                                    ← 购物车事件
4. SessionMemory.append_message(role="assistant", ...)      ← 写入系统回复
5. _record_turn() 内部:
   a. SessionMemory.append_behaviour()                      ← 行为摘要
   b. SessionMemory.update_dialogue_state()                 ← 更新 current_flow/category/constraints
6. UserHistoryStore.save_turn()                             ← 持久化 turn + state_snapshot
   → 内部调用 _promote_turn_memory() 更新 semantic_memory 计数器（Layer 3b）
7. UserProfileService.maybe_refresh_profile()               ← 刷新用户画像（仅 force=True 或语义模式）
8. SessionMemory.append_trace()                             ← 保存 trace 日志
```

### 真实代码执行顺序（`shopping_agent.py`）

```
L430:  append_message(user)
L912:  record_recommendation_event()      ← LLM 回复 + 卡片输出成功后
L878:  append_message(assistant)
L1003: _record_turn()                     ← append_behaviour + update_dialogue_state
L1048: save_turn()                        ← 持久化（含 _promote_turn_memory）
L1058: maybe_refresh_profile()            ← 刷新画像
L1080: append_trace()
```

---

## 5. 每一层具体存储什么

### Layer 1: 短期会话状态（SessionState, `domain.py:331`）

生命周期为一个会话，存在内存 `InMemoryStore` 中，服务重启丢失。

| 字段 | 类型 | 来源 | 用途 |
|------|------|------|------|
| `session_id` | str | 前端传入/系统生成 | 会话唯一标识 |
| `user_id` | str\|None | 前端传入 | 关联用户历史 |
| `recent_messages` | list[ConversationTurn] | `append_message()` | 最近12轮对话文本 |
| `user.global_preferences` | GlobalPreferences | `PreferenceManager.update_from_query()` | 用户明确声明的长期偏好（preferred_brands, excluded_brands, preferred_style, avoid_terms） |
| `user_profile_summary_text` | str\|None | `attach_user_profile()` 从 profile.json 注入 | LLM 生成或计数器拼接的自然语言画像摘要 |
| `user_profile_structured` | dict | `attach_user_profile()` 从 profile.json 注入 | 9字段结构化画像 |
| `goods.last_recommendations` | list[RecommendationRecord] | `record_recommendation_event()` | 最近推荐结果（含 rank, sku_id, name, price） |
| `goods.last_candidates` | list[RecommendationRecord] | `record_recommendation_event()` | 最近候选列表 |
| `goods.viewed_skus` | list[str] | `record_product_detail_event()` | 最多50个已查看 SKU |
| `goods.compared_skus` | list[str] | `record_comparison_event()` | 当前比较的 SKU 列表 |
| `memory_events` | list[MemoryEventRecord] | 各 `record_*_event()` | 最多50条统一事件记录 |
| `event_memory` | EventMemory | 各 `record_*_event()` | 分类型事件 + active 指针 |
| `behaviours` | list[BehaviourRecord] | `append_behaviour()` | 行为摘要列表 |
| `dialogue_state_tracking` | DialogueStateTracking | `update_dialogue_state()` | **当前流程/类目/约束** |
| `cart` | CartState | `sync_cart()` | 购物车状态 |
| `trace_log` | list[dict] | `append_trace()` | 最近30条完整 trace 日志 |

#### DialogueStateTracking 字段详解（`domain.py:299`）

| 字段 | 含义 | 写入代码 |
|------|------|----------|
| `current_intent` | 当前意图类型 | `session_memory.py:347` |
| `current_flow` | 当前对话流（17种之一） | `session_memory.py:349` |
| `current_category` | 当前锁定的大类目 | `_record_turn()` L2578 |
| `current_sub_category` | 当前锁定的子类目 | `_record_turn()` L2579 |
| `active_constraints` | 活跃约束字典: `{price_min, price_max, features, negative_constraints, exclude_brands, include_brands, scenario}` | `_record_turn()` L2551-2560 |
| `missing_slots` | 澄清流程的缺失槽位 | `update_dialogue_state(missing_slots=decision.missing_slots)` |
| `resolved_references` | 引用别名→SKU 映射 | `build_reference_map()` 每事件后重建 |
| `last_task_plan` | 上轮任务计划 | `update_dialogue_state(task_plan=task_plan)` |
| `last_model_route` | 上轮模型路由 | `update_model_route()` |
| `last_trace` | 上轮完整 trace | `append_trace()` |

### Layer 2: 近期结构化事件记忆

生命周期为一个会话，存在 `SessionState.event_memory` 和 `SessionState.memory_events` 中。

#### 统一事件记录 MemoryEventRecord（`domain.py:154`）

| 字段 | 含义 |
|------|------|
| `event_id` | 唯一事件ID（`rec_001`, `detail_001`, `cart_001`, `cmp_001`） |
| `event_type` | "recommendation" / "product_detail" / "comparison" / "cart_action" |
| `turn_id` | 事件发生的轮次 |
| `source_event_id` | **事件链字段**——溯源到父推荐事件 |
| `category` | 事件所属商品类目 |
| `related_product_ids` | 涉及的商品 SKU 列表 |
| `payload` | rank_to_sku 映射、reference_alias_to_sku 映射、action 类型等 |

#### 分类型事件（`domain.py:186-239`）

- **RecommendationEvent**: event_id, query_id, turn_id, **rank_to_sku** (dict), products 列表, recommendation_mode, result_status, constraints
- **ProductDetailEvent**: event_id, query_id, turn_id, sku_id, target_ref, **source_event_id**, source_rank
- **ComparisonEvent**: event_id, query_id, turn_id, sku_ids, references, resolved_references, source_event_id
- **CartEvent**: event_id, query_id, turn_id, action, sku_ids, target_ref, source_event_id

#### active 指针（`EventMemory` 的四个状态字段）

- `active_recommendation_event_id` — 最近推荐事件 ID
- `active_detail_sku_id` — 最近查看详情的 SKU
- `active_comparison_event_id` — 最近比较事件 ID
- `active_cart_sku_id` — 最近加购的 SKU

#### 容量限制

| 数据结构 | 上限 | 代码位置 |
|----------|------|----------|
| `memory_events` | 50条 | `session_memory.py:587` |
| `recommendation_events` | 20条 | `session_memory.py:131` |
| `product_detail_events` | 30条 | `session_memory.py:189` |
| `comparison_events` | 20条 | `session_memory.py:249` |
| `cart_events` | 30条 | `session_memory.py:307` |

### Layer 3: 长期用户记忆

生命周期跨会话，保存在文件系统中。分为两个子部分。

#### Layer 3a: 原始历史记忆（`user_history_store.py`）

**存储目录**: `storage/user_history/{user_id}/`

```
{user_id}/
  profile.json          ← 用户画像 + semantic_memory + memory_cards
  sessions/
    {session_id}.json   ← 每会话完整 turn 记录 + state_snapshot
```

**profile.json 关键字段**:

| 字段 | 内容 |
|------|------|
| `profile_summary_text` | LLM 生成的自然语言画像（正常模式）或计数器拼接文字（隐私模式） |
| `structured_profile` | 9字段：说话风格/语言风格/价格偏好/类别偏好/品牌偏好/排斥条件/决策风格/信息关注点/客服交互偏好 |
| `explicit_preferences` | 用户明确声明的：price_preference, preferred_brands, excluded_brands, preferred_style, avoid_terms |
| `privacy_settings` | personalization_mode（full/semantic/off）等 |
| `semantic_memory` | 语义计数器（→ Layer 3b） |
| `memory_cards` | 最多50条结构化偏好卡片（含 confidence, evidence_count） |
| `memory_promotion_log` | 最近30条画像更新日志 |

**session JSON（每会话）**:

| 字段 | 内容 |
|------|------|
| `turns[]` | 每轮：turn_id, user_input, assistant_reply, recommended_products, retrieval_summary, cart_change, dialogue_state |
| `state_snapshot` | 完整 `SessionState.model_dump()`，用于跨会话恢复 |
| `cart` | 购物车快照 |

#### Layer 3b: 语义用户画像（`semantic_memory` 字段, `user_history_store.py:447-460`）

| 计数器 | 含义 | 更新代码 |
|--------|------|----------|
| `category_counts` | 类目→次数 | L498: `_inc(semantic["category_counts"], category)` |
| `sub_category_counts` | 子类→次数 | L499 |
| `feature_counts` | 偏好特征→次数 | L501 |
| `negative_constraint_counts` | 排除条件→次数 | L503 |
| `brand_counts` | 品牌→次数 | L505 |
| `price_signals` | 最近20条价格范围快照 | L508-518 |
| `recommended_skus` | SKU→推荐次数 | L520 |
| `cart_skus` | SKU→加购次数（amount=quantity） | L522 |
| `purchased_skus` | SKU→购买次数 | L527 |
| `style_signals` | 风格偏好→次数 | L529 |

计数器**每轮都更新**，数据来源是 `trace.parsed_query` 中解析出的结构化标签，而非对话原文。推荐/加购/购买的计数权重相同（都是 `amount=1`，cart_skus 使用 quantity）。

---

## 6. 关键代码调用链

### 指代消解完整调用链

```
ShoppingAgent._resolve_event_references()              ← shopping_agent.py:1144
  ├─ _collect_reference_terms(parsed_query)            ← L1247
  │    └─ 从 parsed_query.referents / cart_action.target_ref / intent_plan 各 step 收集
  │    └─ _references_in_text(): 匹配 query_understanding._reference_terms (27个词)
  ├─ SessionMemory.resolve_reference_from_memory_events(state, raw_message, references)
  │    ├─ latest_recommendation_event() → 找到最近推荐事件
  │    ├─ _rank_map_from_memory_event() → 从事件 payload 提取 rank→SKU 映射
  │    ├─ _resolve_rank_reference(ref, rank_map) → "第一个" → "第1个" → SKU
  │    └─ 返回 resolved: {"第一个": "p_beauty_005", ...}, source_event_id
  ├─ _apply_resolved_references_to_query()             ← L1217
  │    └─ 将解析出的 SKU 写入 parsed_query.mentioned_products / cart_action.sku_id
  └─ 降级: refresh_references() → build_reference_map()
       └─ 从 state.dialogue_state_tracking.resolved_references 查找
```

### rank→SKU 映射构建

```
PostProcessor.build_recommendation_records(candidates)   ← post_processor.py:85
  └─ rank = enumerate(candidates, start=1)

SessionMemory.record_recommendation_event()              ← session_memory.py:83
  └─ _build_rank_to_sku(recommendations)                 ← L597
      └─ 对 rank=1 生成: "第1个","第1款","第1件","第一个","第一款","第一件","一号","1号"
      └─ rank_to_sku 字典写入 RecommendationEvent 和 MemoryEventRecord.payload
```

### 话题延续/切换调用链

```
ShoppingAgent._merge_context_constraints(parsed_query, state)  ← L2598
  ├─ explicit_new_scope: 本轮有 category 且无 inherit_context 且无延续词
  │    └─ True → return（不继承任何约束，价格/品牌/特征全清空）
  ├─ same_topic: category 匹配上轮（或本轮 None）
  ├─ should_inherit: inherit_context 或 intent==REFINE 或有延续词
  └─ 若 same_topic && should_inherit: 合并 price/features/negative/brands

ShoppingAgent._record_turn()  ← L2524
  ├─ same_topic=False → previous_constraints = {} → active_constraints 仅来自本轮
  └─ same_topic=True  → 继承合并
```

---

## 7. 记忆写入的精确时机

| 写入操作 | 时机 | 代码位置 |
|----------|------|----------|
| `append_message(user)` | 意图解析、参考解析完成后，各业务逻辑执行前 | `shopping_agent.py:430` |
| `record_recommendation_event` | **LLM 回复生成后、商品卡片输出后**（动作成功后才写） | `shopping_agent.py:912-924` |
| `record_comparison_event` | 比较流 LLM 回复生成后 | `shopping_agent.py:925-936` |
| `record_cart_event` | 购物车工具调用成功后 | `shopping_agent.py` 购物车分支 |
| `record_product_detail_event` | 商品详情流回复后 | `shopping_agent.py` 详情分支 |
| `append_message(assistant)` | 各流回复生成后 | `shopping_agent.py:878` |
| `_record_turn` (append_behaviour + update_dialogue_state) | 所有前端事件生成后 | `shopping_agent.py:1003` |
| `save_turn` (持久化 turn + 更新 semantic_memory) | `_record_turn` 之后 | `shopping_agent.py:1048` |
| `maybe_refresh_profile` (LLM 画像刷新) | `save_turn` 之后，仅 force=True 或 privacy=semantic | `shopping_agent.py:1058` |
| `append_trace` | 全部完成后 | `shopping_agent.py:1080` |

**关键原则**: 事件是在**业务动作成功执行后**写入，而非意图识别后立即写入。推荐事件等 LLM 回复和卡片都生成完毕后才记录。

---

## 8. 指代消解的实现细节

### rank 别名生成（`session_memory.py:691`）

`_rank_aliases = ["一", "二", "三", "四", "五"]`——中文仅支持 rank 1~5。

```python
def _rank_reference_aliases(self, rank: int) -> list[str]:
    chinese_rank = self._rank_aliases[rank - 1] if rank <= 5 else str(rank)
    return [
        f"第{rank}个", f"第{rank}款", f"第{rank}件",
        f"第{chinese_rank}个", f"第{chinese_rank}款", f"第{chinese_rank}件",
        f"{chinese_rank}号", f"{rank}号",
    ]
```

列表长度为 8。在 rank 1~5 范围内，数字形式与中文形式不同，因此 8 个全部唯一。在 rank 6+ 时 `chinese_rank = str(rank)`（与数字一致），会产生重复键，但 `rank_to_sku` 是 dict，重复不影响功能。由于默认 `top_k=5`，rank 6+ 在实际使用中极少出现。

**核对结论**: 每个 rank 的别名生成函数始终返回 8 个元素；在 rank 1~5 范围内均为有效去重别名；rank 6+ 存在自重复但无实际影响。

### reference_terms（`query_understanding.py:58`）共 27 个

```python
_reference_terms = [
    "第一个","第一款","第一件","第1个","第1款",
    "第二个","第二款","第二件","第2个","第2款",
    "第三个","第三款","第3个","第3款",
    "第四个","第四款","第五个","第五款",
    "刚才那款","刚才那个","刚刚那款","刚刚那个",
    "前面那款","前面那个","上一个","上一款",
    "这个","这款","这一款","那个","那款",
    "它","它们","这两个","这几款","刚才这几款",
]
```

### "这个" / "它" 的绑定优先级

代码路径: `session_memory.py:558-563`，`build_reference_map()` 方法中：

```python
detail_sku = state.event_memory.active_detail_sku_id
cart_sku = state.event_memory.active_cart_sku_id

# 优先级 1: active_detail_sku_id（使用 references[alias] = 覆盖写入）
if detail_sku:
    for alias in ["这个", "这款", "这一款", "它", "当前这个", "当前这款",
                  "刚才介绍的", "刚才看的", "刚才这款"]:
        references[alias] = detail_sku

# 优先级 2: 最近推荐的第一款（elif，仅在 detail_sku 为空时执行）
elif first_recommended_sku:
    for alias in ["这个", "这款", "这一款", "它", "刚才那款", "刚才那个",
                  "前面那款", "前面那个"]:
        references[alias] = first_recommended_sku

# 优先级 3: active_cart_sku_id 绑定的是不同别名集合，不冲突
if cart_sku:
    for alias in ["刚才加购的", "刚才加到购物车的", "购物车里的那个",
                  "购物车里那个", "刚才买的"]:
        references[alias] = cart_sku
```

**真实优先级**: `active_detail_sku_id` > `first_recommended_sku` > rank_to_sku 中的通用别名。

注意 "刚才加购的" 和 "这个" 是不同别名集合，不存在冲突。`active_cart_sku_id` 不影响 "这个" 的绑定。

### source_event_id 事件链

```python
# 详情事件: source_event_id = 来源推荐事件 ID
record_product_detail_event(source_event_id=source_event_id)

# 购物车事件: source_event_id = 来源推荐事件 ID
record_cart_event(source_event_id=source_event_id)

# 比较事件: source_event_id = reference_resolution 中解析到的 source_event_id
record_comparison_event(source_event_id=reference_resolution.get("source_event_id"))
```

### 旧事件避免错误引用

`build_reference_map()` 优先使用 `active_recommendation_event_id` 指向的当前活跃推荐事件。`resolve_reference_from_memory_events()`（`session_memory.py:442`）仅查 `latest_recommendation_event()`，不遍历历史事件链。这意味着"上一轮的第三款"在中间有新推荐后可能无法正确解析。

---

## 9. 话题延续 vs 话题切换

### 延续当前话题（`_merge_context_constraints`, L2601-2631）

需同时满足三个条件：

1. `explicit_new_scope = False`
2. `same_topic = True`
3. `should_inherit = True`

```python
context_terms = ["继续","上次","刚才","前面","告诉我","哪些","合适",
                 "再","换","更","便宜","贵","只剩","还剩","剩下",
                 "零花钱","不要","排除","这个","那个","它","一起","分享","配着"]

explicit_new_scope = (
    bool(parsed_query.category or parsed_query.sub_category)
    and not parsed_query.inherit_context
    and not any(term in message for term in
        ["继续","上次","刚才","前面","这个","那个","它","第",
         "哪些","合适","再","换","更","便宜","贵了","太贵"])
)

should_inherit = (
    parsed_query.inherit_context
    or parsed_query.intent == IntentType.REFINE.value
    or any(term in message for term in context_terms)
)
```

满足后合并: `parsed_query.price_range`, `positive_constraints`, `negative_constraints`, `brands_include`, `brands_exclude` 均从 `active_constraints` 继承。

### 切换到新话题

`explicit_new_scope = True` → 直接 `return`（L2610-2611），**不继承任何约束**——价格、品牌、正负特征全部不合并到 `parsed_query`。

`_record_turn()` 中（L2539-2550）: `same_topic=False` → `previous_constraints = {}`，`active_constraints` 仅从本轮 `parsed_query` 构建。

### 切换类目后清理范围确认

当 `explicit_new_scope=True` 或 `same_topic=False` 时，以下全部清空/不继承：

| 字段 | `_merge_context_constraints` | `_record_turn` |
|------|------------------------------|----------------|
| price_min / price_max | 不合并到 parsed_query | active_constraints 无旧值 |
| positive_constraints (features) | 不合并 | 无旧 features |
| negative_constraints | 不合并 | 无旧 negative |
| brands_include | 不合并 | 无旧 include_brands |
| brands_exclude | 不合并 | 无旧 exclude_brands |
| scenario | — | 无旧 scenario |

购物车操作（CART_ACTION/CHECKOUT）**不改变** `current_category` 和 `active_constraints`，推荐主题保持不变。

### 优先级（代码验证的真实顺序）

```
1. 本轮 parsed_query 硬约束（negative_constraints, brands_exclude, price_range）
   → _hard_filter: 直接拦截不符合的商品
2. 本轮 parsed_query 正向约束（category, sub_category, positive_constraints）
   → _constraint_score: 正向加分
3. 当前会话 active_constraints（合并后的约束字典）
   → 用于补全本轮未指定的条件
4. 当前会话事件记忆（latest recommendation/detail event）
   → 用于指代消解
5. 长期偏好（global_preferences + structured_profile）
   → 仅软加分（_preference_score: -1.0 ~ +1.0），权重 4%~8%
6. 系统默认值
```

---

## 10. 记忆冲突与优先级（代码验证）

### 场景1: 长期偏好黑色，但本轮说不要黑色

- 长期偏好存在 `user.global_preferences.preferred_style`
- 检索时 `_preference_score()` 做软加分（+0.3）
- 但 `_hard_filter` L218-224: `negative_constraints` 中的词直接返回 `"negative_constraint:{term}"` 拦截
- **结论**: 本轮否定约束是硬拦截，长期偏好是软加分。本轮优先。`session_memory.py  L215` `brands_exclude` 同理。

### 场景2: 历史预算500，但本轮说1000

- `_merge_context_constraints` L2633-2636: `if parsed_query.price_range.max is None` 才继承旧值
- 本轮 `max=1000` 不为 None → 不继承 → 使用本轮 1000
- `_record_turn` L2553-2554 同理
- **结论**: 本轮明确价格优先于历史约束。

### 场景3: 上轮跑鞋，本轮明确要手机

- `_merge_context_constraints` L2610-2611: `explicit_new_scope=True` → `return`（不合并）
- `_record_turn` L2549: `same_topic=False` → `previous_constraints={}`
- **结论**: 旧约束全部清空。

### 场景4: 历史偏爱某品牌，但本轮明确排除

- `_hard_filter` L215: `if any(brand in product.brand for brand in parsed_query.brands_exclude)` → 硬拦截
- `_preference_score` L317: `if any(brand in product.brand for brand in preferences.excluded_brands): score -= 1.0`
- **结论**: 硬过滤 > 软减分 > 软加分。

### 场景5: 历史状态与最新推荐事件指向不同商品

- `build_reference_map()` 始终优先使用 `active_recommendation_event_id` 指向的最新事件
- "这个" / "它" 优先查 `active_detail_sku_id`
- **结论**: 最新事件优先。

---

## 11. 持久化、恢复和遗忘

### 存储目录和格式

- **路径**: `storage/user_history/{user_id}/profile.json` + `sessions/{session_id}.json`
- **格式**: JSON（`json.dumps(ensure_ascii=False, indent=2)`）
- **写入**: `path.write_text(json.dumps(...), encoding="utf-8")`，无并发锁

### 保存粒度

- **每轮保存**: `save_turn()` 每轮调用（`shopping_agent.py:1048`）
- session JSON 追加新 turn + 覆盖 `state_snapshot`
- profile.json 更新 `semantic_memory` 计数器

### 服务重启恢复

`shopping_agent.py:258-270`:

```python
restored_state, restored_from_session_id = self.user_history_store.restore_state(
    user_id=effective_user_id,
    source_session_id=target_session_id,
    target_session_id=session_id,
)
if restored_state is not None:
    self.session_memory.replace_state(restored_state)
```

恢复完整 `SessionState`（从 `state_snapshot` 用 `SessionState.model_validate()` 重建），包括对话状态、购物车、事件记忆、推荐记录。

### 容量上限

| 数据结构 | 上限 | 代码 |
|----------|------|------|
| `recent_messages` | 12条 | `session_memory.py:369` |
| `memory_events` | 50条 | `session_memory.py:587` |
| `recommendation_events` | 20条 | `session_memory.py:131` |
| `product_detail_events` | 30条 | `session_memory.py:189` |
| `comparison_events` | 20条 | `session_memory.py:249` |
| `cart_events` | 30条 | `session_memory.py:307` |
| `viewed_skus` | 50条 | `session_memory.py:193` |
| `trace_log` | 30条 | `session_memory.py:388` |
| `memory_cards` | 50条 | `user_history_store.py:548` |
| `memory_promotion_log` | 30条 | `user_history_store.py:565` |
| `price_signals` | 20条 | `user_history_store.py:518` |

### 未实现的功能（代码中未找到对应实现）

- **偏好时间衰减**: `confidence = min(confidence + 0.08, 0.98)` 只增不减，无衰减机制
- **会话过期清理**: 无自动清理，文件无限累积
- **并发写入保护**: `write_text` 无锁
- **旧 SKU 失效处理**: 无商品下架后的清理
- **用户删除偏好 API**: `apply_privacy_preferences` 可切换模式，但无"删除某个偏好"接口
- **负向反馈软减分**: `negative_constraint_counts` 仅硬过滤，不作为软减分权重

---

## 12. 长期个性化形成机制

### 计数器更新（`user_history_store.py:481-565`）

`_promote_turn_memory()` **每轮都调用**（在 `save_turn()` 内部），无论隐私模式：

1. 从 `trace.parsed_query` 提取 category, sub_category, positive_constraints, negative_constraints, brands, price_range
2. 对每个值 `_inc(counter, key, amount=1)`
3. 推荐过的 SKU: `_inc(semantic["recommended_skus"], sku_id)` — 不区分用户是否点击/查看
4. 加购过的 SKU: `_inc(semantic["cart_skus"], sku_id, amount=quantity)`
5. 购买过的 SKU: `_inc(semantic["purchased_skus"], sku_id)`

**权重差异**: 推荐/加购/购买/偏好特征的计数权重相同（都是 `amount=1`），cart_skus 使用 quantity（可能 > 1）。无事件类型差异化权重。

### 记忆卡片（`user_history_store.py:568-591`）

从 `parsed_query` 的 constraints 生成:
- 类型: "preference"（confidence=0.62）/ "avoidance"（0.66）/ "price_preference"（0.58）
- 重复命中: `confidence = min(confidence + 0.08, 0.98)`, `evidence_count += 1`
- 最多50条，按 `confidence × last_seen_at` 排序

### 在后续检索中的使用

`HybridRetriever._preference_score()`（`hybrid_retriever.py:310-323`）:

```python
if any(brand in product.brand for brand in preferences.preferred_brands): score += 0.7
if any(brand in product.brand for brand in preferences.excluded_brands): score -= 1.0
if any(term in product.searchable_text for term in preferences.preferred_style): score += 0.3
if any(term in product.searchable_text for term in preferences.avoid_terms): score -= 0.5
```

在 `final_score` 公式中占 **4%~8%** 权重（有 reranker 时 0.08×preference_score，无 reranker 时 0.04×preference_score）。

### 画像形成的准确描述

- 计数器**每轮都更新**，数据持续积累
- `memory_cards` 的 confidence 只增不减，无反例衰减
- 画像在 LLM prompt 注入和检索重排序中使用（均为软约束）
- **计数器不直接参与硬过滤**——category_counts/brand_counts 本身不改变 `_hard_filter` 行为

---

## 13. 多轮对话完整案例

```
用户: 推荐三款防晒
  → category="美妆护肤", sub_category="防晒" → 检索返回3款
  → record_recommendation_event: rank_to_sku={"第一个":"p_beauty_010","第1个":"p_beauty_010",...}
  → _record_turn: active_constraints={price_max:null, features:["防晒"],...}
  → save_turn → _promote_turn_memory: category_counts["美妆护肤"]+=1, feature_counts["防晒"]+=1

用户: 第一个太贵了
  → referents=["第一个"] → _resolve_event_references → latest_recommendation_event()
  → rank_map["第一个"]="p_beauty_010" → resolved
  → intent=REFINE → _merge_context_constraints: same_topic=True, should_inherit=True
  → 继承 active_constraints.price_max + features

用户: 把第二款加入购物车
  → referents=["第二款"] → rank_map["第二款"]="p_beauty_009"
  → cart_action.sku_id="p_beauty_009" → execute_cart → success
  → record_cart_event: sku_ids=["p_beauty_009"], source_event_id="rec_001"
  → active_cart_sku_id="p_beauty_009"
  → _record_turn: same_topic=True（购物车不影响推荐主题）

用户: 刚才加购的那款适合敏感肌吗？
  → referents=["刚才加购的那款"]
  → resolve_reference_from_memory_events() → rank_map 无"刚才加购的" → resolved={}
  → 降级: build_reference_map() → active_cart_sku_id="p_beauty_009"
  → resolved_references["刚才加购的"]="p_beauty_009"
  → _promote_ellipsis_reference_intent: intent改为DETAIL
  → record_product_detail_event: sku_id="p_beauty_009", source_event_id="rec_001"
```

---

## 14. 90 秒面试回答

> 我们的记忆系统解决的核心问题是：用户在多轮对话中不断补充偏好、指代之前的商品、切换话题，系统需要准确理解上下文。
>
> 代码上由四类组件共同实现，但在设计上按照时间尺度归纳为三层记忆。
>
> 第一层是短期会话状态，存在内存里，追踪当前对话流程——在17种对话流中的哪一种、用户正在看的商品类目、以及累积的筛选条件如价格区间和品牌，生命周期是一个会话。
>
> 第二层是近期结构化事件记忆，每条推荐、比较、加购都记录为带 ID 的事件。最核心的是推荐事件的 rank 到 SKU 映射——"第一个"对应哪个具体商品——以及事件之间的 source_event_id 溯源链。这层专门解决"第一个太贵了""刚才加购的那个怎么样"这类指代。
>
> 第三层是长期用户记忆，文件持久化，跨会话保存。内部包含两个部分：一是原始历史记录——每轮对话的完整 turn 和状态快照，支持服务重启后恢复；二是语义计数画像——比如用户看过美妆12次、关注保湿15次，这些计数用于后续的软排序和个性化风格调整。
>
> 优先级上，本轮用户明确说的条件永远是硬约束，历史偏好只做软加分，不会覆盖本轮需求。

---

## 15. 3 分钟详细面试回答

> 代码上由四类组件共同实现，但在设计上按照时间尺度归纳为三层记忆：会话状态、事件记忆和长期用户记忆。长期用户记忆内部同时保存可恢复的原始历史，以及面向个性化的语义统计画像。
>
> **第一层是短期会话状态**（SessionState），纯内存存储。核心是 DialogueStateTracking，追踪当前处于哪种对话流程——17种 DialogueFlow、当前锁定的商品类目和子类目、以及活跃的约束条件字典——price_min、price_max、正向特征列表、排除条件、品牌黑名单。这个字典在每轮结束时合并更新：同话题下自动继承——用户说"推荐防晒"后锁定美妆护肤，再说"便宜一点的"，系统知道在美妆护肤里找、且继承价格约束；但切换类目时全部清空——用户突然说"推荐一款手机"，旧的防晒类约束不继承。
>
> **第二层是近期事件记忆**，解决指代消解。每次推荐完成后生成一个 RecommendationEvent，核心是 rank_to_sku 映射。rank=1 生成"第1个""第一个""第一款""1号""一号"等别名——在 rank 1~5 范围内这8个别名全部指向同一个 SKU。用户说"第一个太贵了"，系统从最新活跃推荐事件中 O(1) 查到对应 SKU。"这个"和"它"的绑定有优先级：如果用户刚看过商品详情，指向那个详情商品；否则指向最近推荐的第一款。"刚才加购的"则通过 active_cart_sku_id 指针绑定。
>
> 比较事件、详情事件、购物车事件通过 source_event_id 链接回源推荐事件，形成事件链——用户先推荐三款防晒，加购某款，再问细节，系统能追溯到是哪个推荐事件产生的。
>
> 所有事件都是在业务动作成功执行后才写入——推荐事件等 LLM 回复和卡片都生成完毕才记录，购物车事件等工具调用成功后记录。不存在"意图识别后就写事件"的提前写入。
>
> **第三层是长期用户记忆**，文件持久化到 `storage/user_history/{user_id}/`。每轮 `save_turn()` 写 turn 记录和完整 SessionState 快照——对话流程、购物车、事件链、约束条件都在。服务重启后从快照恢复完整状态。
>
> 同时 `_promote_turn_memory()` 从每轮解析结果中提取结构化标签做本地计数——用户说"推荐保湿面霜"，category_counts["美妆护肤"]+=1, feature_counts["保湿"]+=1。这些计数器有两个用途：隐私模式下直接拼成文字画像（"用户关注保湿15次"），不把原文发给 LLM；在检索重排序中做软加分——偏好品牌加0.7分、排斥品牌减1.0分。但占最终分仅 4%~8%，不会改变硬约束。
>
> **话题切换**：每轮开始时记录 flow_before，结束后对比 flow_after。独立的上下文延续逻辑通过 explicit_new_scope 和 same_topic 两个判定处理。从美妆突然跳到数码时，active_constraints 中所有字段——价格、品牌、正负特征——全部清空。
>
> **当前局限**：计数器无时间衰减；单次查询和反复确认的权重相同；文件持久化无并发锁；事件查找只取最近一次，不支持"上一轮的第三款"这种跨事件引用；rank 中文别名仅支持 1~5 位。

---

## 16. 面试追问与回答

### Q1: 为什么不能只保存完整对话文本？

对话文本无法直接支持三类核心操作。一是指代消解——"第一个"需要 rank→SKU 映射，纯文本没有这种结构。二是约束继承——"再便宜一点"需要带上轮类目和价格语境，文本需要重新理解。三是个性化计数——隐私模式下需要不暴露原文就能形成偏好摘要，结构化计数器天然支持这一点。

### Q2: 为什么区分 SessionState 和事件记忆？

SessionState 存储当前进行中的状态（current_category、active_constraints），用于下一轮的上下文继承，每轮覆盖更新。事件记忆存储已完成动作的结果（rank→SKU 映射），按时间追加，不可变。而且 active 指针（active_recommendation_event_id）和历史事件列表分离，确保指代解析总引用最新事件。

### Q3: "第一个"和"这个"是怎么定位 SKU 的？

"第一个"通过 rank 映射。推荐事件写入时预生成所有别名，"第一个"→"第1个"→SKU，O(1) 字典查找。

"这个"有三级优先级（`session_memory.py:558-563`）：active_detail_sku_id（刚看过详情）> 最近推荐的第一款 > rank_to_sku 中的通用映射。

### Q4: 什么时候写事件，意图识别后还是动作成功后？

**动作成功后**。推荐事件在 LLM 回复和商品卡片都生成后才写入（`shopping_agent.py:912`），购物车事件在工具调用成功后写入。意图识别正确但动作执行失败的情况下不会留下错误的事件记录。

### Q5: 如何避免一次购买被当成长期偏好？

`PreferenceManager` 仅对包含"以后""一直""记住""平时"等长期标记词的输入才写入 `global_preferences`。计数器中单次行为会被计入，但检索中权重仅 4%~8%。不过当前确实没有单次 vs 多次的计数权重区分。

### Q6: 本轮需求和长期偏好冲突怎么办？

硬过滤优先。`_hard_filter` 中的 negative_constraints 和 brands_exclude 直接拦截商品，不管长期偏好。`_preference_score` 的软加减分仅占 4%~8%。"长期喜欢兰蔻但本轮说不要兰蔻"→ brands_exclude 硬拦截生效。

### Q7: 服务重启后如何恢复？

从 `sessions/{session_id}.json` 的 `state_snapshot` 字段读取，`SessionState.model_validate(snapshot)` 重建完整 Pydantic 对象——dialogue_state_tracking、event_memory、cart、goods、recent_messages 全部恢复。

### Q8: 事件记忆越来越大怎么办？

有硬上限：推荐事件20条、详情30条、购物车30条、memory_events 50条。超限 slice 截断旧事件。不支持按时间淘汰或按重要性保留。

### Q9: 为什么用计数器而不是每轮让 LLM 总结？

延迟和隐私两个原因。计数器在 `_promote_turn_memory` 中同频更新，毫秒级。隐私模式下可以在不暴露对话原文的情况下形成画像摘要。LLM 画像只在会话结束时触发一次。

### Q10: 当前记忆系统最大的局限是什么？

五个方面：计数器无时间衰减（confidence 只增不减）；单次行为与多次确认权重相同；文件持久化无并发锁；事件查找只取最近一次——"上次推荐的第三款"如果中间有新推荐会找错；rank 中文别名仅支持 1~5 位。

---

## 17. 代码事实核对表

| 说法 | 核对结果 | 代码证据 |
|------|----------|----------|
| 代码上由四类组件实现，设计上归纳为三层记忆 | **准确** | SessionState、EventMemory、UserHistoryStore、semantic_memory 四组件 → 会话状态/事件记忆/长期记忆三层 |
| SessionMemory 管理 17 种对话流 | **已实现** | `DialogueStateTracking.current_flow`, 17种定义在 `agent.py:7-24` |
| 当前类别锁定 | **已实现** | `current_category` 在 `_record_turn()` L2578 中写入，`_merge_context_constraints()` 中继承 |
| 话题切换检测 | **已实现** | `flow_before` vs `flow_after` 对比（L283），`explicit_new_scope`（L2602-2611），`same_topic`（L2539-2549） |
| 切换类目时清理全部约束（价格/品牌/特征） | **已实现** | `_merge_context_constraints` L2610 `return` → 不合并；`_record_turn` L2550 `previous_constraints={}` |
| 推荐事件保存 rank→SKU 映射 | **已实现** | `record_recommendation_event()` → `_build_rank_to_sku()` → `rank_to_sku` dict |
| rank=1 生成 "第一个""第一款""第1个"等别名 | **已实现** | `_rank_reference_aliases()` L691-702，列表长度8，rank 1~5 范围内全部唯一 |
| rank 中文别名仅支持 1~5 | **已实现** | `_rank_aliases = ["一","二","三","四","五"]` L23；rank 6+ 中文回退为数字 |
| "这个"绑定优先级: detail_sku > first_recommended | **已实现** | `build_reference_map()` L558-563: `if detail_sku:` → overwrite; `elif first_recommended_sku:` |
| "刚才加购的"绑定到 active_cart_sku_id | **已实现** | `build_reference_map()` L565-567 |
| 事件通过 source_event_id 形成事件链 | **部分实现** | Detail/Cart/Comparison 有 source_event_id；但 resolve 时仅查 latest，不遍历链 |
| 事件在业务动作成功后写入，非意图识别后 | **已实现** | 推荐事件在 LLM 回复+卡片生成后（L912）；购物车事件在工具成功后 |
| 每轮保存完整 turn 和 state_snapshot | **已实现** | `save_turn()` 追加 turn + 覆盖 state_snapshot |
| 服务重启后支持恢复完整 SessionState | **已实现** | `restore_state()` → `model_validate(snapshot)` → `replace_state()` |
| category_counts 等计数器每轮更新 | **已实现** | `_promote_turn_memory()` 在每轮 `save_turn()` 内部调用 |
| 计数器在检索重排序中使用 | **部分实现** | `_preference_score()` 使用 preferred_brands/style/avoid_terms；但计数器本身不直接参与打分公式 |
| 不需要 LLM 就能形成画像 | **部分实现** | 隐私语义模式不需要 LLM；正常模式仍依赖 LLM（会话结束时触发一次） |

---

## 18. 评价当前设计

### 已实现的亮点

- **结构化会话状态**: `DialogueStateTracking` 将流程/类目/约束拆分为独立字段，不依赖 LLM 理解上下文
- **rank→SKU 预生成别名**: 事件写入时预生成全部别名，解析时 O(1) 查找
- **事件链可追溯**: `source_event_id` 串联推荐→详情/加购/比较
- **跨会话持久化恢复**: `state_snapshot` 完整快照 + session JSON 分文件存储
- **可解释的偏好计数**: 计数器按来源分类，可追溯到具体行为
- **本轮需求优先**: `_hard_filter` 硬约束 > `active_constraints` 继承 > 长期偏好软加分

### 当前局限（均有代码证据）

- **别名硬编码**: `_reference_terms` 27个词，`_rank_aliases` 仅5个中文，rank 6+ 中文回退为数字
- **事件检索仅最近一次**: `resolve_reference_from_memory_events()` 只查 `latest_recommendation_event()`，不支持跨事件引用
- **偏好无时间衰减**: `confidence` 只增不减
- **单次行为权重同多次**: `_inc` 每次都是 `amount=1`
- **文件持久化无并发锁**: `path.write_text()` 直接写入
- **缺少负向反馈软减分**: `negative_constraint_counts` 仅硬过滤，不作为排序软信号
- **事件记忆与 SessionState 存在数据重复**: `goods.last_recommendations` 与 `event_memory.recommendation_events[-1]` 存相似数据
- **缺少用户主动管理偏好的 API**: 只能切换隐私模式，不能删除特定偏好
