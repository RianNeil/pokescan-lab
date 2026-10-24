"""Download the selected TCGdex card references for local/offline use."""

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "starter_cards.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "reference_library"
API_ROOT = "https://api.tcgdex.net/v2"
TIMEOUT_SECONDS = 25


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "PokeScan-Lab/0.1 (school STEM project)"})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError(f"TCGdex returned an unexpected response for {url}")
    return payload


def download_image(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "PokeScan-Lab/0.1 (school STEM project)"})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        content_type = response.headers.get_content_type()
        image_bytes = response.read()

    if content_type != "image/webp" or not image_bytes.startswith(b"RIFF") or image_bytes[8:12] != b"WEBP":
        raise ValueError(f"Expected a WebP image from TCGdex, got {content_type} at {url}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp_file:
        temp_file.write(image_bytes)
        temp_path = Path(temp_file.name)
    os.replace(temp_path, destination)


def build_index(manifest_path: Path, output_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cards = manifest.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValueError(f"The starter-card manifest is empty or invalid: {manifest_path}")

    image_dir = output_path / "images"
    indexed_cards: list[dict[str, Any]] = []
    for selection in cards:
        card_id = selection["id"]
        language = selection.get("language", "en")
        api_url = f"{API_ROOT}/{language}/cards/{card_id}"
        try:
            card = fetch_json(api_url)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"Could not load {selection['name']} ({card_id}) from TCGdex: {error}") from error

        if card.get("error") or card.get("id") != card_id:
            raise ValueError(f"TCGdex did not return the selected card {card_id}: {card.get('error', 'ID mismatch')}")
        image_base_url = card.get("image")
        if not isinstance(image_base_url, str) or not image_base_url.startswith("https://assets.tcgdex.net/"):
            raise ValueError(f"TCGdex has no usable reference image for {card_id}")

        image_url = f"{image_base_url}/high.webp"
        image_path = image_dir / f"{card_id}.webp"
        try:
            download_image(image_url, image_path)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"Could not download the image for {selection['name']} ({card_id}): {error}") from error

        card_set = card.get("set") or {}
        indexed_cards.append(
            {
                "id": card_id,
                "name": selection["name"],
                "tcgdex_name": card.get("name"),
                "set": selection["set"],
                "tcgdex_set": card_set.get("name"),
                "number": selection["number"],
                "tcgdex_local_id": card.get("localId"),
                "language": language,
                "tcgdex_api_url": api_url,
                "reference_image_source": image_base_url,
                "download_url": image_url,
                "local_image": f"images/{card_id}.webp",
                "image_format": "webp",
                "source": "TCGdex",
                "note": selection.get("note"),
            }
        )
        print(f"Saved {selection['name']} ({card_id})")

    output_path.mkdir(parents=True, exist_ok=True)
    index = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_source": "TCGdex",
        "api_documentation": "https://tcgdex.dev/rest/card",
        "image_documentation": "https://tcgdex.dev/assets",
        "manifest_source": manifest.get("source_url"),
        "artwork_note": "Card artwork belongs to its rights holders. Keep these local experiment references out of public code releases.",
        "cards": indexed_cards,
    }
    index_path = output_path / "index.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the 10 chosen TCGdex references for offline scanning.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="JSON list of selected TCGdex card IDs")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Folder for downloaded images and index")
    args = parser.parse_args()
    index_path = build_index(args.manifest, args.output)
    print(f"Done. Local index saved to: {index_path}")


if __name__ == "__main__":
    main()
