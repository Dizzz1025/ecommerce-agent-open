from typing import Any

from pydantic import BaseModel, Field


class SSEEvent(BaseModel):
    event: str
    data: dict[str, Any] = Field(default_factory=dict)
    id: str | None = None

