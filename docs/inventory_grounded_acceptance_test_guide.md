# 多轮库存对齐验收测试指南

本文档给测试和前端同学使用，用来验证当前后端在复杂多轮对话中的真实能力。所有案例都已经按 `ecommerce_agent_dataset` 中的真实商品改写；如果用户提到当前库存没有的商品，正确表现是如实说明暂无或推荐相近真实商品，绝不能编造库存外商品。

## 1. 测试前准备

打开 VSCode 终端：

```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
```

正式验收建议使用真实 Doubao 和本地小模型：

```bash
export USE_MOCK_LLM=0
export ENABLE_LOCAL_MODELS=true
```

如果只是检查程序能不能跑通，可以临时离线：

```bash
export USE_MOCK_LLM=1
export ENABLE_LOCAL_MODELS=false
```

建议测试前清理对应用户历史，避免旧记忆影响：

```bash
rm -rf ../storage/user_history/qa_child_drink
rm -rf ../storage/user_history/qa_working_woman
rm -rf ../storage/user_history/qa_exclusion
rm -rf ../storage/user_history/qa_scene
rm -rf ../storage/user_history/qa_cart_combo
rm -rf ../storage/user_history/qa_privacy_off
rm -rf ../storage/user_history/qa_privacy_semantic
rm -rf ../storage/user_history/qa_privacy_no_raw
```

## 2. 观察方法

启动脚本后，不要一次性输入全部 query。必须等系统每轮回复后，再根据结果输入下一轮。

每轮默认观察：

- `frontend_events`：前端要按顺序执行哪些动作；
- `frontend_data`：回复文本、商品卡片、购物车或跳转数据；
- `system_debug`：本轮理解、IntentPlan、检索摘要、工具和模型调用。
- `system_debug.进度事件`：前端等待态 progress 的预测和模板；
- `system_debug.运行耗时统计`：总耗时、模型调用、Top 耗时模块；
- `system_debug.购物车商品侧个性化`：购物车如何影响本轮推荐排序；
- `system_debug.商品增强字段使用`：增强字段和非标准问题标签是否命中。

常用斜杠命令：

```text
/state    看当前状态摘要
/memory   看短期记忆摘要
/trace    看最近一轮执行链路和 IntentPlan
/profile  看长期画像
/debug    看完整 JSON
/end      生成画像并退出
```

正式测试前建议先跑一次自动化回归：

```bash
USE_MOCK_LLM=1 pytest -q
```

当前预期：

```text
49 passed
```

### 2.1 三类历史用户专项验收

用于验证“加载历史 + 购物车侧个性化 + 商品增强字段”的组合能力：

```bash
USE_MOCK_LLM=1 python3 scripts/agent_console.py --mode old_user --user_id sophia_digital --session_id sophia_digital_check "我想再配一个适合现在购物车的数码产品"
USE_MOCK_LLM=1 python3 scripts/agent_console.py --mode old_user --user_id alex_sports --session_id alex_sports_check "我想再配一个适合训练用的装备"
USE_MOCK_LLM=1 python3 scripts/agent_console.py --mode old_user --user_id victoria_beauty --session_id victoria_beauty_check "我想再加一件适合现在护肤步骤的产品"
```

应该看到：

- `sophia_digital` 恢复 iPhone + MacBook 购物车，命中 Apple 生态规则，推荐 iPad / AirPods；
- `alex_sports` 恢复训练服和运动裤购物车，命中训练搭配规则，推荐跑鞋和运动帽；
- `victoria_beauty` 恢复高端护肤购物车，命中高端护肤链路规则，推荐面霜和修护保湿商品；
- 每组输出都会展示历史摘要、购物车共性分析、本地规则、是否调用 Doubao、商品增强字段命中和推荐结果。

## 3. 案例一：4 岁小朋友买饮料和零食

目标：

- 测试童真、较长、带碎碎念的表达；
- 测试系统能否从“妈妈说不能总吃糖”理解为“少糖/无糖/不太甜”；
- 测试根据儿童身份做温和、安全的个性化表达；
- 测试金额多轮修改；
- 测试饮料 -> 零食新需求切换；
- 测试加购、结束对话和跳转购物车。

启动：

```bash
python3 scripts/agent_console.py \
  --user_id qa_child_drink \
  --session_id qa_child_drink_01 \
  --new_session
```

逐轮输入。

### 第 1 轮：小朋友想要好喝饮料

```text
你好呀，我今年4岁啦，我有一点点小零花钱，想买一瓶喝起来好喝的饮料，最好是我出去玩的时候可以拿着喝的那种，你帮我挑一挑好不好呀？
```

预期：

- 系统识别为饮料推荐；
- 推荐必须来自 `食品饮料` 类目，例如无糖茶、0 糖气泡水、功能饮料等；
- 回复语气应该温柔、简单，适合小朋友理解；
- 不应推荐不存在的儿童饮料。

### 第 2 轮：模糊表达少糖需求

```text
可是妈妈说小朋友不能总吃糖，也不能老是喝甜甜的饮料，不然牙齿会不开心，肚子也会不舒服。
```

预期：

- 系统应理解为“少糖、无糖、不太甜”；
- 应重新推荐更贴近的饮料，例如东方树叶无糖茶、元气森林 0 糖气泡水；
- 不要只说“我记下了”，必须推进购买流程并展示商品。

### 第 3 轮：比较三款哪个更适合

```text
那你刚才说的这几个里面，哪个最好喝呀？我想要一个小朋友也比较容易接受的。
```

预期：

- 系统做商品对比；
- 必须基于刚才推荐的真实商品；
- 可以说明“如果更想要清爽甜感，0 糖气泡水更容易接受；如果更想少甜，东方树叶更合适”；
- 不要强行说功能饮料适合 4 岁小朋友。

### 第 4 轮：预算变为 4.6 元

```text
我数了一下，我现在只剩下4块6毛钱啦，太贵的我买不起。
```

预期：

- 系统应更新当前预算为 `price_max=4.6`；
- 重新筛选单瓶低价饮料；
- 推荐应优先在 `p_food_003` 东方树叶 4 元、`p_food_004` 元气森林 4.5 元等真实商品中选择。

### 第 5 轮：零食预算改为 10 元

```text
那如果我还有10块钱零花钱，想再买一点可以配着喝的小零食，可以买什么呀？
```

预期：

- 系统应识别为新需求：零食；
- 金额应从饮料的 4.6 元切换为零食预算 10 元；
- 当前库中 10 元以内零食很少，可能推荐相近真实商品或说明暂无完全匹配；
- 不应继续把 4.6 元当作零食预算。

### 第 6 轮：排除大包装、糕点和谷物类

```text
我不要包装太大的，也不要那种糕点和谷物类的零食，我怕吃不完。
```

预期：

- 系统应把“大包装、糕点、谷物类”作为否定约束；
- 不应推荐肉松饼这类糕点；
- 如果无完全匹配，要如实说明并给真实相近商品。

### 第 7 轮：适合和爸爸妈妈一起吃

```text
那有没有适合我和爸爸妈妈一起吃的呀？我想我们三个一起分着吃。
```

预期：

- 系统可以推荐更适合分享的真实零食，例如每日坚果；
- 如果价格超过 10 元，要明确说明超预算，是家庭分享备选；
- 回复要体现用户是小朋友，但不输出内部画像词。

### 第 8 轮：选定并跳转购物车

根据系统上一轮推荐结果，测试同学按真实排序选择一款。例如：

```text
那我就要第一款吧，帮我加入购物车，然后带我去购物车看看。
```

预期：

- IntentPlan 应包含 `cart_add -> cart_view` 或等价动作；
- 前端事件应包含 `show_reply`、`update_cart`、`navigate`；
- `navigation.target_page` 应为 `cart_page`；
- 购物车商品必须是刚才推荐的真实商品。

结束时输入：

```text
/end
```

观察：

- `/profile` 应能看到用户表达偏童真、对低糖和低价敏感等摘要；
- 不应推断未明确说明的敏感身份。

## 4. 案例二：25-35 岁女性长流程多需求

目标：

- 测试用户在一个长会话中多次切换商品目标；
- 测试早餐速食、发饰、彩妆、通勤组合等不同类目；
- 测试详情页、购物车页和聊天页来回；
- 测试长期画像逐步形成。

启动：

```bash
python3 scripts/agent_console.py \
  --user_id qa_working_woman \
  --session_id qa_working_woman_01 \
  --new_session
```

### 4.1 早餐速食

逐轮输入：

```text
早上上班很赶，帮我推荐一点早餐速食，最好方便带走。
```

```text
我想要低脂一点、不要太油的。
```

```text
50元以内一箱，最好不要甜味。
```

预期：

- 进入 `食品饮料/方便食品` 或相近真实食品；
- 价格应作为硬约束；
- “不要甜味”应成为否定约束；
- 推荐必须来自方便面、咖啡、牛奶、酸奶、坚果等真实库；
- 如果没有完全健康低脂速食，应说明并给相近真实备选。

可以继续：

```text
查看第一款商品详情。
```

预期：

- 出现 `show_product_detail`；
- 出现 `navigate -> product_detail_page`。

### 4.2 发圈需求改写为库存可测发饰/帽子需求

当前商品库没有“女生发圈”。为了测试真实库存，不使用发圈；改为帽子：

```text
我还想买一个适合通勤和周末出门戴的帽子，价格别太高。
```

预期：

- 系统应切换到 `服饰运动/帽子`；
- 推荐真实帽子，如 Nike 棒球帽或 The North Face 速干运动鸭舌帽；
- 如果没有 5 元以内发圈，正确行为是说明库存暂无，不编造。

加购：

```text
把第一款加入购物车。
```

预期：

- 只 `update_cart`，不自动跳转。

### 4.3 眼线笔需求改写为真实彩妆需求

当前库没有眼线笔，有眉笔、蜜粉、唇釉、粉底液。用眉笔测试：

```text
再帮我看看眉笔，不要笔头太粗的，日常上班用自然一点。
```

预期：

- 系统推荐 `p_beauty_025` 花西子眉笔；
- 否定约束包含“笔头太粗”；
- 如果用户明确说眼线笔，应如实说明当前库暂无眼线笔，可推荐眉笔等相近彩妆。

继续：

```text
这个详情打开看看。
```

预期：

- 跳商品详情页。

### 4.4 职场新人组合方案

当前库没有办公文具和桌面收纳，因此把案例改成真实库存可覆盖的通勤组合：

```text
我下周要入职新公司，帮我搭配一套职场新人通勤好物，包含通勤背包、轻薄电脑或者耳机，最好别太夸张。
```

预期：

- 可进入 `scene_bundle`；
- 推荐真实背包、笔记本电脑、耳机；
- 如提到办公文具、桌面收纳，应说明当前库暂无，不编造；
- 回复要符合职场新人，语气简洁但有解释。

查看购物车：

```text
查看购物车。
```

预期：

- `navigate -> cart_page`。

结束：

```text
/end
```

观察 `/profile`：

- 画像应包含通勤、职场、价格敏感、偏实用等稳定信息；
- 不应从商品偏好强行推断敏感身份。

## 5. 案例三：反选 / 排除约束

启动：

```bash
python3 scripts/agent_console.py \
  --user_id qa_exclusion \
  --session_id qa_exclusion_01 \
  --new_session
```

### 5.1 防晒排除酒精和日系品牌

```text
推荐防晒霜，但我不要含酒精的，也不要日系品牌。
```

预期：

- 推荐应优先出现 `p_beauty_006` 巴黎欧莱雅防晒隔离露；
- 不应推荐安热沙、资生堂、珊珂、芳珂、SK-II 等日系品牌；
- 不应出现 `show_error`。

### 5.2 短袖排除紧身和印花

```text
买夏季短袖，不要紧身款，不要大Logo印花，想要宽松基础款。
```

预期：

- 推荐应优先出现 `p_clothes_001` 优衣库 AIRism 宽松基础短袖；
- 商品卡片理由必须是完整自然句；
- 不应推荐明显紧身或大 Logo 印花款。

### 5.3 彩妆排除过粗笔头

```text
推荐眉笔，不要笔头过粗，最好日常自然一点。
```

预期：

- 推荐真实眉笔 `p_beauty_025`；
- 回复说明适合自然日常妆；
- 不编造眼线笔。

## 6. 案例四：场景化组合推荐

启动：

```bash
python3 scripts/agent_console.py \
  --user_id qa_scene \
  --session_id qa_scene_01 \
  --new_session
```

### 6.1 西北自驾旅行

```text
下周去西北自驾旅行，帮我搭配一套户外用品清单。
```

预期可推荐真实商品：

- `p_beauty_023` 理肤泉清爽控油防晒；
- `p_clothes_014` SALOMON 徒步鞋；
- `p_clothes_017` Arc'teryx 户外裤；
- `p_clothes_024` The North Face 防晒帽；
- `p_clothes_025` Osprey 背包。

预期说明：

- 当前库没有帐篷、睡袋、车载冰箱、户外炊具等。

### 6.2 情侣海边短途度假

```text
情侣一周短途海边度假，穿搭、护肤、随身好物全套搭配。
```

预期：

- 可推荐防晒、短袖、帽子、背包、饮品等真实商品；
- 应说明当前库没有泳衣、拖鞋、沙滩垫等；
- 不要把不存在商品加入商品卡片。

### 6.3 居家健身基础方案

```text
居家健身，搭配运动服饰和运动后补给的一整套方案。
```

预期：

- 推荐速干 T 恤、运动短裤、跑鞋、饮品或食品补给；
- 说明当前库没有哑铃、弹力带、防滑垫、小型器械；
- 不编造健身器材。

## 7. 案例五：购物车与下单

### 7.1 洁面乳 + 爽肤水 + 默认地址结算

启动：

```bash
python3 scripts/agent_console.py \
  --user_id qa_cart_combo \
  --session_id qa_cart_beauty_01 \
  --new_session
```

逐轮输入：

```text
推荐一款适合油皮的洁面乳。
```

```text
把第一款加入购物车。
```

```text
再推荐一瓶保湿爽肤水。
```

```text
把第一款加入购物车。
```

```text
现在结算下单，用默认收货地址。
```

预期：

- 洁面乳推荐真实商品 `p_beauty_011`；
- 爽肤水推荐真实化妆水，例如 `p_beauty_019` 或 `p_beauty_003`；
- 普通加购不跳转；
- 结算时出现 `navigate -> checkout_page`；
- `cart_state.cart.order` 中有模拟订单信息。

### 7.2 清空购物车后重新挑背包

启动：

```bash
python3 scripts/agent_console.py \
  --user_id qa_cart_combo \
  --session_id qa_cart_bag_01 \
  --new_session
```

逐轮输入：

```text
推荐一款适合户外的防晒霜。
```

```text
把第一款加入购物车。
```

```text
刚才加购的防晒不要了，清空购物车，重新挑选一款适合通勤和旅行的背包。
```

预期：

- IntentPlan 应为 `cart_clear -> refine`；
- 购物车先清空；
- 随后推荐真实背包；
- 推荐商品必须全是 `服饰运动/背包`；
- 不应混入防晒、T 恤、饮料。

### 7.3 两款耳机加购，对比后删除较贵款并付款

启动：

```bash
python3 scripts/agent_console.py \
  --user_id qa_cart_combo \
  --session_id qa_cart_earphone_01 \
  --new_session
```

逐轮输入：

```text
推荐两款适合学生的降噪蓝牙耳机。
```

```text
把第一款和第二款耳机都加入购物车。
```

```text
告诉我哪个更适合学生。
```

```text
对比后删除较贵的那款再付款。
```

预期：

- 推荐真实耳机，如 `p_digital_007` 华为 FreeBuds Pro 5、`p_digital_018` AirPods Pro 3；
- 对比回复应考虑学生场景、价格、降噪和佩戴；
- 最后一轮 IntentPlan 应包含删除较贵商品和 checkout；
- 购物车保留较便宜耳机；
- 出现 `navigate -> checkout_page`。

## 8. 案例六：复杂组合 IntentPlan

启动：

```bash
python3 scripts/agent_console.py \
  --user_id qa_cart_combo \
  --session_id qa_intent_plan_01 \
  --new_session
```

### 8.1 加购、防误删、再推荐

逐轮输入：

```text
推荐防晒霜。
```

```text
把第二款加入购物车。
```

```text
帮我把你推荐的第一个防晒乳加到购物车，把购物车中其他的防晒乳全部删掉，再给我推荐一个200块左右的背包，也是旅游使用的。
```

预期：

- `/trace` 或默认 system_debug 中 `意图计划` 应显示 `cart_add -> cart_remove -> refine`；
- 先把推荐第一款防晒加入购物车；
- 再删除购物车中“其他”防晒，保留刚加入的商品；
- 最后检索背包；
- 如果没有 200 元左右背包，应展示真实相近背包，并说明不完全贴合；
- 不能编造 200 元背包。

### 8.2 模糊表达删除旧商品 + 加购第二个 6 瓶

启动新会话：

```bash
python3 scripts/agent_console.py \
  --user_id qa_cart_combo \
  --session_id qa_intent_plan_02 \
  --new_session
```

逐轮输入：

```text
推荐功能饮料。
```

```text
把第一款加入购物车。
```

```text
我不喜欢刚才加到购物车的那个饮料了，你帮我把现在推荐的第二个往购物车加6瓶吧。
```

预期：

- IntentPlan 应显示 `cart_remove -> cart_add`；
- “不喜欢刚才加到购物车的那个饮料了”应执行删除购物车旧饮料；
- “第二个加6瓶”应执行加购第二个推荐商品，数量 6；
- 最终购物车只剩新加的第二款饮料，数量为 6。

## 9. 历史恢复测试

先生成历史：

```bash
python3 scripts/agent_console.py \
  --user_id qa_child_drink \
  --session_id qa_child_drink_resume_seed \
  --new_session
```

逐轮输入：

```text
我喜欢不太甜的饮料，也喜欢便宜一点的小零食，你记住哦。
```

```text
推荐一瓶4块多的小饮料。
```

```text
/end
```

恢复：

```bash
python3 scripts/agent_console.py \
  --user_id qa_child_drink \
  --session_id qa_child_drink_resume_new \
  --resume
```

输入：

```text
继续帮我看看上次那种不太甜的小饮料吧。
```

预期：

- 系统能参考历史偏好；
- 仍以本轮明确需求为最高优先级；
- 回复里不能出现“长期记忆”“用户画像”等内部词。

## 10. 图片 + 文本多模态验收

多模态第一版仍然遵守库存 grounded 原则。准备几张任意测试图片即可；如果没有真实图片，也可以用文件名包含目标词的本地图片做流程测试。

### 10.1 背包相似款

```bash
python3 scripts/agent_console.py \
  --user_id qa_multimodal \
  --session_id qa_multimodal_bag \
  --image_path "/Users/grsxsa/Desktop/backpack.jpg" \
  "有没有类似这种款式，但价格低一点的背包"
```

预期：

- `multimodal_debug` 中 `是否启用多模态=true`；
- 图片理解结果主要类别为背包或相近包类；
- 推荐商品必须是 `服饰运动/背包`；
- 不应混入防晒、T 恤、饮料。

### 10.2 鞋子相似风格

```bash
python3 scripts/agent_console.py \
  --user_id qa_multimodal \
  --session_id qa_multimodal_shoe \
  --image_path "/Users/grsxsa/Desktop/sneaker.jpg" \
  "想要这双老爹鞋，还要相似风格的其他款式"
```

预期：

- 当前库没有“老爹鞋”专门子类，因此系统应按相似运动鞋/跑步鞋检索；
- 商品卡片必须来自真实鞋类库存；
- 回复中不能承诺“完全同款”。

### 10.3 库存不覆盖的毛绒玩偶

```bash
python3 scripts/agent_console.py \
  --user_id qa_multimodal \
  --session_id qa_multimodal_toy \
  --image_path "/Users/grsxsa/Desktop/plush_toy.jpg" \
  "找同款毛绒玩偶，要大号版本"
```

预期：

- 系统说明当前库没有毛绒玩偶；
- 不返回编造商品卡片；
- `system_debug.多模态分析.库存匹配判断.库存是否覆盖目标类目=false`。

### 10.4 无 GPU 和 GPU 方案验收

无 GPU、本地 CPU 流程测试：

```bash
touch /tmp/commute_backpack.jpg
USE_MOCK_LLM=1 ENABLE_LOCAL_MODELS=false python3 scripts/agent_console.py \
  --user_id qa_multimodal_cpu \
  --session_id qa_multimodal_cpu_bag \
  --image_path "/tmp/commute_backpack.jpg" \
  "有没有类似这种款式，但价格低一点的背包"
```

预期：

- 走保守 fallback，`图片理解结果.分析来源=MockLLMClient`；
- 商品仍必须来自真实背包库存；
- 该模式用于无 GPU 的稳定流程验证，不代表真实视觉识别质量。

GPU 或云端 VLM 效果验收：

```bash
USE_MOCK_LLM=0 ENABLE_LOCAL_MODELS=true python3 scripts/agent_console.py \
  --user_id qa_multimodal_vlm \
  --session_id qa_multimodal_vlm_bag \
  --image_path "/Users/grsxsa/Desktop/backpack.jpg" \
  "有没有类似这种款式，但价格低一点的背包"
```

预期：

- 图片理解由真实视觉模型/云端 VLM 完成；
- 后续检索仍然经过库存 grounded 的 RAG；
- 如果视觉模型识别出库存不覆盖类目，系统必须如实说明暂无，不造商品。

## 11. 隐私保护与层次记忆验收

### 11.1 关闭个性化

```bash
python3 scripts/agent_console.py \
  --user_id qa_privacy_off \
  --session_id qa_privacy_off_01 \
  --new_session
```

逐轮输入：

```text
关闭个性化推荐，不要根据历史推荐。
```

```text
推荐一款清爽一点的防晒霜。
```

预期：

- 系统仍推荐真实防晒商品；
- `/trace` 或默认 debug 中 `隐私保护.个性化模式=off`；
- `个性化分析.是否启用个性化=false`；
- 回复中不能出现“用户画像”“长期记忆”等内部词。

### 11.2 隐私个性化，只使用语义摘要

```bash
python3 scripts/agent_console.py \
  --user_id qa_privacy_semantic \
  --session_id qa_privacy_semantic_01 \
  --new_session
```

逐轮输入：

```text
我一直比较喜欢清爽、性价比高的护肤品，记住一下。
```

```text
推荐一款适合夏天通勤的防晒霜。
```

```text
开启隐私个性化，只用语义摘要，不要用原文历史。
```

```text
再推荐一款清爽防晒。
```

预期：

- `隐私保护.个性化模式=semantic`；
- `是否允许使用历史原文做个性化=false`；
- `个性化分析.本轮使用的few-shot示例=[]`；
- 仍然可以使用类目计数、偏好标签、价格信号等语义摘要做个性化。

### 11.3 不保存原始历史，但保留语义记忆

```bash
python3 scripts/agent_console.py \
  --user_id qa_privacy_no_raw \
  --session_id qa_privacy_no_raw_01 \
  --new_session
```

输入：

```text
不要保存聊天，开启隐私个性化，然后推荐一款性价比高的饮料。
```

再打开服务后检查：

```bash
curl "http://127.0.0.1:8000/api/session/qa_privacy_no_raw_01/history?user_id=qa_privacy_no_raw" | python3 -m json.tool
```

预期：

- session history 中原始输入和回复被替换为隐私占位文本；
- `profile.semantic_memory`、`memory_cards` 仍可更新；
- 商品推荐仍然 grounded，不受隐私模式破坏。

## 12. 验收底线

- 不得出现商品库外商品。
- 用户排除的品牌、成分、款式不得进入最终推荐卡片。
- 推荐理由必须是自然完整句。
- 用户可见回复不能出现 `memory`、`RAG`、`状态机`、`IntentPlan`、`长期记忆` 等开发者内部词。
- 正常澄清、无完全匹配、库存不覆盖不是系统异常，不应出现 `show_error`。
- 普通推荐和普通加购不应主动跳页。
- 明确查看详情、查看购物车、结算/付款时才可以出现 `navigate`。
- 购物车和下单必须由后端工具执行，不能由大模型口头编造。
