import json
from datetime import datetime
from pathlib import Path


class PosDraftRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, draft: dict, change_note: str) -> Path:
        draft_id = datetime.now().strftime("POS-DRAFT-%Y%m%d-%H%M%S")
        payload = {
            "draft_id": draft_id,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "change_note": change_note,
            **draft,
        }

        path = self.data_dir / f"{draft_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list_all(self) -> list[dict]:
        items = []
        for path in sorted(self.data_dir.glob("*.json"), reverse=True):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items
