from app.models.agent import ScenePlan, SceneSubQuery


class ScenarioPlanner:
    """Rule-based scene decomposition with LLM-friendly output."""

    def plan(self, message: str) -> ScenePlan:
        if any(term in message for term in ["西北", "自驾", "户外用品", "露营", "徒步"]):
            return ScenePlan(
                scenario="西北自驾/户外旅行",
                sub_queries=[
                    SceneSubQuery(label="高倍防晒", category="美妆护肤", sub_category="防晒", query=f"{message} 户外 高倍 防晒 清爽", reason="西北日晒强，防晒需要优先准备"),
                    SceneSubQuery(label="徒步鞋", category="服饰运动", sub_category="徒步鞋", query=f"{message} 徒步鞋 抓地 防水 支撑", reason="自驾旅行中会有砂石路和短途徒步，需要稳定抓地"),
                    SceneSubQuery(label="户外长裤", category="服饰运动", sub_category="户外裤", query=f"{message} 户外裤 耐磨 弹力 徒步", reason="户外活动需要耐磨、活动方便的裤装"),
                    SceneSubQuery(label="遮阳帽", category="服饰运动", sub_category="帽子", query=f"{message} 防晒 帽子 轻量 透气", reason="长时间户外需要遮阳和头部防晒"),
                    SceneSubQuery(label="随身背包", category="服饰运动", sub_category="背包", query=f"{message} 背包 轻量 收纳 户外", reason="自驾下车游玩时需要携带水、纸巾和随身物品"),
                ],
                unsupported_needs=["帐篷", "睡袋", "车载冰箱", "户外炊具"],
            )
        if any(term in message for term in ["情侣", "海边", "短途海边"]):
            return ScenePlan(
                scenario="情侣短途海边度假",
                sub_queries=[
                    SceneSubQuery(label="面部防晒", category="美妆护肤", sub_category="防晒", query=f"{message} 海边 防晒 清爽 高倍", reason="海边紫外线强，防晒是第一优先级"),
                    SceneSubQuery(label="清爽短袖", category="服饰运动", sub_category="短袖T恤", query=f"{message} 清爽 透气 短袖 百搭", reason="短途海边穿搭需要轻松、透气、好搭配"),
                    SceneSubQuery(label="遮阳帽", category="服饰运动", sub_category="帽子", query=f"{message} 海边 帽子 防晒 透气", reason="拍照和遮阳都能用上"),
                    SceneSubQuery(label="随身背包", category="服饰运动", sub_category="背包", query=f"{message} 轻量 背包 收纳 旅行", reason="短途出行需要收纳防晒、纸巾和随身物品"),
                    SceneSubQuery(label="补水饮品", category="食品饮料", sub_category="茶饮", query=f"{message} 无糖 饮料 补水", reason="出门游玩时准备低负担饮品更方便"),
                ],
                unsupported_needs=["泳衣", "拖鞋", "沙滩毯"],
            )
        if "居家健身" in message:
            return ScenePlan(
                scenario="居家健身基础装备（基于现有商品库）",
                sub_queries=[
                    SceneSubQuery(label="速干上衣", category="服饰运动", sub_category="速干T恤", query=f"{message} 速干 透气 训练 上衣", reason="居家运动出汗时需要透气速干"),
                    SceneSubQuery(label="运动下装", category="服饰运动", sub_category="运动短裤", query=f"{message} 运动短裤 轻薄 透气", reason="在家训练需要活动方便的下装"),
                    SceneSubQuery(label="训练鞋", category="服饰运动", sub_category="跑步鞋", query=f"{message} 跑步鞋 缓震 支撑", reason="跳操或基础训练时需要脚部支撑"),
                    SceneSubQuery(label="运动补给", category="食品饮料", sub_category="功能饮料", query=f"{message} 运动 饮料 补给", reason="运动后可以准备补给饮品"),
                ],
                unsupported_needs=["小型器械", "防滑垫", "弹力带", "哑铃"],
            )
        if any(term in message for term in ["三亚", "海边", "度假", "旅行"]):
            return ScenePlan(
                scenario="旅行/三亚度假",
                sub_queries=[
                    SceneSubQuery(label="防晒保护", category="美妆护肤", sub_category="防晒", query=f"{message} 防晒 清爽", reason="海边紫外线强，优先防晒"),
                    SceneSubQuery(label="清爽穿搭", category="服饰运动", sub_category="短袖T恤", query=f"{message} 清爽 透气 短袖", reason="高温场景需要透气衣物"),
                    SceneSubQuery(label="随身收纳", category="服饰运动", sub_category="背包", query=f"{message} 轻便 背包 通勤 旅行", reason="短途出行需要收纳"),
                    SceneSubQuery(label="补水饮品", category="食品饮料", sub_category="功能饮料", query=f"{message} 饮料 补水", reason="户外活动需要补水"),
                ],
                unsupported_needs=["拖鞋", "泳衣"],
            )
        if any(term in message for term in ["健身", "健身房", "运动装备", "开始运动"]):
            return ScenePlan(
                scenario="健身入门",
                sub_queries=[
                    SceneSubQuery(label="运动上衣", category="服饰运动", sub_category="速干T恤", query=f"{message} 速干 运动 T恤", reason="训练时需要吸汗透气"),
                    SceneSubQuery(label="跑步训练鞋", category="服饰运动", sub_category="跑步鞋", query=f"{message} 跑步鞋 缓震 轻量", reason="基础有氧和器械训练都需要支撑"),
                    SceneSubQuery(label="运动长裤", category="服饰运动", sub_category="运动长裤", query=f"{message} 运动裤 训练", reason="适合健身房训练"),
                    SceneSubQuery(label="补给饮品", category="食品饮料", sub_category="功能饮料", query=f"{message} 功能饮料", reason="运动后补给"),
                ],
                unsupported_needs=["水杯", "毛巾"],
            )
        if any(term in message for term in ["礼物", "送朋友", "送人", "用心"]):
            return ScenePlan(
                scenario="礼物组合",
                sub_queries=[
                    SceneSubQuery(label="精致护肤", category="美妆护肤", sub_category="精华", query=f"{message} 礼物 精致 护肤", reason="护肤礼物有实用感"),
                    SceneSubQuery(label="咖啡礼盒", category="食品饮料", sub_category="咖啡", query=f"{message} 礼盒 咖啡", reason="咖啡礼盒适合加班或日常提神"),
                    SceneSubQuery(label="百搭服饰", category="服饰运动", sub_category="短袖T恤", query=f"{message} 百搭 礼物", reason="基础款更不挑人"),
                ],
            )
        if any(term in message for term in ["开学", "宿舍"]):
            return ScenePlan(
                scenario="开学/宿舍生活",
                sub_queries=[
                    SceneSubQuery(label="学习数码", category="数码电子", sub_category="平板电脑", query=f"{message} 学习 平板", reason="学习和笔记"),
                    SceneSubQuery(label="早餐饮品", category="食品饮料", sub_category="牛奶", query=f"{message} 早餐 牛奶", reason="宿舍早餐补给"),
                    SceneSubQuery(label="通勤背包", category="服饰运动", sub_category="背包", query=f"{message} 背包 通勤", reason="上课收纳"),
                ],
                unsupported_needs=["床品", "台灯"],
            )
        if any(term in message for term in ["职场新人", "入职", "办公文具", "桌面收纳", "通勤小物"]):
            return ScenePlan(
                scenario="职场新人入职（基于现有商品库的相近方案）",
                sub_queries=[
                    SceneSubQuery(label="通勤背包", category="服饰运动", sub_category="背包", query=f"{message} 通勤 背包 轻量 收纳", reason="商品库没有办公文具和桌面收纳时，用通勤背包满足入职收纳需求"),
                    SceneSubQuery(label="办公平板", category="数码电子", sub_category="平板电脑", query=f"{message} 办公 平板 学习 便携", reason="平板可作为会议记录和轻办公工具"),
                    SceneSubQuery(label="通勤耳机", category="数码电子", sub_category="真无线耳机", query=f"{message} 通勤 耳机 降噪 办公", reason="通勤和办公室专注时可使用耳机"),
                ],
                unsupported_needs=["办公文具", "桌面收纳", "卡套钥匙扣"],
            )
        return ScenePlan(
            scenario="通用场景",
            sub_queries=[
                SceneSubQuery(label="实用单品", category=None, sub_category=None, query=message, reason="先从当前商品库宽召回"),
            ],
        )
