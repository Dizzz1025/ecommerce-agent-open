# 文档目录

本文档是 `docs/` 的总入口，用来告诉后端、前端和测试同学每份文档应该怎么读。当前目录只保留与最新后端实现一致的文档；所有说明均以 2026-06-02 版本为准。

## 推荐阅读顺序

1. [system_design.md](./system_design.md)
   最新系统设计文档。适合答辩、后端交接和整体理解，包含 Doubao-first IntentPlan、商品 RAG、事件记忆、隐私个性化、运行耗时统计、progress events、购物车侧个性化、商品增强字段和多模态扩展。

2. [unified_agent_console_test_guide.md](./unified_agent_console_test_guide.md)
   统一后端 Agent 控制台测试指南。当前测试主入口，说明唯一脚本 `backend/scripts/agent_console.py` 的老用户/新用户模式、多轮输入、progress events、个性化、购物车侧个性化、多模态和复杂问题测试。

3. [local_backend_testing_guide.md](./local_backend_testing_guide.md)
   本地测试指南。适合测试同学从 VSCode 终端开始完成环境准备、健康检查、单元测试、统一脚本固定消息模式、多轮交互、历史恢复、三用户历史测试和调试命令使用。

4. [api.md](./api.md)
   前端联调文档。说明 HTTP/SSE 接口、`progress` 事件、`turn_result` 三段式输出、`frontend_events` 执行顺序和 `system_debug` 的测试用途。

5. [inventory_grounded_acceptance_test_guide.md](./inventory_grounded_acceptance_test_guide.md)
   库存真实约束验收文档。所有案例都基于真实商品库，重点验证多轮对话、排除约束、场景组合、复杂 IntentPlan、购物车和下单。

6. [advanced_capability_test_results.md](./advanced_capability_test_results.md)
   高级能力与创新设计测试结果。记录目前所有特殊设计、创新能力、完整测试命令和预期效果。

7. [product_enhancement_report.md](./product_enhancement_report.md)
   商品增强字段说明。解释新增商品字段、字段用途，以及这些字段如何进入 query enhancement、召回、重排、推荐理由、比较和详情问答。

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

## 当前版本底线

- 商品推荐必须来自 `ecommerce_agent_dataset`，禁止编造库存外商品。
- 当前用户本轮明确需求是硬约束；历史画像、购物车画像和增强字段都是软约束。
- 普通推荐和普通加购不主动跳转页面，只有用户明确要求查看详情、查看购物车或结算时才发 `navigate`。
- 用户可见回复不能出现 `RAG`、`memory`、`状态机`、`trace`、`IntentPlan` 等开发者内部词。
- 复杂、多动作、模糊 Mandarin 表达默认交给 Doubao 识别为结构化 IntentPlan，再由后端工具确定性执行。
- 正常澄清、无完全匹配、库存不覆盖某类商品不是系统异常，不应展示成 `show_error`。
