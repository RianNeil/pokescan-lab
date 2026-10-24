"""Small local API used to confirm the Python project starts."""

from fastapi import FastAPI

app = FastAPI(title="PokéScan Lab", description="Local project starter")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the starter API is responding."""
    return {"status": "ok", "message": "PokéScan Lab starter is running."}
