# PokéScan Lab

Ezra's school STEM project: build a camera tool that takes a Pokémon card picture, suggests a match, and lets a person confirm or correct it.

## Where things live

- **Code:** [GitHub repository](https://github.com/RianNeil/pokescan-lab)
- **Tasks and checkboxes:** [PokéScan Lab in Linear](https://linear.app/towerb/project/pokescan-lab-14efa1055b40)
- **Plan, decisions, and experiment notes:** [PokéScan Lab Project Notebook in Notion](https://app.notion.com/p/403d236521828142a7fefeb69aad516c)
- **Codex instructions:** [AGENTS.md](AGENTS.md)
- **Project background and current decisions:** [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)

## Current stage

We are setting up the project. The Raspberry Pi has not been flashed yet, and the scanner code has not been built. Start with Linear task [TOW-5: Set up repository and Python project structure](https://linear.app/towerb/issue/TOW-5/set-up-repository-and-python-project-structure), while keeping the Pi setup task [TOW-31](https://linear.app/towerb/issue/TOW-31/install-raspberry-pi-os-and-check-the-camera) visible.

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

The Raspberry Pi and camera have not been set up or tested. Camera packages and camera instructions will be added in the hardware setup task, after Raspberry Pi OS is installed.

## Project in one sentence

The Pi will take the picture and do the card matching. A simple browser screen on the Pi will let the presenter scan a card and confirm or fix the result. The presentation flow should not require typing terminal commands.
