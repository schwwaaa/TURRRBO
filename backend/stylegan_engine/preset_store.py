"""
backend/stylegan_engine/preset_store.py
Persists user presets as individual JSON files in the presets directory.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional


class PresetStore:
    def __init__(self, presets_dir: Path):
        self._dir = presets_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, preset_id: str) -> Path:
        return self._dir / f"{preset_id}.json"

    def list_all(self) -> List[dict]:
        presets = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                presets.append(json.loads(p.read_text()))
            except Exception:
                pass
        return presets

    def get(self, preset_id: str) -> Optional[dict]:
        p = self._path(preset_id)
        if not p.exists():
            return None
        return json.loads(p.read_text())

    def save(self, preset: dict) -> dict:
        if not preset.get("id"):
            preset["id"] = str(uuid.uuid4())[:8]
        self._path(preset["id"]).write_text(json.dumps(preset, indent=2))
        return preset

    def delete(self, preset_id: str):
        p = self._path(preset_id)
        if p.exists():
            p.unlink()
