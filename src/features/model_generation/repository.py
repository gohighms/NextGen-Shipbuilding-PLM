import json
from pathlib import Path


class ModelRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def list_all(self) -> list[dict]:
        items = []
        for path in sorted(self.data_dir.glob("*.json")):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items

    def find_by_source_spec_id(self, spec_id: str) -> list[dict]:
        return [item for item in self.list_all() if item.get("source_spec_id") == spec_id]
