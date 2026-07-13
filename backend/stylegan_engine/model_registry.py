"""
backend/stylegan_engine/model_registry.py
Loads model metadata from model_card.json files.
Accepts an explicit directory — in bundled builds this comes from --models-dir.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class ModelRegistry:
    def __init__(self, models_dir: Path):
        self._dir = Path(models_dir)
        self._cache: Dict[str, dict] = {}
        self._scan()

    def _scan(self):
        self._cache.clear()
        if not self._dir.exists():
            print(f"[ModelRegistry] directory not found: {self._dir}")
            return

        for card_path in sorted(self._dir.glob("*/model_card.json")):
            try:
                card = json.loads(card_path.read_text())
                model_id = card.get("id")
                if not model_id:
                    continue
                # Resolve checkpoint relative to the card's folder
                checkpoint = card.get("checkpoint_file", "")
                if not Path(checkpoint).is_absolute():
                    checkpoint = str(card_path.parent / checkpoint)
                card["checkpoint_file"] = checkpoint
                self._cache[model_id] = card
            except Exception as e:
                print(f"[ModelRegistry] failed to load {card_path}: {e}")

        print(f"[ModelRegistry] {len(self._cache)} models in {self._dir}")

    def list_all(self) -> List[dict]:
        return list(self._cache.values())

    def get(self, model_id: str) -> Optional[dict]:
        return self._cache.get(model_id)

    def refresh(self):
        self._scan()
