from app.models.domain import Product
from app.repositories.product_repository import ProductRepository


class ProductService:
    def __init__(self, product_repository: ProductRepository) -> None:
        self.product_repository = product_repository

    def list_products(
        self,
        query: str | None = None,
        limit: int = 20,
        category: str | None = None,
        sub_category: str | None = None,
        brand: str | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
    ) -> list[Product]:
        products = self.product_repository.list_products()
        filtered = []
        for product in products:
            if category and category not in product.category:
                continue
            if sub_category and (not product.sub_category or sub_category not in product.sub_category):
                continue
            if brand and brand not in product.brand:
                continue
            if price_min is not None and product.price < price_min:
                continue
            if price_max is not None and product.price > price_max:
                continue
            filtered.append(product)

        if not query:
            return filtered[:limit]
        lowered = query.lower()
        matched = [
            product
            for product in filtered
            if self._product_matches(product, lowered)
        ]
        return matched[:limit]

    def get_product(self, sku_id: str) -> Product | None:
        return self.product_repository.get_product(sku_id)

    @staticmethod
    def _product_matches(product: Product, lowered_query: str) -> bool:
        spotlight_terms = [
            *product.spotlight.skin_type,
            *product.spotlight.features,
            *product.spotlight.exclude,
            product.spotlight.description,
            product.sub_category or "",
            product.searchable_text,
        ]
        haystack = " ".join(
            [
                product.name,
                product.brand,
                product.category,
                product.reviews_summary,
                *spotlight_terms,
            ]
        ).lower()
        return lowered_query in haystack
