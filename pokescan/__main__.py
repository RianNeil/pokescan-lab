"""Start the local PokéScan Lab status API."""

import uvicorn


def main() -> None:
    """Run the development server on this computer only."""
    uvicorn.run("pokescan.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
