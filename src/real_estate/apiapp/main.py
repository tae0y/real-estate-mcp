"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(title="Real Estate API")


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Hello from Real Estate"}
