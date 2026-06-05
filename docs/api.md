# 后端 API 与前端联调说明

本文档给前端和测试同学使用，说明当前后端真实可用的 HTTP/SSE 接口、请求格式、流式事件、统一输出结构，以及前端应该如何根据 `frontend_events` 和 `frontend_data` 执行动作。本文只描述最新实现，不保留旧版字段或旧联调假设。

## 1. 基本约定

- 本地后端地址：`http://127.0.0.1:8000`
- API 前缀：`/api`
- 商品主键：`sku_id`
- 商品来源：只来自 `ecommerce_agent_dataset`
- 主对话接口：SSE 流式返回
- 前端最推荐消费：最终 `turn_result` 事件

## 2. 健康检查

```http
GET /health
```

响应：

```json
{"status": "ok"}
```

## 3. 商品接口

### 3.1 商品列表

```http
GET /api/products
```

可选参数：

| 参数 | 说明 |
| --- | --- |
| `q` | 关键词 |
| `category` | 一级类目，例如 `数码电子` |
| `sub_category` | 二级类目，例如 `智能手机` |
| `brand` | 品牌 |
| `price_min` | 最低价 |
| `price_max` | 最高价 |
| `limit` | 返回数量，默认 20，最大 100 |

示例：

```bash
curl "http://127.0.0.1:8000/api/products?category=数码电子&sub_category=智能手机&limit=3"
```

响应结构：

```json
{
  "products": [
    {
      "sku_id": "p_digital_016",
      "product_id": "p_digital_016",
      "name": "OPPO Reno 16 Pro 轻薄人像摄影高刷屏快充5G智能手机12+256GB",
      "category": "数码电子",
      "sub_category": "智能手机",
      "brand": "OPPO",
      "price": 3299.0,
      "stock": 80,
      "image_url": "/static/dataset/2_数码电子/images/p_digital_016_live.jpg",
      "tags": ["拍照", "轻薄", "快充"],
      "reviews_summary": "来自商品知识库的评价摘要"
    }
  ]
}
```

### 3.2 商品详情

```http
GET /api/products/{sku_id}
```

示例：

```bash
curl "http://127.0.0.1:8000/api/products/p_digital_016"
```

商品不存在时返回：

```json
{"detail": "Product not found"}
```

## 4. 主对话接口

```http
POST /api/chat/stream
Content-Type: application/json
```

请求体：

```json
{
  "user_id": "user_001",
  "session_id": "session_001",
  "message": "推荐一款适合油皮的洗面奶",
  "input_type": "text",
  "resume": false,
  "new_session": false,
  "metadata": {}
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `user_id` | 用户 ID，用于长期历史、画像和恢复；可以为空 |
| `session_id` | 会话 ID；同一个 ID 会延续短期记忆和购物车 |
| `message` | 用户本轮输入 |
| `input_type` | `text` 或 `image_text`；图片+文本多模态使用 `image_text` |
| `resume` | 是否从该用户最近历史会话恢复 |
| `new_session` | 是否强制开启新会话 |
| `metadata` | 扩展字段；多模态可放 `image_path`、`image_url`、`image_base64`，恢复可放 `resume_session_id`，隐私可放 `privacy_mode` 和 `store_raw_history` |

说明：如果 `metadata.resume_session_id` 存在，后端会自动按老用户历史恢复处理，即使请求体没有显式传 `resume=true`，也会尝试恢复指定历史会话。

图片 + 文本请求示例：

```json
{
  "user_id": "user_001",
  "session_id": "session_mm_001",
  "message": "有没有类似这种款式，但价格低一点的背包",
  "input_type": "image_text",
  "metadata": {
    "image_path": "/Users/grsxsa/Desktop/backpack.jpg"
  }
}
```

隐私设置请求示例：

```json
{
  "user_id": "user_001",
  "session_id": "session_privacy_001",
  "message": "开启隐私个性化，只用语义信息，然后推荐一款适合通勤的背包",
  "metadata": {
    "privacy_mode": "semantic",
    "store_raw_history": false
  }
}
```

隐私字段说明：

| 字段 | 可选值 | 说明 |
| --- | --- | --- |
| `metadata.privacy_mode` | `full` / `semantic` / `off` | 完整个性化、隐私个性化、关闭个性化 |
| `metadata.store_raw_history` | `true` / `false` | 是否把原始用户输入和系统回复保存到本地 history |

用户也可以直接用自然语言切换：

- `关闭个性化推荐`
- `开启隐私个性化，只用语义摘要，不要用原文历史`
- `不要保存聊天`
- `开启个性化，可以根据历史偏好推荐`

## 5. SSE 事件

后端会返回多个 SSE 事件。前端可以边接收 `token` 边展示打字效果，但最终页面状态应以 `turn_result` 为准。

| 事件 | 前端建议 |
| --- | --- |
| `state` | 调试用，可忽略 |
| `progress` | 展示“正在理解需求/正在检索/正在组织回复”等处理状态，正式结果返回后停止展示 |
| `token` | 流式展示回复文本 |
| `product_cards` | 可提前渲染商品卡片，也可等待 `turn_result` |
| `products` | 兼容商品卡片事件 |
| `alternatives` | 相近备选商品 |
| `cart_update` / `cart` | 购物车工具结果 |
| `scenario` | 场景组合方案 |
| `frontend_action` | 页面动作摘要，可调试用 |
| `turn_result` | 前端最终推荐使用的统一输出 |
| `done` | 本轮结束 |
| `error` | 系统异常 |

前端推荐做法：

1. 用 `token` 做流式文本；
2. 用 `progress` 做等待态提示，不要展示成模型推理链；
3. 收到 `turn_result` 后，用里面的 `frontend_events` 和 `frontend_data` 校准最终 UI；
4. 不要直接依赖 `system_debug` 做普通页面展示。

`progress` 事件示例：

```text
event: progress
data: {"progress_message":"已经理解您的需求，正在查找目标商品","stage":"retrieval"}
```

注意：

- `progress_message` 是面向用户的等待态文案，不是模型推理链；
- 如果正式结果提前返回，前端应立即停止 progress 动画，展示 `turn_result`；
- progress 只表达后端工作阶段，不承诺最终一定推荐成功。

## 6. `turn_result` 三段式输出

完整结构：

```json
{
  "frontend_events": [
    {
      "步骤": 1,
      "动作类型": "show_reply",
      "含义": "展示系统回复",
      "数据参考": "reply_message",
      "blocking": false
    }
  ],
  "frontend_data": {
    "reply_message": {
      "中文说明": "系统要展示给用户的回复文本。",
      "text": "我按你的要求筛到了这些更合适的商品。"
    }
  },
  "system_debug": {
    "中文说明": "本部分用于后端调试，普通用户不展示。"
  }
}
```

前端只需要理解：

- `frontend_events` 是动作步骤；
- 每个事件的 `数据参考` 指向 `frontend_data` 中的一个 key；
- 按步骤读取对应数据并更新 UI；
- `system_debug` 是后端调试信息，不展示给普通用户。

## 7. 前端动作类型

| 动作类型 | 数据参考 | 前端动作 |
| --- | --- | --- |
| `show_reply` | `reply_message` | 展示 AI 回复文本 |
| `show_products` | `recommended_products` 或 `alternative_products` | 展示商品卡片或图片 |
| `show_product_detail` | `product_detail` | 展示商品详情或商品问答 |
| `navigate` | `navigation` | 跳转页面 |
| `update_cart` | `cart_state` | 更新购物车角标、购物车列表、订单状态 |
| `update_page_state` | `page_state` | 更新非对话页面状态；当前只在必要时出现 |
| `show_clarification_options` | `clarification_options` | 展示澄清问题和快捷选项 |
| `show_error` | `error_message` | 展示真实系统异常 |

重要约束：

- 正常无完全匹配不一定是错误，通常会用 `reply_message` 和 `alternative_products` 表达；
- 需要用户澄清不算错误，用 `show_clarification_options`；
- 只有真实后端异常才用 `show_error`。

## 8. 常见 `frontend_data` 字段

### 8.1 回复文本

```json
{
  "reply_message": {
    "中文说明": "系统要展示给用户的回复文本。",
    "text": "这款比较适合你现在的预算和拍照需求。"
  }
}
```

用户只看 `text`，不要展示 `中文说明`。

### 8.2 推荐商品

```json
{
  "recommended_products": {
    "中文说明": "本轮推荐给用户看的商品卡片，全部来自本地商品库和检索结果。",
    "products": [
      {
        "sku_id": "p_digital_016",
        "name": "OPPO Reno 16 Pro ...",
        "category": "数码电子",
        "sub_category": "智能手机",
        "brand": "OPPO",
        "price": 3299.0,
        "image_url": "/static/dataset/...",
        "reason": "这款轻薄好带，拍照表现也更贴合你想要的日常人像需求。",
        "highlight_short": "轻薄人像摄影手机",
        "suitable_scenarios": ["通勤", "拍照"],
        "target_user_tags": ["拍照用户"],
        "non_standard_query_tags": ["拍照好的手机"],
        "score": 0.84
      }
    ]
  }
}
```

前端卡片建议展示：

- 图片：`image_url`
- 名称：`name`
- 价格：`price`
- 推荐理由：`reason`
- 点击详情时使用：`sku_id`

说明：

- `highlight_short`、`suitable_scenarios`、`target_user_tags`、`non_standard_query_tags` 来自商品库增强字段；
- 前端可以展示 `highlight_short` 或 `reason`，不要自己生成商品事实；
- 商品卡片里的所有价格、名称、类目和图片都以接口返回为准。

### 8.3 相近备选商品

```json
{
  "alternative_products": {
    "中文说明": "没有完全命中时提供的相近备选商品，前端可作为弱提示展示。",
    "products": []
  }
}
```

适用情况：

- 真实库存没有完全符合预算或类目的商品；
- 系统仍找到了相近真实商品；
- 回复文本会说明不完全贴合，前端不要标成错误。

### 8.4 购物车状态

```json
{
  "cart_state": {
    "中文说明": "购物车工具执行后的真实购物车状态。",
    "tool_ok": true,
    "tool_name": "add_to_cart",
    "message": "已把 OPPO Reno 16 Pro 加入购物车，数量 1。",
    "cart": {
      "items": [],
      "total_items": 1,
      "total_price": 3299.0
    }
  }
}
```

前端用途：

- 更新购物车角标；
- 更新购物车列表；
- 展示工具反馈；
- 如果 `cart.order` 存在，展示订单预览。

### 8.5 页面跳转

```json
{
  "navigation": {
    "中文说明": "页面跳转动作。前端可以按 target_page 切换页面，并使用 params 定位商品或订单。",
    "target_page": "cart_page",
    "reason": "用户明确要求查看购物车",
    "should_end_conversation": false,
    "params": {}
  }
}
```

页面跳转策略：

| 用户表达 | 是否跳转 |
| --- | --- |
| `推荐一款手机` | 不跳转 |
| `把第一款加入购物车` | 不跳转 |
| `查看第一款详情` | 跳 `product_detail_page` |
| `查看购物车` | 跳 `cart_page` |
| `下单/结算/付款` | 跳 `checkout_page` |

### 8.6 澄清选项

```json
{
  "clarification_options": {
    "中文说明": "当用户需求不完整时，前端可以展示这些快捷选项。",
    "question": "你更关注拍照、续航还是性价比？",
    "missing_slots": ["priority"],
    "options": ["拍照", "续航", "性价比"]
  }
}
```

前端可以把 `options` 做成快捷按钮，也可以只展示 `question`。

## 9. `system_debug` 给谁看

`system_debug` 只给后端、测试和答辩使用，不给普通用户展示。它通常包含：

- 当前轮次分析；
- 对话状态变化；
- 记忆变化；
- RAG 检索过程；
- 工具执行；
- 模型调用；
- Doubao 意图计划；
- 个性化分析；
- 购物车商品侧个性化；
- 商品增强字段使用；
- 回复策略；
- 进度事件；
- 运行耗时统计；
- 多模态分析；
- 隐私保护；
- 层次记忆；
- 输出校验；
- 历史恢复状态；
- 前端动作决策。

其中 `Doubao意图计划` 用来检查复杂组合动作是否被正确拆解。例如：

```json
{
  "Doubao意图计划": {
    "中文说明": "Doubao 返回并被系统解析后的 IntentPlan。",
    "内容": {
      "primary_intent": "refine",
      "is_multi_intent": true,
      "steps": [
        {"intent": "cart_add"},
        {"intent": "cart_remove"},
        {"intent": "refine"}
      ]
    }
  }
}
```

隐私和层次记忆调试示例：

```json
{
  "隐私保护": {
    "个性化模式": "semantic",
    "是否允许个性化": true,
    "是否允许使用历史原文做个性化": false,
    "是否仅使用语义摘要": true,
    "是否保存原始历史": false
  },
  "层次记忆": {
    "短期会话消息数": 4,
    "最近推荐商品数": 3,
    "本轮是否产生晋升候选": true,
    "本轮晋升候选观察": ["用户偏好：清爽", "预算上限：200元"]
  }
}
```

购物车侧个性化和商品增强字段调试示例：

```json
{
  "购物车商品侧个性化": {
    "是否启用": true,
    "参考购物车商品": [{"sku_id": "p_digital_001"}],
    "商品标签": ["Apple生态", "数码生态"],
    "价格画像": {"tier": "high"},
    "命中的本地规则": [{"rule_id": "apple_macbook_ecosystem"}],
    "是否调用Doubao": false,
    "排序影响": [{"sku_id": "p_digital_025", "boost": 0.66}]
  },
  "商品增强字段使用": {
    "是否启用": true,
    "使用的增强字段": ["highlight_short", "suitable_scenarios", "non_standard_query_tags"],
    "命中的非标准问题标签": ["适合记笔记的平板"],
    "命中的适用场景": ["通勤"]
  }
}
```

Progress 和耗时统计示例：

```json
{
  "进度事件": {
    "预测的工作类型": ["意图理解", "记忆读取", "检索执行", "回复组织"],
    "预计耗时等级": "medium",
    "使用的模板": ["intent_understanding", "retrieval", "response_generation"]
  },
  "运行耗时统计": {
    "total_duration_ms": 1200.5,
    "model_call_count": 1,
    "Top耗时模块": [{"module": "rag_retrieval", "duration_ms": 520.1}]
  }
}
```

前端正式页面不展示这些字段；测试模式可以展示，用于确认隐私设置和长期偏好晋升是否生效。

## 10. Session 调试接口

这些接口主要给调试和答辩使用，普通前端页面不需要依赖。

```http
GET /api/session/{session_id}/state
GET /api/session/{session_id}/memory
GET /api/session/{session_id}/trace
GET /api/session/{session_id}/profile?user_id=user_001
GET /api/session/{session_id}/history?user_id=user_001
```

含义：

| 接口 | 用途 |
| --- | --- |
| `/state` | 当前流程、意图、类目、约束、购物车数量、最近模型路由 |
| `/memory` | 完整短期会话状态 |
| `/trace` | 每轮执行链路 |
| `/profile` | 本地长期用户画像和历史会话索引 |
| `/history` | 本地指定 session 历史文件，便于检查原文是否按隐私设置隐藏 |

交互脚本已经把这些接口压缩成 `/state`、`/memory`、`/trace`、`/profile` 命令。

## 11. 购物车接口

### 11.1 查看购物车

```http
GET /api/cart?session_id=session_001
GET /api/cart/{session_id}
```

响应：

```json
{
  "items": [
    {
      "sku_id": "p_digital_016",
      "name": "OPPO Reno 16 Pro ...",
      "price": 3299.0,
      "quantity": 1,
      "image_url": "/static/dataset/..."
    }
  ],
  "total_price": 3299.0,
  "total_items": 1
}
```

### 11.2 加入购物车

```http
POST /api/cart/add
Content-Type: application/json
```

```json
{
  "session_id": "session_001",
  "sku_id": "p_digital_016",
  "quantity": 1,
  "source": "button"
}
```

### 11.3 删除、修改、清空

```http
POST /api/cart/remove
POST /api/cart/update
POST /api/cart/clear
POST /api/cart/{session_id}/clear
```

删除请求：

```json
{
  "session_id": "session_001",
  "sku_id": "p_digital_016"
}
```

修改数量请求：

```json
{
  "session_id": "session_001",
  "sku_id": "p_digital_016",
  "quantity": 2
}
```

清空请求：

```json
{
  "session_id": "session_001"
}
```

## 12. 前端联调建议

1. 聊天页只需要先支持 `show_reply`、`show_products`、`update_cart`、`navigate` 四类动作。
2. 商品卡片点击详情时，前端可以直接请求 `GET /api/products/{sku_id}`。
3. 普通推荐结果不要自动跳商品列表页，维持在聊天页展示卡片。
4. 普通加购不要自动跳购物车页，只更新角标。
5. 只有 `navigation.target_page` 出现时才切页。
6. `system_debug` 可以做成测试模式面板，正式用户页面关闭。

## 13. 多模态输出说明

图片 + 文本输入仍然使用同一个 `turn_result`。前端普通展示不需要新增复杂事件，仍按 `frontend_events` 执行即可。

多模态相关信息主要出现在：

```json
{
  "system_debug": {
    "多模态分析": {
      "是否启用多模态": true,
      "图片输入": {},
      "图片理解结果": {},
      "图文融合查询": {},
      "视觉匹配商品": {
        "best_match": {
          "sku_id": "p_beauty_001",
          "name": "雅诗兰黛特润修护肌活精华露淡纹紧致保湿夜间修护抗初老精华30ml"
        }
      },
      "库存匹配判断": {}
    }
  }
}
```

前端测试模式可以展示这些信息；正式用户页面只展示回复和商品卡片即可。若 `视觉匹配商品.best_match` 存在，说明后端已经把图片匹配到某个真实库存商品。若 `库存匹配判断.库存是否覆盖目标类目=false`，系统会如实说明当前库没有对应商品，不会返回编造商品卡片。
