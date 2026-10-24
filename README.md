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

## Run the starter on a Mac

Use Python 3.11 or newer. These steps make a private project environment, install the pinned Python packages, and start a small local status API. The API is just a setup check; it does not use a camera or scan cards.

```sh
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pokescan
```

When it starts, open <http://127.0.0.1:8000/health> in a browser. You should see a short JSON message saying the starter is running. Press Control-C in the terminal to stop it. To use the project another time, open a terminal in this folder, run `source .venv/bin/activate`, then run `python -m pokescan`.

The Mac status API is only a setup check. It does not use the camera or scan cards. The Pi camera was tested separately by running `scripts/capture_test.py` on the Pi.

## Project in one sentence

The Pi will take the picture and do the card matching. A simple browser screen on the Pi will let the presenter scan a card and confirm or fix the result. The presentation flow should not require typing terminal commands.
