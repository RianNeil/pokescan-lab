"""Create local, cleaned-up previews of camera photos or reference pictures."""

import argparse
from pathlib import Path
import sys

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pokescan.image_preprocessing import (
    OUTPUT_HEIGHT,
    OUTPUT_WIDTH,
    SUPPORTED_IMAGE_SUFFIXES,
    preprocess_card_image,
    read_image,
)


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "preprocessed"


def _fit_on_canvas(image, width: int = OUTPUT_WIDTH, height: int = OUTPUT_HEIGHT):
    """Resize an image to fit on a fixed canvas without stretching it."""
    source_height, source_width = image.shape[:2]
    scale = min(width / source_width, height / source_height)
    resized = cv2.resize(
        image,
        (max(1, round(source_width * scale)), max(1, round(source_height * scale))),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
    )
    canvas = np.full((height, width, 3), 32, dtype=np.uint8)
    y = (height - resized.shape[0]) // 2
    x = (width - resized.shape[1]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def _save_comparison(original, processed, path: Path) -> None:
    left = _fit_on_canvas(original)
    right = _fit_on_canvas(processed)
    comparison = cv2.hconcat((left, right))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), comparison):
        raise OSError(f"Could not save comparison image: {path}")


def _input_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    if source.is_dir():
        return sorted(path for path in source.iterdir() if path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES)
    raise FileNotFoundError(f"Image or folder not found: {source}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crop and normalize card pictures. The original pictures are never changed."
    )
    parser.add_argument("source", type=Path, help="One image file or a folder of images")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="Where to save processed copies")
    parser.add_argument(
        "--reference-images",
        action="store_true",
        help="Use for TCGdex reference pictures that already show only the card",
    )
    args = parser.parse_args()

    paths = _input_files(args.source)
    if not paths:
        raise SystemExit(f"No supported images found in {args.source}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for source_path in paths:
        original = read_image(source_path)
        result = preprocess_card_image(original, detect_card=not args.reference_images)
        output_path = args.output_dir / f"{source_path.stem}.jpg"
        if not cv2.imwrite(str(output_path), result.image):
            raise OSError(f"Could not save processed image: {output_path}")
        comparison_path = args.output_dir / f"{source_path.stem}-comparison.jpg"
        _save_comparison(original, result.image, comparison_path)

        if args.reference_images:
            print(f"Processed reference: {source_path.name}")
        elif result.card_edge_found:
            print(f"Detected and cropped card: {source_path.name}")
        else:
            print(f"Warning: card outline not found; kept full photo: {source_path.name}")
        print(f"  Processed copy: {output_path}")
        print(f"  Side-by-side preview: {comparison_path}")


if __name__ == "__main__":
    main()
