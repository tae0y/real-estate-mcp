"""Unit tests for OAuth auth server."""

import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OAUTH_CLIENT_ID", "test_id")
    monkeypatch.setenv("OAUTH_CLIENT_SECRET", "test_secret")


@pytest.fixture(autouse=True)
def clear_tokens() -> None:
    from real_estate import auth_server

    auth_server._tokens.clear()


@pytest.fixture
def client() -> TestClient:
    from real_estate.auth_server import app

    return TestClient(app)


class TestTokenEndpoint:
    def test_valid_credentials_returns_token(self, client: TestClient) -> None:
        resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test_id",
                "client_secret": "test_secret",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 3600

    def test_wrong_secret_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test_id",
                "client_secret": "wrong",
            },
        )
        assert resp.status_code == 401

    def test_wrong_client_id_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "nobody",
                "client_secret": "test_secret",
            },
        )
        assert resp.status_code == 401

    def test_unsupported_grant_type_returns_400(self, client: TestClient) -> None:
        resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "test_id",
                "client_secret": "test_secret",
            },
        )
        assert resp.status_code == 400


class TestVerifyEndpoint:
    def test_valid_token_returns_200(self, client: TestClient) -> None:
        token_resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test_id",
                "client_secret": "test_secret",
            },
        )
        token = token_resp.json()["access_token"]

        resp = client.get("/oauth/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_missing_token_returns_401(self, client: TestClient) -> None:
        resp = client.get("/oauth/verify")
        assert resp.status_code == 401

    def test_unknown_token_returns_401(self, client: TestClient) -> None:
        resp = client.get("/oauth/verify", headers={"Authorization": "Bearer nosuchtoken"})
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client: TestClient) -> None:
        token_resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test_id",
                "client_secret": "test_secret",
            },
        )
        token = token_resp.json()["access_token"]

        from real_estate import auth_server

        auth_server._tokens[token] = time.time() - 1  # 만료 처리

        resp = client.get("/oauth/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
