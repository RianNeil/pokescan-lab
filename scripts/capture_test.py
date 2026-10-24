from pathlib import Path
from picamera2 import Picamera2

output_folder = Path.home() / "pokescan-lab" / "test-images"
output_folder.mkdir(parents=True, exist_ok=True)
photo_path = output_folder / "test-card.jpg"

camera = Picamera2()
try:
    camera.start_and_capture_file(str(photo_path))
finally:
    camera.close()

print(f"Photo saved to: {photo_path}")
