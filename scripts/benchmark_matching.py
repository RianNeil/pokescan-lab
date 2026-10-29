"""Measure repeatable card matches for several saved sample photos."""

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pokescan.card_matching import MODEL_NAME, MODEL_SETTINGS, CardMatcher


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photos", nargs="+", type=Path, help="Saved card photos to compare")
    parser.add_argument(
        "--expected-id",
        action="append",
        default=[],
        help="Known TCGdex card ID for a photo, in photo order; repeat for each known card",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for a local JSON experiment report (keep it off GitHub if it contains photos)",
    )
    args = parser.parse_args()
    if args.expected_id and len(args.expected_id) != len(args.photos):
        parser.error("Pass one --expected-id for every photo, in the same order.")

    started = time.perf_counter()
    matcher = CardMatcher()
    setup_ms = round((time.perf_counter() - started) * 1000, 1)
    results = []
    for index, photo in enumerate(args.photos):
        match = matcher.match_photo(photo)
        expected = args.expected_id[index] if args.expected_id else None
        guesses = match["guesses"]
        results.append(
            {
                "photo": str(photo),
                "expected_id": expected,
                "top_guess_correct": bool(guesses and guesses[0]["id"] == expected)
                if expected
                else None,
                **match,
            }
        )

    report = {
        "model": MODEL_NAME,
        "settings": MODEL_SETTINGS,
        "initial_setup_ms_including_reference_embeddings": setup_ms,
        "samples": results,
        "note": "Per-photo matching_ms includes preprocessing and one model run; startup builds embeddings if missing.",
    }
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
