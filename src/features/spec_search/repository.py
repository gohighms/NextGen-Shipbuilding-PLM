import json
from pathlib import Path

from src.features.spec_search.models import SpecDocument


class SpecRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def list_all(self) -> list[SpecDocument]:
        items = []
        for path in sorted(self.data_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            items.append(SpecDocument(**payload))
        return items
