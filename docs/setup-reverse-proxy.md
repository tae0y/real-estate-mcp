# Set Up a Reverse Proxy

This page describes how to expose the MCP server over the internet using a reverse proxy.

Once the proxy is running, connect clients to it using [setup-with-http.md](setup-with-http.md).

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose plugin)
- API key from [공공데이터포털](https://www.data.go.kr) — see [setup-prerequisites.md](setup-prerequisites.md)
- This repository cloned locally

---

## Cloudflare Tunnel

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
    docker compose --env-file .env -f docker/docker-compose.yml --profile cloudflare up -d --build
    ```

    > **Important:** `--env-file .env` is required because Compose v2 otherwise treats the compose file's directory (`docker/`) as the project directory and looks for `docker/.env` instead of the root `.env`, leaving `CLOUDFLARE_TUNNEL_TOKEN` blank. `--env-file` is a global flag and must come before `up`.

    The `cloudflared` service depends on the `mcp` health check passing, so it starts roughly 15–45 seconds after Docker Compose begins. Once both containers are running, the tunnel status in the Cloudflare dashboard changes to **Healthy**.

### Verify

1. Open the Cloudflare Zero Trust dashboard → **Networks** → **Tunnels** — confirm the tunnel shows **Healthy**.
1. Connect a client using the public URL ending in `/mcp` — see [setup-with-http.md](setup-with-http.md).

### Remove

1. Stop and remove the containers.

    ```bash
    docker compose --env-file .env -f docker/docker-compose.yml --profile cloudflare down
    ```

1. In the Cloudflare Zero Trust dashboard → **Networks** → **Tunnels**, select the tunnel → **Delete**.
