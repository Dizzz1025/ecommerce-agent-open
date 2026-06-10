import re

from app.models.agent import CandidateProduct, ParsedQuery, ProductQAResult
from app.models.domain import Product


class ProductQAModule:
    """Answers product detail questions from stored product facts."""

    def answer(
        self,
        *,
        parsed_query: ParsedQuery,
        products: list[Product],
        candidates: list[CandidateProduct],
    ) -> ProductQAResult:
        if not products:
            return ProductQAResult(
                answered=False,
                answer="我还没确定你问的是哪款商品，可以说“第一款”或点开商品后再问。",
                missing_field="product_reference",
            )
        product = products[0]
        question = parsed_query.raw_message
        document = product.searchable_text
        evidence = self._collect_evidence(question, product)
        candidate = next((item for item in candidates if item.sku_id == product.sku_id), None)

        if any(term in question for term in ["适合敏感肌", "敏感肌能用", "会刺激"]):
            return self._contains_answer(
                product,
                document,
                include_terms=["敏感肌"],
                positive_answer=f"{product.name} 的商品信息中提到了敏感肌相关内容，但建议先做局部测试；",
                question_tail="如果你是高敏肤质，我建议优先选择明确标注温和、低刺激的产品。",
                evidence=evidence,
            )

        if any(term in question for term in ["续航", "能用多久", "电池", "耗电", "充电", "快充"]):
            return self._field_answer(product, question, "续航", evidence, extra_terms=["电池", "耗电", "满电", "快充", "充电", "一整天"])
        if any(term in question for term in ["材质", "面料", "什么料"]):
            return self._field_answer(product, question, "材质/面料", evidence, extra_terms=["棉", "AIRism", "针织", "PP材质", "铝合金"])
        if any(term in question for term in ["14寸", "电脑", "容量", "能放"]):
            return self._field_answer(product, question, "容量/尺寸", evidence, extra_terms=["14寸", "容量", "尺寸", "电脑"])
        if any(term in question for term in ["含酒精", "酒精", "乙醇"]):
            return self._contains_answer(
                product,
                document,
                include_terms=["酒精"],
                positive_answer=f"{product.name} 的当前商品信息中出现了“酒精”相关描述，建议谨慎；",
                question_tail="如果你明确要避开酒精，我会把它作为排除条件。",
                evidence=evidence,
            )
        if any(term in question for term in ["成分", "配方", "功效通路"]):
            return self._field_answer(product, question, "成分/配方", evidence, extra_terms=["成分", "配方", "二裂酵母", "Pitera", "PITERA", "烟酰胺", "玻色因", "A醇", "修护"])
        if any(term in question for term in ["适用场景", "使用场景", "场景", "适合什么时候"]):
            if product.suitable_scenarios:
                return ProductQAResult(
                    answered=True,
                    answer=f"{product.name} 更适合这些场景：" + "、".join(product.suitable_scenarios[:5]) + "。",
                    product_ids=[product.sku_id],
                    evidence=[*evidence, "适用场景：" + "、".join(product.suitable_scenarios[:5])],
                )
            return self._field_answer(product, question, "适用场景", evidence, extra_terms=["通勤", "旅行", "办公", "健身", "日常", "妆前", "修护"])
        if any(term in question for term in ["新手", "小白", "入门"]):
            return self._field_answer(product, question, "新手适配", evidence, extra_terms=["新手", "入门", "日常", "简单"])
        if any(term in question for term in ["低糖", "无糖", "糖"]):
            return self._field_answer(product, question, "糖分/版本", evidence, extra_terms=["低糖", "无糖", "糖"])
        if "库存" in question:
            return ProductQAResult(
                answered=True,
                answer=f"{product.name} 在 Demo 商品库里的静态库存字段为 {product.stock}。这不是实时库存接口结果，实际下单前仍建议以前端商品详情或库存服务为准。",
                product_ids=[product.sku_id],
                evidence=[f"stock={product.stock}"],
            )

        if self._is_general_intro_question(question):
            intro_evidence = self._build_intro_evidence(product, parsed_query, candidate)
            return ProductQAResult(
                answered=True,
                answer=self._intro_answer(product, intro_evidence),
                product_ids=[product.sku_id],
                evidence=intro_evidence,
            )

        if evidence:
            return ProductQAResult(
                answered=True,
                answer=f"关于 {product.name}，我从商品信息里找到这些相关内容：{evidence[0]}",
                product_ids=[product.sku_id],
                evidence=evidence,
            )
        return ProductQAResult(
            answered=False,
            answer="这项细节商品库暂时没有直接字段；我可以先帮你看价格、规格、适用场景或评价反馈这些已知信息。",
            product_ids=[product.sku_id],
            missing_field="unknown_detail",
        )

    @staticmethod
    def _is_general_intro_question(question: str) -> bool:
        intro_terms = [
            "介绍", "介绍下", "介绍一下", "讲讲", "说说", "展开说", "具体说说",
            "怎么样", "如何", "不错", "第一款呢", "第二款呢", "第三款呢",
            "第一个呢", "第二个呢", "第三个呢", "值得买吗", "适合我吗",
        ]
        return any(term in question for term in intro_terms)

    def _build_intro_evidence(
        self,
        product: Product,
        parsed_query: ParsedQuery,
        candidate: CandidateProduct | None = None,
    ) -> list[str]:
        dimensions = self._select_intro_dimensions(product, parsed_query, candidate)
        evidence: list[str] = [
            f"基础信息：{product.name}，品牌 {product.brand}，价格 ¥{product.price:g}，类目 {product.category}/{product.sub_category or '未标注'}。",
        ]
        if candidate and candidate.matched_reasons:
            needs = [
                _clean_need_text(item)
                for item in candidate.matched_reasons
                if _clean_need_text(item)
            ][:4]
            if needs:
                evidence.append("匹配本轮需求：" + "、".join(needs) + "。")
        if product.highlight_short:
            evidence.append(f"一句话亮点：{product.highlight_short}")
        if product.suitable_scenarios:
            evidence.append("适用场景：" + "、".join(product.suitable_scenarios[:5]) + "。")
        if product.target_user_tags:
            evidence.append("适合人群：" + "、".join(product.target_user_tags[:5]) + "。")
        if product.non_standard_query_tags:
            matched_tags = [
                tag for tag in product.non_standard_query_tags
                if any(term and term in tag for term in re.findall(r"[\u4e00-\u9fff]{2,4}|[A-Za-z0-9]+", parsed_query.raw_message))
            ]
            if matched_tags:
                evidence.append("相关问题标签：" + "、".join(matched_tags[:3]) + "。")
        if product.tags:
            evidence.append("商品标签：" + "、".join(product.tags[:8]) + "。")
        for dimension, terms in dimensions:
            snippets = self._collect_term_evidence(product, terms)
            if snippets:
                evidence.append(f"{dimension}：{snippets[0]}")
        if product.reviews_summary:
            evidence.append(f"评价反馈：{product.reviews_summary}")
        knowledge = product.rag_knowledge
        marketing = str(knowledge.get("marketing_description", "")).strip()
        if marketing and not any(marketing[:30] in item for item in evidence):
            evidence.append("官方描述：" + re.sub(r"\s+", "", marketing)[:220])
        return list(dict.fromkeys(evidence))[:6]

    def _select_intro_dimensions(
        self,
        product: Product,
        parsed_query: ParsedQuery,
        candidate: CandidateProduct | None = None,
    ) -> list[tuple[str, list[str]]]:
        question = parsed_query.raw_message
        candidate_terms = candidate.matched_reasons if candidate else []
        need_text = " ".join([question, *parsed_query.positive_constraints, *candidate_terms])
        dimension_terms: list[tuple[str, list[str]]] = []
        candidates = [
            ("影像/拍照", ["影像", "拍照", "主摄", "长焦", "夜拍", "人像", "自拍", "视频", "相机"]),
            ("续航/充电", ["续航", "电池", "快充", "充电", "满电", "一整天", "120W", "100W"]),
            ("屏幕/观感", ["屏幕", "2K", "高刷", "护眼", "PWM", "亮度", "色彩"]),
            ("性能/使用流畅度", ["处理器", "性能", "游戏", "高性能", "芯片", "LPDDR", "UFS"]),
            ("肤质/适配人群", ["油皮", "混油皮", "干皮", "敏感肌", "学生党", "男士", "儿童", "小朋友", "肤质"]),
            ("功效/肤感", ["保湿", "补水", "修护", "控油", "温和", "清爽", "轻薄", "不油腻", "不黏腻", "屏障", "提亮"]),
            ("成分/配方", ["成分", "配方", "玻尿酸", "透明质酸", "烟酰胺", "神经酰胺", "A醇", "酒精", "香精"]),
            ("容量/收纳", ["容量", "尺寸", "电脑", "收纳", "大容量", "28L", "15寸", "14寸"]),
            ("材质/穿着体验", ["材质", "面料", "透气", "速干", "凉感", "棉", "针织"]),
            ("口味/配料", ["口味", "低糖", "无糖", "糖", "配料", "咖啡因", "甜"]),
            ("适用场景", ["通勤", "旅行", "户外", "办公", "学习", "健身", "日常", "学生"]),
        ]
        explicit = [
            item for item in candidates
            if any(term in question for term in item[1])
        ]
        if explicit:
            dimension_terms.extend(explicit)
        else:
            if product.sub_category == "智能手机":
                preferred = ["影像/拍照", "续航/充电", "屏幕/观感"]
            elif product.sub_category in {"真无线耳机"}:
                preferred = ["续航/充电", "适用场景"]
            elif product.category == "服饰运动":
                preferred = ["容量/收纳", "材质/穿着体验", "适用场景"]
            elif product.category == "食品饮料":
                preferred = ["口味/配料", "适用场景"]
            elif product.category == "美妆护肤":
                preferred = ["肤质/适配人群", "功效/肤感", "成分/配方"]
            else:
                preferred = ["适用场景", "材质/穿着体验"]
            dimension_terms.extend([item for item in candidates if item[0] in preferred])

        for item in candidates:
            if item in dimension_terms:
                continue
            if any(term in need_text for term in item[1]):
                dimension_terms.append(item)
        return dimension_terms[:3]

    @staticmethod
    def _intro_answer(product: Product, evidence: list[str]) -> str:
        useful_evidence = [item for item in evidence if not item.startswith("商品标签")]
        details = [item.split("：", 1)[-1].strip("。") for item in useful_evidence[1:4]]
        first = f"可以的，这款是 {product.name}，售价 ¥{product.price:g}。"
        if len(useful_evidence) > 1 and useful_evidence[1].startswith("匹配本轮需求") and details:
            second = f"它比较贴合你对{details[0]}的需求。"
        else:
            second = f"它的主要亮点是{details[0]}。" if details else "它属于当前商品库里和你刚才需求相关的候选商品。"
        if len(details) >= 2:
            third = f"另外，{details[1]}，你可以结合商品卡片里的图片和参数一起看。"
        else:
            third = "你可以结合商品卡片里的图片、参数和评价摘要一起判断是否适合。"
        return "\n".join([first, second, third])

    def _field_answer(
        self,
        product: Product,
        question: str,
        field_name: str,
        evidence: list[str],
        extra_terms: list[str] | None = None,
    ) -> ProductQAResult:
        terms = [field_name, *(extra_terms or [])]
        matched = [item for item in [*evidence, *self._collect_term_evidence(product, terms)] if any(term in item for term in terms)]
        if matched:
            return ProductQAResult(
                answered=True,
                answer=f"{product.name} 关于{field_name}的信息是：{matched[0]}",
                product_ids=[product.sku_id],
                evidence=matched,
            )
        return ProductQAResult(
            answered=False,
            answer=f"{field_name} 这个参数商品库暂时没有直接字段；我可以继续帮你看已有规格、价格或评价摘要。",
            product_ids=[product.sku_id],
            evidence=evidence,
            missing_field=field_name,
        )

    def _contains_answer(
        self,
        product: Product,
        document: str,
        *,
        include_terms: list[str],
        positive_answer: str,
        question_tail: str,
        evidence: list[str],
    ) -> ProductQAResult:
        if any(term in document for term in include_terms):
            return ProductQAResult(
                answered=True,
                answer=positive_answer + question_tail,
                product_ids=[product.sku_id],
                evidence=evidence,
            )
        return ProductQAResult(
            answered=False,
            answer=f"“{'/'.join(include_terms)}”这项信息商品库暂时没有直接字段；我可以先基于已有规格、价格和评价帮你判断是否值得看。",
            product_ids=[product.sku_id],
            evidence=evidence,
            missing_field="/".join(include_terms),
        )

    @staticmethod
    def _collect_evidence(question: str, product: Product) -> list[str]:
        snippets: list[str] = []
        knowledge = product.rag_knowledge
        text_blocks = [
            product.highlight_short,
            product.highlight_detail,
            " ".join(product.suitable_scenarios),
            " ".join(product.target_user_tags),
            " ".join(product.non_standard_query_tags),
            knowledge.get("marketing_description", ""),
            product.reviews_summary,
        ]
        for faq in knowledge.get("official_faq", []):
            text_blocks.append(f"{faq.get('question', '')} {faq.get('answer', '')}")
        question_terms = set(re.findall(r"[\u4e00-\u9fff]{2,4}|[A-Za-z0-9]+", question))
        for block in text_blocks:
            compact = re.sub(r"\s+", "", block)
            if not compact:
                continue
            if any(term and term in compact for term in question_terms):
                snippets.append(compact[:140] + ("..." if len(compact) > 140 else ""))
        return snippets[:3]

    @staticmethod
    def _collect_term_evidence(product: Product, terms: list[str]) -> list[str]:
        snippets: list[str] = []
        knowledge = product.rag_knowledge
        text_blocks = [
            product.highlight_short,
            product.highlight_detail,
            " ".join(product.suitable_scenarios),
            " ".join(product.target_user_tags),
            " ".join(product.non_standard_query_tags),
            knowledge.get("marketing_description", ""),
            product.reviews_summary,
        ]
        for sku in product.skus:
            if sku.properties:
                text_blocks.append(" ".join(str(value) for value in sku.properties.values()))
        for faq in knowledge.get("official_faq", []):
            question = str(faq.get("question", ""))
            answer = str(faq.get("answer", ""))
            combined = f"{question} {answer}"
            if any(term and term in combined for term in terms):
                text_blocks.append(answer or combined)
                continue
        for block in text_blocks:
            compact = re.sub(r"\s+", "", block)
            if not compact:
                continue
            if any(term and term in compact for term in terms):
                snippets.append(compact[:180] + ("..." if len(compact) > 180 else ""))
        return snippets[:3]


def _clean_need_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    blocked = {"类目一致", "已排除否定条件", "已避开指定品牌", "匹配度一般，作为备选", "来自上一轮推荐或用户指代"}
    if not text or text in blocked:
        return ""
    return (
        text.removeprefix("匹配")
        .removeprefix("贴合问题标签:")
        .removeprefix("购物车偏好:")
        .strip()
    )
