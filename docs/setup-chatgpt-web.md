# Connect with ChatGPT (Web)

This page describes how to connect the real estate MCP server to [ChatGPT](https://chatgpt.com) via the connector feature using Auth0 as the OAuth 2.1 identity provider.

> **Note:** ChatGPT's MCP connector only supports HTTP transport and requires OAuth 2.1 authorization code + PKCE. The stdio mode and client_credentials grant are not supported.

## Prerequisites

- ChatGPT Plus / Pro / Team / Enterprise account (MCP connector feature required)
- A publicly reachable HTTPS URL
  - Recommended: DDNS (e.g. no-ip) + router port forwarding (80/443) + Docker Caddy setup (see [setup-docker.md](setup-docker.md))
- Auth0 account (free tier is sufficient)

## Auth0 and Server Setup

Complete the **Auth0** option in [setup-oauth.md](setup-oauth.md#option-b-auth0-chatgpt-web--authorization-code--pkce--dcr).

## Verify Before Connecting

1. Protected resource metadata (ChatGPT reads this first)

    ```bash
    curl https://your-domain.ddns.net/.well-known/oauth-protected-resource
    ```

    Expected:

    ```json
    {
      "resource": "https://your-domain.ddns.net/mcp",
      "authorization_servers": ["https://your-tenant.us.auth0.com"],
      "scopes_supported": []
    }
    ```

1. Authorization server metadata (must include PKCE + registration_endpoint)

    ```bash
    curl https://your-domain.ddns.net/.well-known/oauth-authorization-server
    ```

    Expected (key fields):

    ```json
    {
      "authorization_endpoint": "https://your-tenant.us.auth0.com/authorize",
      "token_endpoint": "https://your-tenant.us.auth0.com/oauth/token",
      "registration_endpoint": "https://your-tenant.us.auth0.com/oidc/register",
      "code_challenge_methods_supported": ["S256"]
    }
    ```

1. MCP endpoint returns 401 (auth guard is active)

    ```bash
    curl -o /dev/null -w "%{http_code}" https://your-domain.ddns.net/mcp
    # Expected: 401
    ```

    If this returns 406 or reaches the MCP server without auth, `AUTH_MODE` is not being read correctly by Caddy — verify the container env: `docker compose exec caddy sh -c 'env | grep AUTH_MODE'`

1. DCR endpoint

    ```bash
    curl -X POST https://your-tenant.us.auth0.com/oidc/register \
      -H "Content-Type: application/json" \
      -d '{"client_name":"test","redirect_uris":["https://chatgpt.com/connector_platform_oauth_redirect"]}'
    ```

    Expected: `{"client_id": "...", "client_secret": "...", ...}`

## Add the Connector in ChatGPT

Once all four checks pass:

1. Go to **Settings → Connectors** → **Add connector**

1. Enter the MCP server URL:
   ```
   https://your-domain.ddns.net/mcp
   ```

1. ChatGPT automatically discovers Auth0 via `/.well-known/oauth-protected-resource` and redirects you to the Auth0 login page — **no client ID/secret input required**.

1. Log in with the Auth0 user created in step 7 above.

1. Confirm the `real-estate` tools appear in the connector tool list.

## Access Control

### Grant access

1. Auth0 → Settings → Advanced → Enable Dynamic Client Registration

1. Auth0 → User Management → Users → Create User*— create an account for each user

1. Share the MCP URL: `https://your-domain.ddns.net/mcp`

1. Users add it as a ChatGPT connector and log in with their Auth0 account

### Revoke access

1. Option A — Disable DCR (quickest, blocks all new and re-authentication)

    Auth0 → Settings → Advanced → Disable Dynamic Client Registration

    Existing sessions remain valid until token expiry (default 1 hour), then all users are blocked on re-authentication.

1. Option B — Block specific users

    Auth0 → *ser Management → Users → select user → Block
    
    Blocks that user immediately on next token refresh without affecting others.

## Remove your own connector

Go to **Settings → Connectors** and delete the `real-estate` connector entry.
