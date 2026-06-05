import json
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> Any:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))

