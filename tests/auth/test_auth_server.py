"""Unit tests for OAuth auth server."""

import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt

_TEST_DOMAIN = "test.us.auth0.com"
_TEST_AUDIENCE = "https://example.com/mcp"


@pytest.fixture(autouse=True)
def set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OAUTH_CLIENT_ID", "test_id")
    monkeypatch.setenv("OAUTH_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("AUTH0_DOMAIN", _TEST_DOMAIN)
    monkeypatch.setenv("AUTH0_AUDIENCE", _TEST_AUDIENCE)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com")


@pytest.fixture
def rsa_key_pair():
    """Generate a throwaway RSA key pair for JWT signing in tests."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    return private_pem, public_key


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


class TestProtectedResourceMetadata:
    def test_returns_resource_and_authorization_server(self, client: TestClient) -> None:
        resp = client.get("/.well-known/oauth-protected-resource")
        assert resp.status_code == 200
        body = resp.json()
        assert body["resource"] == f"https://example.com/mcp"
        assert f"https://{_TEST_DOMAIN}" in body["authorization_servers"]

    def test_returns_scopes_supported(self, client: TestClient) -> None:
        resp = client.get("/.well-known/oauth-protected-resource")
        assert "scopes_supported" in resp.json()


class TestOAuthAuthorizationServerMetadata:
    def test_has_pkce_and_registration_endpoint(self, client: TestClient) -> None:
        resp = client.get("/.well-known/oauth-authorization-server")
        assert resp.status_code == 200
        body = resp.json()
        assert "S256" in body["code_challenge_methods_supported"]
        assert body["registration_endpoint"] == f"https://{_TEST_DOMAIN}/oidc/register"
        assert body["authorization_endpoint"] == f"https://{_TEST_DOMAIN}/authorize"
        assert body["token_endpoint"] == f"https://{_TEST_DOMAIN}/oauth/token"


class TestVerifyJWT:
    def test_valid_jwt_returns_200(self, client: TestClient, rsa_key_pair, monkeypatch) -> None:
        private_pem, public_key = rsa_key_pair

        # Patch _get_jwks to return public key directly (bypasses HTTP call)
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        pub_pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()

        import real_estate.auth_server as auth_mod
        async def fake_get_jwks():
            return pub_pem  # python-jose accepts PEM string

        monkeypatch.setattr(auth_mod, "_get_jwks", fake_get_jwks)

        token = jwt.encode(
            {"sub": "user1", "aud": _TEST_AUDIENCE, "iss": f"https://{_TEST_DOMAIN}/"},
            private_pem,
            algorithm="RS256",
        )
        resp = client.get("/oauth/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_forged_jwt_returns_401(self, client: TestClient, rsa_key_pair, monkeypatch) -> None:
        private_pem, public_key = rsa_key_pair

        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        pub_pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()

        import real_estate.auth_server as auth_mod
        async def fake_get_jwks():
            return pub_pem

        monkeypatch.setattr(auth_mod, "_get_jwks", fake_get_jwks)

        # Sign with a different key → signature mismatch
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other_pem = other_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        token = jwt.encode(
            {"sub": "attacker", "aud": _TEST_AUDIENCE, "iss": f"https://{_TEST_DOMAIN}/"},
            other_pem,
            algorithm="RS256",
        )
        resp = client.get("/oauth/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
