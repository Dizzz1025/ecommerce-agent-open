# 面试问答准备

基于已确认的项目事实，为 AI Agent 工程师面试准备的问答材料。

---

## 一、项目介绍题

### Q1: 请简单介绍你的项目

**建议回答框架**：
> 我构建了一个 RAG 多轮电商导购 AI Agent 系统。用户可以用自然语言描述需求（如"帮我推荐适合混油皮的清爽防晒，预算 300 以内"），系统理解意图后从真实商品库检索、打分、排序，通过 LLM 生成有理由的推荐，并通过 SSE 流式返回给 Android 客户端。系统还支持多轮对话、个性化记忆、自然语言购物车操作、图片搜索和结账引导。

**关键数字**：
- 151 件真实商品，4 大类，美妆 24 个子类目
- 18 种意图类型，17 种对话流
- 后端 50+ Python 文件，前端 37 个 Kotlin 文件
- 20+ SSE 事件类型
- 3 个本地 ML 模型

### Q2: 这个项目解决的核心问题是什么？

1. **搜索效率**：用户不需要自己从大量商品中筛选，Agent 理解复杂需求并直接给出推荐
2. **推荐可信度**：基于真实商品库 + 事实边界隔离 + 输出校验，防止 LLM 编造
3. **个性化**：记住用户偏好，千人千面的导购体验
4. **转化闭环**：推荐→比较→加购→结账，一站式完成

---

## 二、架构设计题

### Q3: 为什么选择三阶意图理解（模板→LLM→规则）而不是直接用 LLM？

**技术原因**：
1. **延迟**：简单查询（如"推荐一款精华"）可以通过模板在 <1ms 内完成，不需要等待 LLM ~2s
2. **可靠性**：LLM 输出可能无法解析为 JSON，规则回退作为保底方案保证系统可用
3. **成本**：减少不必要的 LLM 调用（问候、越界输入等）
4. **可控性**：模板匹配对简单模式更精确

**代码证据**：`backend/app/agents/query_understanding.py` — `parse()` 方法

### Q4: 为什么 SSE 事件要设计 20+ 种而不是简单的"一次性返回所有结果"？

1. **用户体验**：即时反馈（进度事件），减少感知等待
2. **流式展示**：推荐理由逐字显示（打字机效果），更像真人在导购
3. **前端解耦**：progress → token → recommendation_section → product_card 各有独立的 UI 组件
4. **可中断**：用户可以在流式输出过程中继续输入

**代码证据**：`backend/app/utils/sse.py` + `ChatViewModel.kt` — `handleStreamEvent()`

### Q5: 为什么 Agent 不使用 LangChain/AutoGPT 等框架，而是自建编排？

**代码证据表明的设计选择**：
1. **可控性**：ShoppingAgent 的 10 阶段编排完全是确定性的代码逻辑，不存在 Agent 框架的黑盒行为
2. **性能**：LangChain 的 Agent 循环模式（thought→action→observation→thought...）会显著增加 LLM 调用次数
3. **领域适配**：电商导购有明确的业务流程（17 种），不需要通用的 ReAct 循环
4. **依赖最小化**：requirements.txt 仅 7 个依赖，无框架锁定

### Q6: 混合检索的 7 维权重是如何设计的？

- **有 Reranker 时**：keyword 0.18, semantic 0.24, constraint 0.22, enhancement 0.08, price_fit 0.10, preference 0.08, reranker 0.10
- **无 Reranker 时**：keyword 0.24, semantic 0.28, constraint 0.22, enhancement 0.12, price_fit 0.10, preference 0.04

**设计思路**（合理推断）：
- Semantic 权重最高（语义匹配是核心）
- Reranker 存在时分担了 semantic 的部分权重
- Preference 权重较低（避免个性化过强覆盖用户当前需求）

**代码证据**：`backend/app/retrieval/hybrid_retriever.py` — `retrieve()` 方法

---

## 三、Agent 技术题

### Q7: Agent 的状态管理是怎么做的？

**三层状态管理**：

| 层 | 存储 | 生命周期 | 内容 |
|----|------|---------|------|
| 会话状态 | SessionMemory (内存 dict) | 服务重启丢失 | 对话状态、事件记忆、引用图谱 |
| 事件记忆 | 会话状态的一部分 | 会话内 | RecommendationEvent, CartEvent 等（最近 20 条） |
| 用户历史 | UserHistoryStore (文件系统 JSON) | 持久化 | Profile, SemanticMemory, MemoryCards |

**关键设计**：
- 会话状态通过 state_snapshot 序列化到文件系统，支持恢复
- 事件记忆包含 rank_to_sku 映射，支持"第一个"这类指代消解
- 语义记忆通过 `_promote_turn_memory()` 在每轮后增量更新

**代码证据**：`backend/app/memory/session_memory.py` + `user_history_store.py`

### Q8: 如何处理多轮对话中的上下文继承？

1. **话题锁定**：`_should_lock_current_topic()` 检测是否延续上一轮话题
2. **约束合并**：`context_merge` 将当前轮次的约束与历史约束合并
3. **指代消解**：8 个别名/排名 + 代词绑定 + 事件链追踪
4. **意图继承**：REFINE/FILTER 意图自动继承上一轮类别

**代码证据**：`shopping_agent.py` — `_stream_chat_core()` 阶段 3

### Q9: 系统的容错和降级策略是什么？

1. **检索容错**：4 级渐进式松弛（价格→子类目→否定→全库存）
2. **LLM 降级**：DoubaoClient → MockLLMClient（200+ 行规则引擎）→ 模板回复
3. **意图理解降级**：LLM IntentPlan → 规则回退（200+ 条别名）
4. **画像生成降级**：LLM → 语义计数器 → 关键词回退
5. **视觉分析降级**：VLM → 关键词匹配回退
6. **全局异常捕获**：try/except 整轮 → 格式化的错误 SSE 事件序列

### Q10: 如何防止 LLM 幻觉？

1. **事前隔离**：LLM 只能看到 `Verified product facts`（当前候选商品），无法看到全库存
2. **事后校验**：ResponseValidator 扫描输出中的产品名和价格
3. **价格上下文豁免**：8 个预算相关 token（"以内"、"以下"、"预算"、"不超过" 等）不会被误判
4. **安全回退**：检测到幻觉时用排名第一的真实商品生成安全文案

**代码证据**：`backend/app/agents/response_validator.py`

---

## 四、RAG 与 Memory 题

### Q11: 你的 RAG 和标准 RAG 有什么区别？

**标准 RAG**：Embedding → 向量检索 → Top-K → LLM 生成

**本项目的 RAG**：
1. **意图理解前置**：先解析意图（类别、约束、价格），再检索
2. **硬过滤优先**：在语义匹配之前用业务规则排除不相关商品
3. **七维混合打分**：不仅看语义相似度，还考虑约束满足、偏好、价格适配
4. **查询扩展**：`_enhanced_query()` 将领域同义词加入检索（如 "皮肤干" → "皮肤干燥起皮 补水保湿推荐 干皮"）
5. **后处理校验**：否定词安全处理，去除未通过硬过滤的商品
6. **渐进式容错**：0 结果时自动松弛约束

**代码证据**：`backend/app/retrieval/hybrid_retriever.py`

### Q12: 用户记忆如何跨会话持久化？

1. **存储格式**：`storage/user_history/{user_id}/profile.json` + `sessions/{session_id}.json`
2. **每轮持久化**：`UserHistoryStore.save_turn()` 在每轮对话后写入磁盘
3. **语义积累**：`_promote_turn_memory()` 增量更新类别计数、特征计数、品牌计数等
4. **画像更新**：`UserProfileService.maybe_refresh_profile()` 非强制模式下按需更新（LLM 调用）
5. **记忆卡片**：每个偏好/行为被提升为记忆卡片（confidence × last_seen_at 排序），保留前 50 条

**代码证据**：`backend/app/memory/user_history_store.py`

### Q13: 协同过滤具体怎么实现的？

1. 构建"风格文档"（画像 + 最近轮次 + 当前查询）
2. 从优先级列表 + 全局用户池加载候选参考用户
3. `LocalModelManager.semantic_scores()` 计算当前用户与候选用户的语义相似度
4. `_lexical_similarity()` 作为词汇级回退
5. 类别重叠得分
6. 融合：`max(语义, 回退×0.88) × 0.72 + 类别重叠 × 0.28`
7. 阈值 0.38（有语义分）或 0.28（无语义分）
8. Top 3 相似用户的 profile 和 few-shot 示例注入 prompt

**代码证据**：`backend/app/memory/personalization_service.py` — `_collaborative_style_reference()`

---

## 五、工程化题

### Q14: 你的依赖注入是怎么设计的？

- 使用 `@lru_cache` + 工厂函数模式（非装饰器 DI 框架）
- 所有依赖在 `backend/app/core/dependencies.py` 中集中管理
- `ShoppingAgent` 接收 20 个依赖参数
- 优势：零外部依赖、类型安全、易于测试（可替换任何依赖）
- 劣势：手动管理依赖图，新增模块需要修改工厂函数

**代码证据**：`backend/app/core/dependencies.py`

### Q15: 如何处理 LLM 调用的超时和重试？

- `generate_response()`：超时 20s
- `stream_generate_response()`：超时 30s
- `decide_frontend_action()`：超时 25s，重试 2 次
- `resolve_user_intent()`：超时 25s，重试 2 次
- `analyze_user_profile()`：超时 18s，重试 1 次
- JSON 提取失败时自动尝试截取 `{...}` 重新解析
- 全部失败时触发对应的回退路径

**代码证据**：`backend/app/llm/doubao_client.py` — 各方法的 timeout 参数

### Q16: 有没有做 A/B 测试或效果评估？

**从代码可以确认**：
- 有隐私模式 A/B 对照测试（TC-PRIV-001）：同一用户 lily_beauty_pro，三个 session 使用不同隐私模式，验证 full/semantic/off 的差异
- 有协同过滤风格对比：xiaomei_beauty（小白型）vs lily_beauty_pro（专家型），同一查询观察回复风格差异
- 有购物车个性化验证：5 个预置购物车用户

**代码证据**：`测试场景与测试用例.md` — TC-PRIV-001; `docs/综合测试报告cc.md:254-263`

**需要用户确认**：是否有定量指标（准确率、延迟、用户满意度）？

---

## 六、项目难点题

### Q17: 这个项目最大的技术挑战是什么？

**候选回答（需要根据你的实际经历选择/调整）**：

1. **LLM 输出的可控性**：如何让 LLM 既保持自然语言的表现力，又不编造商品信息？
2. **多轮对话的上下文管理**：如何在有限 token 内传递足够的对话历史和个性化信息？
3. **实时流式 + 复杂 UI 的协调**：20+ SSE 事件类型如何在 Android 上正确组装为连贯的 UI？
4. **意图理解的工程权衡**：如何在延迟（<1ms 模板）和准确率（~2s LLM）之间取得平衡？

### Q18: 遇到过一个具体 bug 是怎么解决的？

以下是从代码中观察到的设计迭代线索：

1. **InputPreprocessor 的"好的"误判**（`input_preprocessor.py`）："拍照好的手机"中的"好的"曾被误判为问候。解决方法：添加产品意图词检测，在 `_is_greeting()` 中检查是否为产品相关短语。

2. **ResponseValidator 的价格误判**（`response_validator.py`）：LLM 说"在 300 元以内"时，"300 元"被误判为幻觉价格。解决方法：添加 8 个预算上下文 token 豁免。

3. **Windows 文件名乱码**（`product_repository.py`）：商品图片在 Windows 文件系统上的路径包含 mojibake 字符。解决方法：rglob 文件名匹配回退。

### Q19: 这个系统和 ChatGPT 插件/Copilot 有什么不同？

1. **领域深度**：ChatGPT 是通用对话，本系统有领域特定的意图类型（18 种）和业务流程（17 种）
2. **可信度机制**：事实边界隔离 + 双重验证，而 ChatGPT 插件可能返回不存在的信息
3. **个性化**：5 层个性化（硬约束→画像→购物车→风格→隐私），而非通用的 memory 功能
4. **业务闭环**：推荐→加购→结账是完整的电商转化链路，而非独立的问题回答
5. **成本优化**：本地模型（embedding/reranker）+ 模板路由减少不必要的 LLM 调用

---

## 七、个人贡献题

> 根据 `my-contributions-template.md` 中的填写内容回答。

### Q20: 你在项目中具体负责什么？

（需要你根据实际情况填写，参考 `my-contributions-template.md`）

### Q21: 哪些设计决策是你主导的？

（需要你根据实际情况填写）

---

## 八、压力追问题

### Q22: 如果商品库扩大到 10 万件，你的检索方案需要怎么改？

1. **Embedding 预计算 + 向量数据库**：当前方案每次检索时对所有商品计算 embedding，需要改为预计算 + Milvus/Qdrant
2. **两阶段检索**：粗排（向量检索 Top-100）→ 精排（混合打分 + Reranker Top-10）
3. **硬过滤前置**：在向量检索前就通过类别/价格索引过滤
4. **分片策略**：按类目分片，减少单次检索范围

### Q23: 如果 Doubao API 完全不可用，你的系统还能工作吗？

**能**，代码中已有完整降级：
1. MockLLMClient 替代 LLM（200+ 行规则意图解析 + 模板回复）
2. 本地 embedding/reranker 模型（BGE + text2vec）替代 API 的语义能力
3. 模板回复覆盖所有核心流程（推荐、购物车、结账、问候等）
4. 规则意图解析覆盖 16 种意图 + 200+ 条类别别名

**但降级后的局限**：
- 回复模板化，缺乏个性化表达
- 复杂场景（场景捆绑、商品对比）质量下降
- 多模态功能完全不可用

### Q24: 系统的延迟瓶颈在哪里？

**代码中可观察到的耗时点**：
1. Doubao LLM IntentPlan 调用（~2s）
2. Doubao LLM 回复生成（~3-5s）
3. 本地模型推理：embedding + reranker（~0.5-2s，取决于 CPU 和商品数量）
4. 图片分析 VLM 调用（~3s）
5. 画像刷新 LLM 调用（非每轮触发）

**优化方向**（合理推断）：
- LLM 调用并行化（IntentPlan 和回复生成无法并行，但图片分析和意图理解可以）
- Embedding 预计算和缓存
- 流式输出减少感知延迟（已实现）
- 进度事件提供即时反馈（已实现）

### Q25: 如果你现在重写这个系统，会怎么设计？

可能的改进方向（需要你根据实际反思回答）：
1. 使用向量数据库替代内存检索
2. 引入 Agent 评测框架和自动化回归测试
3. 前端改用声明式 SSE 解析（Kotlin Flow + sealed class 事件层次）
4. 购物车状态迁移到 Redis 实现服务无状态
5. 添加 LLM 调用缓存减少重复调用
6. 引入结构化日志和分布式追踪

---

## 九、项目不足和改进方向

### Q26: 你认为这个项目最大的不足是什么？

**可以从代码中确认的不足**（避免显得在自我批评）：
1. 商品库规模小（151 件），大规模下的检索效果未验证
2. 测试覆盖不足（前端零测试，后端仅基础 API 测试）
3. 单机架构，无法水平扩展
4. 用户画像完全依赖对话历史，无外部信号（浏览、点击、购买）
5. LLM 输出的风格一致性没有 A/B 测试验证

### Q27: 如果有更多时间，你会优先做什么？

建议优先级：
1. P0：补充核心流程的集成测试和回归测试套件
2. P0：LLM 调用的可观测性（延迟、成功率、token 用量）
3. P1：检索性能优化（embedding 预计算、向量数据库）
4. P1：商品库扩容 + 大规模下的效果验证
5. P2：前端单元测试
6. P2：多语言支持

---

## 十、针对 JD 的匹配要点

根据 `岗位JD.md`，AI Agent 工程师的核心要求与本项目的对应关系：

| JD 要求 | 项目对应 | 证据 |
|---------|---------|------|
| 需求理解与归因 | 三阶意图理解（18 种意图） | `query_understanding.py` |
| AI 原生架构设计 | ShoppingAgent 自研编排（非 LangChain） | `shopping_agent.py` |
| 知识/环境建设 | 商品知识库 + RAG（混合检索+7维打分） | `hybrid_retriever.py` |
| 核心能力实现 | 意图识别 + 任务分解 + 反思/修正 | TaskPlanner + ResponseValidator |
| 系统迭代与评估 | 隐私 A/B 对照 + 协同过滤风格对比 | 测试场景与测试用例.md |
| 性能优化 | 异步+降级+流式+可观测 | 全系统降级链路 |
