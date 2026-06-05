import json

from app.models.events import SSEEvent


def format_sse(event: SSEEvent) -> str:
    lines = []
    if event.id is not None:
        lines.append(f"id: {event.id}")
    lines.append(f"event: {event.event}")
    lines.append(f"data: {json.dumps(event.data, ensure_ascii=False)}")
    return "\n".join(lines) + "\n\n"

