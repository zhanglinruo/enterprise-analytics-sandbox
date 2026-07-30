from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any


COLLECTIONS = (
    "spaces",
    "colleagues",
    "tasks",
    "actions",
    "artifacts",
    "approvals",
    "evaluations",
    "events",
)


class JsonStore:
    """Tiny replaceable repository used by the starter demo."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = RLock()

    def initialize(self, reset: bool = False) -> None:
        with self._lock:
            if reset or not self.path.exists():
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._write({name: [] for name in COLLECTIONS})

    def all(self, collection: str) -> list[dict[str, Any]]:
        self._validate(collection)
        with self._lock:
            return list(self._read()[collection])

    def get(self, collection: str, item_id: str) -> dict[str, Any] | None:
        return next((item for item in self.all(collection) if item["id"] == item_id), None)

    def add(self, collection: str, item: dict[str, Any]) -> dict[str, Any]:
        self._validate(collection)
        with self._lock:
            data = self._read()
            data[collection].append(item)
            self._write(data)
        return item

    def update(self, collection: str, item_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        self._validate(collection)
        with self._lock:
            data = self._read()
            for item in data[collection]:
                if item["id"] == item_id:
                    item.update(changes)
                    self._write(data)
                    return item
        raise KeyError(f"{collection}/{item_id} not found")

    def clear_runtime(self) -> None:
        with self._lock:
            data = self._read()
            for name in ("tasks", "actions", "artifacts", "approvals", "evaluations", "events"):
                data[name] = []
            self._write(data)

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return self._read()

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def _validate(collection: str) -> None:
        if collection not in COLLECTIONS:
            raise ValueError(f"Unknown collection: {collection}")

