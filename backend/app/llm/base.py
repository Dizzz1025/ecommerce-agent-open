from abc import ABC, abstractmethod
from typing import Any

from app.models.domain import IntentType


class BaseLLMClient(ABC):
    @abstractmethod
    def generate_response(
        self,
        intent: IntentType,
        message: str,
        context: str,
        product_names: list[str],
    ) -> str:
        raise NotImplementedError

    def decide_frontend_action(self, context: dict[str, Any]) -> dict[str, Any]:
        return {}

    def analyze_user_profile(self, context: dict[str, Any]) -> dict[str, Any]:
        return {}

    def resolve_user_intent(self, context: dict[str, Any]) -> dict[str, Any]:
        return {}

    def analyze_image(self, context: dict[str, Any]) -> dict[str, Any]:
        return {}
