# Set Up OAuth Authentication

This page describes how to enable OAuth for the real estate MCP server when serving over HTTP.

OAuth is required when the server is publicly reachable and you want to restrict access.
If you are running locally on a trusted network, `AUTH_MODE=none` (the default) is sufficient.

## Prerequisites

- Docker + Caddy already running — see [setup-docker.md](setup-docker.md) first
- `AUTH_MODE` is read from `.env` by Caddy; do not export it from the host shell

| `AUTH_MODE` | Behaviour | When to use |
|-------------|-----------|-------------|
| `none` (default) | No authentication | Development, local trusted network |
| `oauth` | OAuth 2.0 | Shared access over the internet |

## Option A: Client credentials (Claude Web)

Use this when connecting Claude.ai (web) or sharing with the others via a shared secret.

1. Add to `.env`:

    ```
    AUTH_MODE=oauth
    PUBLIC_BASE_URL=https://your-domain.com
    OAUTH_CLIENT_ID=<generate with: openssl rand -hex 16>
    OAUTH_CLIENT_SECRET=<generate with: openssl rand -hex 32>
    ```

1. Restart the containers.

    ```bash
    # bash/zsh
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d
    ```

    ```powershell
    # PowerShell
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d
    ```

1. Share `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` with the others.

   They enter these into the OAuth Client ID / OAuth Client Secret fields in Claude Web.

1. To revoke access: remove or change `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` in `.env`, then restart.

### Token endpoint

```
POST https://your-domain.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=<id>&client_secret=<secret>
```

Response:

```json
{"access_token": "...", "token_type": "bearer", "expires_in": 3600}
```

## Option B: Auth0 (ChatGPT Web — Authorization Code + PKCE + DCR)

ChatGPT Web requires Auth0 as the identity provider.

### Configure Auth0 tenant

1. Sign up at [auth0.com](https://auth0.com) and create a free tenant.

1. Create an Application.

    Applications → Create Application → Regular Web App

    > Select Regular Web App, not Machine to Machine. M2M only supports client_credentials grant and cannot do the authorization code flow required by ChatGPT.

    - Name: `real-estate-mcp`
    - Allowed Callback URLs: `https://chatgpt.com/connector_platform_oauth_redirect`

1. Create an API.

    Applications → APIs → Create API

    > The "Create API" button is in the left sidebar under Applications → APIs, separate from Applications → Applications.

    - Name: `real-estate-mcp-api`
    - Identifier (audience): `https://your-domain.com/mcp`

1. Enable Dynamic Client Registration.

    Settings → Advanced → Enable Dynamic Client Registration

    ChatGPT auto-registers itself as a client on first connection. This setting must be on.

1. Enable Application Connections (required for DCR).

    Settings → Advanced → Enable Application Connections

    Without it, DCR-created clients have no connections enabled and Auth0 returns `no connections enabled for the client`, blocking the login page.

### Set domain connection

1. Grant `update:connections` permission to the Test Application.

    Auth0 → Applications → Applications → Auth0 Management API (Test Application) → APIs tab → Auth0 Management API → enable `update:connections` → Update

1. Get a Management API token.

    ```bash
    TOKEN=$(curl -s -X POST "https://your-tenant.us.auth0.com/oauth/token" \
      -H "Content-Type: application/json" \
      -d '{
        "client_id": "YOUR_TEST_APP_CLIENT_ID",
        "client_secret": "YOUR_TEST_APP_CLIENT_SECRET",
        "audience": "https://your-tenant.us.auth0.com/api/v2/",
        "grant_type": "client_credentials"
      }' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
    ```

1. Find your Connection ID.

    Auth0 → Authentication → Database → Username-Password-Authentication → the URL contains the ID:

    ```
    .../connections/database/con_XXXXXXXXXXXXXXXX/settings
    ```

1. Set `is_domain_connection: true` on the connection.

    ```bash
    curl -X PATCH "https://your-tenant.us.auth0.com/api/v2/connections/con_XXXXXXXXXXXXXXXX" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"is_domain_connection": true}'
    ```

    Expected: JSON response with `"is_domain_connection": true`

1. Create a user.

    Auth0 → User Management → Users → Create User

    - Email: your email
    - Password: your password
    - Connection: `Username-Password-Authentication`

    This account is used to log in when ChatGPT redirects to the Auth0 login page.

1. Note your tenant domain.

    Settings → General → Domain

    Format: `your-tenant.us.auth0.com` (includes region subdomain such as `us`, `us-5`, `eu` — not `your-tenant.auth0.com`)

### Deploy

1. Add to `.env`:

    ```
    AUTH_MODE=oauth
    PUBLIC_BASE_URL=https://your-domain.com

    # Auth0 PKCE (used by ChatGPT Web)
    AUTH0_DOMAIN=your-tenant.us.auth0.com
    AUTH0_AUDIENCE=https://your-domain.com/mcp
    ```

1. Rebuild and restart.

    ```bash
    # bash/zsh
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d --build
    ```

    ```powershell
    # PowerShell
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d --build
    ```

1. Verify that Caddy picks up `AUTH_MODE`.

    ```bash
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml exec caddy sh -c 'env | grep AUTH_MODE'
    # expected: AUTH_MODE=oauth
    ```

    > If `AUTH_MODE` shows `none`, the Caddy service is missing `env_file` in `docker-compose.yml`. Auth guard will not activate and `/mcp` will return 406 instead of 401.

> ChatGPT sends a `resource` parameter during authorization, which causes Auth0 to issue a JWE token (not RS256 JWT). The server validates it via Auth0's `/userinfo` endpoint instead of JWKS local verification.

### Access control

1. Open access (share with the others):

    Auth0 → Settings → Advanced → Enable Dynamic Client Registration

    Auth0 → User Management → Users → Create User — create an account for each colleague

    Share the MCP URL: `https://your-domain.com/mcp`

1. Close access — Option A: Disable DCR (blocks all new and re-authentication)

    Auth0 → Settings → Advanced → Disable Dynamic Client Registration

    Existing sessions remain valid until token expiry (default 1 hour).

    Close access — Option B: Block specific users

    Auth0 → User Management → Users → select user → Block

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_MODE` | `none` | Auth mode: `oauth` or `none` |
| `PUBLIC_BASE_URL` | — | Public HTTPS base URL, e.g. `https://your-domain.com` (required when `AUTH_MODE=oauth`) |
| `OAUTH_CLIENT_ID` | — | Client ID for client_credentials flow (Claude Web) |
| `OAUTH_CLIENT_SECRET` | — | Client secret for client_credentials flow |
| `OAUTH_TOKEN_TTL` | `3600` | Access token lifetime in seconds |
| `AUTH0_DOMAIN` | — | Auth0 tenant domain, e.g. `your-tenant.us.auth0.com` (required for ChatGPT Web) |
| `AUTH0_AUDIENCE` | — | Auth0 API identifier, e.g. `https://your-domain.com/mcp` (required for ChatGPT Web) |
