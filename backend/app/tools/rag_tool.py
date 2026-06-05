from app.models.domain import Product
from app.models.agent import CandidateProduct
from app.models.domain import SessionState
from app.rag.pipeline import RagPipeline


class RagTool:
    def __init__(self, pipeline: RagPipeline) -> None:
        self.pipeline = pipeline

    def build_context(
        self,
        message: str,
        products: list[Product],
        candidates: list[CandidateProduct] | None = None,
        state: SessionState | None = None,
    ) -> str:
        return self.pipeline.build_context(
            message=message,
            products=products,
            candidates=candidates,
            state=state,
        )
