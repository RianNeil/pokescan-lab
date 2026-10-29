"""Local PokéScan Lab page and camera actions."""

from pathlib import Path

import cv2
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from pokescan.card_matching import get_matcher
from pokescan.image_preprocessing import preprocess_card_image, read_image

app = FastAPI(title="PokéScan Lab", description="Local camera photo capture")

PROJECT_FOLDER = Path.home() / "pokescan-lab"
ORIGINAL_PHOTO = PROJECT_FOLDER / "test-images" / "test-card.jpg"
CLEANED_PHOTO = PROJECT_FOLDER / "data" / "preprocessed" / "test-card-cleaned.jpg"
PAGE_FILE = Path(__file__).parent / "static" / "index.html"


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    """Show the local page Ezra uses to take a card picture."""
    try:
        return PAGE_FILE.read_text(encoding="utf-8")
    except OSError as error:
        raise HTTPException(status_code=500, detail="The photo page could not be opened.") from error


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the starter API is responding."""
    return {"status": "ok", "message": "PokéScan Lab starter is running."}


@app.post("/api/capture")
def capture_photo() -> dict[str, object]:
    """Take a photo, save a cleaned copy, and return their local page links."""
    try:
        from picamera2 import Picamera2
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="The camera tools are not available. Run this page on the Pi with Picamera2 installed.",
        ) from error

    try:
        ORIGINAL_PHOTO.parent.mkdir(parents=True, exist_ok=True)
        CLEANED_PHOTO.parent.mkdir(parents=True, exist_ok=True)

        camera = Picamera2()
        try:
            camera.start_and_capture_file(str(ORIGINAL_PHOTO), show_preview=False)
        finally:
            camera.close()

        original_image = read_image(ORIGINAL_PHOTO)
        result = preprocess_card_image(original_image)
        if not cv2.imwrite(str(CLEANED_PHOTO), result.image):
            raise OSError("The cleaned picture could not be saved.")
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"The picture could not be taken and cleaned. Check the camera and try again. Details: {error}",
        ) from error

    if result.card_edge_found:
        message = "Picture saved. I found the card edges and straightened the cleaned copy."
    else:
        message = "Picture saved. I could not find the card edges, so the cleaned copy uses the full photo."

    try:
        matches = get_matcher().match_processed_image(result.image)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Picture saved, but card matching could not start. Check that the ten reference pictures are saved and the Pi has internet for its first model download. Details: {error}",
        ) from error

    return {
        "message": message,
        "card_edge_found": result.card_edge_found,
        "original_url": "/photos/original",
        "cleaned_url": "/photos/cleaned",
        "matches": matches,
    }


@app.get("/photos/{photo_kind}")
def show_photo(photo_kind: str) -> FileResponse:
    """Return one of the two known local photos, never an arbitrary file."""
    photo_files = {
        "original": ORIGINAL_PHOTO,
        "cleaned": CLEANED_PHOTO,
    }
    photo_path = photo_files.get(photo_kind)
    if photo_path is None:
        raise HTTPException(status_code=404, detail="That photo was not found.")
    if not photo_path.is_file():
        raise HTTPException(status_code=404, detail="Take a picture first to see it here.")

    return FileResponse(
        photo_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )
