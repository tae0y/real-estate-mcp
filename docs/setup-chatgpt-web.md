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

- Name: `real-estate-mcp`
- Allowed Callback URLs: `https://chatgpt.com/connector_platform_oauth_redirect`

### 3. Create an API

**Applications → APIs → Create API**

- Name: `real-estate-mcp-api`
- Identifier (audience): `https://your-domain.ddns.net/mcp`

### 4. Enable Dynamic Client Registration

**Settings → Advanced → Enable Dynamic Client Registration**

ChatGPT auto-registers itself as a client on first connection. This setting must be on.

### 5. Note your tenant domain

**Settings → General → Domain**

Format: `your-tenant.us.auth0.com` (includes region subdomain — not `your-tenant.auth0.com`)

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

**3. DCR endpoint**

```bash
curl -X POST https://your-tenant.us.auth0.com/oidc/register \
  -H "Content-Type: application/json" \
  -d '{"client_name":"test","redirect_uris":["https://chatgpt.com/connector_platform_oauth_redirect"]}'
```

Expected: `{"client_id": "...", "client_secret": "...", ...}`

## Add the Connector in ChatGPT

Once all three checks pass:

1. Go to **Settings → Connectors** → **Add connector**
2. Enter the MCP server URL:
   ```
   https://your-domain.ddns.net/mcp
   ```
3. ChatGPT automatically discovers Auth0 via `/.well-known/oauth-protected-resource` and redirects you to the Auth0 login page — **no client ID/secret input required**.
4. Log in with your Auth0 account and authorize.
5. Confirm the `real-estate` tools appear in the connector tool list.

## Access Control (Open / Close)

### Open access (share with colleagues)

1. Auth0 → **Settings → Advanced → Enable Dynamic Client Registration**
2. Share the MCP URL: `https://your-domain.ddns.net/mcp`
3. Colleagues add it as a ChatGPT connector and log in with their Auth0 account

### Close access (revoke all)

**Option A — Disable DCR (quickest, blocks all new and re-authentication)**

Auth0 → **Settings → Advanced → Disable Dynamic Client Registration**

Existing sessions remain valid until token expiry (default 1 hour), then all users are blocked on re-authentication.

**Option B — Block specific users**

Auth0 → **User Management → Users** → select user → **Block**

Blocks that user immediately on next token refresh without affecting others.

### Remove your own connector

Go to **Settings → Connectors** and delete the `real-estate` connector entry.
