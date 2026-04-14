import json
from datetime import datetime
from pathlib import Path


class WorkInstructionRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, payload: dict) -> Path:
        instruction_id = datetime.now().strftime("WORKINST-%Y%m%d-%H%M%S")
        data = {
            "instruction_id": instruction_id,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **payload,
        }
        path = self.data_dir / f"{instruction_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list_all(self) -> list[dict]:
        items = []
        for path in sorted(self.data_dir.glob("*.json"), reverse=True):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items
