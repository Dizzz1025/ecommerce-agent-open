# 电商导购 UI 设计 Token 与交互说明

## 1. 文档目标

本文件用于指导 Codex 将 UI 视觉稿系统化地实现为 Android Jetpack Compose 页面。

视觉稿包含以下界面：

1. AI 导购对话页；
2. 购物车页；
3. 商品详情页沉浸大图状态；
4. 商品详情页信息展开状态。

其中第 3、4 个界面不是两个独立页面，而是同一个商品详情页在不同滚动位置下的两种状态。

实现时需要遵守以下原则：

* 视觉稿用于定义视觉语言和页面结构；
* 商品名称、价格、图片和规格均为示例，不允许直接硬编码到页面；
* 必须复用当前项目已有的 `UiModel`、`ViewModel`、`Repository`、导航和后端接口；
* 所有页面统一使用 Design Token；
* 重复元素必须抽取成公共 Compose 组件；
* 页面整体保持中性黑白灰，不根据商品颜色改变页面主题；
* 不使用默认 Material 紫色；
* 不使用明显渐变、重阴影、大面积高饱和颜色；
* 保持简洁、克制、轻量和具有电商产品感。

---

# 2. Design Token

## 2.1 Token 文件建议

建议建立以下文件：

```text
theme/
├── AppColors.kt
├── AppSpacing.kt
├── AppRadius.kt
├── AppTypography.kt
├── AppDimensions.kt
├── AppMotion.kt
└── AppTheme.kt
```

也可以根据当前项目目录结构调整文件名，但所有 Token 必须集中管理，禁止散落在不同页面中。

---

## 2.2 颜色 Token

整体色彩采用中性黑白灰，少量暖色只用于折扣、AI 标签等辅助信息。

```kotlin
object AppColors {

    // 页面背景
    val Background = Color(0xFFF7F7F5)
    val BackgroundElevated = Color(0xFFFAFAF8)

    // 容器背景
    val Surface = Color(0xFFFFFFFF)
    val SurfaceSoft = Color(0xFFF4F4F1)
    val SurfacePressed = Color(0xFFEEEEEA)

    // 文字
    val TextPrimary = Color(0xFF151515)
    val TextSecondary = Color(0xFF6F6F6B)
    val TextTertiary = Color(0xFFA0A09B)
    val TextDisabled = Color(0xFFC3C3BE)
    val TextInverse = Color(0xFFFFFFFF)

    // 边框与分割线
    val Border = Color(0xFFE8E8E4)
    val BorderStrong = Color(0xFFD8D8D3)
    val Divider = Color(0xFFF0F0EC)

    // 主操作
    val Primary = Color(0xFF151515)
    val PrimaryPressed = Color(0xFF30302E)
    val OnPrimary = Color(0xFFFFFFFF)

    // 次操作
    val SecondaryButton = Color(0xFFFFFFFF)
    val SecondaryButtonPressed = Color(0xFFF2F2EF)

    // 暖色辅助，只能小面积使用
    val AccentWarm = Color(0xFFB7835F)
    val AccentWarmSoft = Color(0xFFF6EEE8)

    // 危险操作
    val Danger = Color(0xFFB65A50)
    val DangerSoft = Color(0xFFF8EFED)

    // 成功反馈
    val Success = Color(0xFF4F7A5D)
    val SuccessSoft = Color(0xFFEDF4EF)

    // 遮罩
    val OverlayLight = Color(0x26000000)
    val OverlayMedium = Color(0x52000000)
    val OverlayStrong = Color(0x80000000)

    // 图片上的文字与按钮
    val HeroText = Color(0xFFFFFFFF)
    val HeroIconBackground = Color(0xD9FFFFFF)
    val HeroIcon = Color(0xFF1A1A1A)
}
```

### 颜色使用规则

1. 页面背景统一使用 `Background`。
2. 商品卡片、聊天卡片和信息面板使用 `Surface`。
3. 主要购买按钮使用黑色 `Primary`。
4. 次级按钮使用白底黑色描边。
5. 暖色只用于：

   * 折扣标签；
   * AI 推荐标识；
   * 少量强调信息。
6. 删除操作不得使用高饱和大面积纯红色区域。
7. 商品颜色仅影响商品图片和颜色选择圆点，不影响整个页面主题。

---

## 2.3 间距 Token

所有布局优先采用 4dp 网格。

```kotlin
object AppSpacing {
    val None = 0.dp
    val Xxs = 2.dp
    val Xs = 4.dp
    val Sm = 8.dp
    val Md = 12.dp
    val Lg = 16.dp
    val Xl = 20.dp
    val Xxl = 24.dp
    val Xxxl = 32.dp
    val Huge = 40.dp
}
```

### 间距使用规则

```text
页面左右边距：16dp
页面顶部普通间距：16dp
卡片内部边距：12dp 或 16dp
卡片之间间距：12dp
文本标题与副标题：4dp
模块标题与内容：8dp
大模块之间间距：20dp 或 24dp
底部安全区域：系统 Insets + 8dp
```

禁止在页面中随意出现大量 `13.dp`、`17.dp`、`19.dp` 等零散值。

---

## 2.4 圆角 Token

```kotlin
object AppRadius {
    val Xs = 6.dp
    val Small = 8.dp
    val Medium = 12.dp
    val Large = 16.dp
    val Card = 20.dp
    val Panel = 24.dp
    val LargePanel = 28.dp
    val Pill = 100.dp
}
```

### 圆角使用规则

```text
小标签：6–8dp
颜色和尺码选项：8–12dp
输入框：20–24dp
普通按钮：12–16dp
商品卡片：16–20dp
聊天气泡：16–20dp
商品详情信息面板：24–28dp
圆形图标按钮：Pill
```

同类组件必须使用同一个圆角 Token，不得每个页面单独定义。

---

## 2.5 字体 Token

字体使用系统无衬线字体，优先采用 Android 默认字体，不额外引入难以分发的字体文件。

```kotlin
object AppTypography {

    val Caption = TextStyle(
        fontSize = 11.sp,
        lineHeight = 16.sp,
        fontWeight = FontWeight.Normal
    )

    val CaptionStrong = TextStyle(
        fontSize = 12.sp,
        lineHeight = 18.sp,
        fontWeight = FontWeight.Medium
    )

    val BodySmall = TextStyle(
        fontSize = 13.sp,
        lineHeight = 20.sp,
        fontWeight = FontWeight.Normal
    )

    val Body = TextStyle(
        fontSize = 15.sp,
        lineHeight = 22.sp,
        fontWeight = FontWeight.Normal
    )

    val BodyStrong = TextStyle(
        fontSize = 15.sp,
        lineHeight = 22.sp,
        fontWeight = FontWeight.SemiBold
    )

    val TitleSmall = TextStyle(
        fontSize = 16.sp,
        lineHeight = 24.sp,
        fontWeight = FontWeight.SemiBold
    )

    val Title = TextStyle(
        fontSize = 20.sp,
        lineHeight = 28.sp,
        fontWeight = FontWeight.SemiBold
    )

    val TitleLarge = TextStyle(
        fontSize = 24.sp,
        lineHeight = 32.sp,
        fontWeight = FontWeight.SemiBold
    )

    val PriceSmall = TextStyle(
        fontSize = 16.sp,
        lineHeight = 22.sp,
        fontWeight = FontWeight.Bold
    )

    val Price = TextStyle(
        fontSize = 22.sp,
        lineHeight = 28.sp,
        fontWeight = FontWeight.Bold
    )

    val HeroPrice = TextStyle(
        fontSize = 28.sp,
        lineHeight = 34.sp,
        fontWeight = FontWeight.Medium
    )

    val Button = TextStyle(
        fontSize = 15.sp,
        lineHeight = 20.sp,
        fontWeight = FontWeight.SemiBold
    )
}
```

### 字体层级规则

* 页面标题：`TitleSmall` 或 `Title`
* 商品名称：`TitleSmall`
* 正文：`Body`
* 辅助说明：`BodySmall`
* 标签和销量：`CaptionStrong`
* 当前价格：`Price` 或 `PriceSmall`
* 原价：`BodySmall`，添加删除线
* 按钮：`Button`

禁止用颜色代替全部层级。层级需要通过字号、字重、行高和颜色共同体现。

---

## 2.6 组件尺寸 Token

```kotlin
object AppDimensions {

    // 触控区域
    val MinimumTouchTarget = 48.dp

    // 图标视觉尺寸
    val IconSmall = 18.dp
    val IconMedium = 22.dp
    val IconLarge = 24.dp

    // 圆形图标按钮
    val IconButtonSmall = 40.dp
    val IconButton = 44.dp
    val IconButtonLarge = 48.dp

    // 按钮
    val ButtonSmallHeight = 40.dp
    val ButtonHeight = 48.dp
    val PrimaryButtonHeight = 52.dp

    // 输入框
    val ChatInputMinHeight = 52.dp
    val ChatInputMaxHeight = 120.dp

    // 商品图片
    val RecommendationImageHeight = 144.dp
    val CartImageSize = 92.dp

    // 购物车删除区域
    val SwipeDeleteActionWidth = 56.dp
    val SwipeDeleteIconSize = 19.dp

    // 底部操作栏
    val BottomActionBarMinHeight = 72.dp

    // 顶栏
    val TopBarHeight = 56.dp
}
```

### 触控规则

图标视觉尺寸可以只有 18～22dp，但外部点击区域不得小于 44～48dp。

例如购物车删除图标：

```text
图标视觉尺寸：19dp
点击区域：48dp
左滑删除区域宽度：56dp
```

---

## 2.7 边框和阴影

整体不依赖明显阴影，优先通过背景层级和边框区分。

```kotlin
object AppElevation {
    val None = 0.dp
    val Low = 1.dp
    val Medium = 4.dp
    val Floating = 8.dp
}
```

使用规则：

* 普通商品卡片：`None` 或 `Low`
* 底部固定栏：顶部细分割线，不使用重阴影
* 浮动圆形按钮：`Medium`
* Bottom Sheet：`Floating`
* 信息面板：白色背景 + 极浅边框即可

---

## 2.8 动画 Token

```kotlin
object AppMotion {
    const val Fast = 120
    const val Normal = 200
    const val Slow = 280

    val StandardEasing = FastOutSlowInEasing
    val EnterEasing = LinearOutSlowInEasing
    val ExitEasing = FastOutLinearInEasing
}
```

使用规则：

```text
按钮按压反馈：120ms
卡片展开或收起：200ms
左滑删除区域出现：200ms
商品详情大图折叠：200–280ms
Bottom Sheet 进入：280ms
成功提示淡入淡出：200ms
```

禁止使用弹跳明显、娱乐化程度较高的动画。

---

# 3. 页面级交互说明

# 3.1 AI 导购对话页

## 3.1.1 页面结构

页面从上到下依次包含：

1. 用户信息顶栏；
2. 对话消息区域；
3. 思考过程或推荐思路区域；
4. 推荐商品区域；
5. 底部输入栏。

顶栏固定在页面顶部，输入栏固定在页面底部，中间聊天内容可滚动。

---

## 3.1.2 顶栏

顶栏左侧显示：

* 用户头像；
* 问候文字，例如“你好，Lily”；
* 简短副标题。

顶栏右侧只保留：

1. 历史记录图标；
2. 购物车图标。

不得显示：

* 搜索图标；
* 三条横线菜单图标；
* 单独的“AI 导购助手”标题行。

交互：

```text
点击历史记录：
进入历史会话页面，或打开历史会话抽屉。

点击购物车：
进入购物车页面。
```

历史记录和购物车图标均需要不少于 44dp 的点击区域。

---

## 3.1.3 用户消息

用户发送消息后：

1. 消息立即显示在右侧；
2. 使用浅灰色气泡；
3. 气泡最大宽度为页面宽度的 75%～82%；
4. 支持多行文字；
5. 不固定消息气泡高度。

用户消息不得等待后端返回后才显示。

---

## 3.1.4 AI 回复流程

用户发送消息后，回复区域按以下阶段变化。

### 阶段一：等待后端响应

在 AI 回复位置显示轻量加载状态，例如：

```text
正在理解你的需求…
```

不得显示空白页面或只显示无限转圈。

### 阶段二：接收 progress 事件

将后端返回的 `progress` 事件展示为“推荐思路”卡片。

卡片结构：

```text
推荐思路                         收起图标
① 理解需求：……
② 提取条件：……
③ 筛选商品：……
④ 风格匹配：……
```

要求：

* progress 内容必须来自后端实际事件；
* 不允许把 progress 改名为“你的需求”；
* progress 卡片默认展开；
* 卡片可以点击收起或展开；
* 新的 progress 到达时追加或更新步骤；
* 卡片位于最终回复将要出现的位置。

### 阶段三：正式回复开始生成

正式回复开始产生后：

1. progress 卡片从页面中消失；
2. 最终回复在 progress 原位置出现；
3. 不得让 progress 卡片和正式回复长期同时占据两个区域；
4. 替换过程使用 200ms 左右的淡入淡出；
5. 页面不应发生明显跳动。

---

## 3.1.5 推荐结果结构

最终推荐结果必须是连贯回复，而不是互不相关的独立卡片。

推荐结果顺序：

```text
购买结论

推荐商品 1 的推荐理由
商品卡片 1

推荐商品 2 的推荐理由
商品卡片 2

推荐商品 3 的推荐理由
商品卡片 3

下一步追问或操作建议
```

不得实现成：

```text
所有推荐理由
所有商品卡片
```

也不得只返回商品卡片而缺少购买结论。

---

## 3.1.6 推荐商品卡片

视觉稿中的商品卡片可以横向排列。

建议实现：

* 使用横向可滚动列表；
* 卡片宽度约为屏幕宽度的 28%～34%；
* 商品图片位于上方；
* 商品名称最多两行；
* 底部显示价格和购物车图标；
* 卡片间距使用 `AppSpacing.Md`；
* 商品图片统一比例；
* 不允许拉伸图片。

交互：

```text
点击商品卡片：
进入对应商品详情页。

点击购物车图标：
如果商品存在颜色或尺码规格，打开规格选择面板。
如果商品无规格，可直接加入购物车。
```

---

## 3.1.7 规格选择与加购

从对话页点击加购后：

1. 打开规格选择 Bottom Sheet 或内嵌规格面板；
2. 显示颜色和尺码；
3. 已选规格使用黑底白字或明显描边；
4. 未选择必要规格时不能完成加购；
5. 用户完成规格选择后点击确认加购。

加购成功后：

1. 调用现有购物车业务逻辑；
2. 规格选择面板自动关闭；
3. 显示轻量成功反馈：

```text
轻薄西装外套已加入购物车
```

4. 成功反馈持续约 2～3 秒；
5. 不得在加购成功后继续输出：

```text
暂时没有找到完全符合条件的商品
```

---

## 3.1.8 底部输入栏

输入栏固定在底部，包含：

* 文本输入区域；
* 语音按钮；
* 更多操作按钮；
* 发送按钮可根据当前项目能力显示。

要求：

* 输入框高度随文本增加；
* 最低高度 52dp；
* 最大高度约 120dp；
* 超过最大高度后内部滚动；
* 键盘弹出后输入栏保持可见；
* 使用系统安全区 Insets；
* 输入内容为空时，发送按钮处于不可用状态。

---

# 3.2 购物车页

## 3.2.1 页面结构

页面从上到下包含：

1. 顶栏；
2. 商品数量摘要；
3. 购物车商品列表；
4. 固定底部结算栏。

不得显示优惠券一行。

---

## 3.2.2 顶栏

顶栏包含：

* 左侧返回按钮；
* 中间“购物车”标题；
* 标题下方可显示商品数量；
* 右侧可保留更多操作按钮，但不得影响主要布局。

---

## 3.2.3 商品项

商品项包含：

* 商品图片；
* 商品名称；
* 颜色、尺码；
* 当前价格；
* 原价；
* 数量控制器。

视觉要求：

* 白色或极浅色卡片；
* 卡片圆角使用 `AppRadius.Card`；
* 商品图片圆角 10～12dp；
* 不使用明显阴影；
* 卡片内部间距 12～16dp；
* 商品标题最多两行。

---

## 3.2.4 左滑删除

删除操作默认完全隐藏。

用户向左滑动商品项后：

1. 商品卡片整体向左移动；
2. 右侧露出删除操作区域；
3. 删除操作区域最大宽度为 56dp；
4. 删除区域只显示一个小型垃圾桶图标；
5. 不显示“删除”文字；
6. 不使用大面积鲜红色按钮；
7. 图标视觉尺寸为 18～20dp；
8. 图标点击区域不小于 48dp。

删除区域建议：

```text
背景：DangerSoft
图标：Danger
区域宽度：56dp
图标尺寸：19dp
```

行为规则：

* 左滑超过约 28dp 时可以继续展开；
* 松手超过约 50% 阈值时展开至完整状态；
* 未超过阈值时自动回弹；
* 最大滑动距离只能到删除区域宽度；
* 不允许整条商品项被直接滑出并立即删除；
* 同一时间只允许一个商品项处于展开状态；
* 滑动新的商品项时，之前的商品项自动关闭；
* 点击列表其他区域时，当前展开项自动关闭；
* 页面开始滚动时，当前展开项自动关闭。

---

## 3.2.5 删除商品

点击垃圾桶图标后：

1. 从购物车状态中移除商品；
2. 商品项使用约 200ms 的收起动画；
3. 底部显示 Snackbar：

```text
已删除商品                      撤销
```

4. 用户点击“撤销”时恢复原商品及数量；
5. Snackbar 建议持续 4 秒；
6. 不额外弹出确认对话框。

只有在现有业务明确要求二次确认时，才使用确认弹窗。

---

## 3.2.6 数量控制器

数量控制器结构：

```text
减号    数量    加号
```

要求：

* 使用胶囊形或三个独立圆形区域；
* 单个点击区域不少于 36～40dp；
* 数量变化后立即更新商品小计和总价；
* 数量为 1 时，再点击减号不能直接删除商品；
* 删除商品只能通过左滑垃圾桶操作；
* 更新数量期间需要防止连续请求产生状态错乱。

---

## 3.2.7 底部结算栏

底部结算栏固定在屏幕底部，不随商品列表滚动。

包含：

* 商品总数量；
* 当前总价；
* 原总价，可选；
* “去结算”按钮。

视觉要求：

* 白色背景；
* 顶部使用浅分割线；
* 主按钮为黑底白字；
* 主按钮高度 48～52dp；
* 主按钮圆角采用 `Large` 或 `Pill`；
* 正确处理底部系统导航栏安全区域。

当购物车为空时：

* 底部结算按钮不可用或不显示；
* 显示购物车空状态；
* 提供“去逛逛”入口。

---

# 3.3 商品详情页

## 3.3.1 页面关系

视觉稿中的：

* 沉浸式商品大图；
* 商品详细信息面板；

属于同一个 `ProductDetailScreen`。

禁止实现成两个独立路由页面，禁止通过点击按钮在两个页面之间跳转。

建议使用：

* `LazyColumn`；
* `NestedScrollConnection`；
* 可折叠 Hero Header；
* 或等价的 Compose 嵌套滚动方案。

---

## 3.3.2 初始沉浸状态

进入商品详情页后，首屏优先展示商品大图。

顶部浮动操作包括：

* 返回；

要求：

* 按钮悬浮在图片上；
* 使用半透明白色圆形背景；
* 按钮点击区域 44～48dp；
* 图标视觉尺寸 20～22dp；
* 顶部按钮跟随系统状态栏安全区域。

商品信息覆盖在图片底部，可显示：

* 品牌或系列；
* 当前价格；
* 原价；
* 评分；
* 图片页码指示器。

覆盖文字需要根据图片亮度保持可读性，可以在图片底部增加轻量黑色透明遮罩，但不得使用明显的大面积渐变装饰。

---

## 3.3.3 商品图片浏览

商品图片区域支持左右滑动。

要求：

* 使用 `HorizontalPager` 或项目现有图片轮播组件；
* 图片保持正确比例；
* 不拉伸；
* 主体人物或商品尽量保持完整；
* 底部显示当前页圆点；
* 当前圆点与其他圆点有明确区分；
* 页面上下滑动和图片左右滑动不得明显冲突。

---

## 3.3.4 上滑展开信息

用户向上滑动时：

1. 商品大图逐渐向上收起；
2. 商品信息面板从下方向上进入；
3. 页面从沉浸浏览状态自然过渡到商品购买状态；
4. 顶部操作按钮保持可用；
5. 不进行路由跳转；
6. 滚动位置连续，不突然切换页面。

商品信息面板顶部使用 24～28dp 圆角。

面板包含：

1. 商品名称；
2. 销量或热销标签；
3. 当前价格；
4. 原价；
5. 折扣；
6. AI 推荐理由；
7. 商品标签；
8. 颜色选择；
9. 尺码选择；
10. 后续商品详情信息。

---

## 3.3.5 商品基础信息

商品名称：

* 使用 `Title`；
* 最多两行；
* 超出时省略。

价格区域：

* 当前价格使用 `Price`；
* 原价使用次级文字并加删除线；
* 折扣使用暖色浅底标签；
* 不使用高饱和红色强调价格。

---

## 3.3.6 AI 推荐理由

AI 推荐理由位于价格区域下方。

结构建议：

```text
AI 匹配推荐
通勤百搭不挑人，轻薄透气，初夏穿着舒适有型。
```

要求：

* 内容来自现有推荐数据；
* 不写死视觉稿文案；
* 使用浅暖色图标或标签；
* 正文使用 `BodySmall`；
* 最多显示三行；
* 内容过长时提供“展开”；
* 不使用大面积彩色背景。

---

## 3.3.7 商品标签

标签示例：

```text
清爽百搭
轻薄透气
垂感有型
```

要求：

* 使用浅灰背景；
* 图标和文字保持小巧；
* 高度约 28～32dp；
* 标签之间间距 8dp；
* 支持自动换行；
* 标签内容来自商品数据或推荐结果。

---

## 3.3.8 颜色选择

颜色选择区包含：

* “颜色”标题；
* 当前选中颜色名称；
* 颜色圆点或图片选项。

要求：

* 当前选择必须明显；
* 使用描边、选中圆环或勾选标识；
* 黑色选项也必须能看出选中状态；
* 颜色选项点击区域不小于 40dp；
* 切换颜色后更新当前 SKU、商品图和库存；
* 切换颜色不得改变整个页面主题色。

---

## 3.3.9 尺码选择

尺码选项例如：

```text
S  M  L  XL
```

要求：

* 未选中：浅灰背景或白底描边；
* 已选中：黑底白字；
* 缺货：禁用并降低透明度；
* 单个尺码高度 36～40dp；
* 点击区域不小于 40dp；
* 同时只能选择一个尺码。

---

## 3.3.10 底部购买操作栏

底部操作栏固定在屏幕底部。

包含：

1. 购物车入口；
2. 加入购物车；
3. 立即购买。

视觉要求：

* 白色背景；
* 顶部浅分割线；
* 购物车入口使用圆形或小型图标按钮；
* 加入购物车使用白底黑色描边；
* 立即购买使用黑底白字；
* 两个主操作按钮高度一致；
* 正确处理系统底部安全区。

交互：

```text
点击购物车入口：
进入购物车页面。

点击加入购物车：
检查必须选择的颜色和尺码。
验证通过后加入购物车，并显示成功反馈。

点击立即购买：
检查必须选择的颜色和尺码。
验证通过后进入确认订单流程。
```

未选择必要规格时：

* 不执行加购或购买；
* 将页面滚动至规格区域；
* 高亮未选择的规格模块；
* 显示轻量提示：

```text
请选择颜色和尺码
```

# 4. 页面状态要求

每个页面必须处理以下状态：

```text
Loading
Content
Empty
Error
PartialContent
```

## 4.1 对话页

需要考虑：

* 消息加载；
* progress 接收中；
* 正式文本流式输出中；
* 商品卡片等待加载；
* 规格选择中；
* 加购成功；
* 加购失败；
* 网络错误。

## 4.2 购物车页

需要考虑：

* 加载中；
* 有商品；
* 空购物车；
* 数量更新中；
* 删除中；
* 撤销删除；
* 更新失败。

## 4.3 商品详情页

需要考虑：

* 页面加载；
* 商品不存在；
* 图片加载失败；
* 颜色或尺码缺货；
* 加购中；
* 加购成功；
* 网络错误。

不得让错误状态直接导致页面崩溃。

---

# 5. 建议公共组件

Codex 在改造页面前，应先检查项目中是否已有以下组件。

```text
AppTopBar
AppIconButton
PrimaryButton
SecondaryButton
PriceText
OriginalPriceText
TagChip
ProductImage
ProductCard
RecommendationProductCard
UserMessageBubble
AssistantMessageBlock
ThinkingProcessCard
ChatInputBar
QuantityStepper
SwipeToDeleteCartItem
CompactDeleteAction
CartSummaryBar
ProductImagePager
ProductInfoPanel
AiRecommendationBlock
ColorSelector
SizeSelector
ProductBottomActionBar
LoadingState
EmptyState
ErrorState
```

组件名称可根据项目已有规范调整。

禁止：

* 对话页和购物车页分别写两套价格组件；
* 多个页面分别实现颜色选择器；
* 多个页面重复实现商品图片加载；
* 将整个页面全部堆在一个数千行的 `Screen.kt` 中。

---

# 6. 数据绑定规则

视觉稿中的数据仅用于说明页面效果。

以下内容必须从现有数据层获得：

```text
用户头像和名字
聊天消息
progress 事件
AI 推荐理由
商品名称
商品图片
商品价格
商品原价
销量
商品标签
颜色规格
尺码规格
库存状态
购物车数量
购物车总价
```

禁止在 Compose 页面内直接写死：

```kotlin
Text("轻薄西装外套")
Text("¥469")
Text("燕麦色")
Text("M")
```

预览代码 `@Preview` 可以使用 Mock 数据，但正式页面必须绑定真实状态。

---

# 7. 响应式与适配规则

页面需要至少适配：

```text
屏幕宽度：360dp～430dp
不同状态栏高度
手势导航栏
三键导航栏
系统字体缩放
键盘弹出
商品名称长度变化
价格位数变化
不同图片宽高比
```

要求：

* 不使用固定绝对坐标布局；
* 不使用只适合单一截图尺寸的宽高；
* 商品名称过长时限制行数；
* 底部固定栏不得遮挡列表内容；
* 列表底部增加与操作栏等高的内容 Padding；
* 使用 `WindowInsets` 处理系统安全区。

---

# 8. Codex 执行顺序

Codex 必须按照以下顺序执行。

## 第一步：代码审查

先阅读：

* 当前 Theme；
* 所有 Screen；
* 当前公共组件；
* `UiModels`；
* `ViewModel`；
* `Repository`；
* 导航；
* SSE 和 progress 事件；
* 购物车逻辑；
* 商品详情逻辑。

输出：

```text
现有 Token
现有公共组件
建议新增 Token
建议新增或改造的组件
需要修改的文件
需要新增的文件
每个交互的实现方案
```

第一步只输出分析，不修改代码。

## 第二步：建立 Token

优先建立颜色、间距、圆角、字体和尺寸 Token。

将已有页面中的零散值逐步迁移到 Token，不要一次性无差别重写全部主题。

## 第三步：建立公共组件

先实现通用组件，再改页面。

## 第四步：逐页修改

推荐顺序：

```text
1. 购物车页
2. 商品详情页
3. AI 导购对话页
```

每完成一个页面后进行编译检查。

## 第五步：整体检查

检查：

* 是否存在默认 Material 紫色；
* 是否存在重复组件；
* 是否存在大面积硬编码；
* 是否存在写死商品数据；
* 是否正确处理加载、空状态和错误；
* 是否正确处理系统 Insets；
* 是否能够正常编译运行。

---

# 9. 验收标准

## 9.1 视觉验收

* 页面整体为中性黑白灰；
* 不随商品颜色切换全局主题；
* 圆角、间距和字体层级统一；
* 卡片没有明显重阴影；
* 主按钮统一为黑底白字；
* 删除操作保持小巧克制；
* 商品图片不拉伸；
* 页面不再呈现明显 Demo 感。

## 9.2 对话页验收

* 顶部只有历史记录和购物车入口；
* progress 正确显示为思考过程；
* 正式回复开始后 progress 被原位置替换；
* 推荐内容按照“理由 + 商品卡片”成组展示；
* 规格选择完成后面板自动关闭；
* 加购成功后显示成功反馈；
* 不再出现错误的兜底推荐文案。

## 9.3 购物车验收

* 删除按钮默认不可见；
* 左滑后只显示小垃圾桶图标；
* 同时只能展开一项；
* 点击其他区域自动关闭；
* 删除后支持撤销；
* 不显示优惠券区域；
* 底部结算栏固定；
* 数量变化后总价实时更新。

## 9.4 商品详情验收

* 沉浸大图与详情信息属于同一页面；
* 上滑过程连续自然；
* 图片支持左右切换；
* 颜色和尺码状态明确；
* 未选择规格时不能购买；
* 底部购买操作栏固定；
* 页面主题不跟随商品颜色变化。

## 9.5 工程验收

* 不破坏已有业务逻辑；
* 不改动后端字段语义；
* 不将真实数据硬编码进页面；
* 公共组件得到复用；
* Token 统一管理；
* 页面支持加载、空、错误和正常状态；
* 项目能够正常编译运行。
