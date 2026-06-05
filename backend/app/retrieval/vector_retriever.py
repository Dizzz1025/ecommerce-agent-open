from app.models.domain import Product
from app.ml.local_models import LocalModelManager
from app.repositories.product_repository import ProductRepository
from app.retrieval.base import BaseRetriever
from app.retrieval.document_builder import ProductDocumentBuilder


class VectorRetriever(BaseRetriever):
    """Standalone local embedding retriever used by experiments and tests."""

    def __init__(
        self,
        *,
        product_repository: ProductRepository,
        local_models: LocalModelManager,
        document_builder: ProductDocumentBuilder | None = None,
    ) -> None:
        self.product_repository = product_repository
        self.local_models = local_models
        self.document_builder = document_builder or ProductDocumentBuilder()

    def search(self, query: str, top_k: int = 5) -> list[Product]:
        products = self.product_repository.list_products()
        documents = [self.document_builder.build_text(product) for product in products]
        score_map = self.local_models.semantic_scores(query, documents)
        scores = score_map.get("bge_embedding") or score_map.get("text2vec_embedding") or []
        if not scores:
            return products[:top_k]
        ranked = sorted(zip(scores, products, strict=False), key=lambda item: item[0], reverse=True)
        return [product for _, product in ranked[:top_k]]
