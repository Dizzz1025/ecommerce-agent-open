import re

from app.llm.base import BaseLLMClient
from app.ml.local_models import LocalModelManager
from app.models.agent import CartAction, IntentPlan, IntentStep, ParsedQuery, PriceRange
from app.models.domain import IntentType, SessionState
from app.repositories.product_repository import ProductRepository


class QueryUnderstandingModule:
    """Hybrid query understanding with Doubao-first planning.

    Only a few strict, low-risk templates are handled locally. All free-form,
    multi-action, vague, or context-dependent Mandarin expressions are routed
    to Doubao for a structured IntentPlan. If the API is unavailable, the old
    rule path remains as a marked fallback so the demo does not crash.
    """

    _feature_terms = [
        "油皮", "混油皮", "干皮", "敏感肌", "痘肌", "控油", "温和", "低刺激", "保湿", "补水", "修护",
        "舒缓", "维稳", "抗初老", "淡纹", "紧致", "提亮", "美白", "防晒", "高倍", "防水", "防汗",
        "水感", "轻薄", "不油腻", "轻量", "轻一点", "轻便", "缓震", "支撑", "耐磨", "回弹",
        "透气", "速干", "凉感", "通勤", "百搭", "显瘦", "宽松", "纯棉", "冰丝", "跑步", "篮球",
        "健身", "瑜伽", "户外", "徒步", "拍照", "自拍", "影像", "长焦", "续航", "快充", "降噪",
        "半入耳", "开放式", "低延迟", "游戏", "办公", "学习", "便携", "护眼", "高刷", "大内存",
        "性价比", "高性价比", "学生党", "实惠", "便宜", "无糖", "低糖", "低卡", "低脂", "提神",
        "速溶", "即食", "早餐", "夜宵", "礼盒", "送礼", "旅行", "旅游", "度假", "三亚", "清爽", "不黏",
        "不粘", "不闷", "大容量", "小巧", "黑色", "白色", "低糖", "新手", "入门",
        "不甜", "无油", "非油炸", "小包装", "咸味", "儿童", "小朋友", "亲子", "分享",
        "基础款", "基础", "纯色", "无印花", "大Logo", "大logo",
        "发圈", "批量", "细头", "不防水", "办公文具", "文具", "收纳", "桌面", "职场新人",
        "底妆", "卡粉", "服帖", "墨水屏", "看书", "备份", "存储", "散热", "补给", "办公室", "低负担",
    ]
    _feature_normalization = {
        "轻一点": "轻量",
        "轻便": "轻量",
        "高性价比": "性价比",
        "实惠": "性价比",
        "便宜": "性价比",
        "不粘": "不黏",
        "不闷": "透气",
        "水感": "轻薄",
        "低卡": "低卡",
        "不甜": "低糖",
        "无油": "无油",
        "非油炸": "无油",
        "小朋友": "儿童",
        "自拍": "拍照",
        "影像": "拍照",
        "长焦": "拍照",
    }
    _negative_terms = [
        "酒精", "香精", "皂基", "糖", "植脂末", "日系", "欧美", "太贵", "贵", "厚重", "油腻",
        "黏腻", "粘腻", "闷", "假滑", "入耳式", "商务", "太小", "太大", "太甜", "辛辣", "咖啡因",
        "耐克", "阿迪", "苹果", "小米", "香味", "香精味", "甜味", "甜", "大包装", "包装太大",
        "糕点", "谷物", "防水", "粗头", "笔头过粗", "紧身", "紧身款", "印花", "印花图案",
        "大Logo", "大logo", "大Logo印花", "大logo印花",
    ]
    _reference_terms = [
        "第一个", "第一款", "第一件", "第1个", "第1款", "第二个", "第二款", "第二件", "第2个", "第2款",
        "第三个", "第三款", "第3个", "第3款", "第四个", "第四款", "第五个", "第五款",
        "刚才那款", "刚才那个", "刚刚那款", "刚刚那个", "前面那款", "前面那个", "上一个", "上一款",
        "这个", "这款", "这一款", "那个", "那款", "它", "它们", "这两个", "这几款", "刚才这几款",
    ]
    _category_aliases = {
        "洗面奶": ("美妆护肤", "洁面"),
        "洁面": ("美妆护肤", "洁面"),
        "男士洗面奶": ("美妆护肤", "男士洁面"),
        "男士洁面": ("美妆护肤", "男士洁面"),
        "精华": ("美妆护肤", "精华"),
        "面霜": ("美妆护肤", "面霜"),
        "防晒": ("美妆护肤", "防晒"),
        "防晒霜": ("美妆护肤", "防晒"),
        "防晒乳": ("美妆护肤", "防晒"),
        "防晒露": ("美妆护肤", "防晒"),
        "防晒喷雾": ("美妆护肤", "防晒喷雾"),
        "眼霜": ("美妆护肤", "眼霜"),
        "粉底": ("美妆护肤", "粉底液"),
        "粉底液": ("美妆护肤", "粉底液"),
        "化妆水": ("美妆护肤", "化妆水"),
        "爽肤水": ("美妆护肤", "化妆水"),
        "水乳": ("美妆护肤", None),
        "卸妆": ("美妆护肤", "卸妆"),
        "卸妆油": ("美妆护肤", "卸妆"),
        "卸妆水": ("美妆护肤", "卸妆"),
        "面膜": ("美妆护肤", "面膜"),
        "唇釉": ("美妆护肤", "唇釉"),
        "口红": ("美妆护肤", "唇釉"),
        "眉笔": ("美妆护肤", "眉笔"),
        "蜜粉": ("美妆护肤", "蜜粉"),
        "散粉": ("美妆护肤", "蜜粉"),
        "护肤品": ("美妆护肤", None),
        "护肤": ("美妆护肤", None),
        "皮肤干": ("美妆护肤", "面霜"),
        "有点干": ("美妆护肤", "面霜"),
        "眼睛累": ("美妆护肤", "眼霜"),
        "眼部": ("美妆护肤", "眼霜"),
        "手机": ("数码电子", "智能手机"),
        "数码产品": ("数码电子", None),
        "数码": ("数码电子", None),
        "数码相机": ("数码电子", None),
        "相机": ("数码电子", None),
        "iphone": ("数码电子", "智能手机"),
        "iPad": ("数码电子", "平板电脑"),
        "ipad": ("数码电子", "平板电脑"),
        "IPad": ("数码电子", "平板电脑"),
        "平板": ("数码电子", "平板电脑"),
        "电脑": ("数码电子", "笔记本电脑"),
        "笔记本": ("数码电子", "笔记本电脑"),
        "耳机": ("数码电子", "真无线耳机"),
        "蓝牙耳机": ("数码电子", "真无线耳机"),
        "无线耳机": ("数码电子", "真无线耳机"),
        "降噪耳机": ("数码电子", "真无线耳机"),
        "跑鞋": ("服饰运动", "跑步鞋"),
        "跑步鞋": ("服饰运动", "跑步鞋"),
        "运动鞋": ("服饰运动", "跑步鞋"),
        "训练鞋": ("服饰运动", "跑步鞋"),
        "健身鞋": ("服饰运动", "跑步鞋"),
        "健身训练鞋": ("服饰运动", "跑步鞋"),
        "篮球鞋": ("服饰运动", "篮球鞋"),
        "徒步鞋": ("服饰运动", "徒步鞋"),
        "背包": ("服饰运动", "背包"),
        "双肩包": ("服饰运动", "背包"),
        "运动帽": ("服饰运动", "帽子"),
        "鸭舌帽": ("服饰运动", "帽子"),
        "棒球帽": ("服饰运动", "帽子"),
        "帽子": ("服饰运动", "帽子"),
        "卫衣": ("服饰运动", "卫衣"),
        "瑜伽裤": ("服饰运动", "瑜伽裤"),
        "运动裤": ("服饰运动", "运动长裤"),
        "运动短裤": ("服饰运动", "运动短裤"),
        "短裤": ("服饰运动", "运动短裤"),
        "户外裤": ("服饰运动", "户外裤"),
        "健身": ("服饰运动", None),
        "运动装备": ("服饰运动", None),
        "t恤": ("服饰运动", "短袖T恤"),
        "T恤": ("服饰运动", "短袖T恤"),
        "短袖": ("服饰运动", "短袖T恤"),
        "速干衣": ("服饰运动", "速干T恤"),
        "速干t恤": ("服饰运动", "速干T恤"),
        "速干T恤": ("服饰运动", "速干T恤"),
        "衣服": ("服饰运动", None),
        "穿搭": ("服饰运动", None),
        # --- 服饰运动 — 上衣/外套类 ---
        "外套": ("服饰运动", None),
        "休闲外套": ("服饰运动", "防晒衣"),
        "夹克": ("服饰运动", None),
        "运动外套": ("服饰运动", None),
        "冲锋衣": ("服饰运动", "冲锋衣"),
        "硬壳": ("服饰运动", "冲锋衣"),
        "羽绒服": ("服饰运动", "羽绒服"),
        "棉服": ("服饰运动", "羽绒服"),
        "大衣": ("服饰运动", None),
        "风衣": ("服饰运动", None),
        "防晒衣": ("服饰运动", "防晒衣"),
        "衬衫": ("服饰运动", "休闲衬衫"),
        "休闲衬衫": ("服饰运动", "休闲衬衫"),
        "牛津纺": ("服饰运动", "休闲衬衫"),
        # --- 服饰运动 — 下装类 ---
        "牛仔裤": ("服饰运动", "牛仔裤"),
        "长裤": ("服饰运动", "运动长裤"),
        "运动袜": ("服饰运动", "运动袜"),
        "袜子": ("服饰运动", "运动袜"),
        "骑行裤": ("服饰运动", "骑行裤"),
        # --- 服饰运动 — 鞋类 ---
        "板鞋": ("服饰运动", "板鞋"),
        "帆布鞋": ("服饰运动", "板鞋"),
        "拖鞋": ("服饰运动", "沙滩拖鞋"),
        "沙滩拖鞋": ("服饰运动", "沙滩拖鞋"),
        "凉拖": ("服饰运动", "沙滩拖鞋"),
        # --- 服饰运动 — 其他装备 ---
        "泳衣": ("服饰运动", "泳衣"),
        "泳装": ("服饰运动", "泳衣"),
        "运动内衣": ("服饰运动", "运动内衣"),
        "连衣裙": ("服饰运动", "连衣裙"),
        "长裙": ("服饰运动", "连衣裙"),
        "裙子": ("服饰运动", "连衣裙"),
        "登山杖": ("服饰运动", "登山杖"),
        "oversize": ("服饰运动", None),
        "大版型": ("服饰运动", None),
        "咖啡": ("食品饮料", "咖啡"),
        "早餐速食": ("食品饮料", "方便食品"),
        "速食早餐": ("食品饮料", "方便食品"),
        "早餐": ("食品饮料", "早餐"),
        "无糖饮料": ("食品饮料", None),
        "低糖饮料": ("食品饮料", None),
        "饮料": ("食品饮料", None),
        "饮品": ("食品饮料", None),
        "喝点什么": ("食品饮料", None),
        "想喝": ("食品饮料", None),
        "喝的": ("食品饮料", None),
        "喝点": ("食品饮料", None),
        "茶": ("食品饮料", "茶饮"),
        "茶饮": ("食品饮料", "茶饮"),
        "气泡水": ("食品饮料", "碳酸饮料"),
        "碳酸饮料": ("食品饮料", "碳酸饮料"),
        "功能饮料": ("食品饮料", "功能饮料"),
        "能量饮料": ("食品饮料", "功能饮料"),
        "零食": ("食品饮料", "坚果/零食"),
        "坚果": ("食品饮料", "坚果/零食"),
        "方便面": ("食品饮料", "方便食品"),
        "方便食品": ("食品饮料", "方便食品"),
        "泡面": ("食品饮料", "方便食品"),
        "调味品": ("食品饮料", "调味品"),
        "酱油": ("食品饮料", "调味品"),
        "牛奶": ("食品饮料", "牛奶"),
        "酸奶": ("食品饮料", "酸奶"),
        "乳酸菌": ("食品饮料", "乳酸菌饮品"),
        "乳酸菌饮品": ("食品饮料", "乳酸菌饮品"),
        "发圈": ("日用百货", "发圈"),
        "头绳": ("日用百货", "发圈"),
        "皮筋": ("日用百货", "发圈"),
        "眼线笔": ("美妆护肤", "眼线笔"),
        "办公文具": ("日用百货", "办公文具"),
        "文具": ("日用百货", "办公文具"),
        "桌面收纳": ("日用百货", "桌面收纳"),
        "收纳": ("日用百货", "桌面收纳"),
        "通勤小物件": ("日用百货", "通勤小物"),
        "通勤小物": ("日用百货", "通勤小物"),
        "礼物": (None, None),
        "洁面乳": ("美妆护肤", "洁面"),
        "洁面啫喱": ("美妆护肤", "洁面"),
        "柔肤水": ("美妆护肤", "化妆水"),
        "神仙水": ("美妆护肤", "化妆水"),
        "乳霜": ("美妆护肤", "面霜"),
        "修复霜": ("美妆护肤", "面霜"),
        "保湿霜": ("美妆护肤", "面霜"),
        "小棕瓶": ("美妆护肤", "精华"),
        "小黑瓶": ("美妆护肤", "精华"),
        "红腰子": ("美妆护肤", "精华"),
        "双抗": ("美妆护肤", "精华"),
        "安瓶": ("美妆护肤", "安瓶"),
        "次抛": ("美妆护肤", "安瓶"),
        "定妆粉": ("美妆护肤", "蜜粉"),
        "粉饼": ("美妆护肤", "蜜粉"),
        "底妆": ("美妆护肤", "底妆"),
        "遮瑕": ("美妆护肤", "底妆"),
        "bb": ("美妆护肤", "BB霜"),
        "BB": ("美妆护肤", "BB霜"),
        "BB霜": ("美妆护肤", "BB霜"),
        "素颜霜": ("美妆护肤", "素颜霜"),
        "隔离": ("美妆护肤", "隔离霜"),
        "防晒隔离": ("美妆护肤", "防晒"),
        "小金管": ("美妆护肤", "防晒"),
        "下午困": ("食品饮料", "咖啡"),
        "困了喝": ("食品饮料", "咖啡"),
        "提神喝": ("食品饮料", "咖啡"),
        "健身后": ("食品饮料", "健身补给"),
        "运动后": ("食品饮料", "健身补给"),
        "补充点东西": ("食品饮料", "健身补给"),
        "运动补给": ("食品饮料", "健身补给"),
        "办公室囤货": ("食品饮料", "坚果/零食"),
        "办公室能囤": ("食品饮料", "坚果/零食"),
        "办公室囤": ("食品饮料", "坚果/零食"),
        "低负担零食": ("食品饮料", "蒟蒻果冻"),
        "低负担": ("食品饮料", "蒟蒻果冻"),
        "低卡零食": ("食品饮料", "蒟蒻果冻"),
        "低卡": ("食品饮料", "蒟蒻果冻"),
        "看书": ("数码电子", "电子书阅读器"),
        "墨水屏": ("数码电子", "电子书阅读器"),
        "不伤眼": ("数码电子", "电子书阅读器"),
        "电子设备": ("数码电子", None),
        "办公学习": ("数码电子", "办公设备"),
        "办公的轻薄设备": ("数码电子", "笔记本电脑"),
        "轻薄设备": ("数码电子", "笔记本电脑"),
        "备份照片": ("数码电子", "移动硬盘"),
        "备份很多照片": ("数码电子", "移动硬盘"),
        "备份资料": ("数码电子", "移动硬盘"),
        "存照片": ("数码电子", "移动硬盘"),
        "移动硬盘": ("数码电子", "移动硬盘"),
        "手机发烫": ("数码电子", "手机散热器"),
        "发烫": ("数码电子", "手机散热器"),
        "手机散热": ("数码电子", "手机散热器"),
        "打游戏": ("数码电子", "手机散热器"),
        "游戏手柄": ("数码电子", "游戏手柄"),
        "游戏鼠标": ("数码电子", "游戏鼠标"),
        "桌面音响": ("数码电子", "蓝牙音箱"),
        "蓝牙音箱": ("数码电子", "蓝牙音箱"),
        "出门充电": ("数码电子", "充电宝"),
        "续航焦虑": ("数码电子", "充电宝"),
        "外套": ("服饰运动", "外套"),
        "休闲外套": ("服饰运动", "外套"),
        "夹克": ("服饰运动", "外套"),
        "运动外套": ("服饰运动", "外套"),
        "裤子": ("服饰运动", "裤子"),
        "瑜伽": ("服饰运动", "瑜伽裤"),
        "包": ("服饰运动", "背包"),
        "旅行穿搭": ("服饰运动", None),
        "健身装备": ("服饰运动", None),
    }
    _brand_aliases = {
        "apple": ["Apple 苹果", "苹果"],
        "苹果": ["Apple 苹果", "苹果"],
        "华为": ["华为"],
        "小米": ["小米"],
        "oppo": ["OPPO"],
        "vivo": ["vivo"],
        "耐克": ["Nike", "耐克"],
        "nike": ["Nike", "耐克"],
        "阿迪": ["阿迪达斯"],
        "阿迪达斯": ["阿迪达斯"],
        "李宁": ["李宁"],
        "安踏": ["安踏"],
        "特步": ["特步"],
        "优衣库": ["优衣库"],
        "北面": ["The North Face", "北面"],
        "north face": ["The North Face", "北面"],
        "科颜氏": ["科颜氏"],
        "理肤泉": ["理肤泉"],
        "薇诺娜": ["薇诺娜"],
        "兰蔻": ["兰蔻"],
        "雅诗兰黛": ["雅诗兰黛"],
        "资生堂": ["资生堂"],
        "安热沙": ["安热沙"],
    }
    _brand_group_aliases = {
        "日系": ["安热沙", "资生堂", "珊珂", "芳珂", "SK-II"],
        "日本": ["安热沙", "资生堂", "珊珂", "芳珂", "SK-II"],
        "欧美": ["雅诗兰黛", "兰蔻", "科颜氏", "巴黎欧莱雅", "The Ordinary", "Apple 苹果"],
        "国货": ["珀莱雅", "薇诺娜", "花西子", "完美日记", "方里", "李宁", "安踏", "特步", "小米", "华为", "OPPO", "vivo"],
    }
    _semantic_intent_examples = {
        IntentType.RECOMMEND.value: ["帮我推荐一款商品", "有什么值得买", "想入手一个", "给我挑一个", "有没有好用的"],
        IntentType.FILTER.value: ["两百以内有哪些", "按预算和品牌筛一下", "有没有符合这些条件的", "价格不要超过"],
        IntentType.REFINE.value: ["再便宜一点", "换一个品牌", "还有别的吗", "不要刚才那个", "想要轻一点"],
        IntentType.COMPARE.value: ["这两个哪个好", "帮我比较一下", "哪款更值得买", "按性价比排一下", "有什么区别"],
        IntentType.DETAIL.value: ["这款续航多久", "是什么材质", "含不含酒精", "能放电脑吗", "库存还有吗"],
        IntentType.SCENE_BUNDLE.value: ["帮我搭配一套", "旅行需要买什么", "健身入门装备", "送礼组合", "开学宿舍用品"],
        IntentType.PREFERENCE.value: ["以后不要推荐", "我一直喜欢", "记住我的偏好", "我平时预算一般"],
    }
    _semantic_category_examples = {
        "美妆护肤|洁面": ["洗面奶 洁面 控油 温和 氨基酸 清洁 油皮"],
        "美妆护肤|防晒": ["防晒霜 防晒乳 清爽 不黏 高倍 户外 通勤"],
        "美妆护肤|面霜": ["面霜 保湿 修护 干皮 屏障 舒缓"],
        "美妆护肤|精华": ["精华 抗初老 淡纹 修护 提亮 维稳"],
        "美妆护肤|眼霜": ["眼霜 眼周 眼睛累 淡纹 黑眼圈"],
        "美妆护肤|面膜": ["面膜 补水 急救 保湿"],
        "数码电子|智能手机": ["手机 拍照 续航 游戏 性价比 快充"],
        "数码电子|真无线耳机": ["蓝牙耳机 无线耳机 降噪 续航 半入耳"],
        "数码电子|平板电脑": ["平板 学习 记笔记 护眼 大屏"],
        "数码电子|笔记本电脑": ["笔记本 电脑 办公 学习 游戏"],
        "服饰运动|跑步鞋": ["跑鞋 跑步鞋 轻量 缓震 慢跑 通勤"],
        "服饰运动|篮球鞋": ["篮球鞋 篮球 支撑 包裹 缓震"],
        "服饰运动|背包": ["双肩包 背包 通勤 旅行 大容量 电脑"],
        "服饰运动|短袖T恤": ["短袖 T恤 穿搭 百搭 透气"],
        "服饰运动|速干T恤": ["速干衣 健身 运动上衣 透气 吸汗"],
        "食品饮料|咖啡": ["咖啡 提神 速溶 黑咖啡 加班"],
        "食品饮料|酸奶": ["酸奶 低糖 早餐 乳酸菌"],
        "食品饮料|牛奶": ["牛奶 早餐 低脂 高钙"],
        "食品饮料|坚果/零食": ["零食 坚果 解馋 办公室"],
        "食品饮料|功能饮料": ["功能饮料 运动 补给 提神"],
        "食品饮料|方便食品": ["早餐 速食 低脂 无油 非甜味 即食 咸味"],
        "食品饮料|乳酸菌饮品": ["儿童 饮料 低糖 小朋友 不含咖啡因 小瓶"],
        "日用百货|发圈": ["发圈 头绳 皮筋 批量 黑色 单价"],
        "日用百货|办公文具": ["办公文具 中性笔 便利贴 文件夹 职场新人 入职"],
        "日用百货|桌面收纳": ["桌面收纳 办公桌 整理盒 分格 收纳"],
        "日用百货|通勤小物": ["通勤小物 卡套 钥匙扣 门禁卡 工牌"],
        "美妆护肤|眼线笔": ["眼线笔 细头 新手 不防水 通勤妆"],
    }
    _scene_bundle_markers = [
        "搭配", "一套", "全套", "方案", "清单", "组合", "配齐", "用品清单", "好物全套",
        "需要买什么", "准备什么", "从", "到",
    ]
    _scene_terms = [
        "西北", "自驾", "户外", "露营", "徒步", "情侣", "海边", "短途海边", "度假",
        "旅行", "三亚", "居家健身", "健身", "职场新人", "入职", "开学", "宿舍", "送礼",
    ]

    def __init__(
        self,
        product_repository: ProductRepository,
        local_models: LocalModelManager | None = None,
        llm_client: BaseLLMClient | None = None,
    ) -> None:
        self.product_repository = product_repository
        self.local_models = local_models
        self.llm_client = llm_client

    def _parse_strict_template(self, message: str, state: SessionState | None = None) -> ParsedQuery | None:
        normalized = message.strip().strip("。！？!? ")
        if not normalized or self._has_complex_intent_signal(normalized):
            return None

        simple_intent = IntentType.RECOMMEND
        target_text = ""
        if match := re.fullmatch(r"推荐(?:一款|一个|一件|一双|一瓶|一盒)?(.{1,24}?)(?:商品|产品)?", normalized):
            target_text = match.group(1).strip()
        elif match := re.fullmatch(r"想要(?:一款|一个|一件|一双|一瓶|一盒)?(.{1,24}?)(?:商品|产品)?", normalized):
            target_text = match.group(1).strip()
        elif match := re.fullmatch(r"选择一款(.{1,24})", normalized):
            target_text = match.group(1).strip()
        elif re.fullmatch(r"预算(?:是|为|:|：)?\s*[^，。,.；;!?！？]{1,16}", normalized):
            simple_intent = IntentType.FILTER if not state or not state.dialogue_state_tracking.current_category else IntentType.REFINE
            target_text = normalized
        else:
            return None

        price_range = self._extract_price_range(target_text)
        brands_include, brands_exclude = self._extract_brands(target_text)
        negative_constraints = self._extract_negative_constraints(target_text)
        positive_constraints = self._extract_positive_constraints(target_text, negative_constraints)
        category, sub_category = self._extract_category(target_text)
        inherit_context = False
        if simple_intent == IntentType.REFINE and state:
            inherit_context = True
            category = category or state.dialogue_state_tracking.current_category
            sub_category = sub_category or state.dialogue_state_tracking.current_sub_category
        if category is None:
            rule_category, rule_sub_category = self._infer_category_from_feature_rules(target_text, positive_constraints)
            category = rule_category
            sub_category = rule_sub_category

        need_clarification, clarification_slots = self._detect_clarification_need(
            intent=simple_intent,
            category=category,
            sub_category=sub_category,
            message=target_text,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            price_range=price_range,
        )
        rewritten_query = self._rewrite_query(
            message=target_text,
            category=category,
            sub_category=sub_category,
            price_range=price_range,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            brands_exclude=brands_exclude,
        )
        confidence = self._estimate_confidence(
            intent=simple_intent,
            category=category,
            sub_category=sub_category,
            price_range=price_range,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            brands_include=brands_include,
            brands_exclude=brands_exclude,
            referents=[],
        )
        plan = IntentPlan(
            primary_intent=simple_intent.value,
            steps=[
                IntentStep(
                    step=1,
                    intent=simple_intent.value,
                    source_text=normalized,
                    requires_retrieval=True,
                )
            ],
            is_multi_intent=False,
            needs_llm_resolution=False,
            resolution_source="strict_template",
            confidence=confidence,
            reason="命中严格本地模板",
        )
        return ParsedQuery(
            raw_message=message,
            intent=simple_intent.value,
            category=category,
            sub_category=sub_category,
            price_range=price_range,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            brands_include=brands_include,
            brands_exclude=brands_exclude,
            scenario=self._extract_scenario(target_text),
            target_user=self._extract_target_user(target_text),
            rewritten_query=rewritten_query,
            need_clarification=need_clarification,
            clarification_slots=clarification_slots,
            inherit_context=inherit_context,
            confidence=confidence,
            route_source="strict_template",
            intent_plan=plan,
        )

    @staticmethod
    def _has_complex_intent_signal(message: str) -> bool:
        """Reject anything beyond the tiny set of safe local templates."""
        complex_markers = [
            "不要", "不含", "不能", "别", "排除", "避开", "除了", "不喜欢", "不想要",
            "拒绝",  # 用户明确拒绝某属性/品类，Doubao 更擅长解析"拒绝XX"结构
            "刚才", "刚刚", "之前", "前面", "上一条", "上次", "购物车", "加购", "下单",
            "结算", "付款", "支付", "对比", "比较", "哪个", "哪款", "详情", "看看",
            "打开", "跳转", "换", "重新", "再", "还有", "便宜", "太贵", "贵了",
            "同时", "顺便", "然后", "并且", "再帮", "也要", "只留下", "只保留",
            "一套", "全套", "清单", "方案", "搭配", "组合", "配齐",
        ]
        if any(marker in message for marker in complex_markers):
            return True
        if re.search(r"[，,；;、].{1,}", message):
            return True
        # Multiple verbs usually means ordering and scope matter; let Doubao plan it.
        verb_like_terms = ["推荐", "想要", "选择", "看看", "加入", "删除", "清空", "比较", "换", "下单", "结算"]
        return sum(1 for term in verb_like_terms if term in message) >= 2

    def _parse_with_llm(self, message: str, state: SessionState | None = None) -> ParsedQuery | None:
        if self.llm_client is None:
            return None
        payload = self.llm_client.resolve_user_intent(self._llm_intent_context(message, state))
        if not payload:
            return None
        return self._parsed_query_from_llm_payload(payload, message, state)

    def parse(self, message: str, state: SessionState | None = None) -> ParsedQuery:
        normalized = message.strip()
        strict = self._parse_strict_template(normalized, state)
        if strict is not None:
            return strict

        llm_parsed = self._parse_with_llm(normalized, state)
        if llm_parsed is not None:
            return llm_parsed

        # Doubao/API failure fallback. This path is intentionally conservative
        # and marked in route_source so it is visible in debug output.
        fallback = self._parse_legacy_rule(message, state)
        fallback.route_source = f"{fallback.route_source}+llm_failed_rule_fallback"
        fallback.uncertain_points.append("Doubao 意图解析不可用，已降级到本地规则")
        return fallback

    def _parse_legacy_rule(self, message: str, state: SessionState | None = None) -> ParsedQuery:
        normalized = message.strip()
        intent = self._detect_intent(normalized)
        route_sources = ["rule"]
        semantic_intent, semantic_intent_score = self._infer_intent_with_small_model(normalized, intent)
        if semantic_intent is not None:
            intent = semantic_intent
            route_sources.append(f"text2vec_intent:{semantic_intent_score:.3f}")
        llm_intent, llm_intent_score = self._resolve_complex_intent_with_llm(normalized, intent, state)
        if llm_intent is not None:
            intent = llm_intent
            route_sources.append(f"doubao_intent:{llm_intent_score:.3f}")
        price_range = self._extract_price_range(normalized)
        brands_include, brands_exclude = self._extract_brands(normalized)
        negative_constraints = self._extract_negative_constraints(normalized)
        positive_constraints = self._extract_positive_constraints(normalized, negative_constraints)
        category, sub_category = self._extract_category(normalized)
        explicit_category = category is not None
        if intent == IntentType.SCENE_BUNDLE and explicit_category and not self._has_scene_bundle_command(normalized):
            intent = IntentType.RECOMMEND if not any(term in normalized for term in ["重新", "再", "换", "继续"]) else IntentType.REFINE
            route_sources.append("scene_demoted_explicit_product")
        topic_locked = self._should_lock_current_topic(
            message=normalized,
            state=state,
            intent=intent,
            explicit_category=explicit_category,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            price_range=price_range,
        )
        if topic_locked and state:
            previous = state.dialogue_state_tracking
            category = previous.current_category
            sub_category = previous.current_sub_category
            route_sources.append("context_topic_lock")
        elif category is None:
            rule_category, rule_sub_category = self._infer_category_from_feature_rules(normalized, positive_constraints)
            if rule_category:
                category = rule_category
                sub_category = rule_sub_category
                route_sources.append("rule_feature_category")
        if (category is None or sub_category is None) and intent not in {
            IntentType.CART_ADD,
            IntentType.CART_REMOVE,
            IntentType.CART_UPDATE,
            IntentType.CART_CLEAR,
            IntentType.CART_VIEW,
            IntentType.CART_KEEP_ONLY,
            IntentType.CHECKOUT,
            IntentType.PREFERENCE,
        }:
            semantic_category, semantic_sub_category, semantic_category_score = self._infer_category_with_small_model(normalized)
            if semantic_category and (category is None or sub_category is None):
                if state and state.dialogue_state_tracking.current_category and not explicit_category:
                    current_category = state.dialogue_state_tracking.current_category
                    if semantic_category != current_category and self._has_topic_continuity_signal(
                        normalized,
                        intent,
                        positive_constraints,
                        negative_constraints,
                        price_range,
                        state,
                    ):
                        category = current_category
                        sub_category = state.dialogue_state_tracking.current_sub_category
                        route_sources.append(f"context_topic_lock_ignored_text2vec:{semantic_category_score:.3f}")
                    else:
                        category = category or semantic_category
                        sub_category = sub_category or semantic_sub_category
                        route_sources.append(f"text2vec_category:{semantic_category_score:.3f}")
                else:
                    category = category or semantic_category
                    sub_category = sub_category or semantic_sub_category
                    route_sources.append(f"text2vec_category:{semantic_category_score:.3f}")
        referents = [term for term in self._reference_terms if term in normalized]
        cart_action = self._extract_cart_action(normalized, intent, referents)
        compare_targets = self._extract_compare_targets(normalized, referents) if intent == IntentType.COMPARE else []
        scenario = self._extract_scenario(normalized)
        target_user = self._extract_target_user(normalized)
        mentioned_products = self._extract_mentioned_products(normalized)

        inherit_context = topic_locked or self._should_inherit_context(normalized, category if explicit_category else None, state, intent)
        if inherit_context and state:
            previous = state.dialogue_state_tracking
            category = category or previous.current_category
            sub_category = sub_category or previous.current_sub_category

        confidence = self._estimate_confidence(
            intent=intent,
            category=category,
            sub_category=sub_category,
            price_range=price_range,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            brands_include=brands_include,
            brands_exclude=brands_exclude,
            referents=referents,
        )
        need_clarification, clarification_slots = self._detect_clarification_need(
            intent=intent,
            category=category,
            sub_category=sub_category,
            message=normalized,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            price_range=price_range,
        )

        rewritten_query = self._rewrite_query(
            message=normalized,
            category=category,
            sub_category=sub_category,
            price_range=price_range,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            brands_exclude=brands_exclude,
        )
        return ParsedQuery(
            raw_message=message,
            intent=intent.value,
            category=category,
            sub_category=sub_category,
            price_range=price_range,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            brands_include=brands_include,
            brands_exclude=brands_exclude,
            compare_targets=compare_targets,
            cart_action=cart_action,
            referents=referents,
            mentioned_products=mentioned_products,
            scenario=scenario,
            target_user=target_user,
            sub_intent=self._sub_intent(intent, normalized),
            rewritten_query=rewritten_query,
            need_clarification=need_clarification,
            clarification_slots=clarification_slots,
            inherit_context=inherit_context,
            confidence=confidence,
            route_source="+".join(route_sources),
            intent_plan=self._build_intent_plan(normalized, intent, route_sources),
        )

    def _llm_intent_context(self, message: str, state: SessionState | None) -> dict:
        taxonomy: dict[str, set[str]] = {}
        for product in self.product_repository.list_products():
            taxonomy.setdefault(product.category, set())
            if product.sub_category:
                taxonomy[product.category].add(product.sub_category)
        return {
            "message": message,
            "available_intents": [intent.value for intent in IntentType],
            "available_categories": {category: sorted(subs) for category, subs in sorted(taxonomy.items())},
            "supported_actions": {
                "recommend": "推荐或重新推荐真实商品",
                "filter": "按预算、品牌、类目、属性筛选商品",
                "refine": "在上一轮主题上补充或修改条件并重新推荐",
                "compare": "比较最近推荐、购物车或用户点名的商品",
                "detail": "查看/解释某个商品详情",
                "scene_bundle": "用户明确要求一套、全套、清单、方案、组合搭配时才使用",
                "preference": "用户明确要求长期记住偏好",
                "cart_add": "加入购物车",
                "cart_remove": "删除购物车商品",
                "cart_update": "修改购物车数量",
                "cart_clear": "清空购物车",
                "cart_view": "查看购物车",
                "cart_keep_only": "购物车只保留某些商品",
                "checkout": "结算、下单、付款、计算总价",
            },
            "current_state": {
                "current_category": state.dialogue_state_tracking.current_category if state else None,
                "current_sub_category": state.dialogue_state_tracking.current_sub_category if state else None,
                "active_constraints": state.dialogue_state_tracking.active_constraints if state else {},
                "missing_slots": state.dialogue_state_tracking.missing_slots if state else [],
            },
            "last_recommendations": [
                {
                    "rank": item.rank,
                    "sku_id": item.sku_id,
                    "name": item.name,
                    "category": item.category,
                    "price": item.price,
                }
                for item in (state.goods.last_recommendations[:5] if state else [])
            ],
            "cart_items": [
                {"sku_id": item.sku_id, "quantity": item.quantity}
                for item in (state.cart.items if state else [])
            ],
            "rules": [
                "当前用户明说的本轮需求优先于历史状态。",
                "如果用户明确说某个单品类目，例如背包、手机、耳机、防晒、短袖，通常不要改成 scene_bundle。",
                "只有出现一套、全套、清单、方案、搭配、组合、配齐等组合表达时，才使用 scene_bundle。",
                "刚才加购的、之前买的、购物车里的这类表达是历史描述，不等于当前要 cart_add。",
                "一句话有多个动作时，请按真实执行顺序输出 intent_plan.steps。",
                "购物车工具相关动作必须只使用支持的 cart_* 或 checkout intent。",
            ],
        }

    def _parsed_query_from_llm_payload(
        self,
        payload: dict,
        message: str,
        state: SessionState | None,
    ) -> ParsedQuery | None:
        intent = self._coerce_intent(payload.get("primary_intent") or payload.get("intent"))
        if intent is None:
            return None

        scope = payload.get("product_scope") if isinstance(payload.get("product_scope"), dict) else {}
        category = _none_if_empty(payload.get("category") or payload.get("product_category") or scope.get("category"))
        sub_category = _none_if_empty(payload.get("sub_category") or payload.get("product_sub_category") or scope.get("sub_category"))
        intent_plan = self._intent_plan_from_payload(payload, intent, message)
        retrieval_step_source = self._last_retrieval_step_source(intent_plan)
        local_scope_source = _combine_scope_text(retrieval_step_source, message)

        explicit_category, explicit_sub_category = self._extract_category(local_scope_source)
        new_explicit_scope = bool(
            state
            and explicit_sub_category
            and state.dialogue_state_tracking.current_sub_category
            and explicit_sub_category != state.dialogue_state_tracking.current_sub_category
        )
        if explicit_category and (not category or category != explicit_category):
            category = explicit_category
            sub_category = explicit_sub_category
        elif explicit_category and explicit_sub_category and sub_category != explicit_sub_category:
            # The user's own words are the hard scope. Doubao may generalize
            # "手机发烫" to "智能手机", but inventory retrieval should keep the
            # more specific local alias "手机散热器".
            sub_category = explicit_sub_category
        elif explicit_sub_category and not sub_category:
            sub_category = explicit_sub_category
        category, sub_category = self._normalize_llm_category_scope(category, sub_category)
        if (
            sub_category is None
            and explicit_category
            and explicit_sub_category
            and category == explicit_category
        ):
            # Keep a user-explicit but currently out-of-stock sub-category
            # (e.g. 连衣裙) so retrieval can report exact-miss and surface
            # grounded same-domain alternatives instead of asking a vague
            # clarification question.
            sub_category = explicit_sub_category
        if intent == IntentType.COMPARE and not self._message_has_real_compare_signal(message):
            intent = IntentType.REFINE if state and state.dialogue_state_tracking.current_category else IntentType.RECOMMEND
        if intent == IntentType.SCENE_BUNDLE and explicit_category and not self._has_scene_bundle_command(message):
            intent = IntentType.REFINE if any(term in message for term in ["重新", "再", "换", "继续"]) else IntentType.RECOMMEND
        if (
            intent == IntentType.CLARIFY
            and category
            and (
                sub_category
                or self._extract_price_range(message).min is not None
                or self._extract_price_range(message).max is not None
            )
            and any(term in message for term in ["推荐", "想要", "想买", "买", "选择", "挑", "找"])
        ):
            intent = IntentType.FILTER if (self._extract_price_range(message).min is not None or self._extract_price_range(message).max is not None) else IntentType.RECOMMEND
        if (
            intent == IntentType.CLARIFY
            and category
            and sub_category
            and explicit_category
            and any(term in message for term in ["推荐", "想要", "想买", "想看", "看看", "看一下", "买", "选择", "挑", "找"])
        ):
            intent = IntentType.REFINE if state and state.dialogue_state_tracking.current_category else IntentType.RECOMMEND

        price_range = self._price_range_from_payload(payload.get("price_range"))
        local_price = self._extract_price_range(local_scope_source)
        price_range.min = price_range.min if price_range.min is not None else local_price.min
        price_range.max = price_range.max if price_range.max is not None else local_price.max
        if new_explicit_scope and local_price.min is None and local_price.max is None:
            price_range = PriceRange()

        positive_constraints = _safe_str_list(payload.get("positive_constraints") or payload.get("features"))
        negative_constraints = _normalize_negative_constraints(_safe_str_list(payload.get("negative_constraints")))
        brands_include = _safe_str_list(payload.get("brands_include"))
        brands_exclude = _safe_str_list(payload.get("brands_exclude"))
        compare_targets = _safe_str_list(payload.get("compare_targets"))
        referents = _safe_str_list(payload.get("referents"))
        mentioned_products = _safe_str_list(payload.get("mentioned_products"))

        negative_constraints = _normalize_negative_constraints(
            _merge_unique(negative_constraints, self._extract_negative_constraints(local_scope_source))
        )
        local_include, local_exclude = self._extract_brands(local_scope_source)
        brands_include = _merge_unique(brands_include, local_include)
        brands_exclude = _merge_unique(brands_exclude, local_exclude)
        if new_explicit_scope and not local_include:
            brands_include = []
        local_positive_constraints = self._extract_positive_constraints(local_scope_source, negative_constraints)
        if new_explicit_scope and local_positive_constraints:
            positive_constraints = local_positive_constraints
        elif not positive_constraints:
            positive_constraints = local_positive_constraints
        elif local_positive_constraints:
            positive_constraints = _merge_unique(positive_constraints, local_positive_constraints)
        if category is None or sub_category is None:
            rule_category, rule_sub_category = self._infer_category_from_feature_rules(local_scope_source, positive_constraints)
            category = category or rule_category
            sub_category = sub_category or rule_sub_category
        if intent == IntentType.CHITCHAT and (
            category
            or sub_category
            or positive_constraints
            or negative_constraints
            or _looks_like_shopping_recommendation(message)
        ):
            intent = IntentType.REFINE if state and state.dialogue_state_tracking.current_category and not explicit_category else IntentType.RECOMMEND

        inherit_context = bool(payload.get("inherit_context", False))
        if inherit_context and state:
            category = category or state.dialogue_state_tracking.current_category
            sub_category = sub_category or state.dialogue_state_tracking.current_sub_category
        if intent in {IntentType.REFINE, IntentType.FILTER, IntentType.COMPARE, IntentType.DETAIL} and category is None and state:
            category = state.dialogue_state_tracking.current_category
            sub_category = state.dialogue_state_tracking.current_sub_category
            inherit_context = True
        topic_locked = False
        if (
            not explicit_category
            and state
            and state.dialogue_state_tracking.current_category
            and intent
            not in {
                IntentType.CART_ADD,
                IntentType.CART_REMOVE,
                IntentType.CART_UPDATE,
                IntentType.CART_CLEAR,
                IntentType.CART_VIEW,
                IntentType.CART_KEEP_ONLY,
                IntentType.CHECKOUT,
                IntentType.CHITCHAT,
                IntentType.OUT_OF_SCOPE,
                IntentType.INVALID,
                IntentType.SCENE_BUNDLE,
            }
            and self._has_topic_continuity_signal(
                message,
                intent,
                positive_constraints,
                negative_constraints,
                price_range,
                state,
            )
        ):
            previous = state.dialogue_state_tracking
            if category is None or category == previous.current_category:
                category = previous.current_category
                sub_category = previous.current_sub_category or sub_category
                inherit_context = True
                topic_locked = True

        cart_action = self._cart_action_from_payload(payload.get("cart_action"), intent, referents, message)
        if cart_action and intent_plan:
            matching_step = next(
                (
                    step
                    for step in intent_plan.steps
                    if step.intent == cart_action.action and step.quantity is not None
                ),
                None,
            )
            if matching_step is not None and matching_step.quantity is not None:
                cart_action.quantity = matching_step.quantity
        scenario = _none_if_empty(payload.get("scenario")) or self._extract_scenario(local_scope_source)
        target_user = _none_if_empty(payload.get("target_user")) or self._extract_target_user(local_scope_source)
        confidence = _clamp_float(payload.get("confidence"), default=0.82)

        need_clarification = bool(payload.get("need_clarification", False))
        clarification_slots = _safe_str_list(payload.get("clarification_slots"))
        if not need_clarification:
            need_clarification, clarification_slots = self._detect_clarification_need(
                intent=intent,
                category=category,
                sub_category=sub_category,
                message=local_scope_source,
                positive_constraints=positive_constraints,
                negative_constraints=negative_constraints,
                price_range=price_range,
            )
        if need_clarification and category and sub_category and set(clarification_slots).issubset({"category", "sub_category_or_scene"}):
            need_clarification = False
            clarification_slots = []
        if need_clarification and category and sub_category and intent in {IntentType.RECOMMEND, IntentType.FILTER, IntentType.REFINE}:
            need_clarification = False
            clarification_slots = []
        if need_clarification and category and (positive_constraints or negative_constraints or scenario) and intent in {IntentType.RECOMMEND, IntentType.FILTER, IntentType.REFINE, IntentType.SCENE_BUNDLE}:
            need_clarification = False
            clarification_slots = []

        rewritten_query = str(payload.get("rewritten_query") or "").strip() or self._rewrite_query(
            message=local_scope_source,
            category=category,
            sub_category=sub_category,
            price_range=price_range,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            brands_exclude=brands_exclude,
        )
        return ParsedQuery(
            raw_message=message,
            intent=intent.value,
            category=category,
            sub_category=sub_category,
            price_range=price_range,
            positive_constraints=positive_constraints,
            negative_constraints=negative_constraints,
            brands_include=brands_include,
            brands_exclude=brands_exclude,
            compare_targets=compare_targets,
            cart_action=cart_action,
            referents=referents,
            mentioned_products=mentioned_products,
            scenario=scenario,
            target_user=target_user,
            sub_intent=self._sub_intent(intent, message),
            rewritten_query=rewritten_query,
            need_clarification=need_clarification,
            clarification_slots=clarification_slots,
            inherit_context=inherit_context,
            confidence=confidence,
            route_source="doubao_intent_plan+context_topic_lock" if topic_locked else "doubao_intent_plan",
            uncertain_points=_safe_str_list(payload.get("uncertain_points")),
            intent_plan=intent_plan,
        )

    def _cart_action_from_payload(
        self,
        payload: object,
        intent: IntentType,
        referents: list[str],
        message: str,
    ) -> CartAction | None:
        if intent not in {
            IntentType.CART_ADD,
            IntentType.CART_REMOVE,
            IntentType.CART_UPDATE,
            IntentType.CART_CLEAR,
            IntentType.CART_VIEW,
            IntentType.CART_KEEP_ONLY,
            IntentType.CHECKOUT,
        }:
            return None
        data = payload if isinstance(payload, dict) else {}
        target_ref = _none_if_empty(data.get("target_ref")) or (referents[0] if referents else None)
        quantity = data.get("quantity")
        try:
            quantity = int(quantity) if quantity is not None else None
        except (TypeError, ValueError):
            quantity = None
        category, sub_category = self._extract_category(message)
        return CartAction(
            action=str(data.get("action") or intent.value),
            quantity=quantity,
            target_ref=target_ref,
            sku_id=_none_if_empty(data.get("sku_id")),
            keep_categories=_safe_str_list(data.get("keep_categories") or ([category] if category and not sub_category else [])),
            keep_sub_categories=_safe_str_list(data.get("keep_sub_categories") or ([sub_category] if sub_category else [])),
            exclude_sku_ids=_safe_str_list(data.get("exclude_sku_ids")),
        )

    def _intent_plan_from_payload(self, payload: dict, intent: IntentType, message: str) -> IntentPlan:
        plan_payload = payload.get("intent_plan") if isinstance(payload.get("intent_plan"), dict) else {}
        raw_steps = plan_payload.get("steps") or payload.get("intent_sequence") or []
        steps: list[IntentStep] = []
        if isinstance(raw_steps, list):
            for index, item in enumerate(raw_steps, start=1):
                if isinstance(item, str):
                    step_intent = self._coerce_intent(item)
                    source_text = item
                    target_ref = self._first_reference_in_message(message)
                elif isinstance(item, dict):
                    step_intent = self._coerce_intent(item.get("intent") or item.get("action"))
                    source_text = str(item.get("source_text") or item.get("text") or "")
                    target_ref = _none_if_empty(item.get("target_ref")) or self._first_reference_in_message(message)
                    quantity = _optional_int(item.get("quantity"))
                    sku_id = _none_if_empty(item.get("sku_id"))
                    keep_categories = _safe_str_list(item.get("keep_categories"))
                    keep_sub_categories = _safe_str_list(item.get("keep_sub_categories"))
                    exclude_sku_ids = _safe_str_list(item.get("exclude_sku_ids"))
                else:
                    continue
                if step_intent is None:
                    continue
                if not isinstance(item, dict):
                    quantity = None
                    sku_id = None
                    keep_categories = []
                    keep_sub_categories = []
                    exclude_sku_ids = []
                if quantity is None and step_intent in {IntentType.CART_ADD, IntentType.CART_UPDATE}:
                    quantity = _quantity_from_text(source_text or message)
                steps.append(
                    IntentStep(
                        step=index,
                        intent=step_intent.value,
                        action=step_intent.value,
                        source_text=source_text or message,
                        target_ref=target_ref,
                        quantity=quantity,
                        sku_id=sku_id,
                        keep_categories=keep_categories,
                        keep_sub_categories=keep_sub_categories,
                        exclude_sku_ids=exclude_sku_ids,
                        requires_tool=step_intent in {
                            IntentType.CART_ADD,
                            IntentType.CART_REMOVE,
                            IntentType.CART_UPDATE,
                            IntentType.CART_CLEAR,
                            IntentType.CART_VIEW,
                            IntentType.CART_KEEP_ONLY,
                            IntentType.CHECKOUT,
                        },
                        requires_retrieval=step_intent in {
                            IntentType.RECOMMEND,
                            IntentType.FILTER,
                            IntentType.REFINE,
                            IntentType.COMPARE,
                            IntentType.DETAIL,
                            IntentType.SCENE_BUNDLE,
                        },
                    )
                )
        if not steps:
            return self._build_intent_plan(message, intent, ["doubao_intent_plan"])
        for index, step in enumerate(steps, start=1):
            steps[index - 1] = step.model_copy(update={"step": index})
        return IntentPlan(
            primary_intent=intent.value,
            steps=steps,
            is_multi_intent=len(steps) > 1,
            needs_llm_resolution=True,
            resolution_source="doubao",
            confidence=_clamp_float(plan_payload.get("confidence") or payload.get("confidence"), default=0.82),
            reason=str(plan_payload.get("reason") or payload.get("reason") or "Doubao 结构化意图计划"),
        )

    @staticmethod
    def _coerce_intent(value: object) -> IntentType | None:
        if value is None:
            return None
        try:
            return IntentType(str(value))
        except ValueError:
            return None

    @staticmethod
    def _last_retrieval_step_source(intent_plan: IntentPlan | None) -> str | None:
        if intent_plan is None:
            return None
        retrieval_intents = {
            IntentType.RECOMMEND.value,
            IntentType.FILTER.value,
            IntentType.REFINE.value,
            IntentType.COMPARE.value,
            IntentType.DETAIL.value,
            IntentType.SCENE_BUNDLE.value,
        }
        for step in reversed(intent_plan.steps):
            if step.intent in retrieval_intents and step.source_text.strip():
                return step.source_text.strip()
        return None

    @staticmethod
    def _price_range_from_payload(payload: object) -> PriceRange:
        if not isinstance(payload, dict):
            return PriceRange()
        return PriceRange(
            min=_optional_float(payload.get("min")),
            max=_optional_float(payload.get("max")),
        )

    def _normalize_llm_category_scope(
        self,
        category: str | None,
        sub_category: str | None,
    ) -> tuple[str | None, str | None]:
        products = self.product_repository.list_products()
        main_categories = {product.category for product in products}
        sub_to_main = {
            product.sub_category: product.category
            for product in products
            if product.sub_category
        }
        virtual_sub_to_main = {
            "底妆": "美妆护肤",
            "外套": "服饰运动",
            "运动鞋": "服饰运动",
            "裤子": "服饰运动",
            "饮料": "食品饮料",
            "早餐": "食品饮料",
            "健身补给": "食品饮料",
            "办公设备": "数码电子",
        }
        if category in sub_to_main and sub_category is None:
            return sub_to_main[category], category
        if category in virtual_sub_to_main and sub_category is None:
            return virtual_sub_to_main[category], category
        if category is not None and category not in main_categories:
            category = None
        if sub_category is not None:
            owner = sub_to_main.get(sub_category) or virtual_sub_to_main.get(sub_category)
            if owner is None:
                sub_category = None
            elif category is None:
                category = owner
            elif owner != category:
                sub_category = None
        return category, sub_category

    def _detect_intent(self, message: str) -> IntentType:
        lowered = message.lower()
        if any(token in message for token in ["清空购物车", "购物车清空", "全删了", "都不要了"]):
            return IntentType.CART_CLEAR
        if any(token in message for token in ["只留下", "只保留", "只要购物车里的", "购物车只留", "其他都不要", "别的都删"]):
            return IntentType.CART_KEEP_ONLY
        if any(token in message for token in ["移出购物车", "删除购物车", "从购物车删", "删掉", "删除", "不要购物车里", "先别买", "先不要这个", "这个不要了", "不要了"]):
            return IntentType.CART_REMOVE
        if any(token in message for token in ["数量改", "改成", "修改数量", "加到", "减到", "改为", "改两", "改三", "买两", "买三"]):
            return IntentType.CART_UPDATE
        if any(token in message for token in ["购物车有什么", "查看购物车", "看看购物车", "购物车里有什么", "购物车列表", "我加了什么"]):
            return IntentType.CART_VIEW
        if any(token in message for token in ["下单", "结算", "提交订单", "地址用默认", "直接买", "去支付", "付款", "支付", "算出总价格", "总价格", "一共多少钱"]):
            return IntentType.CHECKOUT
        if self._has_cart_add_command(message):
            return IntentType.CART_ADD
        if any(token in message for token in ["以后", "之后", "长期", "记住", "预算一般", "平时", "通常", "以后都", "我一直", "我通常", "我平时", "经常"]):
            return IntentType.PREFERENCE
        if any(token in lowered for token in ["compare", " vs ", "vs", "pk"]) or any(token in message for token in ["对比", "比较一下", "帮我比较", "比较第", "比较这", "比较那", "哪个更", "哪款更", "哪个最", "哪款最", "谁更", "哪个好", "哪个好喝", "最好喝", "最适合", "区别", "差别", "排序", "排一下", "值不值", "更值得"]):
            return IntentType.COMPARE
        if any(token in message for token in ["详情", "参数", "规格", "介绍", "介绍下", "介绍一下", "讲讲", "说说", "展开说", "具体说说", "怎么样", "值得买吗", "适合敏感肌吗", "续航多久", "电池", "什么材质", "面料", "成分", "配料", "含酒精吗", "低糖版本", "保质期", "能放", "容量", "尺寸", "适合新手", "库存", "现货", "有货", "口味", "颜色"]):
            return IntentType.DETAIL
        if self._has_scene_bundle_command(message):
            return IntentType.SCENE_BUNDLE
        if any(token in message for token in ["便宜点", "再便宜", "贵了", "太贵", "好贵", "超出预算", "超预算", "不合适", "不喜欢", "换个", "换一个", "还有别的", "还有其他", "别的呢", "不要", "不含", "避开", "排除", "除了", "轻一点", "大一点", "小一点"]):
            return IntentType.REFINE
        if any(token in message for token in ["以下", "以内", "之内", "不超过", "别超过", "低于", "少于", "预算", "价位", "价格", "筛选", "控制在"]):
            return IntentType.FILTER
        if any(token in message for token in ["你好", "您好", "谢谢", "多谢", "辛苦", "你是谁", "你能做什么", "你能干嘛"]) and not any(alias in message for alias in self._category_aliases):
            return IntentType.CHITCHAT
        return IntentType.RECOMMEND

    def _resolve_complex_intent_with_llm(
        self,
        message: str,
        rule_intent: IntentType,
        state: SessionState | None,
    ) -> tuple[IntentType | None, float]:
        if self.llm_client is None or not self._needs_llm_intent_resolution(message, rule_intent):
            return None, 0.0
        payload = self.llm_client.resolve_user_intent(
            {
                "message": message,
                "rule_intent": rule_intent.value,
                "current_category": state.dialogue_state_tracking.current_category if state else None,
                "current_sub_category": state.dialogue_state_tracking.current_sub_category if state else None,
                "cart_items": [
                    {
                        "sku_id": item.sku_id,
                        "quantity": item.quantity,
                    }
                    for item in (state.cart.items if state else [])
                ],
                "last_recommendations": [
                    {
                        "rank": item.rank,
                        "sku_id": item.sku_id,
                        "name": item.name,
                        "category": item.category,
                    }
                    for item in (state.goods.last_recommendations[:5] if state else [])
                ],
            }
        )
        if not payload or not payload.get("should_override_rule"):
            return None, 0.0
        try:
            confidence = float(payload.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < 0.75:
            return None, confidence
        intent_value = str(payload.get("primary_intent") or "")
        try:
            return IntentType(intent_value), confidence
        except ValueError:
            return None, confidence

    def _build_intent_plan(
        self,
        message: str,
        primary_intent: IntentType,
        route_sources: list[str],
    ) -> IntentPlan:
        signal_groups = self._cart_intent_signal_groups(message)
        if signal_groups.get(IntentType.CART_CLEAR.value):
            signal_groups[IntentType.CART_REMOVE.value] = []
        located_steps: list[tuple[int, IntentStep]] = []
        for intent in [
            IntentType.CART_CLEAR,
            IntentType.CART_KEEP_ONLY,
            IntentType.CART_REMOVE,
            IntentType.CART_UPDATE,
            IntentType.CART_ADD,
            IntentType.CHECKOUT,
            IntentType.CART_VIEW,
        ]:
            signals = signal_groups.get(intent.value, [])
            if not signals:
                continue
            first_position = min((message.find(signal) for signal in signals if message.find(signal) >= 0), default=9999)
            located_steps.append(
                (
                    first_position,
                    IntentStep(
                        step=0,
                        intent=intent.value,
                        action=intent.value,
                        source_text="、".join(signals),
                        target_ref=self._first_reference_in_message(message),
                        requires_tool=True,
                        requires_retrieval=False,
                    ),
                )
            )
        located_steps.sort(key=lambda item: item[0])
        steps = [item[1] for item in located_steps]
        if any(step.intent == IntentType.CHECKOUT.value for step in steps) and len(steps) > 1:
            steps = [step for step in steps if step.intent != IntentType.CHECKOUT.value] + [
                step for step in steps if step.intent == IntentType.CHECKOUT.value
            ]
        if any(step.intent == IntentType.CART_VIEW.value for step in steps) and len(steps) > 1:
            steps = [step for step in steps if step.intent != IntentType.CART_VIEW.value] + [
                step for step in steps if step.intent == IntentType.CART_VIEW.value
            ]
        for index, step in enumerate(steps, start=1):
            steps[index - 1] = step.model_copy(update={"step": index})
        if not steps:
            steps.append(
                IntentStep(
                    step=1,
                    intent=primary_intent.value,
                    source_text=message,
                    requires_tool=primary_intent in {
                        IntentType.CART_ADD,
                        IntentType.CART_REMOVE,
                        IntentType.CART_UPDATE,
                        IntentType.CART_CLEAR,
                        IntentType.CART_VIEW,
                        IntentType.CART_KEEP_ONLY,
                        IntentType.CHECKOUT,
                    },
                    requires_retrieval=primary_intent in {
                        IntentType.RECOMMEND,
                        IntentType.FILTER,
                        IntentType.REFINE,
                        IntentType.COMPARE,
                        IntentType.DETAIL,
                        IntentType.SCENE_BUNDLE,
                    },
                )
            )
        return IntentPlan(
            primary_intent=primary_intent.value,
            steps=steps,
            is_multi_intent=len(steps) > 1,
            needs_llm_resolution="doubao_intent" in "+".join(route_sources),
            resolution_source="doubao" if "doubao_intent" in "+".join(route_sources) else "rule",
            confidence=0.86 if len(steps) == 1 else 0.78,
            reason="多动作组合意图" if len(steps) > 1 else "单一主意图",
        )

    def _first_reference_in_message(self, message: str) -> str | None:
        for ref in self._reference_terms:
            if ref in message:
                return ref
        return None

    @classmethod
    def _needs_llm_intent_resolution(cls, message: str, rule_intent: IntentType) -> bool:
        signal_groups = cls._cart_intent_signal_groups(message)
        has_multiple_cart_signals = sum(bool(items) for items in signal_groups.values()) >= 2
        has_sequence_marker = any(marker in message for marker in ["然后", "再", "并且", "同时", "顺便", "，", "；", "后"])
        has_history_add_phrase = any(term in message for term in ["刚才加购的", "刚刚加购的", "之前加购的", "已经加购的"])
        return has_multiple_cart_signals or (has_sequence_marker and has_history_add_phrase and rule_intent == IntentType.CART_ADD)

    @classmethod
    def _cart_intent_signal_groups(cls, message: str) -> dict[str, list[str]]:
        signals = {
            "cart_clear": ["清空购物车", "购物车清空", "全删了", "都不要了"],
            "cart_keep_only": ["只留下", "只保留", "购物车只留", "其他都不要", "别的都删"],
            "cart_remove": ["移出购物车", "删除购物车", "从购物车删", "删掉", "删除", "不要购物车里", "这个不要了", "不要了"],
            "cart_update": ["数量改", "修改数量", "改为", "改两", "改三", "买两", "买三"],
            "cart_view": ["查看购物车", "看看购物车", "购物车里有什么"],
            "checkout": ["下单", "结算", "提交订单", "去支付", "付款", "支付"],
            "cart_add": ["加入购物车", "加购物车", "加到购物车", "加入到购物车", "放购物车", "放进购物车", "放到购物车", "买这个", "要这个", "拿下", "来一件", "来一份"],
        }
        grouped: dict[str, list[str]] = {}
        for intent, terms in signals.items():
            grouped[intent] = [term for term in terms if term in message]
        if "加购" in message and not any(term in message for term in ["刚才加购的", "刚刚加购的", "之前加购的", "已经加购的"]):
            grouped["cart_add"].append("加购")
        return grouped

    @classmethod
    def _has_cart_add_command(cls, message: str) -> bool:
        return bool(cls._cart_intent_signal_groups(message).get("cart_add"))

    @classmethod
    def _has_scene_bundle_command(cls, message: str) -> bool:
        has_marker = any(marker in message for marker in cls._scene_bundle_markers)
        has_scene = any(term in message for term in cls._scene_terms)
        has_multi_category = sum(
            1
            for group in [
                ["穿搭", "衣服", "短袖", "裤", "鞋", "帽子", "背包"],
                ["护肤", "防晒", "洁面", "面霜", "精华"],
                ["随身", "好物", "收纳", "耳机", "手机", "平板"],
                ["饮料", "零食", "补给", "早餐"],
            ]
            if any(term in message for term in group)
        ) >= 2
        explicit_single_product = any(term in message for term in ["一款", "一个", "一只", "一双", "一件"]) and not has_multi_category
        if explicit_single_product and not has_marker:
            return False
        return (has_marker and (has_scene or has_multi_category)) or ("全套" in message and has_multi_category)

    def _extract_price_range(self, message: str) -> PriceRange:
        price_min = None
        price_max = None
        amount_pattern = r"(?:[1-9]\d*(?:\.\d+)?[kK]|\d+(?:\.\d+)?|[一二两三四五六七八九十百千万]+(?![点些]))"
        range_match = re.search(rf"({amount_pattern})\s*(?:-|到|至|~|—)\s*({amount_pattern})\s*(?:元|块|块钱)?", message)
        if range_match:
            price_min = _parse_amount(range_match.group(1))
            price_max = _parse_amount(range_match.group(2))
        around_match = re.search(rf"({amount_pattern})\s*(?:元|块|块钱)?\s*(?:左右|上下|附近|差不多)", message)
        if around_match:
            amount = _parse_amount(around_match.group(1))
            if amount is not None:
                price_min = round(amount * 0.8, 2)
                price_max = round(amount * 1.2, 2)
        max_match = None
        if price_max is None:
            max_match = (
                re.search(rf"({amount_pattern})\s*(?:元|块|块钱)?\s*(?:以下|以内|内|封顶)", message)
                or re.search(rf"(?:不超过|不要超过|别超过|低于|少于|控制在|预算|价位|价格|最多|上限|封顶|只剩|还剩|剩下|还有)\s*(?:是|在|为|大概|大约|约|差不多|控制在|不超过|不要超过|别超过)?\s*({amount_pattern})", message)
            )
            if max_match is None and any(token in message for token in ["预算", "价位", "价格", "最多", "上限", "只剩", "还剩", "剩下", "还有", "零花钱"]):
                max_match = re.search(rf"(?:预算|价位|价格|最多|上限|只剩|还剩|剩下|还有)[^，。,.；;]*?({amount_pattern})\s*(?:元|块|块钱)?", message)
            if max_match:
                price_max = _parse_amount(max_match.groups()[-1])
        min_match = re.search(rf"({amount_pattern})\s*(?:元|块|块钱)?\s*(?:以上|起)", message)
        if min_match:
            price_min = _parse_amount(min_match.group(1))
        if price_min is not None and price_max is not None and price_min > price_max:
            price_min, price_max = price_max, price_min
        return PriceRange(min=price_min, max=price_max)

    def _extract_brands(self, message: str) -> tuple[list[str], list[str]]:
        include: list[str] = []
        exclude: list[str] = []
        lowered = message.lower()
        for alias, brands in self._brand_aliases.items():
            if alias.lower() not in lowered:
                continue
            target = exclude if self._has_negation_before(message, alias) else include
            target.extend(brand for brand in brands if brand in self.product_repository.list_brands())
        for alias, brands in self._brand_group_aliases.items():
            if alias not in message:
                continue
            target = exclude if self._has_negation_before(message, alias) else include
            target.extend(brand for brand in brands if brand in self.product_repository.list_brands())
        for brand in self.product_repository.list_brands():
            aliases = [brand, brand.split()[0], brand.replace(" ", ""), brand.lower(), brand.replace(" ", "").lower()]
            for alias in {item for item in aliases if item}:
                haystack = lowered if alias.islower() else message
                if alias and alias in haystack:
                    if self._has_negation_before(message, alias):
                        exclude.append(brand)
                    else:
                        include.append(brand)
                    break
        return sorted(set(include)), sorted(set(exclude))

    def _extract_negative_constraints(self, message: str) -> list[str]:
        found = [term for term in self._negative_terms if term in message and self._has_negation_before(message, term)]
        found = [term for term in found if term not in {"太贵", "贵"}]
        if any(term in message for term in ["不能总吃糖", "少吃糖", "少喝甜", "不甜", "不要甜味", "别太甜", "甜的不好", "对身体不好"]):
            found.extend(["糖", "甜味"])
        if any(term in message for term in ["不要包装太大的", "包装不要太大", "别太大包", "不要大包装"]):
            found.append("大包装")
        if "笔头过粗" in message or "笔头太粗" in message:
            found.append("粗头")
        if any(term in message for term in ["不要紧身", "别紧身", "不想要紧身", "不要紧身款"]):
            found.append("紧身")
        if any(term in message for term in ["不要印花", "不要印花图案", "不要大Logo", "不要大logo", "不要大Logo印花", "不要大logo印花"]):
            found.append("印花")
        # ---- 拒绝XX 类否定约束 ----
        if any(term in message for term in ["拒绝黑色", "拒绝黑色系", "拒绝黑颜色", "拒绝黑色的", "排除黑色", "避开黑色"]):
            found.append("黑色")
        if any(term in message for term in ["拒绝白色", "拒绝白色系", "拒绝白色的", "排除白色"]):
            found.append("白色")
        if any(term in message for term in ["拒绝红色", "拒绝红色系", "拒绝红色的", "排除红色"]):
            found.append("红色")
        if any(term in message for term in ["拒绝 oversize", "拒绝oversize", "拒绝大版型", "拒绝宽松版型", "拒绝宽松", "不要oversize", "不要大版型", "不要宽松版型"]):
            found.append("oversize")
            found.append("大版型")
        if any(term in message for term in ["拒绝紧身", "拒绝修身", "拒绝紧身款", "不要紧身款", "别紧身", "不想要紧身款"]):
            found.append("紧身")
        if any(term in message for term in ["拒绝日系", "拒绝日系品牌", "不要日系", "排除日系品牌", "避开日系"]):
            found.append("日系")
        if any(term in message for term in ["拒绝含酒精", "拒绝酒精", "不要含酒精", "不要酒精", "避开含酒精"]):
            found.append("酒精")
        if any(term in message for term in ["拒绝太甜", "拒绝甜", "拒绝甜味", "拒绝太甜的"]):
            found.extend(["甜", "甜味"])
        for match in re.finditer(r"(?:不要|不含|不想要|不喜欢|排除|避开|除了|拒绝|别给我|别推荐|不要有|不能有|不想|不买|别要)\s*([^\s，。,.；;、]{1,12})", message):
            value = _normalize_negative_value(match.group(1).strip())
            if value:
                found.append(value)
        return sorted(set(found))

    def _extract_positive_constraints(self, message: str, negative_constraints: list[str]) -> list[str]:
        found = []
        for term in self._feature_terms:
            if term in message and term not in negative_constraints and not self._has_negation_before(message, term):
                found.append(self._feature_normalization.get(term, term))
        if any(term in message for term in ["别太贵", "不要太贵", "不太贵", "价格亲民", "预算友好", "便宜一点", "便宜点", "便宜的", "不贵", "贵了", "太贵", "好贵"]):
            found.append("性价比")
        if any(term in message for term in ["不能总吃糖", "少吃糖", "少喝甜", "不甜", "不要甜味", "别太甜", "甜的不好", "对身体不好"]):
            found.extend(["低糖", "无糖"])
        if _is_beverage_request(message):
            found.append("饮料")
        if any(term in message for term in ["皮肤干", "有点干", "干燥起皮", "缺水起皮", "缺水", "拔干"]):
            found.extend(["干皮", "补水", "保湿"])
        if any(term in message for term in ["卡粉", "上妆总是卡粉", "上妆不服帖", "底妆"]):
            found.extend(["底妆", "保湿", "服帖"])
        if any(term in message for term in ["下午困", "困了", "犯困", "提神"]):
            found.extend(["提神", "饮料"])
        if any(term in message for term in ["健身后", "运动后", "补充点东西", "运动补给"]):
            found.extend(["健身", "补给", "蛋白"])
        if any(term in message for term in ["办公室囤", "办公室能囤", "囤点零食"]):
            found.extend(["办公室", "囤货", "零食"])
        if any(term in message for term in ["低负担", "不想长胖", "低卡零食", "低卡"]):
            found.extend(["低卡", "低糖", "低负担"])
        if any(term in message for term in ["看书", "墨水屏", "不伤眼"]):
            found.extend(["看书", "护眼", "墨水屏"])
        if any(term in message for term in ["备份照片", "备份很多照片", "备份资料", "存照片"]):
            found.extend(["备份", "存储", "大容量"])
        if any(term in message for term in ["手机发烫", "发烫", "散热"]):
            found.append("散热")
        if any(term in message for term in ["外套", "通勤的外套"]):
            found.extend(["外套", "通勤"])
        if any(term in message for term in ["三亚", "海边", "度假"]):
            found.extend(["旅行", "度假", "防晒"])
        if any(term in message for term in ["屏障", "屏障修护", "屏障受损"]):
            found.append("修护")
        if any(term in message for term in ["不想黏腻", "不想粘腻", "不要黏腻", "不要粘腻", "不黏腻", "不粘腻", "不要太油", "别太油", "不想太油"]):
            found.extend(["清爽", "不油腻"])
        if any(term in message for term in ["小朋友", "四岁", "4岁", "宝宝", "孩子"]):
            found.extend(["儿童", "小包装"])
        if any(term in message for term in ["爸爸妈妈", "一家人", "一起吃", "一起分享"]):
            found.extend(["亲子", "分享"])
        return sorted(set(found))

    def _extract_category(self, message: str) -> tuple[str | None, str | None]:
        if any(term in message for term in ["低负担", "不想长胖", "低卡零食", "低卡"]):
            return "食品饮料", "蒟蒻果冻"
        specific_shoe_aliases = ["篮球鞋", "徒步鞋", "跑鞋", "跑步鞋", "板鞋", "帆布鞋", "拖鞋", "沙滩拖鞋", "训练鞋", "健身鞋"]
        if (
            "鞋" in message
            and not any(alias in message for alias in specific_shoe_aliases)
            and any(term in message for term in ["健身", "训练", "运动", "通勤", "走路", "慢跑", "跑步"])
        ):
            return "服饰运动", "跑步鞋"
        for alias, category_pair in sorted(self._category_aliases.items(), key=lambda item: len(item[0]), reverse=True):
            if alias in message:
                return category_pair
        for category_name in self.product_repository.list_categories():
            if category_name and category_name in message:
                if category_name in {"美妆护肤", "数码电子", "服饰运动", "食品饮料"}:
                    return category_name, None
                product = next((item for item in self.product_repository.list_products() if item.sub_category == category_name), None)
                return (product.category if product else None), category_name
        return None, None

    @staticmethod
    def _message_has_real_compare_signal(message: str) -> bool:
        return (
            any(term in message for term in ["对比", "比较一下", "帮我比较", "比较第", "比较这", "比较那", "哪个更", "哪款更", "哪个好", "哪款好", "区别", "差别", "排一下", "排序", "最适合", "最好喝"])
            or ("哪个" in message and "更" in message)
        )

    @staticmethod
    def _infer_category_from_feature_rules(message: str, positive_constraints: list[str]) -> tuple[str | None, str | None]:
        if "拍照" in positive_constraints and not any(term in message for term in ["防晒", "粉底", "口红", "唇釉", "妆", "美妆", "护肤", "面霜", "精华"]):
            return "数码电子", "智能手机"
        if any(term in message for term in ["皮肤干", "干燥起皮", "缺水起皮", "屏障修护"]):
            return "美妆护肤", "面霜"
        if any(term in message for term in ["卡粉", "底妆", "遮瑕", "上妆不服帖", "上妆总是"]):
            return "美妆护肤", "底妆"
        if any(term in message for term in ["下午困", "困了喝", "提神喝", "犯困"]):
            return "食品饮料", "咖啡"
        if any(term in message for term in ["健身后", "运动后", "补充点东西", "运动补给"]):
            return "食品饮料", "健身补给"
        if any(term in message for term in ["早餐", "早饭"]):
            return "食品饮料", "早餐"
        if any(term in message for term in ["办公室囤", "能囤的零食", "囤点零食"]):
            return "食品饮料", "坚果/零食"
        if any(term in message for term in ["低负担", "不想长胖", "低卡零食", "低卡"]):
            return "食品饮料", "蒟蒻果冻"
        if any(term in message for term in ["看书", "墨水屏", "不伤眼", "电子书"]):
            return "数码电子", "电子书阅读器"
        if any(term in message for term in ["备份照片", "备份很多照片", "备份资料", "存照片", "存很多照片"]):
            return "数码电子", "移动硬盘"
        if any(term in message for term in ["办公的轻薄设备", "办公学习", "轻薄设备", "适合办公"]):
            return "数码电子", "办公设备"
        if any(term in message for term in ["手机发烫", "发烫", "手机散热", "散热"]):
            return "数码电子", "手机散热器"
        if any(term in message for term in ["通勤的外套", "适合通勤的外套", "外套"]):
            return "服饰运动", "外套"
        if any(term in message for term in ["瑜伽的裤子", "瑜伽裤", "瑜伽"]):
            return "服饰运动", "瑜伽裤"
        if any(term in message for term in ["三亚", "海边", "度假"]):
            return "服饰运动", None
        return None, None

    def _extract_cart_action(self, message: str, intent: IntentType, referents: list[str]) -> CartAction | None:
        if intent not in {
            IntentType.CART_ADD,
            IntentType.CART_REMOVE,
            IntentType.CART_UPDATE,
            IntentType.CART_CLEAR,
            IntentType.CART_VIEW,
            IntentType.CART_KEEP_ONLY,
            IntentType.CHECKOUT,
        }:
            return None
        quantity_match = re.search(r"(\d+|[一二两三四五六七八九十])\s*(?:件|个|份|双|台|瓶|盒)?", message)
        quantity_value = _parse_amount(quantity_match.group(1)) if quantity_match else None
        quantity = int(quantity_value) if quantity_value is not None else None
        target_ref = referents[0] if referents else None
        category, sub_category = self._extract_category(message)
        keep_categories: list[str] = []
        keep_sub_categories: list[str] = []
        if intent == IntentType.CART_KEEP_ONLY:
            for alias, (cat, sub) in self._category_aliases.items():
                if alias in message:
                    if cat and not sub:
                        keep_categories.append(cat)
                    if sub:
                        keep_sub_categories.append(sub)
        return CartAction(
            action=intent.value,
            quantity=quantity,
            target_ref=target_ref,
            keep_categories=sorted(set(keep_categories + ([category] if category and not sub_category else []))),
            keep_sub_categories=sorted(set(keep_sub_categories + ([sub_category] if sub_category else []))),
        )

    def _extract_compare_targets(self, message: str, referents: list[str]) -> list[str]:
        if not any(token in message for token in ["对比", "比较", "哪个更", "哪款更", "vs", "VS"]):
            return []
        if len(referents) >= 2:
            return referents[:2]
        split_tokens = re.split(r"(?:和|跟|与|vs|VS|,|，)", message)
        targets = [part.strip(" ？?。.!哪个更比较对比") for part in split_tokens if len(part.strip()) >= 2]
        return targets[:2]

    def _should_inherit_context(
        self,
        message: str,
        category: str | None,
        state: SessionState | None,
        intent: IntentType,
    ) -> bool:
        if intent in {
            IntentType.CART_ADD,
            IntentType.CART_REMOVE,
            IntentType.CART_UPDATE,
            IntentType.CART_CLEAR,
            IntentType.CART_VIEW,
            IntentType.CART_KEEP_ONLY,
            IntentType.CHECKOUT,
            IntentType.SCENE_BUNDLE,
        }:
            return False
        if category or not state:
            return False
        if state.dialogue_state_tracking.current_category is None:
            return False
        return (
            any(token in message for token in ["再", "换", "便宜", "贵", "合适", "告诉我", "哪些", "预算", "以内", "以下", "不超过", "别超过", "只剩", "还剩", "剩下", "零花钱", "不要", "不含", "除了", "排除", "第二", "第一", "这个", "这款", "刚才", "前面", "上一个", "那款", "还有", "一起", "分享", "配着", "适合", "拍照", "续航", "快充", "性能", "屏幕", "内存", "好看"])
            or any(term in message for term in self._feature_terms)
        )

    def _should_lock_current_topic(
        self,
        *,
        message: str,
        state: SessionState | None,
        intent: IntentType,
        explicit_category: bool,
        positive_constraints: list[str],
        negative_constraints: list[str],
        price_range: PriceRange,
    ) -> bool:
        if explicit_category or not state or not state.dialogue_state_tracking.current_category:
            return False
        if intent in {
            IntentType.CART_ADD,
            IntentType.CART_REMOVE,
            IntentType.CART_UPDATE,
            IntentType.CART_CLEAR,
            IntentType.CART_VIEW,
            IntentType.CART_KEEP_ONLY,
            IntentType.CHECKOUT,
            IntentType.CHITCHAT,
            IntentType.OUT_OF_SCOPE,
            IntentType.INVALID,
            IntentType.SCENE_BUNDLE,
        }:
            return False
        # 检测用户是否暗示更换商品类目：如果消息命中了与当前类目不同的别名，
        # 说明用户在主动切换话题，不应锁定旧主题。
        if self._message_suggests_topic_switch(message, state):
            return False
        return self._has_topic_continuity_signal(
            message,
            intent,
            positive_constraints,
            negative_constraints,
            price_range,
            state,
        )

    @staticmethod
    def _message_suggests_topic_switch(message: str, state: SessionState | None) -> bool:
        """Check if the message hints at switching to a different product category.

        Uses a broader keyword approach beyond exact alias matches: looks for
        general category-indicating nouns and domain-specific terms that are
        unlikely to belong to the current category.
        """
        if not state or not state.dialogue_state_tracking.current_category:
            return False
        current_cat = state.dialogue_state_tracking.current_category
        # Cross-category signal terms: if any of these appear and the current
        # category is not the one they point to, treat as a topic switch.
        _cross_category_signals: dict[str, str] = {
            # 美妆护肤 signal -> category
            "面霜": "美妆护肤", "精华": "美妆护肤", "洁面": "美妆护肤",
            "洗面奶": "美妆护肤", "防晒霜": "美妆护肤", "粉底": "美妆护肤",
            "口红": "美妆护肤", "卸妆": "美妆护肤", "面膜": "美妆护肤",
            "眼霜": "美妆护肤", "化妆水": "美妆护肤", "水乳": "美妆护肤",
            # 数码电子 signals
            "手机": "数码电子", "电脑": "数码电子", "笔记本": "数码电子",
            "平板": "数码电子", "耳机": "数码电子", "相机": "数码电子",
            # 服饰运动 signals
            "跑鞋": "服饰运动", "运动鞋": "服饰运动", "篮球鞋": "服饰运动",
            "外套": "服饰运动", "夹克": "服饰运动", "羽绒服": "服饰运动",
            "冲锋衣": "服饰运动", "牛仔裤": "服饰运动", "卫衣": "服饰运动",
            "T恤": "服饰运动", "t恤": "服饰运动", "短袖": "服饰运动",
            "衬衫": "服饰运动", "背包": "服饰运动", "帽子": "服饰运动",
            "瑜伽裤": "服饰运动", "短裤": "服饰运动", "长裤": "服饰运动",
            "泳衣": "服饰运动", "袜子": "服饰运动", "拖鞋": "服饰运动",
            "板鞋": "服饰运动", "帆布鞋": "服饰运动", "连衣裙": "服饰运动",
            "长裙": "服饰运动", "裙子": "服饰运动",
            # 食品饮料 signals
            "咖啡": "食品饮料", "茶": "食品饮料", "牛奶": "食品饮料",
            "酸奶": "食品饮料", "零食": "食品饮料", "坚果": "食品饮料",
            "饮料": "食品饮料", "早餐": "食品饮料", "方便面": "食品饮料",
        }
        for keyword, target_category in _cross_category_signals.items():
            if keyword in message and target_category != current_cat:
                return True
        return False

    @staticmethod
    def _has_topic_continuity_signal(
        message: str,
        intent: IntentType,
        positive_constraints: list[str],
        negative_constraints: list[str],
        price_range: PriceRange,
        state: SessionState | None,
    ) -> bool:
        if state and state.dialogue_state_tracking.missing_slots:
            return True
        if intent in {IntentType.REFINE, IntentType.FILTER, IntentType.DETAIL, IntentType.COMPARE}:
            return True
        if price_range.min is not None or price_range.max is not None:
            return True
        if positive_constraints or negative_constraints:
            return True
        return any(
            token in message
            for token in [
                "拍照", "好看", "续航", "快充", "性能", "屏幕", "内存", "颜色",
                "便宜", "贵", "预算", "价格", "合适", "这个", "这款", "刚才",
                "前面", "还有", "换", "再", "不要", "不含", "除了", "排除",
            ]
        )

    def _estimate_confidence(
        self,
        *,
        intent: IntentType,
        category: str | None,
        sub_category: str | None,
        price_range: PriceRange,
        positive_constraints: list[str],
        negative_constraints: list[str],
        brands_include: list[str],
        brands_exclude: list[str],
        referents: list[str],
    ) -> float:
        score = 0.45
        if intent:
            score += 0.12
        if category:
            score += 0.14
        if sub_category:
            score += 0.06
        if price_range.min is not None or price_range.max is not None:
            score += 0.07
        if positive_constraints:
            score += 0.08
        if negative_constraints or brands_include or brands_exclude:
            score += 0.05
        if referents:
            score += 0.03
        return min(score, 0.96)

    def _detect_clarification_need(
        self,
        *,
        intent: IntentType,
        category: str | None,
        sub_category: str | None,
        message: str,
        positive_constraints: list[str],
        price_range: PriceRange,
        negative_constraints: list[str] | None = None,
    ) -> tuple[bool, list[str]]:
        if intent in {IntentType.CART_ADD, IntentType.CART_REMOVE, IntentType.CART_UPDATE, IntentType.CART_CLEAR, IntentType.CART_VIEW, IntentType.CART_KEEP_ONLY, IntentType.CHECKOUT, IntentType.COMPARE, IntentType.CHITCHAT, IntentType.PREFERENCE, IntentType.DETAIL}:
            return False, []
        if intent == IntentType.SCENE_BUNDLE:
            return False, []
        if category is None:
            return True, ["category"]
        negative_constraints = negative_constraints or []
        has_specific_constraints = bool(positive_constraints or negative_constraints or price_range.min is not None or price_range.max is not None)
        if category == "食品饮料" and _is_beverage_request(message) and has_specific_constraints:
            return False, []
        if sub_category is None and category in {"服饰运动", "食品饮料", "数码电子", "美妆护肤", "日用百货"} and not has_specific_constraints:
            return True, ["sub_category_or_scene"]
        if any(term in message for term in ["手机", "护肤品", "运动装备", "礼物"]) and not positive_constraints and price_range.max is None:
            return True, ["priority"]
        return False, []

    def _extract_scenario(self, message: str) -> str | None:
        for term in ["三亚", "海边", "度假", "旅行", "短途", "出差", "露营", "健身房", "健身", "通勤", "开学", "宿舍", "送礼", "礼物", "加班", "办公室", "上班", "学生党", "职场新人", "入职"]:
            if term in message:
                return term
        return None

    def _extract_target_user(self, message: str) -> str | None:
        for term in ["小朋友", "4岁", "四岁", "宝宝", "孩子", "朋友", "女朋友", "男朋友", "女生", "女性", "男生", "妈妈", "爸爸", "爸爸妈妈", "父母", "长辈", "同事", "学生", "学生党", "上班族", "职场新人", "新手", "小白", "敏感肌", "油皮", "干皮"]:
            if term in message:
                if term in {"4岁", "四岁", "宝宝", "孩子"}:
                    return "小朋友"
                return term
        return None

    def _extract_mentioned_products(self, message: str) -> list[str]:
        mentioned = []
        for product in self.product_repository.list_products():
            short_name = product.name[:8]
            if product.sku_id in message or product.name in message or short_name in message:
                mentioned.append(product.sku_id)
        return mentioned[:5]

    @staticmethod
    def _sub_intent(intent: IntentType, message: str) -> str | None:
        if intent == IntentType.COMPARE:
            if any(term in message for term in ["排序", "排一下", "综合"]):
                return "ranking_compare"
            return "attribute_compare"
        if intent == IntentType.FILTER:
            return "condition_filter"
        if intent == IntentType.DETAIL:
            return "product_qa"
        return None

    def _rewrite_query(
        self,
        *,
        message: str,
        category: str | None,
        sub_category: str | None,
        price_range: PriceRange,
        positive_constraints: list[str],
        negative_constraints: list[str],
        brands_exclude: list[str],
    ) -> str:
        parts = [message]
        if category:
            parts.append(category)
        if sub_category:
            parts.append(sub_category)
        parts.extend(positive_constraints)
        if price_range.max is not None:
            parts.append(f"{price_range.max:g}元以内")
        for item in negative_constraints:
            parts.append(f"不要{item}")
        for brand in brands_exclude:
            parts.append(f"不要{brand}")
        return " ".join(dict.fromkeys(part for part in parts if part))

    @staticmethod
    def _has_negation_before(message: str, term: str) -> bool:
        index = message.find(term)
        if index < 0:
            index = message.lower().find(term.lower())
        if index < 0:
            return False
        window = message[max(0, index - 12):index]
        return any(token in window for token in ["不要", "不含", "不想要", "不喜欢", "排除", "避开", "除了", "拒绝", "别", "不能有", "不能", "不", "无", "不想"])

    def _infer_intent_with_small_model(self, message: str, rule_intent: IntentType) -> tuple[IntentType | None, float]:
        if not self.local_models:
            return None, 0.0
        if rule_intent in {
            IntentType.CART_ADD,
            IntentType.CART_REMOVE,
            IntentType.CART_UPDATE,
            IntentType.CART_CLEAR,
            IntentType.CART_VIEW,
            IntentType.CART_KEEP_ONLY,
            IntentType.CHECKOUT,
            IntentType.PREFERENCE,
        }:
            return None, 0.0
        label, score = self.local_models.best_text2vec_label(
            message,
            self._semantic_intent_examples,
            threshold=0.56,
        )
        if not label:
            return None, score
        inferred = IntentType(label)
        if inferred == IntentType.COMPARE and not self._message_has_real_compare_signal(message):
            return None, score
        if inferred == IntentType.SCENE_BUNDLE and not self._has_scene_bundle_command(message):
            return None, score
        if rule_intent == IntentType.RECOMMEND:
            return inferred, score
        if inferred in {IntentType.COMPARE, IntentType.DETAIL, IntentType.SCENE_BUNDLE} and score >= 0.62:
            return inferred, score
        return None, score

    def _infer_category_with_small_model(self, message: str) -> tuple[str | None, str | None, float]:
        if not self.local_models:
            return None, None, 0.0
        label, score = self.local_models.best_text2vec_label(
            message,
            self._semantic_category_examples,
            threshold=0.55,
        )
        if not label:
            return None, None, score
        category, sub_category = label.split("|", 1)
        return category or None, sub_category or None, score


def _combine_scope_text(primary: str | None, full_message: str) -> str:
    """Combine an LLM step source with the original user sentence.

    Doubao may summarize a retrieval step as "具体单品" or "重新推荐".
    The original sentence still contains hard facts like "饮料/防晒霜/背包",
    so local deterministic correction must keep it visible.
    """

    parts = []
    for item in [primary, full_message]:
        text = str(item or "").strip()
        if text and text not in parts:
            parts.append(text)
    return " ".join(parts)


def _is_beverage_request(message: str) -> bool:
    return any(
        term in message
        for term in ["饮料", "饮品", "喝的", "喝点", "喝点什么", "想喝", "口渴", "渴了", "一瓶喝"]
    )


def _looks_like_shopping_recommendation(message: str) -> bool:
    return any(
        term in message
        for term in [
            "想买", "想要", "推荐", "有没有", "有什么", "来点", "吃点", "喝什么", "喝点",
            "买什么", "需要买什么", "准备什么", "适合用什么", "用什么", "怎么办",
            "能囤", "囤点", "补充点东西", "电子设备", "装备", "底妆推荐", "具体单品",
        ]
    )


def _parse_amount(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if text.lower().endswith("k"):
        try:
            return float(text[:-1]) * 1000
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return _chinese_number_to_float(text)


def _chinese_number_to_float(text: str) -> float | None:
    digits = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    if not text:
        return None
    total = 0
    section = 0
    number = 0
    for char in text:
        if char in digits:
            number = digits[char]
        elif char in units:
            unit = units[char]
            if unit == 10000:
                section = (section + number) * unit
                total += section
                section = 0
            else:
                section += (number or 1) * unit
            number = 0
        else:
            return None
    return float(total + section + number)


def _normalize_negative_value(value: str) -> str:
    cleaned = value.strip()
    cleaned = cleaned.strip("了的吧吗呢啊啦哈呀哦")
    if cleaned in {"", "了", "的", "吧", "吗", "呢", "啊", "啦", "哈", "呀", "哦"}:
        return ""
    cleaned = re.sub(r"^(太|过于|很|特别)", "", cleaned)
    cleaned = re.sub(r"^(含|有)", "", cleaned)
    cleaned = re.sub(r"(的|一点|一些|品牌|牌子|款|商品|产品|东西)$", "", cleaned)
    if cleaned in {"", "了", "的"}:
        return ""
    if cleaned in {"贵", "太贵"}:
        return "太贵"
    if cleaned in {"油", "太油", "粘腻", "黏腻", "油腻"}:
        return "油腻"
    if cleaned in {"酒精成分", "乙醇"}:
        return "酒精"
    if cleaned in {"含酒精", "有酒精", "酒精的"}:
        return "酒精"
    if cleaned in {"含糖", "有糖", "糖分", "糖的"}:
        return "糖"
    if cleaned in {"糖的饮料", "糖饮料", "含糖饮料", "甜的饮料", "甜饮料"}:
        return "糖"
    if cleaned in {"紧身款", "修身紧身"}:
        return "紧身"
    if cleaned in {"印花图案", "大Logo印花", "大logo印花", "大logo", "大Logo"}:
        return "印花"
    return cleaned[:8]


def _normalize_negative_constraints(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        normalized_value = _normalize_negative_value(text)
        normalized.append(normalized_value or text)
    return sorted(set(item for item in normalized if item))


def _safe_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = re.split(r"[,，、;；]\s*", value)
    elif isinstance(value, list):
        values = value
    else:
        return []
    result: list[str] = []
    for item in values:
        text = str(item).strip()
        if text and text.lower() not in {"none", "null", "unknown", "未知", "无", "没有"}:
            result.append(text[:40])
    return list(dict.fromkeys(result))


def _merge_unique(first: list[str], second: list[str]) -> list[str]:
    return list(dict.fromkeys([item for item in [*first, *second] if item]))


def _none_if_empty(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "unknown"} or text in {"无", "未知", "空"}:
        return None
    return text


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.strip().lower() in {"none", "null", "unknown", "无", "未知"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        if isinstance(value, str):
            return _parse_amount(value)
        return None


def _optional_int(value: object) -> int | None:
    number = _optional_float(value)
    if number is None:
        return None
    return int(number)


def _quantity_from_text(text: str) -> int | None:
    matches = list(re.finditer(r"(?:加|买|来|要|改成|改为|数量改成|数量改为)?\s*(\d+|[一二两三四五六七八九十两]+)\s*(?:瓶|件|个|份|双|台|盒|包|箱)", text))
    usable = [match for match in matches if match.start(1) == 0 or text[match.start(1) - 1] != "第"]
    if not usable:
        return None
    amount = _parse_amount(usable[-1].group(1))
    if amount is None:
        return None
    return max(1, int(amount))


def _clamp_float(value: object, *, default: float = 0.0, lower: float = 0.0, upper: float = 1.0) -> float:
    parsed = _optional_float(value)
    if parsed is None:
        parsed = default
    return max(lower, min(upper, parsed))
