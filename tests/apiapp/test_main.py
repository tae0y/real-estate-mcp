"""Tests for the main FastAPI application."""

from fastapi.testclient import TestClient

from real_estate.apiapp.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    """Test that the root endpoint returns the expected message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Real Estate"}
