# 本地后端测试指南

本文档给测试同学使用，从 VSCode 打开项目开始，说明如何准备环境、配置变量、启动后端、做健康检查、使用统一脚本运行固定消息和多轮测试、恢复历史，并解释每一轮输出应该怎么看。本文只描述当前最新版本，不包含旧版长 JSON 默认输出方式。

## 1. 打开项目和终端

1. 打开 VSCode。
2. 选择 `File -> Open Folder...`。
3. 打开：

```text
/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main
```

4. 打开终端：

```text
Terminal -> New Terminal
```

5. 进入后端目录：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
```

## 2. 安装依赖

第一次运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

以后每次测试只需要：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
```

## 3. 配置环境变量

项目根目录已有 `.env.example`。建议复制一份 `.env`：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main"
cp .env.example .env
```

打开 `.env`，建议正式测试使用：

```env
PRODUCT_DATASET_DIR=/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/ecommerce_agent_dataset

USE_MOCK_LLM=0
DOUBAO_API_KEY=填入自己的Doubao API Key
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/
DOUBAO_MODEL=ep-20260514111645-lmgt2

ENABLE_LOCAL_MODELS=true
LOCAL_MODEL_DEVICE=cpu
BGE_EMBEDDING_MODEL_PATH=/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/models/bge-small-zh-v1.5
TEXT2VEC_MODEL_PATH=/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/models/text2vex-base-chinese
BGE_RERANKER_MODEL_PATH=/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/models/bge-reranker-base
```

说明：

- `USE_MOCK_LLM=0`：真实调用 Doubao，适合正式验收。
- `USE_MOCK_LLM=1`：不用真实 API，只跑离线流程，适合快速检查程序有没有崩。
- `ENABLE_LOCAL_MODELS=true`：加载本地 BGE、text2vec、reranker，适合正式验收。
- `ENABLE_LOCAL_MODELS=false`：跳过本地小模型，启动更快，适合离线单元测试。
- 不要把真实 API Key 发到群里或提交到仓库。

## 4. 健康检查和自动测试

进入后端目录：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
```

编译检查：

```bash
python3 -m compileall app scripts tests
```

离线单元测试：

```bash
USE_MOCK_LLM=1 pytest -q
```

预期：测试全部通过，例如看到类似：

```text
49 passed
```

说明：

- `USE_MOCK_LLM=1` 表示离线回归，不调用真实 Doubao；
- 正式验收时去掉 `USE_MOCK_LLM=1`，并确保 `.env` 中 Doubao 配置正确；
- 如果本地小模型路径可用，正式 Demo 建议使用 `ENABLE_LOCAL_MODELS=true`。

启动 FastAPI 服务：

```bash
uvicorn app.main:app --reload --port 8000
```

不要关闭这个终端。再打开一个新的 VSCode 终端，执行：

```bash
curl http://127.0.0.1:8000/health
```

预期：

```json
{"status":"ok"}
```

商品接口检查：

```bash
curl "http://127.0.0.1:8000/api/products?limit=3" | python3 -m json.tool
```

如果 URL 里有中文，建议先用浏览器或 Postman 测试；终端中文 URL 可能需要编码。

## 5. 统一脚本固定消息测试

少量固定句子可以用统一脚本直接传参；它仍然会按多轮会话机制执行，只是不用手动逐轮输入：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate

USE_MOCK_LLM=0 ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --session single_turn_demo \
  "推荐一款适合油皮的洗面奶"
```

这个脚本会输出：

- `frontend_events / 前端动作列表`：前端按顺序执行的动作；
- `frontend_data / 前端动作数据`：回复文本、商品卡片、购物车或跳转数据；
- `system_debug / 系统调试摘要`：意图、检索、工具、模型、耗时、个性化等摘要；
- 使用 `--memory` 或交互脚本的 `/debug` 时，可查看更完整的 memory、state 和 trace。

适合快速确认某个单句能不能跑通。

## 6. 多轮交互测试

真实测试推荐使用交互脚本，一轮一轮输入用户 query：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate

USE_MOCK_LLM=0 ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --user_id local_test_user \
  --session_id local_test_session \
  --new_session
```

看到：

```text
USER>
```

再逐轮输入，例如：

```text
推荐一款性价比高的手机
```

等系统回复后再输入：

```text
我想要拍照好一点，价格 4000 以内
```

再输入：

```text
把第一款加入购物车
```

再输入：

```text
查看购物车
```

再输入：

```text
下单吧，地址用默认的
```

## 7. 每轮输出怎么看

交互脚本每轮默认展示三块内容。

### 7.1 `frontend_events / 前端动作列表`

这是前端应该按顺序执行的动作。例如：

```text
1. show_reply -> reply_message
2. show_products -> recommended_products
```

含义：

- 先展示回复文本；
- 再展示商品卡片。

普通推荐和普通加购不会自动跳转页面。只有用户明确说“查看购物车”“查看第一款详情”“下单/付款”时，才会出现 `navigate`。

### 7.2 `frontend_data / 前端动作数据`

这是前端动作需要使用的数据，常见字段：

| 字段 | 用途 |
| --- | --- |
| `reply_message` | 展示给用户看的回复文本 |
| `recommended_products` | 推荐商品卡片 |
| `alternative_products` | 没有完全匹配时的相近真实商品 |
| `product_detail` | 商品详情或商品问答 |
| `cart_state` | 购物车工具执行结果 |
| `navigation` | 页面跳转目标和参数 |
| `clarification_options` | 澄清问题和快捷选项 |

### 7.3 `system_debug / 系统调试摘要`

这是给后端和测试同学看的，普通用户不会看到。默认摘要包括：

- 本轮理解：意图、流程、类目、价格、正向偏好、否定约束；
- 意图计划：Doubao 解析出的 IntentPlan；
- 状态结果：当前流程、当前类别、购物车数量、最近推荐商品；
- 检索摘要：检索方式、召回数量、最终推荐商品 ID、Top 评分；
- 工具与模型：是否调用 Doubao、是否执行购物车工具、本地小模型任务；
- 前端动作：是否跳页、跳到哪里、来源。

## 8. 交互脚本斜杠命令

在 `USER>` 后输入这些命令，可以查看不同中间状态：

```text
/state    当前状态摘要：流程、意图、类目、约束、购物车数量
/memory   短期记忆摘要：最近消息、最近推荐、购物车简况
/trace    最近执行链路：理解结果、检索、工具、模型和前端动作
/profile  长期画像摘要
/debug    最近一轮完整 turn_result + 完整 state/memory/trace/profile
/all      同 /debug
/help     查看命令说明
/end      强制生成/刷新用户画像并退出
/quit     退出，不强制刷新画像
```

建议：

- 日常测试看默认摘要即可；
- 发现意图识别不对，输入 `/trace`；
- 发现状态继承或购物车异常，输入 `/state` 和 `/memory`；
- 需要完整 JSON，再输入 `/debug`；
- 一个测试用户结束后输入 `/end`，让系统刷新用户画像。

## 9. Progress、耗时和高级调试

当前每轮 `system_debug` 都会包含更细的工程调试信息：

| 字段 | 作用 |
| --- | --- |
| `进度事件` | 前端可展示的“正在理解需求/正在检索/正在组织回复”等处理进度 |
| `运行耗时统计` | 本轮总耗时、模块耗时、模型调用次数、Top 耗时模块 |
| `购物车商品侧个性化` | 购物车商品共性、价格画像、命中搭配规则、排序影响 |
| `商品增强字段使用` | 本轮使用了哪些商品增强字段，命中了哪些非标准问题标签 |
| `Doubao意图计划` | 复杂用户表达被拆解成的动作序列 |

快速查看耗时和进度：

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py \
  --session progress_timing_demo \
  "推荐10000元以内，拍照好的手机"
```

重点看：

- `system_debug.进度事件`
- `system_debug.运行耗时统计`
- `Top耗时模块`

## 10. 三类用户历史与购物车侧个性化测试

系统内置了三个用户历史样例：

- `sophia_digital`：数码小白女生，购物车里有 iPhone 和 MacBook；
- `alex_sports`：健身达人男生，购物车里有训练/速干服饰；
- `victoria_beauty`：美妆专家女士，购物车里有高端精华和化妆水。

运行专项脚本：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
USE_MOCK_LLM=1 python3 scripts/agent_console.py --mode old_user --user_id sophia_digital --session_id sophia_digital_check "我想再配一个适合现在购物车的数码产品"
USE_MOCK_LLM=1 python3 scripts/agent_console.py --mode old_user --user_id alex_sports --session_id alex_sports_check "我想再配一个适合训练用的装备"
USE_MOCK_LLM=1 python3 scripts/agent_console.py --mode old_user --user_id victoria_beauty --session_id victoria_beauty_check "我想再加一件适合现在护肤步骤的产品"
```

统一脚本会打印：

- 历史格式检查；
- 加载到的历史摘要；
- 购物车商品共性分析；
- 命中的本地搭配/兼容规则；
- 是否调用 Doubao 做购物车画像；
- 商品增强字段命中；
- 推荐结果；
- 模型与耗时摘要。

预期效果：

- `sophia_digital` 会优先推荐 iPad / AirPods 等 Apple 生态商品；
- `alex_sports` 会优先推荐跑步鞋、运动帽等训练搭配商品；
- `victoria_beauty` 会优先推荐面霜、修护保湿、高端护肤链路商品。

## 11. 历史保存和恢复

每轮多轮脚本都会把历史保存到：

```text
storage/user_history/{user_id}
```

先创建历史：

```bash
USE_MOCK_LLM=0 ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --user_id resume_test_user \
  --session_id resume_seed_session \
  --new_session
```

逐轮输入：

```text
我一直比较喜欢清爽、性价比高的商品，记住一下
```

```text
帮我看看拍照好的手机，预算 5000 以内
```

```text
/end
```

恢复历史：

```bash
USE_MOCK_LLM=0 ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --user_id resume_test_user \
  --session_id resume_new_session \
  --resume
```

输入：

```text
那继续帮我看看上次那个方向
```

观察：

- `/state` 能看到恢复后的当前主题或候选商品；
- `/profile` 能看到长期画像摘要；
- 回复可以参考画像，但不会对用户说“根据你的长期记忆”。

## 12. 个性化测试

可以用内置多轮场景快速观察个性化 evidence 和 few-shot：

```bash
USE_MOCK_LLM=0 ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --user_id personalization_demo_user \
  --session_id personalization_demo_session \
  --new_session \
  --scenario personalization_flow
```

观察默认 `system_debug` 摘要中的：

```text
个性化 -> 启用
个性化 -> 策略
个性化 -> 历史证据数
个性化 -> few-shot数
```

需要看完整证据时输入：

```text
/debug
```

## 13. 多模态图片 + 文本测试

准备一张本地图片，例如：

```text
/Users/grsxsa/Desktop/backpack.jpg
```

运行：

```bash
USE_MOCK_LLM=0 ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --user_id multimodal_demo_user \
  --session_id multimodal_demo_session \
  --image_path "/Users/grsxsa/Desktop/backpack.jpg" \
  "有没有类似这种款式，但价格低一点的背包"
```

预期：

- 输出 `frontend_events`；
- 输出回复文本；
- 如果库存有对应类目，输出商品卡片；
- 输出 `multimodal_debug`，其中包含图片理解结果、图文融合查询和库存匹配判断。

如果没有真实视觉模型，系统会使用保守降级策略，根据文本和图片文件名推断视觉目标，保证 Demo 不崩。正式效果建议配置支持图片理解的 VLM。

### 11.1 无 GPU 本地方案

无 GPU 或只想在 MacBook CPU 上稳定跑 Demo 时：

```bash
USE_MOCK_LLM=1 ENABLE_LOCAL_MODELS=false python3 scripts/agent_console.py \
  --user_id multimodal_cpu_user \
  --session_id multimodal_cpu_bag \
  --image_path "/tmp/commute_backpack.jpg" \
  "有没有类似这种款式，但价格低一点的背包"
```

说明：

- 这会走保守 fallback：文件名和文字中有 `backpack/背包` 时识别为背包；
- 适合测试前端事件、图文融合、库存不覆盖兜底；
- 不代表真实视觉识别效果。

### 11.2 需要 GPU 或云端 VLM 的方案

如果后续要真正识别街拍、鞋子特写、玩偶照片，建议：

```env
USE_MOCK_LLM=0
ENABLE_MULTIMODAL=true
VISION_MODEL=支持图片输入的视觉模型或云端VLM
```

然后继续使用同一个脚本：

```bash
USE_MOCK_LLM=0 ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --user_id multimodal_vlm_user \
  --session_id multimodal_vlm_bag \
  --image_path "/Users/grsxsa/Desktop/backpack.jpg" \
  "有没有类似这种款式，但价格低一点的背包"
```

GPU/VLM 方案应增加：目标检测或裁剪、视觉 embedding、商品图片向量索引和图文融合重排。

库存不覆盖测试：

```bash
USE_MOCK_LLM=0 ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --user_id multimodal_demo_user \
  --session_id multimodal_toy_session \
  --image_path "/Users/grsxsa/Desktop/toy.jpg" \
  "找同款毛绒玩偶，要大号版本"
```

预期：系统说明当前库没有毛绒玩偶，不会编造商品。

## 14. 页面跳转测试

启动多轮脚本后逐轮输入：

```text
推荐一款性价比高的手机
```

预期：

- 有 `show_reply`、`show_products`；
- 没有 `navigate`。

```text
把第一款加入购物车
```

预期：

- 有 `update_cart`；
- 没有 `navigate`。

```text
查看购物车
```

预期：

- 有 `update_cart`；
- 有 `navigate -> cart_page`。

```text
查看第一款商品详情
```

预期：

- 有 `show_product_detail`；
- 有 `navigate -> product_detail_page`。

```text
下单吧，地址用默认的
```

预期：

- 有 `update_cart`；
- 有 `navigate -> checkout_page`。

## 15. 常见问题

### 13.1 `python3 -m json.tool` 报 `Expecting value`

通常是接口返回不是 JSON，或者 URL 中有中文但没有正确编码。先测试：

```bash
curl -v "http://127.0.0.1:8000/api/products?limit=3"
```

### 13.2 第一次加载小模型很慢

Mac CPU 第一次加载 BGE/text2vec/reranker 慢是正常现象。只想快速跑流程可以临时：

```bash
USE_MOCK_LLM=1 ENABLE_LOCAL_MODELS=false python3 scripts/agent_console.py \
  --user_id quick_user \
  --session_id quick_session \
  --new_session
```

### 13.3 如何确认是否真实调用 Doubao

看默认输出：

```text
工具与模型 -> 模型调用 -> 真实Doubao
```

或者输入：

```text
/trace
```

### 13.4 为什么有时显示相近备选

如果真实库存没有完全符合要求的商品，系统不会编造商品，会返回 `alternative_products`。例如“200元左右的背包”当前库存没有完全合适的低价背包，只能展示真实库存中的相近背包并说明不完全贴合。

## 16. 隐私和个性化测试

### 14.1 关闭个性化

```bash
USE_MOCK_LLM=1 ENABLE_LOCAL_MODELS=false python3 scripts/agent_console.py \
  --session privacy_off_demo \
  "关闭个性化推荐，不要根据历史推荐" \
  "推荐一款清爽一点的防晒霜"
```

预期：

- `system_debug.隐私保护.个性化模式=off`；
- `system_debug.个性化分析.是否启用个性化=false`；
- 回复仍然可以推荐商品，但不使用历史偏好。

### 14.2 隐私个性化，只用语义摘要

```bash
USE_MOCK_LLM=1 ENABLE_LOCAL_MODELS=false python3 scripts/agent_console.py \
  --session privacy_semantic_demo \
  "我一直比较喜欢清爽、性价比高的护肤品，记住一下" \
  "推荐一款适合夏天通勤的防晒霜" \
  "开启隐私个性化，只用语义摘要，不要用原文历史" \
  "再推荐一款清爽防晒"
```

预期：

- `隐私保护.个性化模式=semantic`；
- `是否允许使用历史原文做个性化=false`；
- `few-shot数=0`，但仍有结构化语义证据；
- `profile.json.semantic_memory` 和 `memory_cards` 会继续更新。

### 14.3 不保存原始聊天

```bash
USE_MOCK_LLM=1 ENABLE_LOCAL_MODELS=false python3 scripts/agent_console.py \
  --session privacy_no_raw_demo \
  "不要保存聊天，开启隐私个性化，然后推荐一款性价比高的饮料"
```

检查历史：

```bash
curl "http://127.0.0.1:8000/api/session/privacy_no_raw_demo/history?user_id=privacy_no_raw_demo" | python3 -m json.tool
```

预期 session history 中本轮 `user_input` 和 `assistant_reply` 被替换成隐私占位文本，但语义记忆、推荐商品和购物车摘要仍然保留。
