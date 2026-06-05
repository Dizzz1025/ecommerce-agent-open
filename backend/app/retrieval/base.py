from abc import ABC, abstractmethod

from app.models.domain import Product


class BaseRetriever(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[Product]:
        raise NotImplementedError

