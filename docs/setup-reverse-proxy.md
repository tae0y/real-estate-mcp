# Set Up a Reverse Proxy

This page describes how to expose the MCP server over the internet using a reverse proxy.

Once the proxy is running, connect clients to it using [setup-with-http.md](setup-with-http.md).

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose plugin)
- API key from [공공데이터포털](https://www.data.go.kr) — see [setup-prerequisites.md](setup-prerequisites.md)
- This repository cloned locally

---

## Option A: Cloudflare Tunnel (recommended)

No port forwarding or TLS certificate management required.

### Set up the tunnel

1. Sign in to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Add a site** → enter your domain name → select a plan.

1. Cloudflare shows two nameservers (e.g. `emma.ns.cloudflare.com`, `ivan.ns.cloudflare.com`). Copy both.

1. At your domain registrar, replace the current nameservers with the two Cloudflare nameservers.

   > **Important:** Nameserver propagation can take up to 48 hours, though it usually completes within a few minutes.

1. Back in the Cloudflare dashboard, click **Check nameservers**. Once propagation completes, the domain status changes to **Active**.

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com) → **Networks** → **Connectors** → **Create a tunnel**.

1. Select **Cloudflared** as the connector type, enter a tunnel name (e.g. `real-estate-mcp`), then click **Save tunnel**.

1. Copy the tunnel token from the install command shown on screen (the long string at the end of `cloudflared service install <token>`).

1. Under **Public Hostnames**, add a route:
   - Subdomain: your chosen subdomain (e.g. `mcp`)
   - Domain: your domain
   - Service: `http://mcp:8000`

   > **Important:** The service URL must use the Compose service name `mcp`, not `localhost`. Both containers share the `internal` bridge network defined in `docker-compose.yml`.

1. Click **Save hostname**.
   The tunnel status will remain **Inactive** until the `cloudflared` container starts.

### Start the server

1. Copy `.env.example` to `.env` at the project root and set the required values.

    ```bash
    cp .env.example .env
    ```

    ```env
    DATA_GO_KR_API_KEY=your_api_key_here
    CLOUDFLARE_TUNNEL_TOKEN=<token from Cloudflare Zero Trust>
    ```

1. Start the containers.

    ```bash
    # bash/zsh
    docker compose -f docker/docker-compose.yml --profile cloudflare up -d --build
    ```

    ```powershell
    # PowerShell
    docker compose -f docker/docker-compose.yml --profile cloudflare up -d --build
    ```

    The `cloudflared` service depends on the `mcp` health check passing, so it starts roughly 15–45 seconds after Docker Compose begins. Once both containers are running, the tunnel status in the Cloudflare dashboard changes to **Healthy**.

### Verify

1. Open the Cloudflare Zero Trust dashboard → **Networks** → **Tunnels** — confirm the tunnel shows **Healthy**.
1. Connect a client using the public URL ending in `/mcp` — see [setup-with-http.md](setup-with-http.md).

### Remove

1. Stop and remove the containers.

    ```bash
    # bash/zsh
    docker compose -f docker/docker-compose.yml --profile cloudflare down
    ```

    ```powershell
    # PowerShell
    docker compose -f docker/docker-compose.yml --profile cloudflare down
    ```

1. In the Cloudflare Zero Trust dashboard → **Networks** → **Tunnels**, select the tunnel → **Delete**.

---

## Option B: Caddy + OAuth (deprecated, removed June 1, 2025)

> **Deprecated:** This option will be removed on June 1, 2025.
> Migrate to Option A (Cloudflare Tunnel), which requires no port forwarding and no TLS certificate management.

This option runs the MCP server behind a [Caddy](https://caddyserver.com/) reverse proxy with OAuth authentication.

### Supported clients (Option B)

- [x] Claude CLI (HTTP)
- [x] Claude (Web / Claude.ai) — via client credentials OAuth
- [x] ChatGPT (Web) — via Auth0 PKCE (deprecated, removed end of April 2025)

### Additional prerequisites (Option B)

- A domain pointing to the server's public IP (a DDNS service such as No-IP is sufficient)
- Ports 80 and 443 forwarded on your router

### Start the server

1. Create a `.env` file and set your API key.

    ```bash
    cp .env.example .env
    ```

    ```
    DATA_GO_KR_API_KEY=your_api_key_here
    ```

1. Build and start the containers with the `caddy` profile.

    ```bash
    # bash/zsh
    docker compose -f docker/docker-compose.yml --profile caddy up -d --build
    ```

    ```powershell
    # PowerShell
    docker compose -f docker/docker-compose.yml --profile caddy up -d --build
    ```

1. Verify the MCP server is running.

    ```bash
    curl -s -X POST http://localhost/mcp \
      -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}'
    ```

    You should receive a JSON response containing `protocolVersion`.

### Enable HTTPS (home server with domain)

1. Point your domain to the server's public IP using your DNS provider or DDNS.

1. Forward ports `80` and `443` on your router to the server.

1. Replace `:80` in `docker/Caddyfile` with your domain name.

    ```
    your-domain.com {
        reverse_proxy /mcp* mcp:8000
    }
    ```

1. Restart the Caddy container.

    ```bash
    # bash/zsh
    docker compose -f docker/docker-compose.yml --profile caddy restart caddy
    ```

    ```powershell
    # PowerShell
    docker compose -f docker/docker-compose.yml --profile caddy restart caddy
    ```

### Enable OAuth

By default, `AUTH_MODE=none` — no authentication required.

To restrict access over the public internet, add to `.env`:

```
AUTH_MODE=oauth
PUBLIC_BASE_URL=https://your-domain.com
OAUTH_CLIENT_ID=<generate with: openssl rand -hex 16>
OAUTH_CLIENT_SECRET=<generate with: openssl rand -hex 32>
```

Restart the containers, then share `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` with users.
They enter these into the OAuth Client ID / Client Secret fields in Claude Web.

For ChatGPT Web (Auth0 PKCE + DCR), also set:

```
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://your-domain.com/mcp
```

> For the full Auth0 tenant configuration steps (DCR, domain connection, user creation), see the archived `setup-oauth.md` in the git history.

### Environment variables (Option B)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_GO_KR_API_KEY` | — | 공공데이터포털 API key (required) |
| `AUTH_MODE` | `none` | `oauth` or `none` |
| `PUBLIC_BASE_URL` | — | Public HTTPS base URL (required when `AUTH_MODE=oauth`) |
| `OAUTH_CLIENT_ID` | — | Client ID for client_credentials flow |
| `OAUTH_CLIENT_SECRET` | — | Client secret for client_credentials flow |
| `OAUTH_TOKEN_TTL` | `3600` | Access token lifetime in seconds |
| `AUTH0_DOMAIN` | — | Auth0 tenant domain (required for ChatGPT Web) |
| `AUTH0_AUDIENCE` | — | Auth0 API identifier (required for ChatGPT Web) |

### Remove (Option B)

```bash
# bash/zsh
docker compose -f docker/docker-compose.yml --profile caddy down
```

```powershell
# PowerShell
docker compose -f docker/docker-compose.yml --profile caddy down
```
