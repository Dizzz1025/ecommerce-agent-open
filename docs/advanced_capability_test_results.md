# 高级能力、创新设计与测试结果

本文档汇总当前后端已经实现的特殊设计和创新能力，并给出完整测试命令与应该观察到的效果。它不是接口说明，而是给测试、答辩和后端自查使用的复现清单。所有推荐商品必须来自 `ecommerce_agent_dataset`，不允许编造库存外商品。

## 1. 当前回归结果

进入后端目录：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
```

编译检查：

```bash
python3 -m compileall app
```

离线回归测试：

```bash
USE_MOCK_LLM=1 pytest -q
```

当前结果：

```text
49 passed
```

说明：

- `USE_MOCK_LLM=1` 用于离线回归，不消耗 Doubao API；
- 正式验收可去掉 `USE_MOCK_LLM=1`，使用真实 Doubao；
- 本地小模型路径正确时，可加 `ENABLE_LOCAL_MODELS=true` 做更贴近正式 Demo 的测试。

## 2. 已实现的核心创新设计

### 2.1 Doubao-first IntentPlan

复杂、模糊、多动作 Mandarin 表达优先交给 Doubao 输出结构化 IntentPlan；后端只执行系统支持的动作。

亮点：

- 一句话可拆成多个步骤，例如 `cart_add -> cart_remove -> refine`；
- 工具动作由后端确定性执行，大模型不能伪造购物车状态；
- `system_debug.Doubao意图计划` 会展示 Doubao 返回并被系统解析后的动作序列；
- 只保留极少数严格模板走本地规则，降低本地误判率。

### 2.2 事件记忆

系统除了状态记忆和画像记忆，还维护业务事件记忆：

- 推荐事件：保存一次推荐列表的稳定顺序；
- 商品详情事件：保存用户当前关注的商品；
- 对比事件：保存本轮比较对象；
- 购物车事件：保存加购、删除、结算等动作。

效果：

- 用户说“第二个”“第一款”“刚才那个”时，先从事件记忆解析到稳定 `sku_id`；
- 新推荐目标出现前，系统不会轻易忘记上一轮推荐列表；
- 商品详情、对比和购物车操作都能回溯正确商品。

### 2.3 库存真实约束 RAG

系统采用结构化过滤、关键词匹配、BGE 向量召回、text2vec 语义召回、BGE reranker 和规则重排的 hybrid retrieval。

底线：

- Doubao 只看到检索后的真实商品上下文；
- 回复中的商品名、价格、品牌、库存、参数、成分、优惠都必须来自数据库；
- 没有完全匹配但有相近商品时，主动给出真实备选；
- 完全超出库存时，如实说明，并引导用户调整方向。

### 2.4 积极导购回复策略

系统 prompt 已统一为主动、肯定、清晰的导购风格。

规则：

- 能推荐具体商品时，不以“抱歉/没有找到”开头；
- 部分匹配时说“我先为你挑了几款更接近需求的选择”；
- 普通推荐 2-4 句，比较最多 5 句，购物车反馈 1-2 句；
- 用户画像只影响语气、排序和解释重点，不在用户回复中暴露“画像”“记忆”等内部词。

`system_debug.回复策略` 会记录：

- 匹配状态：`exact_match` / `partial_match` / `alternative` / `no_result` / `out_of_scope`；
- 是否启用积极回复；
- 是否避免否定开头；
- 长度策略；
- 使用的个性化参考。

### 2.5 Progress Events

后端会尽早返回美化后的处理进度，避免前端空转。

示例进度：

- “已经理解您的需求，正在整理关键信息”
- “正在查找目标商品”
- “正在挑选更合适的商品”
- “正在组织回复”

`system_debug.进度事件` 会记录：

- 预测的工作类型；
- 预计耗时等级；
- 使用的模板；
- 实际耗时。

### 2.6 运行耗时统计

每轮对话都会统计关键模块耗时。

覆盖模块：

- memory 读取；
- 意图理解；
- IntentPlan 执行；
- RAG 检索；
- 商品后处理；
- 购物车侧个性化；
- prompt 构造；
- Doubao 调用；
- response validation；
- frontend events 构造；
- history 保存。

`system_debug.运行耗时统计` 会显示：

- 总耗时；
- 模块耗时列表；
- 模型调用次数和耗时；
- 最耗时 Top 模块。

### 2.7 层次记忆与隐私个性化

系统支持短期记忆、事件记忆、长期画像、语义记忆卡片和隐私开关。

模式：

- `full`：允许使用历史摘要、偏好、必要的历史证据；
- `semantic`：只使用语义摘要和向量化/结构化信息，不使用原始聊天文本；
- `off`：关闭个性化。

特点：

- 当前轮需求永远优先于历史画像；
- “这次不要”不会写成长期偏好；
- “以后都不要”“我一直不喜欢”才进入长期偏好候选；
- 用户可选择不保存原始聊天，但仍保留非原文语义记忆。

### 2.8 购物车侧个性化推荐

除用户画像外，系统会分析购物车商品的共性，形成商品侧画像。

已实现本地规则：

- `apple_macbook_ecosystem`：MacBook / Apple 生态 -> iPad、AirPods、同生态数码；
- `phone_audio_ecosystem`：手机 -> 真无线耳机、平板、同品牌生态；
- `training_apparel_to_shoes`：训练/速干服饰 -> 跑步鞋、运动帽、轻量透气装备；
- `premium_skincare_routine`：高端护肤核心单品 -> 面霜、眼霜、精华、修护保湿链路；
- `outdoor_travel_bundle`：户外/旅行商品 -> 防晒、帽子、背包、速干、轻量商品。

`system_debug.购物车商品侧个性化` 会显示：

- 是否启用；
- 参考购物车商品；
- 商品标签；
- 价格画像；
- 命中的本地规则；
- 是否调用 Doubao 做购物车画像；
- 排序影响。

### 2.9 商品增强字段

商品库新增并已被系统真实使用：

- `product_highlight`
- `highlight_short`
- `highlight_detail`
- `suitable_scenarios`
- `target_user_tags`
- `non_standard_query_tags`

这些字段参与：

- query enhancement；
- 商品召回和重排；
- 非标准问题匹配，例如“皮肤干”“送朋友”“通勤用”“健身入门”；
- 推荐理由生成；
- 商品比较维度；
- 商品详情问答。

`system_debug.商品增强字段使用` 会显示：

- 使用的增强字段；
- 命中的非标准问题标签；
- 命中的适用场景；
- 命中的人群标签；
- 排序影响。

### 2.10 多模态扩展

当前已支持图片 + 文本输入的无 GPU fallback 流程。

特点：

- 能跑通上传图片、图文融合查询、库存覆盖判断；
- 无 GPU 时通过文本、文件名和 mock 视觉结果测试端到端流程；
- 真实视觉模型和图文向量索引已预留扩展入口；
- 库存不覆盖时不编造商品。

## 3. 快速自动化测试命令

### 3.1 全量回归

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
python3 -m compileall app
USE_MOCK_LLM=1 pytest -q
```

应该看到：

```text
49 passed
```

### 3.2 三类用户历史 + 购物车侧个性化

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
USE_MOCK_LLM=1 python3 scripts/agent_console.py --mode old_user --user_id sophia_digital --session_id sophia_digital_check "我想再配一个适合现在购物车的数码产品"
USE_MOCK_LLM=1 python3 scripts/agent_console.py --mode old_user --user_id alex_sports --session_id alex_sports_check "我想再配一个适合训练用的装备"
USE_MOCK_LLM=1 python3 scripts/agent_console.py --mode old_user --user_id victoria_beauty --session_id victoria_beauty_check "我想再加一件适合现在护肤步骤的产品"
```

应该看到三组用户：

1. `sophia_digital`
   - 历史购物车：iPhone + MacBook；
   - 命中规则：`phone_audio_ecosystem`、`apple_macbook_ecosystem`；
   - 推荐方向：iPad、AirPods 等 Apple 生态商品；
   - 增强字段命中：`适合记笔记的平板`、`平板电脑能办公吗`、`降噪效果好的蓝牙耳机`。

2. `alex_sports`
   - 历史购物车：Nike 速干训练服 + Decathlon 运动裤；
   - 命中规则：`training_apparel_to_shoes`；
   - 推荐方向：跑步鞋、运动帽；
   - 明确问“运动帽”时，推荐商品必须是帽子，不能被历史拉回跑鞋。

3. `victoria_beauty`
   - 历史购物车：兰蔻精华 + SK-II 化妆水；
   - 命中规则：`premium_skincare_routine`；
   - 推荐方向：面霜、修护保湿、高端护肤链路；
   - 详情问答可围绕成分、适用场景、肤感解释。

脚本会打印：

- 用户输入；
- 加载到的历史摘要；
- 购物车商品共性分析；
- 命中的本地搭配/兼容规则；
- 是否调用 Doubao 做购物车画像；
- 商品增强字段命中；
- 推荐结果；
- system_debug 中的个性化过程和耗时。

## 4. 复杂 IntentPlan 测试

### 4.1 加购、删除、重新推荐同句执行

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session advanced_combo_case \
  "推荐防晒霜" \
  "把第二款加入购物车" \
  "帮我把你推荐的第一个防晒乳加到购物车，把购物车中其他的防晒乳全部删掉，再给我推荐一个200块左右的背包，也是旅游使用的"
```

应该看到：

- 第 1 轮推荐真实防晒商品；
- 第 2 轮执行 `add_to_cart`；
- 第 3 轮 `system_debug.Doubao意图计划` 包含：
  - `cart_add`
  - `cart_remove`
  - `refine`
- 工具先执行，再进入背包检索；
- 新推荐目标为 `服饰运动/背包`；
- 当前库没有 200 元左右背包时，只返回真实相近备选，不编造低价背包。

### 4.2 模糊表达中的删除 + 加购

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session advanced_fuzzy_cart_case \
  "推荐低糖饮料" \
  "把第一款加入购物车" \
  "再推荐几款饮料" \
  "我不喜欢刚才加到购物车的那个饮料了，你帮我把现在推荐的第二个往购物车加6瓶吧"
```

应该看到：

- “不喜欢刚才加到购物车的那个饮料了”被理解为删除购物车中对应饮料；
- “第二个往购物车加6瓶”被解析为对当前推荐列表第二个商品执行加购，数量为 6；
- `system_debug.Doubao意图计划.steps` 至少包含 `cart_remove` 和 `cart_add`；
- 购物车结果来自后端工具，不是 Doubao 口头生成。

## 5. 商品增强字段测试

### 5.1 非标准问题：皮肤干、屏障修护、不黏腻

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session enhancement_skin_case \
  "我皮肤最近有点干，但不想黏腻，哪款更适合做屏障修护？"
```

应该看到：

- 类目聚焦在 `美妆护肤/面霜` 或修护保湿相关护肤品；
- `system_debug.商品增强字段使用.命中的非标准问题标签` 包含干燥、补水、修护或不油腻相关标签；
- 推荐理由是完整自然句，不只写“保湿”“修护”这类碎片词；
- 回复不应以“抱歉，没有找到”开头。

### 5.2 平板非标准问题

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session enhancement_ipad_case \
  "想买个适合记笔记、追剧也舒服的平板"
```

应该看到：

- 类目为 `数码电子/平板电脑`；
- 推荐真实 iPad / 平板商品；
- 增强字段命中 `适合记笔记的平板`、`追剧看视频用什么平板` 等标签。

### 5.3 商品详情：成分和适用场景

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session detail_enhancement_case \
  "推荐一款修护保湿面霜" \
  "第一款从成分和适用场景上给我介绍下"
```

应该看到：

- 第二轮通过事件记忆把“第一款”解析到上一轮推荐商品；
- 商品详情回复基于数据库字段和增强字段；
- 不编造成分、优惠、库存；
- 可解释 2-3 个维度，例如成分/功效、适用场景、肤感或注意点。

## 6. Progress Events 与耗时统计测试

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session progress_timing_case \
  "推荐10000元以内，拍照好的手机"
```

应该看到：

- SSE 事件中较早出现 `progress`；
- 最终 `turn_result.system_debug.进度事件` 包含预测工作类型和模板；
- `turn_result.system_debug.运行耗时统计` 包含：
  - `total_duration_ms`
  - 模块耗时列表；
  - 模型调用次数；
  - `Top耗时模块`。

测试意义：

- 前端可以先展示“正在查找目标商品”等状态；
- 后端可以定位耗时主要在 RAG、模型调用还是历史保存。

## 7. 隐私个性化测试

### 7.1 关闭个性化

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session privacy_off_demo \
  "关闭个性化推荐，不要根据历史推荐" \
  "推荐一款清爽一点的防晒霜"
```

应该看到：

- `system_debug.隐私保护.个性化模式=off`；
- 个性化分析不使用历史证据；
- 仍能按本轮需求推荐真实防晒商品。

### 7.2 只使用语义摘要

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session privacy_semantic_demo \
  "我一直比较喜欢清爽、性价比高的护肤品，记住一下" \
  "开启隐私个性化，只用语义摘要，不要用原文历史" \
  "再推荐一款清爽防晒"
```

应该看到：

- `system_debug.隐私保护.个性化模式=semantic`；
- 不使用历史原文做 few-shot；
- 可以使用语义摘要、结构化偏好和记忆卡片影响排序与回复。

### 7.3 不保存原始聊天

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session privacy_no_raw_demo \
  "不要保存聊天，开启隐私个性化，然后推荐一款性价比高的饮料"
```

如果服务正在运行，可检查历史：

```bash
curl "http://127.0.0.1:8000/api/session/privacy_no_raw_demo/history?user_id=privacy_no_raw_demo" | python3 -m json.tool
```

应该看到：

- `store_raw_history=false`；
- 原始用户输入和系统回复被隐私占位；
- 语义记忆仍可保留结构化类目、偏好和推荐商品。

## 8. 多模态测试

### 8.1 无 GPU fallback：背包

```bash
touch /tmp/commute_backpack.jpg
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session_id doc_mm_backpack \
  --user_id doc_mm_user \
  --image_path /tmp/commute_backpack.jpg \
  "有没有类似这种款式，但价格低一点的背包"
```

应该看到：

- `system_debug.多模态分析.是否启用多模态=true`；
- 图片输入被接收；
- 库存覆盖目标类目；
- 推荐真实背包商品，例如 `p_clothes_018` 或 `p_clothes_025`；
- 无 GPU fallback 不承诺真实看懂图片像素。

### 8.2 库存不覆盖：毛绒玩偶

```bash
touch /tmp/large_plush_toy.jpg
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session_id doc_mm_toy \
  --user_id doc_mm_user \
  --image_path /tmp/large_plush_toy.jpg \
  "找同款毛绒玩偶，要大号版本"
```

应该看到：

- 系统说明当前库没有毛绒玩偶；
- 不返回编造商品卡片；
- `库存匹配判断.库存是否覆盖目标类目=false`。

## 9. 前端动作测试

### 9.1 普通推荐不跳转

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session frontend_action_case \
  "推荐一款拍照好的手机"
```

应该看到：

- `frontend_events` 包含 `show_reply` 和 `show_products`；
- 不应出现 `navigate`。

### 9.2 明确查看详情才跳转详情

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session frontend_detail_case \
  "推荐一款拍照好的手机" \
  "查看第一款详情"
```

应该看到：

- 第二轮包含 `show_product_detail`；
- 如果动作规划判断需要切页，`navigate.target_page=product_detail_page`；
- 商品详情来自上一轮推荐事件记忆。

### 9.3 明确查看购物车才跳转购物车

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session frontend_cart_case \
  "推荐一款低糖饮料" \
  "把第一款加入购物车" \
  "查看购物车"
```

应该看到：

- 加购轮只更新购物车，不强制跳转；
- “查看购物车”轮才出现购物车页面动作。

## 10. 真实 Doubao 测试建议

离线命令用于快速回归；正式 Demo 前建议使用真实 Doubao：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --user_id real_doubao_user \
  --session_id real_doubao_session \
  --new_session
```

逐轮输入：

```text
推荐10000元以内，拍照好的手机
我觉得第二个不错，给我介绍下
第一款呢，给我介绍下
帮我把第二款加入购物车，然后再推荐一个能和它配套的降噪耳机
```

应该观察：

- Doubao 负责复杂理解和自然回复；
- 商品详情基于数据库和增强字段；
- “第一款/第二个”通过事件记忆解析；
- 配套耳机受购物车商品侧个性化影响；
- 用户可见回复不出现内部工程词。

## 11. 当前测试结论

当前版本可稳定展示这些核心竞争力：

- Doubao-first IntentPlan 处理复杂多动作需求；
- 事件记忆保障“第一款/第二个/刚才那个”的稳定指代；
- RAG + response validation 保证商品事实 grounded；
- 积极导购回复策略减少消极、冗长和自相矛盾表达；
- progress events 和运行耗时统计改善前端等待体验与后端性能定位；
- 隐私个性化支持 full / semantic / off；
- 购物车侧个性化把用户当前已选商品转化为搭配与排序信号；
- 商品增强字段能处理非标准问题、推荐理由、比较维度和详情问答；
- 多模态流程在无 GPU 下可跑通，在真实视觉模型接入后可升级为图文检索。
