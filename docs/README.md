## 后端目录速览

后端主目录：

```text
backend/app
```

| 目录 | 作用 |
| --- | --- |
| `api/` | FastAPI 路由层，包含 chat、products、cart、session、health。 |
| `agents/` | Agent 核心编排：意图理解、状态机、任务计划、回复生成、前端事件构造、商品详情问答。 |
| `llm/` | Doubao 与 Mock LLM 客户端。Doubao 负责复杂 IntentPlan、回复生成、画像分析和复杂决策。 |
| `retrieval/` | Hybrid Retrieval：结构化过滤、关键词、向量召回、增强字段匹配、重排序、后处理。 |
| `rag/` | RAG 上下文与 prompt 构造，只把检索后的真实商品事实交给大模型。 |
| `tools/` | 确定性业务工具：购物车、结算、订单、商品检索等。 |
| `memory/` | 短期会话、事件记忆、本地用户历史、长期画像、隐私设置和购物车侧个性化。 |
| `multimodal/` | 图片加载、视觉分析、图文融合查询和无 GPU fallback。 |
| `progress/` | 面向前端的处理进度提示模板。 |
| `repositories/` | 商品仓库读取与标准化，只读取 `ecommerce_agent_dataset`。 |
| `services/` | 商品、购物车、结算、订单等基础服务。 |
| `models/` | Pydantic 数据结构，包括 `ParsedQuery`、`IntentPlan`、商品、购物车、SSE schema。 |
| `ml/` | 本地小模型加载与调用，包含 BGE、text2vec、reranker。 |
| `core/` | 配置、依赖注入和日志。 |
