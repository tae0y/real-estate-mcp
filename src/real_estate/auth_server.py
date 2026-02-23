"""Minimal OAuth 2.0 token server for MCP HTTP access.

Supports two token types:
- client_credentials (legacy hex token) — Claude Web/Desktop
- Auth0 token (JWE or JWT) — ChatGPT Web via authorization_code + PKCE
  Verified via Auth0 token introspection endpoint.
"""

import os
import secrets
import time

import httpx
from fastapi import FastAPI, Form, HTTPException, Request

app = FastAPI()

# in-memory store: token → expiry epoch (legacy client_credentials)
_tokens: dict[str, float] = {}


def _base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "")


def _auth0_domain() -> str:
    return os.getenv("AUTH0_DOMAIN", "")


def _auth0_audience() -> str:
    return os.getenv("AUTH0_AUDIENCE", "")


async def _verify_auth0_token(tok: str) -> bool:
    """Verify Auth0 token via userinfo endpoint. Returns True if valid."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://{_auth0_domain()}/userinfo",
            headers={"Authorization": f"Bearer {tok}"},
        )
        return r.status_code == 200


@app.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata() -> dict:
    """RFC 9728 — MCP resource server metadata. ChatGPT reads this first."""
    base = _base_url()
    domain = _auth0_domain()
    return {
        "resource": f"{base}/mcp",
        "authorization_servers": [f"https://{domain}"],
        "scopes_supported": [],
        "resource_documentation": base,
    }


@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata() -> dict:
    """RFC 8414 Authorization Server Metadata."""
    base = _base_url()
    domain = _auth0_domain()
    return {
        "issuer": base,
        "authorization_endpoint": f"https://{domain}/authorize",
        "token_endpoint": f"https://{domain}/oauth/token",
        "registration_endpoint": f"https://{domain}/oidc/register",
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
    }


@app.post("/oauth/token")
async def token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
) -> dict:
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    if (
        client_id != os.environ["OAUTH_CLIENT_ID"]
        or client_secret != os.environ["OAUTH_CLIENT_SECRET"]
    ):
        raise HTTPException(status_code=401, detail="invalid_client")
    tok = secrets.token_hex(32)
    expires_in = int(os.getenv("OAUTH_TOKEN_TTL", "3600"))
    _tokens[tok] = time.time() + expires_in
    return {"access_token": tok, "token_type": "bearer", "expires_in": expires_in}  # nosec B105


@app.get("/oauth/verify")
async def verify(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_token")
    tok = auth.removeprefix("Bearer ")

    if "." in tok:
        # Auth0 token (JWS or JWE) — verify via userinfo endpoint
        if not await _verify_auth0_token(tok):
            raise HTTPException(status_code=401, detail="invalid_token")
    else:
        # Legacy client_credentials hex token
        if _tokens.get(tok, 0) < time.time():
            _tokens.pop(tok, None)
            raise HTTPException(status_code=401, detail="invalid_token")

    return {}
