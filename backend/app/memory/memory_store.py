from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class MemoryStore(ABC, Generic[T]):
    @abstractmethod
    def get(self, key: str) -> T | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, key: str, value: T) -> T:
        raise NotImplementedError

