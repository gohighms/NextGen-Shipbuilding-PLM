import json
from pathlib import Path


class PosRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def list_all(self) -> list[dict]:
        items = []
        for path in sorted(self.data_dir.glob("*.json")):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items
