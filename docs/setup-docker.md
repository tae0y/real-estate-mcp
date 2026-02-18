# Run the MCP Server in Docker

This page describes how to run the real estate MCP server using Docker Compose,
with [Caddy](https://caddyserver.com/) as a reverse proxy.

Use this setup when you want to serve the MCP server over HTTP —
for example, to connect [ChatGPT](setup-chatgpt-web.md) or other remote clients.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose plugin)
- API key from [공공데이터포털](https://www.data.go.kr)

## Get the repository root

1. Get the repository root.

    ```bash
    # bash/zsh
    REPOSITORY_ROOT=$(git rev-parse --show-toplevel)
    ```

    ```powershell
    # PowerShell
    $REPOSITORY_ROOT = git rev-parse --show-toplevel
    ```

## Run on local machine

1. Make sure you are at the repository root.

    ```bash
    # bash/zsh
    cd $REPOSITORY_ROOT
    ```

    ```powershell
    # PowerShell
    cd $REPOSITORY_ROOT
    ```

1. Create a `.env` file in the project root. Make sure to replace `your_api_key_here` with your actual key.

    ```bash
    cp .env.example .env
    ```

    ```
    DATA_GO_KR_API_KEY=your_api_key_here
    ```

    `DATA_GO_KR_API_KEY` is also used by default for Applyhome (odcloud) and Onbid.
    If you want different keys per service, add them to the `.env` file:

    ```
    ODCLOUD_API_KEY=...        # Applyhome Authorization header
    ODCLOUD_SERVICE_KEY=...    # Applyhome query param
    ONBID_API_KEY=...          # Onbid
    ```

1. Build and start the containers.

    ```bash
    # bash/zsh
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d --build
    ```

    ```powershell
    # PowerShell
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d --build
    ```

1. Verify the MCP server is running.

    The MCP endpoint requires specific headers, so use the command below instead of a plain `curl`.

    ```bash
    curl -s -X POST http://localhost/mcp \
      -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}'
    ```

    You should receive a JSON response containing `protocolVersion`.

1. Connect Claude Desktop to the running server. Open `claude_desktop_config.json`:

    ```bash
    # macOS
    open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    ```

    Add the entry below under `mcpServers`:

    ```json
    {
      "mcpServers": {
        "real-estate": {
          "url": "http://localhost/mcp"
        }
      }
    }
    ```

    Restart Claude Desktop. Setup is complete when you can see the `real-estate` server in the tool list.

1. To stop the containers:

    ```bash
    # bash/zsh
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml down
    ```

    ```powershell
    # PowerShell
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml down
    ```

    To also remove certificate volumes:

    ```bash
    # bash/zsh
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml down -v
    ```

    ```powershell
    # PowerShell
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml down -v
    ```

## Run on a home server (domain + HTTPS)

Caddy automatically obtains and renews a Let's Encrypt certificate when a domain name is configured.

1. Point your domain to the home server's public IP address using your DNS provider or a DDNS service (e.g. No-IP).

1. Forward ports `80` and `443` on your router to the home server.

1. Replace `:80` in `docker/Caddyfile` with your domain name.

    ```
    your-domain.com {
        reverse_proxy /mcp* mcp:8000
    }
    ```

1. Restart the Caddy container to apply the new configuration and obtain the certificate.

    ```bash
    # bash/zsh
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml restart caddy
    ```

    ```powershell
    # PowerShell
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml restart caddy
    ```

1. Verify the endpoint is reachable from outside.

    ```bash
    curl https://your-domain.com/mcp
    ```

## Check logs

```bash
# bash/zsh
docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml logs -f mcp
docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml logs -f caddy
```

```powershell
# PowerShell
docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml logs -f mcp
docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml logs -f caddy
```

## Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| `auth` | local build | 9000 (internal only) | OAuth token server |
| `mcp` | local build | 8000 (internal only) | MCP HTTP server |
| `caddy` | caddy:2-alpine | 80, 443 | Reverse proxy |

The `auth` and `mcp` containers are not exposed directly on any host port.
All traffic reaches them through Caddy.

## Authentication

Set `AUTH_MODE` in `.env` to control access:

| `AUTH_MODE` | Behaviour | When to use |
|-------------|-----------|-------------|
| `none` (default) | No authentication | Development, local trusted network |
| `oauth` | OAuth 2.0 — supports both `client_credentials` (Claude Web) and Auth0 authorization code + PKCE (ChatGPT Web) | Shared access over the internet |

### Enable OAuth (AUTH_MODE=oauth)

#### Option A: Client credentials (Claude Web / colleagues)

1. Add to `.env`:

    ```
    AUTH_MODE=oauth
    PUBLIC_BASE_URL=https://your-domain.com
    OAUTH_CLIENT_ID=<generate with: openssl rand -hex 16>
    OAUTH_CLIENT_SECRET=<generate with: openssl rand -hex 32>
    ```

1. Restart the containers:

    ```bash
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d
    ```

1. Share `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` with colleagues.
   They enter these into the **OAuth Client ID** / **OAuth Client Secret** fields in Claude Web.

1. To revoke access: remove `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` from `.env` (or change the values), then restart.

#### Option B: Auth0 (ChatGPT Web — Authorization Code + PKCE + DCR)

ChatGPT Web requires Auth0 as the identity provider. See the full setup guide: [refer.howto-setup-auth0.md](../localdocs/references/refer.howto-setup-auth0.md)

Key steps:

1. Create an Auth0 account and note your tenant domain from **Settings → General → Domain**.
   The format is `your-tenant.us.auth0.com` — it includes a region subdomain (`us`, `eu`, etc.), not just `your-tenant.auth0.com`.

1. Create an Auth0 Application — choose **Regular Web App** (not Machine to Machine).

1. Create an Auth0 API with identifier `https://your-domain.com/mcp`.

1. Add to `.env`:

    ```
    AUTH_MODE=oauth
    PUBLIC_BASE_URL=https://your-domain.com
    AUTH0_DOMAIN=your-tenant.us.auth0.com
    AUTH0_AUDIENCE=https://your-domain.com/mcp
    ```

1. Rebuild and verify that Caddy picks up `AUTH_MODE`:

    ```bash
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d --build
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml exec caddy sh -c 'env | grep AUTH_MODE'
    # expected: AUTH_MODE=oauth
    ```

    > If `AUTH_MODE` shows `none`, the Caddy service is missing `env_file` in `docker-compose.yml`.
    > Auth guard will not activate and `/mcp` will return 406 instead of 401.

1. Verify endpoints:

    ```bash
    curl -s https://your-domain.com/.well-known/oauth-protected-resource
    curl -s https://your-domain.com/.well-known/oauth-authorization-server
    curl -o /dev/null -w "%{http_code}" https://your-domain.com/mcp
    # expected: 401
    ```

1. In ChatGPT → Settings → Connectors → Add connector:
   - MCP URL: `https://your-domain.com/mcp`
   - Authentication: **OAuth**
   - Client ID / Client Secret: leave blank — ChatGPT registers itself via DCR automatically

**Note on token verification**: ChatGPT sends a `resource` parameter during authorization, which causes Auth0 to issue a JWE token (not RS256 JWT). The server validates it via Auth0's `/userinfo` endpoint instead of JWKS local verification. See [adr.auth0-token-verification.md](../localdocs/adr/adr.auth0-token-verification.md).

**Revoking access**: Block or delete the user in Auth0 → **User Management → Users**.

### OAuth token endpoint

```
POST https://your-domain.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=<id>&client_secret=<secret>
```

Response:

```json
{"access_token": "...", "token_type": "bearer", "expires_in": 3600}
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_GO_KR_API_KEY` | — | 공공데이터포털 API key (required) |
| `ONBID_API_KEY` | falls back to `DATA_GO_KR_API_KEY` | Onbid API key |
| `ODCLOUD_API_KEY` | falls back to `DATA_GO_KR_API_KEY` | Applyhome Authorization header |
| `ODCLOUD_SERVICE_KEY` | falls back to `DATA_GO_KR_API_KEY` | Applyhome query param |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Trusted proxy IPs (set to `caddy` in docker-compose) |
| `AUTH_MODE` | `none` | Auth mode: `oauth` or `none` |
| `PUBLIC_BASE_URL` | — | Public HTTPS base URL, e.g. `https://your-domain.com` (required when `AUTH_MODE=oauth`) |
| `OAUTH_CLIENT_ID` | — | Client ID for client_credentials flow (Claude Web / colleagues) |
| `OAUTH_CLIENT_SECRET` | — | Client secret for client_credentials flow |
| `OAUTH_TOKEN_TTL` | `3600` | Access token lifetime in seconds |
| `AUTH0_DOMAIN` | — | Auth0 tenant domain, e.g. `your-tenant.us.auth0.com` (required for ChatGPT Web) |
| `AUTH0_AUDIENCE` | — | Auth0 API identifier, e.g. `https://your-domain.com/mcp` (required for ChatGPT Web) |
