from app.models.domain import Product


class ProductDocumentBuilder:
    def build_text(self, product: Product) -> str:
        sku_text = " ".join(
            " ".join(str(value) for value in sku.properties.values())
            for sku in product.skus
        )
        return " ".join(
            [
                f"商品名:{product.name}",
                f"品牌:{product.brand}",
                f"类目:{product.category}",
                f"子类目:{product.sub_category or ''}",
                f"价格:{product.price:g}",
                f"规格:{sku_text}",
                f"标签:{' '.join(product.tags)}",
                f"卖点:{product.spotlight.description}",
                f"商品亮点:{product.product_highlight}",
                f"一句话亮点:{product.highlight_short}",
                f"推荐解释:{product.highlight_detail}",
                f"适用场景:{' '.join(product.suitable_scenarios)}",
                f"人群标签:{' '.join(product.target_user_tags)}",
                f"非标准问题标签:{' '.join(product.non_standard_query_tags)}",
                f"评价:{product.reviews_summary}",
                product.searchable_text,
            ]
        )
