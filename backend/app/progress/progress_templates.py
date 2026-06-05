# app/progress/progress_templates.py

# 用途：存储前端 progress events 的候选模板。

# 原则：这些内容只展示“系统正在执行的外部工作状态”，不展示模型内部推理过程。

# 使用方式：后端根据 intent、flow_type、预计耗时、是否需要检索/记忆/大模型，选择若干模板组合成 progress events。

PROGRESS_STAGE_TEMPLATES = {
    "intent_understanding": {
        "中文说明": "意图理解类提示：用户输入后立即展示，表示系统已经开始处理。",
        "stage": "understanding",
        "templates": [
            "收到，我先帮你理解一下需求。",
            "我先看一下你的购买意图和关键条件。",
            "正在判断你是想要推荐、比较、详情，还是购物车操作。",
            "我已经开始处理你的需求，先帮你整理重点。",
            "我先快速确认一下你这轮想完成的导购任务。",
            "正在识别你的商品目标和表达重点。",
            "我先把你的需求拆成更容易处理的导购任务。"
            ]
        },

    "constraint_extraction": {
        "中文说明": "约束提取类提示：用于预算、品牌、功能、否定条件、使用场景等信息分析。",
        "stage": "constraint_extraction",
        "templates": [
            "正在提取预算、品类、品牌和功能偏好。",
            "我在整理你提到的价格、场景和关键要求。",
            "正在识别你明确想要和不想要的条件。",
            "我会优先考虑你刚才强调的核心需求。",
            "正在把你的自然语言需求转成可检索的商品条件。",
            "我在确认哪些条件必须满足，哪些可以作为偏好参考。",
            "正在识别是否存在需要排除的品牌、成分或属性。"
        ]
    },

    "memory_context": {
        "中文说明": "记忆读取类提示：用于多轮对话、历史推荐、用户偏好、指代解析。",
        "stage": "memory",
        "templates": [
            "我正在结合前面的对话一起判断。",
            "正在读取你本轮会话里的历史推荐结果。",
            "我会参考你之前提到的预算和使用场景。",
            "正在确认你说的“这个”“第一个”具体指哪款商品。",
            "我在结合你的历史偏好调整推荐重点。",
            "正在检查最近推荐过的商品和当前购物车状态。",
            "我会把当前需求和你之前的偏好一起考虑。"
        ]
    },

    "retrieval": {
        "中文说明": "商品检索类提示：用于 RAG、数据库检索、关键词/向量检索、结构化过滤。",
        "stage": "retrieval",
        "templates": [
            "正在商品库里查找合适的候选商品。",
            "正在匹配商品名称、属性、价格和适用场景。",
            "我在检索真实可展示的商品信息。",
            "正在根据你的条件筛选商品库。",
            "我在查找更接近你需求的商品选择。",
            "正在结合关键词和商品属性进行检索。",
            "商品库检索中，我会优先找可直接推荐的真实商品。",
            "正在排除明显不符合要求的商品。"
        ]
    },

    "selection_rerank": {
        "中文说明": "筛选排序类提示：用于候选商品过滤、重排、比较、压缩结果。",
        "stage": "rerank",
        "templates": [
            "我在比较候选商品的匹配程度。",
            "正在从候选商品中挑出更值得优先看的几款。",
            "我在按价格、功能和适用场景重新排序。",
            "正在压缩候选结果，只保留最有参考价值的商品。",
            "我在检查这些商品和你需求的匹配点。",
            "正在筛掉不够贴合的结果。",
            "我会优先保留更符合你核心要求的商品。"
        ]
    },

    "response_composition": {
        "中文说明": "回复组织类提示：用于最终回复生成、商品卡片准备、推荐理由整理。",
        "stage": "generation",
        "templates": [
            "正在把结果整理成更容易看的推荐理由。",
            "我在组织一版简洁清楚的导购回复。",
            "正在准备最终建议和商品卡片。",
            "快好了，我正在把商品信息和推荐理由整理给你。",
            "正在生成更清晰的推荐结论。",
            "我在把检索结果整理成适合直接查看的回复。",
            "马上给你一版简洁的推荐结果。"
        ]
    },

    # -------- 购物车专用阶段模板 --------
    # 目的：购物车操作时不再使用通用的"理解需求""结合偏好"等与购物车无关的文案，
    # 而是模拟真实电商系统处理购物车时的状态，让用户感觉系统真的在做库存校验、购物车更新等操作。

    "cart_intent_understanding": {
        "中文说明": "购物车操作意图理解：快速判断用户要做的是加购、删除、结算还是查看。",
        "stage": "understanding",
        "templates": {
            "cart_add": [
                "正在确认你要加入购物车的商品。",
                "我先确认一下你要加购的商品信息。",
                "好的，正在准备将商品加入购物车。"
            ],
            "cart_remove": [
                "正在确认你要从购物车移除的商品。",
                "我先确认一下你要删除的商品。",
                "好的，正在准备调整购物车。"
            ],
            "checkout": [
                "正在确认你的结算需求。",
                "我先核对一下购物车里的商品清单。",
                "好的，正在准备订单结算。"
            ],
            "cart_view": [
                "正在加载你的购物车信息。",
                "我先拉取最新的购物车状态。",
                "好的，正在查看购物车。"
            ],
            "cart_clear": [
                "正在确认清空购物车的操作。",
                "我先确认一下清空范围。"
            ],
            "default": [
                "正在理解你的购物车操作需求。",
                "我先看一下你要对购物车做哪些调整。",
                "好的，正在处理购物车相关操作。"
            ]
        }
    },

    "cart_inventory_check": {
        "中文说明": "库存校验：模拟真实电商在加购/结算前检查库存是否充足。",
        "stage": "inventory",
        "templates": {
            "cart_add": [
                "正在检查库存，确保你要的商品数量充足。",
                "正在帮你确认库存状态，稍等一下。",
                "正在核实商品可售数量，确保不会缺货。",
                "正在确认商品库存，马上就帮你加入。"
            ],
            "checkout": [
                "正在核对所有商品的库存和可售状态。",
                "正在确认订单中每件商品都有库存。",
                "库存校验中，确保商品都能正常下单。"
            ],
            "default": [
                "正在检查库存和商品状态。",
                "正在确认商品库存信息。"
            ]
        }
    },

    "cart_updating": {
        "中文说明": "购物车更新：模拟增删改操作中的购物车状态变更。",
        "stage": "cart",
        "templates": {
            "cart_add": [
                "正在帮您将商品加入购物车，请稍等。",
                "正在更新购物车，马上就好。",
                "正在将商品添加到你购物车里。",
                "购物车正在更新中，稍等哦。"
            ],
            "cart_remove": [
                "正在帮您从购物车中移除商品。",
                "正在调整购物车，帮你删掉不需要的商品。",
                "正在更新购物车内容，稍等哦。"
            ],
            "cart_clear": [
                "正在帮你清空购物车。",
                "正在清理购物车中的所有商品。"
            ],
            "default": [
                "正在帮你调整购物车，请稍等。",
                "正在处理购物车，稍等哦。",
                "购物车正在更新，马上就好。"
            ]
        }
    },

    "cart_checkout_processing": {
        "中文说明": "结算处理：模拟下单流程中的订单生成、地址校验等。",
        "stage": "checkout",
        "templates": [
            "正在核对收货地址和商品清单。",
            "正在生成订单预览，确认金额和数量。",
            "正在计算优惠和运费，准备订单。",
            "订单正在生成中，马上就好。"
        ]
    },

    "cart_completion": {
        "中文说明": "购物车操作收尾：操作即将完成时的提示。",
        "stage": "completion",
        "templates": {
            "cart_add": [
                "加购操作马上完成。",
                "正在同步最新的购物车信息。"
            ],
            "cart_remove": [
                "删除操作马上完成。",
                "正在同步最新购物车状态。"
            ],
            "checkout": [
                "订单马上生成好。",
                "正在同步订单信息。"
            ],
            "default": [
                "购物车操作马上完成。",
                "正在同步购物车最新状态。",
                "马上告诉你操作结果。"
            ]
        }
    }
}

# 不同业务场景默认使用哪些阶段。

# 后端可以根据实际耗时动态截断，真实结果提前返回时前端应立即停止 progress 并展示正式结果。

SCENARIO_PROGRESS_PLANS = {
    "greeting": {
        "中文说明": "简单问候或本地模板回复。",
        "latency_level": "fast",
        "stages": ["intent_understanding", "response_composition"]
    },


    "recommendation": {
        "中文说明": "普通商品推荐。",
        "latency_level": "medium",
        "stages": [
            "intent_understanding",
            "constraint_extraction",
            "retrieval",
            "selection_rerank",
            "response_composition"
        ]
    },

    "filtering": {
        "中文说明": "带预算、品牌、功能等条件的商品筛选。",
        "latency_level": "medium",
        "stages": [
            "intent_understanding",
            "constraint_extraction",
            "retrieval",
            "selection_rerank",
            "response_composition"
        ]
    },

    "negative_constraints": {
        "中文说明": "带有不要、排除、不含、除了等反选条件的推荐。",
        "latency_level": "medium",
        "stages": [
            "intent_understanding",
            "constraint_extraction",
            "retrieval",
            "selection_rerank",
            "response_composition"
        ]
    },

    "multi_turn_refinement": {
        "中文说明": "多轮补充条件，例如再便宜点、换个品牌、要轻一点。",
        "latency_level": "medium",
        "stages": [
            "intent_understanding",
            "memory_context",
            "constraint_extraction",
            "retrieval",
            "selection_rerank",
            "response_composition"
        ]
    },

    "product_detail": {
        "中文说明": "商品详情问答，例如这个怎么样、第一个给我介绍下。",
        "latency_level": "medium",
        "stages": [
            "intent_understanding",
            "memory_context",
            "retrieval",
            "response_composition"
        ]
    },

    "comparison": {
        "中文说明": "商品比较，例如第一个和第二个哪个好。",
        "latency_level": "slow",
        "stages": [
            "intent_understanding",
            "memory_context",
            "retrieval",
            "selection_rerank",
            "response_composition"
        ]
    },

    "scenario_bundle": {
        "中文说明": "场景化组合推荐，例如旅行、健身、开学、送礼。",
        "latency_level": "slow",
        "stages": [
            "intent_understanding",
            "constraint_extraction",
            "retrieval",
            "selection_rerank",
            "response_composition"
        ]
    },

    "cart_action": {
        "中文说明": "购物车操作，例如加入购物车、删除第二个、查看购物车。根据子动作选择不同阶段。",
        "latency_level": "fast",
        "stages": [
            "cart_intent_understanding",
            "cart_inventory_check",
            "cart_updating",
            "cart_completion"
        ],
        "sub_action_stages": {
            "cart_add":         ["cart_intent_understanding", "cart_inventory_check", "cart_updating", "cart_completion"],
            "cart_remove":      ["cart_intent_understanding", "cart_updating", "cart_completion"],
            "cart_clear":       ["cart_intent_understanding", "cart_updating", "cart_completion"],
            "cart_view":        ["cart_intent_understanding", "cart_completion"],
            "checkout":         ["cart_intent_understanding", "cart_inventory_check", "cart_checkout_processing", "cart_completion"],
            "default":          ["cart_intent_understanding", "cart_updating", "cart_completion"]
        }
    },

    "multimodal_search": {
        "中文说明": "图片找货或图片加文本检索。",
        "latency_level": "slow",
        "stages": [
            "intent_understanding",
            "constraint_extraction",
            "retrieval",
            "selection_rerank",
            "response_composition"
        ],
        "extra_templates": [
            "我先分析图片里的商品特征。",
            "正在识别商品类别、颜色、款式和风格。",
            "正在结合图片信息和你的文字要求一起检索。",
            "我在查找同款或相似风格商品。"
        ]
    },

    "clarification": {
        "中文说明": "需求模糊，需要主动澄清。",
        "latency_level": "fast",
        "stages": [
            "intent_understanding",
            "constraint_extraction",
            "response_composition"
        ]
    },

    "no_result_with_alternatives": {
        "中文说明": "没有完全匹配，但有相近或放宽条件后的备选商品。",
        "latency_level": "medium",
        "stages": [
            "intent_understanding",
            "constraint_extraction",
            "retrieval",
            "selection_rerank",
            "response_composition"
        ]
    },

    "out_of_scope": {
        "中文说明": "完全超出系统支持范围。",
        "latency_level": "fast",
        "stages": [
            "intent_understanding",
            "response_composition"
        ]
    }

    }

# 根据预计耗时控制 progress 数量和展示节奏。

LATENCY_LEVEL_CONFIG = {
    "fast": {
        "中文说明": "适合本地模板、购物车查看、简单澄清等快速任务。",
        "min_events": 1,
        "max_events": 2,
        "default_display_duration_ms": 500
        },
    "medium": {
        "中文说明": "适合普通推荐、筛选、商品详情问答。",
        "min_events": 3,
        "max_events": 5,
        "default_display_duration_ms": 700
        },
    "slow": {
        "中文说明": "适合复杂比较、场景组合、多模态检索、个性化推荐。",
        "min_events": 4,
        "max_events": 7,
        "default_display_duration_ms": 850
        }
    }

# 特殊场景可优先使用的开场提示。

OPENING_TEMPLATES = {
    "default": [
        "收到，我马上帮你处理。",
        "好的，我先帮你整理一下需求。",
        "可以，我来帮你筛一筛。"
        ],
    "personalized": [
        "收到，我会结合你之前的偏好一起看。",
        "好的，我会按你之前比较关注的点来筛选。",
        "可以，我先结合你的历史需求帮你缩小范围。"
        ],
    "strict_constraints": [
        "收到，我会优先遵守你明确提出的条件。",
        "好的，我会先按你的硬性要求筛选。",
        "可以，我会先排除不符合条件的商品。"
        ],
    "visual": [
        "收到，我先分析图片里的商品特征。",
        "好的，我先看一下图片中的商品信息。",
        "可以，我先结合图片和你的文字需求一起判断。"
        ]
}

# 特殊结束提示，通常在正式结果即将返回前展示。

ENDING_TEMPLATES = {
    "default": [
        "马上给你整理好结果。",
        "正在准备最终回复。",
        "马上把推荐结果发给你。"
    ],
    "products_ready": [
        "商品卡片马上准备好了。",
        "我已经筛出几款可以优先看的商品。",
        "正在把推荐商品和理由整理给你。"
    ],
    "cart_ready": [
        "购物车状态马上更新。",
        "操作结果马上返回。",
        "我正在同步最新购物车信息。"
    ],
    "comparison_ready": [
        "马上给你一个明确结论。",
        "我正在整理关键差异点。",
        "对比结果马上出来。"
    ]
}

# progress event 的标准输出格式建议。

PROGRESS_EVENT_SCHEMA = {
    "event_type": "progress_message",
    "中文说明": "展示系统处理中状态，减少用户等待感。",
    "data": {
        "text": "",
        "stage": "",
        "display_duration_ms": 700,
        "can_be_replaced": True
    }
}

# 文案风格约束：生成 progress events 时应遵守。

PROGRESS_TEXT_RULES = [
    "不要展示模型内部推理过程，只展示外部工作状态。",
    "不要使用“我正在思考我的推理链”等表述。",
    "不要承诺一定能找到商品，应使用“正在查找”“正在筛选”等过程性表达。",
    "不要让 progress 文案比正式回复更长。",
    "真实结果提前返回时，前端应立即停止 progress 展示。",
    "同一轮中尽量避免重复使用相似句子。",
    "多轮对话中可以适当加入记忆读取类提示，但不要暴露过多用户画像细节。"
]
