"""Start the local PokéScan Lab photo page."""

import uvicorn


def main() -> None:
    """Run the page on this Pi so its local browser can use it."""
    uvicorn.run("pokescan.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
