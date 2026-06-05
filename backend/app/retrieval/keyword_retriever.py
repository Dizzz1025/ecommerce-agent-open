from app.models.domain import Product
from app.repositories.product_repository import ProductRepository
from app.retrieval.base import BaseRetriever


class KeywordRetriever(BaseRetriever):
    def __init__(self, product_repository: ProductRepository) -> None:
        self.product_repository = product_repository

    def search(self, query: str, top_k: int = 5) -> list[Product]:
        products = self.product_repository.list_products()
        if not query.strip():
            return products[:top_k]

        scored: list[tuple[int, Product]] = []
        for product in products:
            score = self._score_product(query=query, product=product)
            if score > 0:
                scored.append((score, product))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [product for _, product in scored[:top_k]]

    @staticmethod
    def _score_product(query: str, product: Product) -> int:
        normalized_query = query.lower()
        spotlight_terms = [
            *product.spotlight.skin_type,
            *product.spotlight.features,
            *product.spotlight.exclude,
            product.spotlight.description,
        ]
        searchable_terms = [
            product.name,
            product.category,
            product.brand,
            product.reviews_summary,
            *spotlight_terms,
        ]
        haystack = " ".join(searchable_terms).lower()
        score = 0

        if normalized_query in haystack:
            score += 5

        for token in [token.strip().lower() for token in query.split() if token.strip()]:
            if token in haystack:
                score += 2

        for term in searchable_terms:
            normalized_term = term.lower().strip()
            if len(normalized_term) >= 2 and normalized_term in normalized_query:
                score += 1
            for fragment in KeywordRetriever._term_fragments(normalized_term):
                if fragment in normalized_query:
                    score += 1

        return score

    @staticmethod
    def _term_fragments(term: str) -> set[str]:
        fragments: set[str] = set()
        compact = term.replace(" ", "")
        for size in range(2, min(len(compact), 4) + 1):
            for index in range(0, len(compact) - size + 1):
                fragments.add(compact[index : index + size])
        return fragments
