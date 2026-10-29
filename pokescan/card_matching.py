"""Find the saved reference card pictures that look most like a scan.

MobileNetV2 was trained on ImageNet, not Pokémon cards. Its 1,000 output
scores are used as a small, repeatable image fingerprint for this baseline.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from pokescan.image_preprocessing import preprocess_card_image, read_image
from pokescan.reference_cards import DEFAULT_INDEX_PATH, load_reference_cards


MODEL_NAME = "ONNX Model Zoo MobileNetV2-1.0-int8 (ImageNet)"
MODEL_URL = "https://github.com/onnx/models/raw/main/validated/vision/classification/mobilenet/model/mobilenetv2-12-int8.onnx"
MODEL_PATH = DEFAULT_INDEX_PATH.parent / "models" / "mobilenetv2-1.0-int8.onnx"
EMBEDDINGS_PATH = DEFAULT_INDEX_PATH.parent / "embeddings.json"
INPUT_SIZE = 224
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)
MODEL_SETTINGS = {
    "input_size": [INPUT_SIZE, INPUT_SIZE],
    "input_color": "RGB",
    "input_layout": "NCHW",
    "pixel_scale": "0..1",
    "normalization_mean": [0.485, 0.456, 0.406],
    "normalization_std": [0.229, 0.224, 0.225],
    "embedding": "L2-normalized 1,000 ImageNet output scores",
    "similarity": "cosine similarity; higher is closer",
    "onnx_runtime_execution_provider": "CPUExecutionProvider",
    "onnx_runtime_intra_op_threads": 2,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _get_model(model_path: Path = MODEL_PATH) -> Path:
    if model_path.is_file():
        return model_path
    model_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = model_path.with_suffix(model_path.suffix + ".download")
    try:
        urllib.request.urlretrieve(MODEL_URL, temporary_path)
        if temporary_path.stat().st_size < 1_000_000:
            raise ValueError("The downloaded MobileNet model file looks incomplete.")
        temporary_path.replace(model_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return model_path


class CardMatcher:
    """Create reference fingerprints once, then rank a processed card photo."""

    def __init__(
        self,
        *,
        index_path: Path = DEFAULT_INDEX_PATH,
        model_path: Path = MODEL_PATH,
        embeddings_path: Path = EMBEDDINGS_PATH,
    ) -> None:
        try:
            import onnxruntime as ort
        except ImportError as error:
            raise RuntimeError("Card matching needs ONNX Runtime. Install the project requirements first.") from error

        self.index_path = index_path
        self.embeddings_path = embeddings_path
        self.model_path = _get_model(model_path)
        options = ort.SessionOptions()
        options.intra_op_num_threads = MODEL_SETTINGS["onnx_runtime_intra_op_threads"]
        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.references = self._load_or_build_references()

    def _embed(self, image: np.ndarray) -> np.ndarray:
        resized = cv2.resize(image, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        normalized = (rgb - IMAGENET_MEAN) / IMAGENET_STD
        tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...].astype(np.float32)
        scores = self.session.run([self.output_name], {self.input_name: tensor})[0].reshape(-1)
        length = float(np.linalg.norm(scores))
        if not np.isfinite(scores).all() or length == 0:
            raise ValueError("The image model returned an unusable image fingerprint.")
        return scores / length

    def _load_or_build_references(self) -> list[dict[str, Any]]:
        cards = load_reference_cards(self.index_path)
        if len(cards) != 10:
            raise ValueError(f"TOW-22 expects 10 saved reference cards, but found {len(cards)}.")

        current_fingerprints = {
            card["id"]: _sha256(self.index_path.parent / card["local_image"])
            for card in cards
        }
        cached: dict[str, Any] = {}
        if self.embeddings_path.is_file():
            try:
                cached = json.loads(self.embeddings_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                cached = {}

        cache_is_current = (
            cached.get("model_name") == MODEL_NAME
            and cached.get("model_sha256") == _sha256(self.model_path)
            and cached.get("settings") == MODEL_SETTINGS
            and cached.get("reference_sha256") == current_fingerprints
            and isinstance(cached.get("embeddings"), dict)
            and set(cached["embeddings"]) == set(current_fingerprints)
        )
        if cache_is_current:
            vectors = cached["embeddings"]
        else:
            vectors = {}
            for card in cards:
                image_path = self.index_path.parent / card["local_image"]
                image = read_image(image_path)
                cleaned = preprocess_card_image(image, detect_card=False).image
                vectors[card["id"]] = self._embed(cleaned).tolist()
            self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
            saved = {
                "model_name": MODEL_NAME,
                "model_url": MODEL_URL,
                "model_sha256": _sha256(self.model_path),
                "settings": MODEL_SETTINGS,
                "reference_sha256": current_fingerprints,
                "embeddings": vectors,
            }
            self.embeddings_path.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")

        return [
            {**card, "embedding": np.asarray(vectors[card["id"]], dtype=np.float32)}
            for card in cards
        ]

    def match_processed_image(self, image: np.ndarray, *, limit: int = 3) -> dict[str, Any]:
        """Rank an already-cleaned OpenCV image. Scores are cosine similarity."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        started = time.perf_counter()
        query_embedding = self._embed(image)
        results = []
        for card in self.references:
            score = float(np.dot(query_embedding, card["embedding"]))
            results.append(
                {
                    "id": card["id"],
                    "name": card["name"],
                    "set": card.get("set"),
                    "number": card.get("number"),
                    "score": round(score, 4),
                }
            )
        results.sort(key=lambda guess: (-guess["score"], guess["id"]))
        return {
            "model": MODEL_NAME,
            "similarity": MODEL_SETTINGS["similarity"],
            "matching_ms": round((time.perf_counter() - started) * 1000, 1),
            "guesses": results[: min(limit, 3)],
        }

    def match_photo(self, photo_path: str | Path, *, limit: int = 3) -> dict[str, Any]:
        """Clean a photo with the project pipeline, then rank its closest cards."""
        photo = read_image(photo_path)
        cleaned = preprocess_card_image(photo).image
        return self.match_processed_image(cleaned, limit=limit)


_default_matcher: CardMatcher | None = None


def get_matcher() -> CardMatcher:
    """Load the model and ten local reference fingerprints once per app process."""
    global _default_matcher
    if _default_matcher is None:
        _default_matcher = CardMatcher()
    return _default_matcher
