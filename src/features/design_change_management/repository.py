import json
from datetime import datetime
from pathlib import Path


class DesignChangeRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, change_request: dict) -> Path:
        request_id = datetime.now().strftime("DCR-%Y%m%d-%H%M%S")
        payload = {
            "request_id": request_id,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **change_request,
        }
        path = self.data_dir / f"{request_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list_all(self) -> list[dict]:
        items = []
        for path in sorted(self.data_dir.glob("*.json"), reverse=True):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items
