from app.models.domain import Product
from app.models.agent import CandidateProduct, ParsedQuery
from app.models.domain import SessionState
from app.retrieval.base import BaseRetriever
from app.retrieval.hybrid_retriever import HybridRetriever


class ProductSearchTool:
    def __init__(self, retriever: BaseRetriever) -> None:
        self.retriever = retriever

    def search(self, query: str, top_k: int = 5) -> list[Product]:
        return self.retriever.search(query=query, top_k=top_k)

    def retrieve_candidates(
        self,
        parsed_query: ParsedQuery,
        state: SessionState | None,
        top_k: int = 5,
    ) -> list[CandidateProduct]:
        if isinstance(self.retriever, HybridRetriever):
            return self.retriever.retrieve(parsed_query=parsed_query, state=state, top_k=top_k)
        products = self.retriever.search(query=parsed_query.rewritten_query or parsed_query.raw_message, top_k=top_k)
        return [
            CandidateProduct(
                candidate_id=f"c_{product.sku_id}",
                product_id=product.product_id or product.sku_id,
                sku_id=product.sku_id,
                name=product.name,
                brand=product.brand,
                category=product.category,
                sub_category=product.sub_category,
                price=product.price,
                image_url=product.image_url,
                matched_reasons=["关键词匹配"],
                score=1.0 - index * 0.05,
            )
            for index, product in enumerate(products)
        ]

    def retrieve_reference_candidates(
        self,
        parsed_query: ParsedQuery,
        state: SessionState,
        top_k: int = 5,
    ) -> list[CandidateProduct]:
        if isinstance(self.retriever, HybridRetriever):
            return self.retriever.retrieve_by_references(parsed_query=parsed_query, state=state, top_k=top_k)
        return self.retrieve_candidates(parsed_query=parsed_query, state=state, top_k=top_k)
