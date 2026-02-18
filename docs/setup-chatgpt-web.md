# Connect with ChatGPT (Web)

This page describes how to connect the real estate MCP server to [ChatGPT](https://chatgpt.com) via the connector feature.

> **Note:** ChatGPT's MCP connector only supports HTTP transport. The stdio mode is not available.

## Prerequisites

- ChatGPT Plus / Pro / Team / Enterprise account (MCP connector feature required)
- A publicly reachable HTTPS URL
  - Recommended: DDNS (e.g. no-ip) + router port forwarding (80/443) + Docker Caddy setup (see [setup-docker.md](setup-docker.md))

## Server Setup

If you deployed with Docker, ensure the following are set in your `.env`:

```env
AUTH_MODE=oauth
OAUTH_CLIENT_ID=your_client_id_here
OAUTH_CLIENT_SECRET=your_client_secret_here
PUBLIC_BASE_URL=https://your-domain.ddns.net
```

Generate credentials:

```bash
openssl rand -hex 16   # for OAUTH_CLIENT_ID
openssl rand -hex 16   # for OAUTH_CLIENT_SECRET
```

Rebuild and restart:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

## Verify Before Connecting

Run these three checks before adding the connector in ChatGPT.

**1. OAuth discovery**

```bash
curl https://your-domain.ddns.net/.well-known/oauth-authorization-server
```

Expected response:

```json
{
  "issuer": "https://your-domain.ddns.net",
  "token_endpoint": "https://your-domain.ddns.net/oauth/token",
  "grant_types_supported": ["client_credentials"],
  "token_endpoint_auth_methods_supported": ["client_secret_post"]
}
```

**2. Token issuance**

```bash
curl -X POST https://your-domain.ddns.net/oauth/token \
  -d "grant_type=client_credentials&client_id=YOUR_ID&client_secret=YOUR_SECRET"
```

Expected: `{"access_token": "...", "token_type": "bearer", "expires_in": 3600}`

**3. MCP access**

```bash
TOKEN=<access_token from above>
curl -X POST https://your-domain.ddns.net/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

Expected: JSON response listing the `real-estate` tools.

## Add the Connector in ChatGPT

Once all three checks pass:

1. Go to **Settings → Connectors** → **Add connector**
2. Enter the MCP server URL:
   ```
   https://your-domain.ddns.net/mcp
   ```
3. Select **OAuth** as the authentication type and enter:

   | Field | Value |
   |-------|-------|
   | Client ID | `OAUTH_CLIENT_ID` from `.env` |
   | Client Secret | `OAUTH_CLIENT_SECRET` from `.env` |

4. Confirm the `real-estate` tools appear in the connector tool list.

## Remove

Go to **Settings → Connectors** and delete the `real-estate` connector entry.
