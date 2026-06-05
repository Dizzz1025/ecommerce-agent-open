# 统一后端 Agent 控制台测试指南

本文档是当前后端测试的主入口，面向测试同学和前端同学。现在 `backend/scripts` 只保留一个主脚本：`scripts/agent_console.py`。它支持两种模式：`old_user` 从本地历史恢复老用户，`new_user` 从零开始测试新用户。所有测试都按多轮对话进行。

## 1. 启动准备

1. 用 VSCode 打开项目根目录：

```bash
/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main
```

2. 打开 VSCode 终端，进入后端目录：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
```

3. 激活 Python 环境：

```bash
source .venv/bin/activate
```

4. 建议先用 Mock 模式跑通流程，速度快且不消耗 Doubao：

```bash
export USE_MOCK_LLM=true
export ENABLE_LOCAL_MODELS=false
```

5. 要测试真实 Doubao 和本地小模型时，再切换：

```bash
export USE_MOCK_LLM=false
export ENABLE_LOCAL_MODELS=true
```

## 2. 启动 FastAPI 服务

如果只用 `scripts/agent_console.py` 测试，可以不启动 FastAPI 服务；脚本会通过 FastAPI `TestClient` 在进程内调用后端。  
如果要给前端联调、用 curl/Postman 测试 SSE，必须启动服务。

### 2.1 启动服务

在 VSCode 终端 1 中执行：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate

export USE_MOCK_LLM=false
export ENABLE_LOCAL_MODELS=true
export ENABLE_MULTIMODAL=true

python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

如果只是快速本地验证，可以用 Mock：

```bash
export USE_MOCK_LLM=true
export ENABLE_LOCAL_MODELS=false
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

看到类似下面内容说明服务已启动：

```text
Uvicorn running on http://127.0.0.1:8000
```

### 2.2 健康检查

在 VSCode 终端 2 中执行：

```bash
curl http://127.0.0.1:8000/health
```

预期输出：

```json
{"status":"ok"}
```

### 2.3 商品库检查

```bash
curl "http://127.0.0.1:8000/api/products?category=数码电子&limit=3" | python3 -m json.tool
```

如果终端因为中文 URL 编码出现问题，可以改用：

```bash
python3 - <<'PY'
import requests
r = requests.get("http://127.0.0.1:8000/api/products", params={"category": "数码电子", "limit": 3})
print(r.text)
PY
```

### 2.4 SSE 流式对话测试

重点观察：`event: progress` 应该先出现，然后才是 `state`、`token`、`product_cards`、`frontend_action`、`turn_result`、`done`。

```bash
curl -N http://127.0.0.1:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "beauty_lily",
    "session_id": "api_stream_check",
    "message": "我还想再加一瓶适合现在护肤步骤的面霜，你有什么推荐？",
    "input_type": "text",
    "resume": true,
    "metadata": {}
  }'
```

`-N` 很重要，它会关闭 curl 缓冲，让你看到真正的 SSE 流式输出。正常情况下，前几行应很快出现：

```text
event: progress
data: {"text": "...正在..."}
```

如果 `progress` 和 `turn_result` 一起出现，说明前端或测试工具在缓冲；请先确认用了 `curl -N`，前端 fetch 端也要按流读取 response body。

如果测试同学想更清楚地看到“首条 progress 是第几毫秒到达的”，可以在 FastAPI 服务启动后运行：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
python scripts/http_stream_observer.py \
  --base_url http://127.0.0.1:8000 \
  --user_id stream_user \
  --session_id stream_observer_demo \
  --message "推荐10000元以内，拍照好的手机"
```

这个脚本走真实 HTTP，不使用 FastAPI TestClient，因此更接近前端 `curl -N` 或 Android 流式读取的效果。

### 2.5 调试接口

服务启动后，可以查看某个 session 的状态：

```bash
curl "http://127.0.0.1:8000/api/session/api_stream_check/state" | python3 -m json.tool
curl "http://127.0.0.1:8000/api/session/api_stream_check/memory" | python3 -m json.tool
curl "http://127.0.0.1:8000/api/session/api_stream_check/trace" | python3 -m json.tool
```

## 3. 唯一测试脚本

### 3.1 老用户模式

老用户模式会在第一轮尝试从 `storage/user_history/{user_id}` 加载历史对话、长期画像和购物车。

```bash
python scripts/agent_console.py --mode old_user --user_id beauty_lily --session_id beauty_lily_console
```

如果要指定恢复某个历史 session，只传 `--resume_session_id` 即可；后端会自动触发恢复，不需要测试同学额外记住 `resume=true`：

```bash
python scripts/agent_console.py \
  --mode old_user \
  --user_id sophia_digital \
  --session_id sophia_resume_auto_demo \
  --resume_session_id sophia_digital_01
```

### 3.2 新用户模式

新用户模式第一轮强制新会话。前三轮主要积累历史，从第四轮开始允许触发用户侧个性化；购物车中有同类商品后，才允许触发购物车商品侧个性化。

```bash
python scripts/agent_console.py --mode new_user --user_id new_demo_001 --session_id new_demo_001_session
```

### 3.3 常用斜杠命令

在脚本启动后的 `USER>` 后输入：

```text
/state    查看当前状态摘要：流程、意图、商品主题、约束、购物车数量。
/memory   查看短期记忆摘要：最近对话、最近推荐商品、购物车简况。
/trace    查看最近一轮执行链路：意图计划、检索、工具、模型、耗时。
/profile  查看长期画像摘要：历史摘要、结构化偏好、隐私设置。
/debug    展示最近一轮完整 JSON。
/end      强制生成或刷新用户画像并退出。
/quit     退出。
```

## 4. 每轮输出怎么看

每轮都会先快速打印：

```text
--- progress_events / 前端流式进度
```

这表示前端可以马上展示“正在理解需求、正在检索商品、正在组织回复”等状态。目标是在输入 query 后约 0.5 秒内出现。

正式结果分三段：

```text
--- frontend_events / 前端动作列表
--- frontend_data / 前端动作数据
--- system_debug / 系统调试摘要
```

前端主要看 `frontend_events` 和 `frontend_data`。后端和测试主要看 `system_debug`，尤其是：

- `意图计划`：Doubao 识别出的动作序列。
- `进度事件`：progress 是否启用、是否并行启动、首条输出耗时、输出条数和停止原因。
- `运行耗时`：总耗时、模型调用次数、Top 耗时模块。
- `个性化`：是否启用用户侧个性化。
- `购物车商品侧个性化`：是否只参考了同类购物车商品。
- `商品增强字段`：是否命中亮点、场景、人群、非标准标签。

## 5. 推荐从老用户开始的测试

### 5.1 测试快速 progress + 老用户历史加载

启动：

```bash
python scripts/agent_console.py --mode old_user --user_id beauty_lily --session_id beauty_lily_console
```

输入：

```text
我还想再加一瓶适合现在护肤步骤的面霜，你有什么推荐？
```

应该看到：

- 很快出现 `progress_events`，例如“正在结合你的历史偏好和购物车记录筛选商品”。
- `system_debug -> 个性化` 显示启用老用户画像。
- `system_debug -> 购物车商品侧个性化` 只参考美妆护肤类购物车商品。
- 推荐商品必须来自商品库，不能出现不存在的商品。

### 5.2 测试购物车只看同类商品

继续输入：

```text
那我再看看拍照好的手机，预算5000以内。
```

应该看到：

- 如果购物车里只有护肤品，`购物车商品侧个性化` 应显示未启用或忽略非同类商品。
- 系统不能因为护肤购物车而影响手机推荐。
- 推荐结果应是数码电子/智能手机，不应混入美妆商品。

### 5.3 测试多意图序列识别

继续输入：

```text
把第一款加入购物车，把购物车里其他同类面霜删掉，再推荐一款更适合晚上修护用的精华。
```

应该看到：

- `意图计划` 中包含多个按顺序执行的动作，例如加购、删除同类商品、重新推荐。
- `工具执行` 中有购物车工具调用。
- 最终仍应给出新的真实商品推荐。
- 正常轮次 Doubao 调用应尽量不超过 2 次。

## 6. 新用户三层记忆测试

启动新用户：

```bash
python scripts/agent_console.py --mode new_user --user_id new_memory_demo --session_id new_memory_demo_session
```

依次输入四轮：

```text
我想买一款适合通勤的背包。
```

```text
我喜欢轻一点的，颜色不要太花。
```

```text
预算最好控制在1200以内。
```

```text
那结合我刚刚说的，帮我选最适合的一款。
```

应该看到：

- 前三轮主要积累短期记忆和状态。
- 第四轮开始，`system_debug -> 个性化 -> 新用户冷启动` 应显示已经有足够近期证据。
- 系统能继承“背包、通勤、轻、不要花、1200以内”等约束。

## 7. 库存 grounded 回复测试

输入：

```text
我想买一个不存在品牌的超便宜折叠屏手机，1000元以内。
```

应该看到：

- 系统不能编造不存在商品。
- 如果没有完全匹配，应主动说“我先为你挑了几款更接近需求的选择”，并给真实备选。
- `商品卡片` 中的商品 ID、价格、名称必须来自商品库。

## 8. 隐私个性化测试

启动：

```bash
python scripts/agent_console.py --mode old_user --user_id beauty_lily --session_id privacy_lily --privacy_mode semantic
```

输入：

```text
我比较注重隐私，后面推荐时可以用偏好向量，但不要直接使用我的历史原文。
```

再输入：

```text
推荐一款适合换季修护的护肤品。
```

应该看到：

- `profile` 或 `system_debug` 中体现隐私模式。
- 个性化可以生效，但不应在回复中暴露历史原文。
- 商品推荐仍以当前需求为硬约束。

## 9. 商品增强字段测试

输入：

```text
我皮肤干但不想黏腻，想要一款适合换季的修护产品。
```

应该看到：

- `商品增强字段` 中命中适用场景、人群标签或非标准问题标签。
- 推荐理由是一句自然完整的话，不只是“保湿”“修护”这种短标签。

## 10. 多模态应对测试

无 GPU 的本地方案会优先使用 Doubao 图像理解；如果视觉模型不可用，则使用本地测试图 fixture、商品图相似度和用户文字做库存匹配兜底，不会编造商品：

```bash
python scripts/agent_console.py --mode new_user --user_id multimodal_demo --session_id multimodal_demo \
  --input_type image_text \
  --image_path "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/storage/test_pic/化妆品照片.jpg"
```

在 `USER>` 输入：

```text
帮我看看图片里的化妆品，找到最相近的护肤品。
```

应该看到：

- `多模态` 显示已启用。
- `system_debug -> 多模态分析 -> 视觉匹配商品 -> best_match.sku_id` 为 `p_beauty_001`。
- 推荐商品第一名是雅诗兰黛特润修护肌活精华露，即小棕瓶。
- 商品必须来自真实商品库。

如果后续使用 GPU 或视觉大模型，可以把 `USE_MOCK_LLM=false` 并使用支持图片的 Doubao/VLM 配置，系统会通过同一脚本透传 `image_path/image_url/image_base64`。

### 10.1 三张本地测试图的真实 Doubao 测试命令

测试前建议切换到真实 Doubao：

```bash
export USE_MOCK_LLM=false
export ENABLE_LOCAL_MODELS=true
export ENABLE_MULTIMODAL=true
```

化妆品照片：

```bash
python scripts/agent_console.py --mode new_user --user_id mm_cosmetic_user --session_id mm_cosmetic_session \
  --input_type image_text \
  --image_path "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/storage/test_pic/化妆品照片.jpg"
```

在 `USER>` 输入：

```text
帮我看看图里的化妆品大概是什么类型，商品库里有没有同类或者相近的护肤品可以推荐。
```

应该看到：`多模态分析 -> 视觉匹配商品 -> best_match.sku_id = p_beauty_001`，图文融合后映射到 `美妆护肤 / 精华`，推荐真实库存中的雅诗兰黛小棕瓶或同类精华。

街拍全身照：

```bash
python scripts/agent_console.py --mode new_user --user_id mm_street_user --session_id mm_street_session \
  --input_type image_text \
  --image_path "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/storage/test_pic/街拍全身照.jpg"
```

在 `USER>` 输入：

```text
我想找图里这种街拍穿搭的同款或相似风格，优先推荐商品库里真实有的衣服、鞋子或背包。
```

应该看到：如果 Doubao 识别为连衣裙但库里没有裙装，系统应说明库存限制，并给真实的服饰运动相近商品；如果识别为上衣、鞋子或背包，则直接按对应库存推荐。

手机照片：

```bash
python scripts/agent_console.py --mode new_user --user_id mm_phone_user --session_id mm_phone_session \
  --input_type image_text \
  --image_path "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/storage/test_pic/手机照片.jpg"
```

在 `USER>` 输入：

```text
我想找图里这种手机，预算5000以内，拍照好一点，帮我推荐商品库里最接近的款。
```

应该看到：图文融合映射到 `数码电子/智能手机`，预算和拍照作为硬约束参与检索；商品卡片不能混入美妆或服饰商品。

## 11. 复杂问题测试

输入：

```text
下周去海边短途旅行，预算500以内，帮我配防晒、饮料和轻便穿搭，不要太甜的饮料，也不要日系防晒。
```

应该看到：

- `意图计划` 能识别场景化组合推荐和否定约束。
- 推荐商品应按商品库实际类目拆分，不能编造没有的泳衣、拖鞋等商品。
- 如果某个子类库存不足，应给真实相近备选，并用正向导购语气引导调整。

## 12. Doubao 调用次数观察

普通对话轮次的目标是 Doubao 调用不超过 2 次：

1. 意图识别与动作序列规划。
2. 基于 RAG 商品和个性化上下文生成回复。

请在每轮 `system_debug -> 运行耗时 -> 模型调用` 中观察调用次数和耗时。`/end` 强制画像刷新属于会话结束后的额外分析，不计入普通购物对话轮次。
