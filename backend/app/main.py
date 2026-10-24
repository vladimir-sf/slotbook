from fastapi import FastAPI

app = FastAPI(title="SlotBook API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Scaffold-only health endpoint; booking routes are future agent work."""
    return {"status": "ok"}
