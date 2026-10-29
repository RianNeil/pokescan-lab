# PokéScan Lab

Ezra's school STEM project: build a camera tool that takes a Pokémon card picture, suggests a match, and lets a person confirm or correct it.

## Where things live

- **Code:** [GitHub repository](https://github.com/RianNeil/pokescan-lab)
- **Tasks and checkboxes:** [PokéScan Lab in Linear](https://linear.app/towerb/project/pokescan-lab-14efa1055b40)
- **Plan, decisions, and experiment notes:** [PokéScan Lab Project Notebook in Notion](https://app.notion.com/p/403d236521828142a7fefeb69aad516c)
- **Codex instructions:** [AGENTS.md](AGENTS.md)
- **Project background and current decisions:** [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)

## Current stage

The Raspberry Pi is set up with the official 64-bit Raspberry Pi OS. Python 3.13.5, SSH, the Arducam OV5647 camera, the GitHub clone, and a basic Python photo capture have been checked. [TOW-20](https://linear.app/towerb/issue/TOW-20/confirm-hardware-and-scanner-target), [TOW-31](https://linear.app/towerb/issue/TOW-31/install-raspberry-pi-os-and-check-the-camera), [TOW-19](https://linear.app/towerb/issue/TOW-19/choose-initial-card-scope-and-reference-data), and [TOW-16](https://linear.app/towerb/issue/TOW-16/capture-and-save-a-test-photo-from-python) are complete.

The photo test proved that the Pi can save a picture. It did not identify the card. The local reference-image index, image preprocessing, card matching, database, and presentation screen still need to be built. The camera is not mounted yet; that later improvement is tracked in [TOW-34](https://linear.app/towerb/issue/TOW-34/mount-the-camera-and-improve-card-framing).

Current unblocked coding tasks are [TOW-21: Build reference-image index](https://linear.app/towerb/issue/TOW-21/build-reference-image-index), [TOW-25: Implement image preprocessing](https://linear.app/towerb/issue/TOW-25/implement-image-preprocessing), and [TOW-26: Create SQLite schema](https://linear.app/towerb/issue/TOW-26/create-sqlite-schema-for-cards-and-scans). TOW-21 uses the card records chosen from TCGdex to build a local library the scanner can use; looking up cards in TCGdex alone does not complete TOW-21.

## Download the selected card references

After the latest code is on the Pi, run this once while the Pi has internet:

```bash
cd ~/pokescan-lab
python3 scripts/download_reference_cards.py
```

The script uses the ten selected TCGdex card IDs in `data/starter_cards.json`, downloads their card details and high-quality WebP reference images, and saves them under `data/reference_library/`. The local index can be read with `pokescan.reference_cards.load_reference_cards()` or searched by TCGdex ID with `find_reference_card()`. After this download, the saved reference library can be read without internet.

Downloaded card artwork and its generated local index are ignored by Git. They are for the project’s local experiments; the image source is recorded in the index, and the artwork should not be redistributed without permission.

## Clean up card pictures (TOW-25)

OpenCV is the picture-cleanup tool. It is not a custom AI model. On the Pi, set up the project environment once. `--system-site-packages` lets the environment use camera packages installed by Raspberry Pi OS:

```bash
cd ~/pokescan-lab
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

To make a cleaned-up copy of the Pi camera photo without changing the original:

```bash
python scripts/preprocess_card_images.py test-images/test-card.jpg
```

To make cleaned-up copies of all saved TCGdex reference pictures:

```bash
python scripts/preprocess_card_images.py data/reference_library/images --reference-images
```

The cleaned pictures and side-by-side previews are saved in `data/preprocessed/`, which stays local and is not pushed to GitHub. For a camera photo, the script tries to find the card edges and straighten the card. If it cannot find the edges, it keeps the photo, prints a warning, and creates a preview so we can inspect it.

## Take a card picture on the Pi (TOW-49)

Start PokéScan Lab on the Pi:

```bash
cd ~/pokescan-lab
source .venv/bin/activate
python -m pokescan
```

Leave that Terminal window open. In the Pi's web browser, open <http://127.0.0.1:8000>. Put a card in front of the camera and click **Take picture**. The page shows both the camera photo and the cleaned-up copy. Click the button again to replace them with a new picture. To stop the app, go back to Terminal and press Control-C.

The original stays in `test-images/test-card.jpg`; the cleaned copy stays in `data/preprocessed/test-card-cleaned.jpg`. Both folders are ignored by Git, so the photos stay on the Pi.

## First card-matching experiment (TOW-22)

Card matching uses **MobileNetV2 1.0 int8**, a small pretrained image model from the [ONNX Model Zoo](https://github.com/onnx/models/blob/main/validated/vision/classification/mobilenet/README.md). The model is Apache 2.0 licensed. [ONNX Runtime's CPU package](https://onnxruntime.ai/docs/get-started/with-python.html) has a CPython 3.13 Linux ARM64 wheel, which fits this Pi's 64-bit OS and Python. We are not training a model. MobileNet was taught to recognize everyday ImageNet categories, not individual Pokémon cards. For this first experiment, its 1,000 output scores become a compact image fingerprint. We compare fingerprints with cosine similarity: a larger score means the model thinks two pictures are more alike. The score is a ranking clue, not a probability or a promise that the guess is right.

The app makes cleaned copies of the ten references using `preprocess_card_image(..., detect_card=False)`. A scan uses the same existing cleanup with card-edge detection. Both are resized to 224 × 224 RGB, scaled to 0–1, and normalized with ImageNet's standard channel means and deviations. The model runs on `CPUExecutionProvider` with two inference threads. Its weights and saved reference fingerprints are kept in the ignored `data/reference_library/` folder. The model downloads the first time matching starts, so the Pi needs internet for that first run; later matches use the local files.

After updating the Pi and installing `requirements.txt`, download the ten reference pictures if needed, then start the app as described above. The first capture may take longer while the model downloads and the ten fingerprints are made. Later captures show up to three card guesses, their cosine scores, and the photo-matching time. The saved fingerprint file includes the model name, settings, model checksum, and checksums for the reference pictures so it can be rebuilt when any of those change.

To compare several sample photos with known cards, save the photos locally on the Pi, then run (repeat `--expected-id` in the same order as the photo paths):

```bash
python scripts/benchmark_matching.py test-images/sample-1.jpg test-images/sample-2.jpg \
  --expected-id base3-50 --expected-id 30th-144 \
  --output data/preprocessed/tow-22-pi-results.json
```

The report separates first-run setup time from each photo's matching time and lists the top three guesses. Example recordings:

| Pi sample photo | Correct card ID | Top guess | Top-three result | Matching time |
| --- | --- | --- | --- | --- |
| Pending Pi run | — | — | — | Not measured yet |

On the Mac, a sanity check compared three saved reference images against the ten-card list; each exact reference ranked itself first. It took 15.3–16.0 ms per image on that Mac. These controlled reference-image checks do not test camera photos, and the Mac time is not the Pi measurement.

Record a few real Pi camera photos here after running the benchmark. The Mac implementation can be checked locally, but its speed does not count as the Pi result. Keep the photo files and report local; the reference artwork is also excluded from Git.

## Run the starter on a Mac

Use Python 3.11 or newer. These steps make a private project environment, install the pinned Python packages, and start the local app. The Mac can show the page, but camera capture needs to run on the Pi.

```sh
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pokescan
```

When it starts, open <http://127.0.0.1:8000/health> in a browser. You should see a short JSON message saying the starter is running. Press Control-C in the terminal to stop it. To use the project another time, open a terminal in this folder, run `source .venv/bin/activate`, then run `python -m pokescan`.

On a Mac, the local app is only a setup check; it cannot use the Pi camera. The Pi camera was tested separately by running `scripts/capture_test.py` on the Pi.

## Project in one sentence

The Pi will take the picture and do the card matching. A simple browser screen on the Pi will let the presenter scan a card and confirm or fix the result. The presentation flow should not require typing terminal commands.
