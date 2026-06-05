from app.models.agent import DialogueFlow, FlowDecision, PlannedTask, TaskPlan, TaskType


class TaskPlanner:
    """Converts flow decisions into deterministic backend steps."""

    def plan(self, decision: FlowDecision) -> TaskPlan:
        flow = decision.flow
        base = [
            self._task(TaskType.PREPROCESS_INPUT, "输入清洗、无效输入和非导购判断"),
            self._task(TaskType.ROUTE_MODEL, "判断规则、本地模板或 Doubao 路由"),
        ]
        if flow in {DialogueFlow.CART_ACTION, DialogueFlow.CHECKOUT}:
            tasks = [
                *base,
                self._task(TaskType.RESOLVE_REFERENCE, "从最近推荐、候选和购物车解析指代"),
                self._task(TaskType.EXECUTE_CART_ACTION, "解析指代并执行购物车工具", data_access=True),
                self._task(TaskType.GENERATE_RESPONSE, "用模板反馈工具执行结果"),
                self._task(TaskType.UPDATE_MEMORY, "同步购物车和对话状态"),
                self._task(TaskType.DISPATCH_FRONTEND_EVENTS, "返回文本和购物车事件"),
            ]
        elif flow == DialogueFlow.CLARIFICATION:
            tasks = [
                *base,
                self._task(TaskType.CLARIFY_USER_NEED, "根据缺失槽位主动追问"),
                self._task(TaskType.UPDATE_MEMORY, "记录待补充槽位"),
                self._task(TaskType.DISPATCH_FRONTEND_EVENTS, "返回澄清事件"),
            ]
        elif flow in {DialogueFlow.CHITCHAT, DialogueFlow.OUT_OF_SCOPE, DialogueFlow.INVALID, DialogueFlow.GREETING}:
            tasks = [
                *base,
                self._task(TaskType.GENERATE_RESPONSE, "短回复并引导回购物场景"),
                self._task(TaskType.UPDATE_MEMORY, "记录普通对话"),
                self._task(TaskType.DISPATCH_FRONTEND_EVENTS, "返回文本事件"),
            ]
        elif flow == DialogueFlow.PREFERENCE_UPDATE:
            tasks = [
                *base,
                self._task(TaskType.SAVE_USER_PREFERENCE, "写入明确长期偏好", data_access=True),
                self._task(TaskType.GENERATE_RESPONSE, "反馈偏好记忆更新结果"),
                self._task(TaskType.UPDATE_MEMORY, "同步长期偏好和 trace"),
                self._task(TaskType.DISPATCH_FRONTEND_EVENTS, "返回文本事件"),
            ]
        elif flow == DialogueFlow.COMPARISON:
            tasks = [
                *base,
                self._task(TaskType.MERGE_CONTEXT, "合并上一轮推荐商品引用"),
                self._task(TaskType.RESOLVE_REFERENCE, "定位比较对象"),
                self._task(TaskType.RETRIEVE_PRODUCTS, "按名称、ID 或指代精确取商品", data_access=True),
                self._task(TaskType.COMPARE_PRODUCTS, "结构化比较价格、卖点、评价风险"),
                self._task(TaskType.GENERATE_RESPONSE, "生成对比解释", llm_call=True),
                self._task(TaskType.VALIDATE_RESPONSE, "校验商品事实"),
                self._task(TaskType.UPDATE_MEMORY, "记录比较对象"),
                self._task(TaskType.DISPATCH_FRONTEND_EVENTS, "返回文本和商品卡片事件"),
            ]
        elif flow == DialogueFlow.PRODUCT_QA:
            tasks = [
                *base,
                self._task(TaskType.RESOLVE_REFERENCE, "定位被询问商品"),
                self._task(TaskType.RETRIEVE_PRODUCTS, "读取商品详情和知识字段", data_access=True),
                self._task(TaskType.ANSWER_PRODUCT_QUESTION, "基于数据库事实回答详情问题"),
                self._task(TaskType.VALIDATE_RESPONSE, "校验事实不越界"),
                self._task(TaskType.UPDATE_MEMORY, "记录查看过的商品"),
                self._task(TaskType.DISPATCH_FRONTEND_EVENTS, "返回文本和商品详情事件"),
            ]
        elif flow == DialogueFlow.SCENE_BUNDLE:
            tasks = [
                *base,
                self._task(TaskType.PLAN_SCENE_BUNDLE, "将场景拆为多个商品子需求"),
                self._task(TaskType.RETRIEVE_PRODUCTS, "按子需求跨类目检索", data_access=True),
                self._task(TaskType.FILTER_PRODUCTS, "过滤不符合约束的结果", data_access=True),
                self._task(TaskType.RERANK_PRODUCTS, "按场景作用和相关性排序"),
                self._task(TaskType.GENERATE_RESPONSE, "生成组合推荐方案", llm_call=True),
                self._task(TaskType.VALIDATE_RESPONSE, "校验商品事实"),
                self._task(TaskType.UPDATE_MEMORY, "保存组合候选"),
                self._task(TaskType.DISPATCH_FRONTEND_EVENTS, "返回文本、场景方案和商品卡片"),
            ]
        else:
            tasks = [
                *base,
                self._task(TaskType.MERGE_CONTEXT, "继承当前类目和活跃约束"),
                self._task(TaskType.EXTRACT_CONSTRAINTS, "合并价格、品牌、功能、否定条件"),
                self._task(TaskType.REWRITE_QUERY, "构造增强检索 query"),
                self._task(TaskType.RETRIEVE_PRODUCTS, "执行结构化过滤、关键词、BGE/text2vec 语义召回", data_access=True),
                self._task(TaskType.FILTER_PRODUCTS, "代码层硬过滤价格、品牌、否定条件", data_access=True),
                self._task(TaskType.RERANK_PRODUCTS, "结合 BGE reranker、约束匹配和偏好重排"),
                self._task(TaskType.GENERATE_RESPONSE, "基于候选商品生成 grounded 回复", llm_call=True),
                self._task(TaskType.VALIDATE_RESPONSE, "校验商品事实不越界"),
                self._task(TaskType.UPDATE_MEMORY, "保存候选、推荐、指代映射和状态"),
                self._task(TaskType.DISPATCH_FRONTEND_EVENTS, "返回文本和商品卡片事件"),
            ]
        return TaskPlan(flow=flow, tasks=tasks)

    @staticmethod
    def _task(
        task_type: TaskType,
        description: str,
        *,
        data_access: bool = False,
        llm_call: bool = False,
    ) -> PlannedTask:
        return PlannedTask(
            task_type=task_type,
            description=description,
            local=not llm_call,
            data_access=data_access,
            llm_call=llm_call,
        )
