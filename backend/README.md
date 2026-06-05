# Backend

Minimum demo backend for the RAG ecommerce shopping guide agent.

## Scope

- Loads the real four-category competition dataset from `PRODUCT_DATASET_DIR`
- `/health`
- `/api/products` with query/category/brand/price filters
- `/api/products/{sku_id}`
- `/api/chat/stream` with `state/token/product_cards/products/cart_update/cart/done`
- `/api/cart` and `/api/cart/{session_id}`
- `/api/session/{session_id}/state`
- `/api/session/{session_id}/memory`
- Rule-first query understanding, dialogue flow controller, task planner
- Hybrid retrieval, post-processing, grounded response generation, validation
- In-memory session state, references, active constraints, and cart
- Input preprocessing, model routing, long-term preference memory, product QA, scene bundle planning
- Trace API for every agent turn
- Local `text2vex-base-chinese`, `bge-small-zh-v1.5`, and `bge-reranker-base` support for semantic classification/retrieval/reranking
- Mock LLM by default, Doubao-compatible client behind `USE_MOCK_LLM=false`

Full local test guide: `../docs/local_backend_testing_guide.md`

## Run

```bash
uvicorn app.main:app --reload
```

## Useful Demo Prompts

- `推荐一款适合油皮的洗面奶`
- `200元以下的蓝牙耳机有哪些`
- `帮我推荐跑鞋` -> `要轻量的` -> `预算1500以内`
- `比较第一款和第二款哪个更适合日常慢跑`
- `推荐一款手机` -> `拍照好一点`
- `这款防晒含酒精吗`
- `我一直比较喜欢清爽一点的护肤品`
- `把第一款加入购物车`
- `查看购物车`

## Debug

```bash
python3 scripts/agent_debug_demo.py --memory
```

Useful endpoints:

- `GET /api/session/{session_id}/state`
- `GET /api/session/{session_id}/memory`
- `GET /api/session/{session_id}/trace`
