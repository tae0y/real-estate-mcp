# Connect with ChatGPT (Web)

This page describes how to connect the real estate MCP server to [ChatGPT](https://chatgpt.com) via the connector feature using Auth0 as the OAuth 2.1 identity provider.

> **Note:** ChatGPT's MCP connector only supports HTTP transport and requires OAuth 2.1 authorization code + PKCE. The stdio mode and client_credentials grant are not supported.

## Prerequisites

- ChatGPT Plus / Pro / Team / Enterprise account (MCP connector feature required)
- A publicly reachable HTTPS URL
  - Recommended: DDNS (e.g. no-ip) + router port forwarding (80/443) + Docker Caddy setup (see [setup-docker.md](setup-docker.md))
- Auth0 account (free tier is sufficient)

## Auth0 Setup

### 1. Create a tenant

Sign up at [auth0.com](https://auth0.com) and create a free tenant.

### 2. Create an Application

**Applications → Create Application → Regular Web App**

> **Important:** Select **Regular Web App**, not Machine to Machine. M2M only supports client_credentials grant and cannot do the authorization code flow required by ChatGPT.

- Name: `real-estate-mcp`
- Allowed Callback URLs: `https://chatgpt.com/connector_platform_oauth_redirect`

### 3. Create an API

**Applications → APIs → Create API**

> The "Create API" button is in the left sidebar under **Applications → APIs**, separate from **Applications → Applications**.

- Name: `real-estate-mcp-api`
- Identifier (audience): `https://your-domain.ddns.net/mcp`

### 4. Enable Dynamic Client Registration

**Settings → Advanced → Enable Dynamic Client Registration**

ChatGPT auto-registers itself as a client on first connection. This setting must be on.

### 5. Enable Application Connections (required for DCR)

**Settings → Advanced → Enable Application Connections**

This must be on. Without it, DCR-created clients have no connections enabled and Auth0 returns `no connections enabled for the client`, blocking the login page.

### 6. Set Username-Password-Authentication as domain connection

DCR-created clients still need a connection explicitly available. Set `is_domain_connection: true` on the `Username-Password-Authentication` connection via Management API:

**Step 1 — Grant update:connections permission to the Test Application**

Auth0 → **Applications → Applications → Auth0 Management API (Test Application)** → **APIs** tab → **Auth0 Management API** → enable `update:connections` → **Update**

**Step 2 — Get a Management API token**

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

**Step 3 — Find your Connection ID**

Auth0 → **Authentication → Database → Username-Password-Authentication** → the URL contains the ID:
```
.../connections/database/con_XXXXXXXXXXXXXXXX/settings
```

**Step 4 — Set as domain connection**

```bash
curl -X PATCH "https://your-tenant.us.auth0.com/api/v2/connections/con_XXXXXXXXXXXXXXXX" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_domain_connection": true}'
```

Expected: JSON response with `"is_domain_connection": true`

### 7. Create a user

Auth0 → **User Management → Users → Create User**

- Email: your email
- Password: your password
- Connection: `Username-Password-Authentication`

This account is used to log in when ChatGPT redirects to the Auth0 login page.

### 8. Note your tenant domain

**Settings → General → Domain**

Format: `your-tenant.us.auth0.com` (includes region subdomain such as `us`, `us-5`, `eu` — not `your-tenant.auth0.com`)

## Server Setup

Add the following to your `.env`:

```env
AUTH_MODE=oauth
PUBLIC_BASE_URL=https://your-domain.ddns.net

# Legacy client_credentials (Claude Web/Desktop — keep existing values)
OAUTH_CLIENT_ID=your_client_id_here
OAUTH_CLIENT_SECRET=your_client_secret_here

# Auth0 (ChatGPT Web)
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://your-domain.ddns.net/mcp
```

Rebuild and restart:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

> **Note:** `AUTH_MODE` is read directly from `.env` by Caddy. Do not export it from the host shell — the compose file handles it via `env_file`.

## Verify Before Connecting

**1. Protected resource metadata (ChatGPT reads this first)**

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

**2. Authorization server metadata (must include PKCE + registration_endpoint)**

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

**3. MCP endpoint returns 401 (auth guard is active)**

```bash
curl -o /dev/null -w "%{http_code}" https://your-domain.ddns.net/mcp
# Expected: 401
```

If this returns 406 or reaches the MCP server without auth, `AUTH_MODE` is not being read correctly by Caddy — verify the container env: `docker compose exec caddy sh -c 'env | grep AUTH_MODE'`

**4. DCR endpoint**

```bash
curl -X POST https://your-tenant.us.auth0.com/oidc/register \
  -H "Content-Type: application/json" \
  -d '{"client_name":"test","redirect_uris":["https://chatgpt.com/connector_platform_oauth_redirect"]}'
```

Expected: `{"client_id": "...", "client_secret": "...", ...}`

## Add the Connector in ChatGPT

Once all four checks pass:

1. Go to **Settings → Connectors** → **Add connector**
2. Enter the MCP server URL:
   ```
   https://your-domain.ddns.net/mcp
   ```
3. ChatGPT automatically discovers Auth0 via `/.well-known/oauth-protected-resource` and redirects you to the Auth0 login page — **no client ID/secret input required**.
4. Log in with the Auth0 user created in step 7 above.
5. Confirm the `real-estate` tools appear in the connector tool list.

## Access Control (Open / Close)

### Open access (share with colleagues)

1. Auth0 → **Settings → Advanced → Enable Dynamic Client Registration**
2. Auth0 → **User Management → Users → Create User** — create an account for each colleague
3. Share the MCP URL: `https://your-domain.ddns.net/mcp`
4. Colleagues add it as a ChatGPT connector and log in with their Auth0 account

### Close access (revoke all)

**Option A — Disable DCR (quickest, blocks all new and re-authentication)**

Auth0 → **Settings → Advanced → Disable Dynamic Client Registration**

Existing sessions remain valid until token expiry (default 1 hour), then all users are blocked on re-authentication.

**Option B — Block specific users**

Auth0 → **User Management → Users** → select user → **Block**

Blocks that user immediately on next token refresh without affecting others.

### Remove your own connector

Go to **Settings → Connectors** and delete the `real-estate` connector entry.
