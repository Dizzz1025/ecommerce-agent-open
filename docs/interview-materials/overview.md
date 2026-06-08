# 项目概览

## 项目基本信息

- **项目名称**：Ecommerce Guider — RAG 多轮电商导购 AI Agent
- **版本**：v8（2026-06-08）
- **代码仓库**：本地 Git 仓库，分支 `v8`，共 10 次提交（0603v1 → v8）
- **技术栈**：Python 3.11+ / FastAPI / Kotlin / Jetpack Compose / Doubao LLM / Sentence Transformers

## 项目背景 【文档确认 + 代码确认】

### 用户问题

传统电商搜索存在以下痛点（来源：`docs/system_design.md`、`技术报告.md`）：
1. 用户需要自己从大量商品中筛选比较，决策成本高
2. 搜索框只能匹配关键词，无法理解"适合混油皮的清爽防晒"这类复杂需求
3. 缺乏个性化，新用户和历史用户看到相同结果
4. 推荐结果缺乏可信的解释和理由
5. 从浏览到下单的转化链路断裂，购物车操作和推荐分离

### 项目目标

构建一个**多轮对话式电商导购 AI Agent**，核心能力：
1. **可信推荐**：基于真实商品库，不编造产品，给出有理由的推荐
2. **个性化导购**：记住用户偏好、肤质、预算，提供千人千面的导购体验
3. **业务闭环**：从推荐 → 比较 → 加购 → 结算的完整转化链路

## 核心功能 【代码确认】

| 功能 | 状态 | 证据 |
|------|------|------|
| 文本对话推荐 | 已完成 | `POST /api/chat/stream` — `backend/app/api/routes/chat.py:16` |
| 图片+文字多模态搜索 | 已完成 | `POST /api/chat/stream/upload` — `backend/app/api/routes/chat.py:49` |
| 多轮上下文理解 | 已完成 | `ShoppingAgent._stream_chat_core()` 中的 `context_merge` + `reference_resolution` |
| 意图识别（18种意图） | 已完成 | `backend/app/models/domain.py` — `IntentType` 枚举 |
| 商品检索（混合检索+重排序） | 已完成 | `backend/app/retrieval/hybrid_retriever.py` |
| 个性化推荐（5层机制） | 已完成 | `backend/app/memory/personalization_service.py` |
| 购物车管理 | 已完成 | `backend/app/services/cart_service.py` |
| 自然语言购物车操作 | 已完成 | `backend/app/tools/action_executor.py` |
| 商品对比 | 已完成 | `ComparisonEvent` + `ScenePresentationBuilder._comparison_prompt()` |
| 场景捆绑推荐 | 已完成 | `backend/app/agents/scenario_planner.py` (8种场景) |
| 商品问答 | 已完成 | `backend/app/agents/product_qa.py` |
| 流式输出 (SSE) | 已完成 | `backend/app/utils/sse.py` + 20+ SSE 事件类型 |
| 推荐结果流式展示 | 已完成 | `backend/app/agents/recommendation_streaming.py` |
| 进度事件反馈 | 已完成 | `backend/app/progress/progress_event_builder.py` |
| 回复幻觉校验 | 已完成 | `backend/app/agents/response_validator.py` |
| 检索容错降级（4级回退） | 已完成 | `backend/app/retrieval/fallback.py` |
| 隐私模式（full/semantic/off） | 已完成 | `backend/app/memory/user_history_store.py` — `apply_privacy_preferences()` |
| 用户画像管理 | 已完成 | `backend/app/memory/user_profile_service.py` |
| Android 客户端 | 已完成 | 37 个 Kotlin 文件，6 个页面 |

## 技术栈 【代码确认】

### 后端
| 组件 | 技术选型 | 证据 |
|------|---------|------|
| Web 框架 | FastAPI 0.115+ | `backend/requirements.txt` |
| 异步服务器 | Uvicorn | `backend/requirements.txt` |
| LLM | Doubao Seed 2.0 (`ep-20260514111645-lmgt2`) | `.env` + `backend/app/llm/doubao_client.py` |
| 本地 Embedding | BGE-small-zh-v1.5 | `backend/models/bge-small-zh-v1.5/` |
| 本地语义模型 | text2vec-base-chinese | `backend/models/text2vec-base-chinese/` |
| 本地 Reranker | BGE-reranker-base | `backend/models/bge-reranker-base/` |
| LLM 降级 | MockLLMClient（本地规则引擎） | `backend/app/llm/mock_llm.py` |
| 数据存储 | 文件系统 JSON（user_history/） | `backend/app/memory/user_history_store.py` |
| 会话状态 | 内存字典 (InMemoryStore) | `backend/app/memory/in_memory_store.py` |
| HTTP 客户端 | httpx | `backend/requirements.txt` |
| 测试框架 | pytest | `backend/pyproject.toml` |

### 前端
| 组件 | 技术选型 | 证据 |
|------|---------|------|
| 平台 | Android (minSdk 26, targetSdk 35) | `android/app/build.gradle.kts` |
| UI 框架 | Jetpack Compose + Material 3 | `android/app/build.gradle.kts` |
| 导航 | Navigation Compose 2.8.9 | `android/app/build.gradle.kts` |
| 架构模式 | ViewModel + Repository | `ChatViewModel.kt`, `ShoppingRepository.kt` |
| 网络通信 | HttpURLConnection + SSE 流解析 | `ShoppingRepository.kt` |
| 状态管理 | Kotlin StateFlow | 各 ViewModel |

### 数据
| 项目 | 数量 | 证据 |
|------|------|------|
| 商品总数 | 151 件 | `docs/综合测试报告.md:20` |
| 美妆护肤 | 40 件，24 个子类目 | `backend/beauty_analysis.json` |
| 数码电子 | 37 件 | `ecommerce_agent_dataset/2_数码电子/` |
| 服饰运动 | 37 件 | `ecommerce_agent_dataset/3_服饰运动/` |
| 食品饮料 | 37 件 | `ecommerce_agent_dataset/4_食品生活/` |
| 构造测试用户 | 8+ 人设 + 3 个重度使用用户 | `storage/user_history/` |
| 本地模型 | 3 个（embedding ×2 + reranker ×1） | `backend/models/` |

## 当前完成程度 【代码确认 + 合理推断】

### 已完成
- 核心 Agent 编排引擎（`ShoppingAgent`，2715 行）
- 三阶意图理解（模板 → LLM → 规则）
- 混合检索（关键词 + 语义 + 约束 + 偏好 + 模型 embedding + 重排序）
- 5 层个性化机制
- 18 种意图类型 + 17 种对话流
- SSE 流式协议（20+ 事件类型）
- 多模态图片搜索
- Android 客户端（6 页面）
- 检索容错降级
- 回复幻觉校验
- 3 种隐私模式
- 场景捆绑推荐
- 结账引导

### 明确限制（来源：`技术报告.md` 第 444-456 行）
1. 商品库仅 151 件
2. 本地模型使用 CPU 推理
3. 会话状态在服务重启后丢失
4. 无真实支付集成
5. 用户画像仅基于对话历史
6. 视觉模型能力有限
7. 无多语言支持

### Git 迭代历史
```
1ea9cc6 v8 (2026-06-08)
bc03d52 v8 (2026-06-07)
8ef99a9 v8 (2026-06-07)
bb2862e v7 (2026-06-06)
ef39e07 v6 (2026-06-06)
8207c32 v5 (2026-06-06)
fb9fdcf v5 (2026-06-06)
751037d v2 (2026-06-06)
7cbc13c v2 (2026-06-05)
cbd37a4 0603v1 (2026-06-05)
```
项目在约 3 天内从 v1 迭代到 v8，总共 10 次提交，v5→v8 之间有大量功能增量。
