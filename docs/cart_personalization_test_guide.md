# CartAwarePersonalization 测试指南

## 1. 功能概述

`CartAwarePersonalization` 根据用户当前购物车中已有的商品，生成**商品侧个性化推荐上下文**。流程如下：

```
购物车商品 → _derive_tags（提取标签）
           → _match_rules（匹配本地搭配规则）
           → _needs_llm（判断是否需要Doubao）
              ├─ 是 → _doubao_analysis（LLM结构化画像）
              └─ 否 → 直接返回本地规则
           → rerank（对候选商品加权排序）
```

**Doubao调用条件**：只要购物车非空，系统都会先做本地购物车画像与规则匹配；当 query 明确包含“搭配/兼容/配套/一整套/一起买/一起用/同系列/补齐/购物车/加购的”等关系信号，且本地没有命中可解释规则时，再调用 Doubao 输出结构化购物车画像、搭配建议和排序软约束。

**调试输出位置**：默认多轮脚本会展示 `progress_events / 前端流式进度`、`system_debug.进度事件`、`system_debug.运行耗时`、`system_debug.购物车商品侧个性化`。如果需要完整 JSON，输入 `/debug` 或 `/all`。

## 2. 新增的本地搭配规则（30+条）

### 美妆护肤 (9条)
| 规则ID | 触发条件 | 推荐方向 |
|--------|----------|----------|
| `serum_to_routine` | 购物车有精华/安瓶/精华油 | 同品牌面霜+眼霜+面膜，高价位偏好 |
| `moisturizer_to_cleanser_sunscreen` | 购物车有面霜/眼霜 | 同品牌洁面+防晒，护肤闭环 |
| `cleanser_to_moisturize_protect` | 购物车有洁面/卸妆 | 保湿修护面霜+防晒，软价格上限500 |
| `sunscreen_to_repair` | 购物车有防晒/防晒喷雾 | 晒后修护面膜+洁面+卸妆 |
| `base_makeup_bundle` | 购物车有粉底/BB霜/素颜霜 | 定妆蜜粉+卸妆+妆前护理 |
| `color_cosmetics_bundle` | 购物车有眉笔/眼影/唇釉 | 其他彩妆+卸妆，软价格上限200 |
| `body_hair_care_bundle` | 购物车有洗发水/身体乳 | 面部护理+香氛 |
| `fragrance_to_skincare` | 购物车有香水 | 同品牌身体乳+精华+面霜，高端偏好 |
| `acne_care_routine` | 购物车有祛痘精华 | 温和洁面+无油保湿+不致痘防晒，价格上限350 |

### 数码电子 (9条)
| 规则ID | 触发条件 | 推荐方向 |
|--------|----------|----------|
| `phone_accessory_ecosystem` | 购物车有手机 | 同品牌耳机+手表+充电宝+平板 |
| `brand_ecosystem_{brand}` | Apple/华为/小米手机 | 强化同品牌全生态配件 |
| `audio_to_phone_watch` | 耳机/音箱 | 手机+手表+充电宝 |
| `tablet_study_bundle` | 平板/电子书 | 耳机+充电宝，价格上限2500 |
| `gaming_gear_bundle` | 游戏鼠标/手柄/散热器 | 高性能手机+显示器+更多外设 |
| `productivity_office_bundle` | 显示器/硬盘/打印机 | 笔记本+键鼠+充电配件 |
| `photography_kit` | 微单相机 | 移动硬盘+充电宝+手机 |
| `wearable_fitness_bundle` | 手表/手环 | 运动耳机+速干服饰+跑鞋 |
| `tablet_study_bundle` | 平板/电子书 | 耳机+手环+便携配件 |

### 服饰运动 (9条)
| 规则ID | 触发条件 | 推荐方向 |
|--------|----------|----------|
| `shoes_to_apparel` | 跑鞋/篮球鞋 | 同品牌速干衣+运动袜+运动下装 |
| `apparel_to_shoes` | 速干服饰/运动内衣/运动袜 | 同品牌跑鞋+帽子，价格上限1200 |
| `outdoor_adventure_bundle` | 冲锋衣/徒步鞋/登山杖 | 背包+帽子+防晒+速干衣 |
| `winter_warm_bundle` | 羽绒服/冲锋衣 | 卫衣+帽子+保暖配件 |
| `beach_summer_bundle` | 泳衣/沙滩拖鞋 | 防晒+防晒衣+帽子+背包，价格上限500 |
| `womens_activewear_bundle` | 运动内衣/瑜伽裤/骑行裤 | 速干上衣+跑鞋+防晒衣 |
| `casual_daily_bundle` | 牛仔裤/衬衫/板鞋/卫衣 | 同品牌百搭鞋款+基础单品，价格上限800 |
| `backpack_travel_bundle` | 背包 | 防晒+帽子+速干衣+徒步鞋+矿泉水 |

### 食品饮料 (8条)
| 规则ID | 触发条件 | 推荐方向 |
|--------|----------|----------|
| `beverage_to_snack` | 咖啡/茶叶 | 饼干+巧克力+蜂蜜，价格上限150 |
| `fitness_nutrition_bundle` | 蛋白粉/能量棒 | 矿泉水+麦片+牛奶+运动袜，价格上限250 |
| `breakfast_bundle` | 麦片/牛奶/酸奶 | 蜂蜜+饼干+果汁+咖啡，价格上限100 |
| `instant_meal_bundle` | 方便面/午餐肉 | 功能饮料+辣条+茶饮，价格上限80 |
| `snack_mix_bundle` | 零食类 | 饮品和更多零食，价格上限120 |
| `gift_quality_bundle` | 蜂蜜/茶叶 | 巧克力+坚果礼盒，高端偏好 |
| `drink_to_snack` | 矿泉水/果汁/碳酸饮料 | 饼干+零食+方便食品，价格上限80 |

### 跨类目 (2条)
| 规则ID | 触发条件 | 推荐方向 |
|--------|----------|----------|
| `cross_fitness_food_fashion` | 运动服饰+蛋白粉/能量棒 | 运动配件+健康食品 |
| `cross_sunscreen_outdoor` | 防晒+户外服饰 | 户外防护+便携装备 |

---

## 3. 测试用户说明

### 本地规则测试用户（4个）

#### 👩 beauty_lily — 美妆护肤规则测试
- **user_id**: `beauty_lily`
- **购物车**: 兰蔻小黑瓶(p_beauty_002) + SK-II神仙水(p_beauty_003)
- **触发规则**: `premium_skincare_routine`, `serum_to_routine`, brand matching
- **恢复命令**:
```bash
python scripts/agent_multiturn_console.py --user_id beauty_lily --session_id beauty_lily_test --resume
```
- **未来query**:
```text
1. 我还想再加一瓶面霜，你有什么推荐？
   → 期望触发: serum_to_routine, premium_skincare_routine
   → 期望: 推荐面霜类商品，优先兰蔻/SK-II/雅诗兰黛高端品牌
   → 观察: system_debug.购物车商品侧个性化.命中的本地规则

2. 帮我推荐一个眼霜，要能和我的精华水搭配的抗初老眼霜
   → 期望触发: premium_skincare_routine
   → 期望: 高价位眼霜，修护/抗初老/提亮标签商品加分

3. 给我搭配一套完整的护肤流程，要和小黑瓶和神仙水兼容的
   → 期望: 包含“搭配”，触发多个规则
```

#### 👨 digital_tony — 数码生态规则测试
- **user_id**: `digital_tony`
- **购物车**: iPhone 17 Pro(p_digital_001) + MacBook Air(p_digital_020)
- **触发规则**: `apple_macbook_ecosystem`, `phone_accessory_ecosystem`, `brand_ecosystem_Apple 苹果`
- **恢复命令**:
```bash
python scripts/agent_multiturn_console.py --user_id digital_tony --session_id digital_tony_test --resume
```
- **未来query**:
```text
1. 推荐一款和我的iPhone搭配使用的耳机
   → 期望触发: phone_accessory_ecosystem
   → 期望: 优先Apple AirPods Pro，其次华为/其他耳机

2. 帮我看看有没有适合办公用的平板，要和我的MacBook协同的
   → 期望触发: apple_macbook_ecosystem, tablet_study_bundle
   → 期望: iPad优先，Apple品牌boost

3. 我的手机和电脑都是苹果的，再帮我推荐一个智能手表和充电宝
   → 期望: Apple Watch优先，Apple生态标签boost
   → 观察: 命中的本地规则 应该有多个规则叠加
```

#### 🏃 sports_mike — 运动穿搭规则测试
- **user_id**: `sports_mike`
- **购物车**: Nike跑鞋(p_clothes_007) + Nike速干T恤(p_clothes_003) + 安踏运动袜(p_clothes_028)
- **触发规则**: `shoes_to_apparel`, `apparel_to_shoes`
- **恢复命令**:
```bash
python scripts/agent_multiturn_console.py --user_id sports_mike --session_id sports_mike_test --resume
```
- **未来query**:
```text
1. 再帮我推荐一条运动短裤，搭配我的跑鞋和速干衣
   → 期望触发: shoes_to_apparel, apparel_to_shoes
   → 期望: Nike优先，运动短裤/运动长裤类目boost

2. 我夏天户外跑步还需要一个帽子，防晒又透气的那种
   → 期望触发: shoes_to_apparel (帽子在boost_sub_categories中)
   → 期望: 速干/透气/轻量标签商品加分

3. 搭配我一整套夏季跑步装备，把缺的都补上
   → 期望: 包含“搭配”，多规则叠加
   → 期望: 价格带友好（购物车均价约¥449，不超过1200）
```

#### 🥣 food_emma — 早餐健康规则测试
- **user_id**: `food_emma`
- **购物车**: 桂格麦片(p_food_032) + 金典牛奶(p_food_007) + 北大荒蜂蜜(p_food_031)
- **触发规则**: `breakfast_bundle`, `gift_quality_bundle`
- **恢复命令**:
```bash
python scripts/agent_multiturn_console.py --user_id food_emma --session_id food_emma_test --resume
```
- **未来query**:
```text
1. 我还想买点配早餐的饼干或者零食，有什么推荐？
   → 期望触发: breakfast_bundle
   → 期望: 苏打饼干/坚果优先，价格不超过100

2. 帮我看看有什么好的咖啡或者果汁，早上搭配麦片喝
   → 期望触发: breakfast_bundle, beverage_to_snack
   → 期望: 咖啡/纯果汁优先

3. 我妈妈生日快到了，想搭配一套健康食品礼盒送她，帮我看看
   → 期望触发: gift_quality_bundle
   → 期望: 高端偏好，茶叶/巧克力/坚果优先
```

---

### Doubao Fallback 测试用户（2个）

#### 🎮 cross_alice — 跨类目无本地规则
- **user_id**: `cross_alice`
- **购物车**: 索尼PS5手柄(p_digital_034) + 卫龙辣条(p_food_034) + 哈瓦那拖鞋(p_clothes_037)
- **Why Doubao**: 三个不同类目，无本地规则覆盖游戏手柄+辣条+拖鞋的组合
- **恢复命令**:
```bash
python scripts/agent_multiturn_console.py --user_id cross_alice --session_id cross_alice_test --resume
```
- **未来query**:
```text
1. 帮我搭配一些和我购物车里的东西配套的商品
   → 期望: "搭配"+"配套"触发 needs_llm=true
   → 观察: system_debug.购物车商品侧个性化.是否调用Doubao 应为 true
   → 观察: Doubao分析 应包含结构化画像

2. 我想周末在家打游戏吃零食，帮我看看还缺什么
   → 期望: 跨类目场景，"搭配"语义触发LLM
   → 观察: Doubao返回的 商品标签 和 搭配建议

3. 推荐一个和我的游戏手柄兼容的鼠标
   → 期望: 单类目query，可能命中 gaming_gear_bundle 或直接走普通推荐
   → 对比: 此query不含"搭配"所以needs_llm=false
```

#### 📚 niche_bob — 小众搭配无本地规则
- **user_id**: `niche_bob`
- **购物车**: 科大讯飞电子书(p_digital_030) + 西湖龙井(p_food_036) + 探路者登山杖(p_clothes_035)
- **Why Doubao**: 电子书+龙井茶+登山杖是文艺小众组合，本地无对应规则
- **恢复命令**:
```bash
python scripts/agent_multiturn_console.py --user_id niche_bob --session_id niche_bob_test --resume
```
- **未来query**:
```text
1. 我周末喜欢带着电子书去爬山喝茶，帮我搭配一整套适合户外的装备
   → 期望: "搭配"+"一整套"触发 needs_llm=true
   → 观察: Doubao分析 应结合三个商品生成综合画像

2. 再帮我推荐一些和我的电子书搭配使用的数码产品
   → 期望: tablet_study_bundle 可能命中（电子书在平板类规则中）
   → 对比: 单类目时本地规则能否命中

3. 我的购物车里有茶叶和电子书，帮我推荐配套的休闲零食
   → 期望: beverage_to_snack 可能被茶叶触发
   → 观察: 如果query不含"搭配/兼容/配套" → needs_llm=false → 本地规则
```

---

## 4. 测试步骤

### Step 1: 创建测试用户
```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main"
python scripts/create_cart_personalization_test_users.py
```

这一步会重置 6 个购物车个性化测试用户。生成后的 `profile.json` 会包含 `profile_summary_text`、`structured_profile`、`explicit_preferences`、`history_summary` 和 `semantic_memory.cart_skus`；`sessions/*.json` 会包含可恢复的 `state_snapshot.cart`。

### Step 2: 启动后端
```bash
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
USE_MOCK_LLM=false ENABLE_LOCAL_MODELS=true uvicorn app.main:app --reload --port 8000
```

### Step 3: 启动交互脚本（逐个用户测试）
```bash
# 终端2 — 以beauty_lily为例
cd "/Users/grsxsa/2026 Spring/ECOMMERCE-GUIDER-main/backend"
source .venv/bin/activate
USE_MOCK_LLM=false ENABLE_LOCAL_MODELS=true python scripts/agent_multiturn_console.py \
  --user_id beauty_lily --session_id beauty_lily_test --resume
```

### Step 4: 在交互脚本中输入query并观察
```text
USER> 我还想再加一瓶面霜，和我购物车里的精华搭配着用
# 等待回复后观察默认摘要中的：
# 1. progress_events / 前端流式进度
# 2. system_debug.进度事件
# 3. system_debug.运行耗时
# 4. system_debug.购物车商品侧个性化

USER> /debug  # 查看完整的个性化上下文
```

### Step 5: 观察系统调试输出关键字段
```
system_debug:
  进度事件:
    预计耗时等级: medium/slow
    预测工作类型: [...]
    events: [...]
    实际总耗时_ms: ...
  运行耗时统计:
    total_duration_ms: ...
    模型调用: {调用次数, 总耗时_ms, 明细}
    Top耗时模块: [...]
  购物车商品侧个性化:
    是否启用: true
    参考购物车商品: [...]
    商品标签: ["高端护肤", "成分功效", ...]
    价格画像: {min, max, avg, tier}
    命中的本地规则: [{rule_id, 说明, boost_*}, ...]
    是否调用Doubao: true/false
    Doubao分析: {...}
    排序影响: [{sku_id, boost, reasons}, ...]
```

---

## 5. 验收标准

### 本地规则测试验收
- [ ] beauty_lily: 查询面霜/眼霜时，`serum_to_routine` 和 `premium_skincare_routine` 规则命中
- [ ] beauty_lily: 推荐结果中兰蔻/SK-II/雅诗兰黛品牌商品获得 boost
- [ ] digital_tony: 查询耳机/平板时，`apple_macbook_ecosystem` 和 `phone_accessory_ecosystem` 规则命中
- [ ] digital_tony: Apple品牌商品、真无线耳机/平板电脑子类获得 boost
- [ ] sports_mike: 查询运动短裤/帽子时，`shoes_to_apparel` 和 `apparel_to_shoes` 规则命中
- [ ] sports_mike: 价格带友好（soft_price_max=1200）生效
- [ ] food_emma: 查询饼干/咖啡时，`breakfast_bundle` 规则命中，价格上限100生效

### Doubao Fallback 测试验收
- [ ] cross_alice: query含"搭配/配套"时，`是否调用Doubao=true`
- [ ] cross_alice: `Doubao分析` 返回结构化JSON，包含商品标签和搭配建议
- [ ] niche_bob: query含"搭配/一整套"时，`是否调用Doubao=true`
- [ ] niche_bob: 单类目query不含触发词时，`是否调用Doubao=false`，走本地规则

---

## 6. 常见问题

**Q: 如何确认规则是否命中？**
输入 `/debug`，查看 `system_debug.购物车商品侧个性化.命中的本地规则` 数组；默认摘要里也会展示 `购物车商品侧个性化.命中规则`。

**Q: 如何确认Doubao是否被调用？**
查看 `system_debug.购物车商品侧个性化.是否调用Doubao` 和 `Doubao分析` 字段。

**Q: 如何确认排序影响？**
查看 `system_debug.购物车商品侧个性化.排序影响`，可以看到哪些商品获得了 boost 及原因。

**Q: 为什么之前 `/profile` 里显式偏好或历史摘要为空？**
旧的模拟用户只写了 `profile_summary_text` 和 `structured_profile`，没有补齐 `explicit_preferences/history_summary/semantic_memory.cart_skus`。现在 `scripts/create_cart_personalization_test_users.py` 会生成完整字段，`UserHistoryStore.load_profile()` 也会在读取旧模拟数据时自动补齐。

**Q: 为什么之前先输入 `/state` 再问问题会导致购物车恢复失败？**
旧逻辑中 `/state` 会创建一个空的内存 session，导致后续 `--resume` 被跳过。现在如果内存 session 仍是空白状态，首轮真实 query 仍会执行历史恢复。

**Q: USE_MOCK_LLM=true 时Doubao分析返回什么？**
MockLLMClient 的 `generate_response` 返回空字符串，`_doubao_analysis` 会返回空dict，系统降级到本地规则。
