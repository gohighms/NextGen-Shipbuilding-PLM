import json
from datetime import datetime
from pathlib import Path


class TagRegistryRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, source_type: str, source_name: str, result: dict) -> Path:
        saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        registry_id = datetime.now().strftime("TAG-%Y%m%d-%H%M%S")
        payload = {
            "registry_id": registry_id,
            "saved_at": saved_at,
            "source_type": source_type,
            "source_name": source_name,
            "tag_count": len(result["tags"]),
            "attributes": result["attributes"],
            "tags": result["tags"],
        }

        path = self.data_dir / f"{registry_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list_all(self) -> list[dict]:
        items = []
        for path in sorted(self.data_dir.glob("*.json"), reverse=True):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items
