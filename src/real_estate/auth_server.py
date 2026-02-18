"""Minimal OAuth 2.0 client_credentials token server for MCP HTTP access."""

import os
import secrets
import time

from fastapi import FastAPI, Form, HTTPException, Request

app = FastAPI()

# in-memory store: token → expiry epoch
_tokens: dict[str, float] = {}

_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")


@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata() -> dict:
    """RFC 8414 Authorization Server Metadata — required for ChatGPT MCP discovery."""
    return {
        "issuer": _BASE_URL,
        "token_endpoint": f"{_BASE_URL}/oauth/token",
        "grant_types_supported": ["client_credentials"],
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
    if client_id != os.environ["OAUTH_CLIENT_ID"] or client_secret != os.environ["OAUTH_CLIENT_SECRET"]:
        raise HTTPException(status_code=401, detail="invalid_client")
    tok = secrets.token_hex(32)
    expires_in = int(os.getenv("OAUTH_TOKEN_TTL", "3600"))
    _tokens[tok] = time.time() + expires_in
    return {"access_token": tok, "token_type": "bearer", "expires_in": expires_in}


@app.get("/oauth/verify")
async def verify(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_token")
    tok = auth.removeprefix("Bearer ")
    if _tokens.get(tok, 0) < time.time():
        _tokens.pop(tok, None)
        raise HTTPException(status_code=401, detail="invalid_token")
    return {}
