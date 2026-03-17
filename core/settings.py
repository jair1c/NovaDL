import json
from dataclasses import asdict
from pathlib import Path

from core.constants import SETTINGS_FILE


class Settings:
    @staticmethod
    def load() -> dict:
        if SETTINGS_FILE.exists():
            try:
                return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @staticmethod
    def save(data: dict) -> None:
        SETTINGS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


class HistoryStore:
    @staticmethod
    def load(path: Path, dataclass_type):
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                return [dataclass_type(**item) for item in raw]
            except Exception:
                return []
        return []

    @staticmethod
    def save(path: Path, items: list) -> None:
        path.write_text(
            json.dumps([asdict(x) for x in items], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
