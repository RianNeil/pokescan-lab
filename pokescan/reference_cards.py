"""Read the locally saved starter-card reference index."""

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_PATH = PROJECT_ROOT / "data" / "reference_library" / "index.json"


def load_reference_cards(index_path: Path = DEFAULT_INDEX_PATH) -> list[dict[str, Any]]:
    """Load the saved index without needing an internet connection."""
    with index_path.open(encoding="utf-8") as index_file:
        index = json.load(index_file)

    cards = index.get("cards") if isinstance(index, dict) else None
    if not isinstance(cards, list):
        raise ValueError(f"Reference index has no card list: {index_path}")
    return cards


def find_reference_card(card_id: str, index_path: Path = DEFAULT_INDEX_PATH) -> dict[str, Any] | None:
    """Find one saved card by its TCGdex ID."""
    return next((card for card in load_reference_cards(index_path) if card.get("id") == card_id), None)
