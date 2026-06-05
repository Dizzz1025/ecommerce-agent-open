from app.memory.memory_store import MemoryStore


class InMemoryStore(MemoryStore[object]):
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        return self._data.get(key)

    def save(self, key: str, value: object) -> object:
        self._data[key] = value
        return value

