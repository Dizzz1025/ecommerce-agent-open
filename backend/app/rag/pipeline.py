from app.models.domain import Product
from app.models.agent import CandidateProduct
from app.models.domain import SessionState
from app.rag.knowledge_formatter import KnowledgeFormatter
from app.rag.prompt_builder import PromptBuilder


class RagPipeline:
    def __init__(
        self,
        knowledge_formatter: KnowledgeFormatter | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.knowledge_formatter = knowledge_formatter or KnowledgeFormatter()
        self.prompt_builder = prompt_builder or PromptBuilder()

    def build_context(
        self,
        message: str,
        products: list[Product],
        candidates: list[CandidateProduct] | None = None,
        state: SessionState | None = None,
        personalization_context: dict | None = None,
        multimodal_context: dict | None = None,
    ) -> str:
        product_facts = self.knowledge_formatter.format_products(products, candidates=candidates)
        return self.prompt_builder.build(
            message=message,
            product_facts=product_facts,
            products=products,
            state=state,
            personalization_context=personalization_context,
            multimodal_context=multimodal_context,
        )
