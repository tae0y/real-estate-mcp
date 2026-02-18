# Run the MCP Server in Docker

This page describes how to run the real estate MCP server using Docker Compose,
with [Caddy](https://caddyserver.com/) as a reverse proxy.

Use this setup when you want to serve the MCP server over HTTP —
for example, to connect [ChatGPT](docs/setup-chatgpt-web.md) or other remote clients.

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
| `oauth` | OAuth 2.0 `client_credentials` | Claude Web, ChatGPT Web, shared access |

### Enable OAuth (AUTH_MODE=oauth)

1. Add to `.env`:

    ```
    AUTH_MODE=oauth
    OAUTH_CLIENT_ID=<generate with: openssl rand -hex 16>
    OAUTH_CLIENT_SECRET=<generate with: openssl rand -hex 32>
    ```

1. Restart the containers:

    ```bash
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d
    ```

1. Share `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` with colleagues.
   They enter these into the **OAuth Client ID** / **OAuth Client Secret** fields in Claude Web or ChatGPT Web.

1. To revoke access: remove `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` from `.env` (or change the values), then restart.

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
| `OAUTH_CLIENT_ID` | — | OAuth client ID (required when `AUTH_MODE=oauth`) |
| `OAUTH_CLIENT_SECRET` | — | OAuth client secret (required when `AUTH_MODE=oauth`) |
| `OAUTH_TOKEN_TTL` | `3600` | Access token lifetime in seconds |
