"""Make camera photos and saved card references more alike before matching."""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


# TCGdex's high-quality card pictures are 600 by 825 pixels.
OUTPUT_WIDTH = 600
OUTPUT_HEIGHT = 825
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class PreprocessingResult:
    """The cleaned image and whether a card edge was found in the photo."""

    image: np.ndarray
    card_edge_found: bool


def read_image(source: str | Path) -> np.ndarray:
    """Read a photo from disk or raise a helpful error if it cannot be opened."""
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not open image: {source}")
    return image


def _sort_corners(points: np.ndarray) -> np.ndarray:
    """Return four points in top-left, top-right, bottom-right, bottom-left order."""
    points = points.reshape(4, 2).astype(np.float32)
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(4)
    return np.array(
        [
            points[np.argmin(sums)],
            points[np.argmin(differences)],
            points[np.argmax(sums)],
            points[np.argmax(differences)],
        ],
        dtype=np.float32,
    )


def find_card_corners(image: np.ndarray) -> np.ndarray | None:
    """Find the largest likely card-shaped outline in a camera photo."""
    height, width = image.shape[:2]
    scale = min(1.0, 1200 / max(height, width))
    if scale < 1.0:
        search_image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        search_image = image.copy()

    gray = cv2.cvtColor(search_image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 130)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    frame_area = search_image.shape[0] * search_image.shape[1]

    likely_cards: list[tuple[float, np.ndarray]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < frame_area * 0.12:
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(polygon) != 4 or not cv2.isContourConvex(polygon):
            continue

        ordered = _sort_corners(polygon)
        top_width = np.linalg.norm(ordered[1] - ordered[0])
        bottom_width = np.linalg.norm(ordered[2] - ordered[3])
        left_height = np.linalg.norm(ordered[3] - ordered[0])
        right_height = np.linalg.norm(ordered[2] - ordered[1])
        card_width = (top_width + bottom_width) / 2
        card_height = (left_height + right_height) / 2
        ratio = card_width / max(card_height, 1)

        # A standard Pokémon card is a little wider than 0.7 times its height.
        # Allow extra room because a camera can see the card at an angle.
        if 0.48 <= ratio <= 1.05:
            likely_cards.append((area, ordered))

    if not likely_cards:
        return None

    _, corners = max(likely_cards, key=lambda item: item[0])
    return corners / scale


def _warp_to_card(image: np.ndarray, corners: np.ndarray) -> np.ndarray:
    destination = np.array(
        [
            [0, 0],
            [OUTPUT_WIDTH - 1, 0],
            [OUTPUT_WIDTH - 1, OUTPUT_HEIGHT - 1],
            [0, OUTPUT_HEIGHT - 1],
        ],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(corners.astype(np.float32), destination)
    return cv2.warpPerspective(image, transform, (OUTPUT_WIDTH, OUTPUT_HEIGHT))


def _normalize_lighting(image: np.ndarray) -> np.ndarray:
    """Gently even out light and contrast while keeping card colors."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    adjusted_lightness = clahe.apply(lightness)
    adjusted = cv2.merge((adjusted_lightness, a_channel, b_channel))
    return cv2.cvtColor(adjusted, cv2.COLOR_LAB2BGR)


def _fit_to_card_canvas(image: np.ndarray) -> np.ndarray:
    """Resize without stretching, adding a dark border if the shape differs."""
    height, width = image.shape[:2]
    scale = min(OUTPUT_WIDTH / width, OUTPUT_HEIGHT / height)
    resized = cv2.resize(
        image,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
    )
    canvas = np.full((OUTPUT_HEIGHT, OUTPUT_WIDTH, 3), 32, dtype=np.uint8)
    y = (OUTPUT_HEIGHT - resized.shape[0]) // 2
    x = (OUTPUT_WIDTH - resized.shape[1]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def preprocess_card_image(image: np.ndarray, *, detect_card: bool = True) -> PreprocessingResult:
    """Crop, resize, and lightly normalize one scan or reference image.

    For a camera scan, card-edge detection corrects perspective when a clear
    four-sided card outline is visible. For a TCGdex reference image, set
    ``detect_card=False`` because the downloaded image already shows the card.
    If a scan's edges cannot be found, its full frame is kept and the result
    reports ``card_edge_found=False`` so the caller can warn the user.
    """
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Expected a color image with three channels")

    card_edge_found = False
    if detect_card:
        corners = find_card_corners(image)
        if corners is not None:
            image = _warp_to_card(image, corners)
            card_edge_found = True

    if image.shape[1] != OUTPUT_WIDTH or image.shape[0] != OUTPUT_HEIGHT:
        image = _fit_to_card_canvas(image)

    return PreprocessingResult(image=_normalize_lighting(image), card_edge_found=card_edge_found)
