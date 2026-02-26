# Connect with Claude (Web)

This page describes how to connect the real estate MCP server to [Claude.ai](https://claude.ai) via the Integrations feature.

> **Note:** Claude.ai's MCP integration only supports HTTP transport. The stdio mode is not available.

## Prerequisites

- Claude Pro / Team / Enterprise account (Integrations feature required)
- A publicly reachable HTTPS URL
  - Recommended: DDNS (e.g. no-ip) + router port forwarding (80/443) + Docker Caddy setup (see [setup-docker.md](setup-docker.md))

## Server Setup

Enable OAuth with the **client credentials** option in [setup-oauth.md](setup-oauth.md#option-a-client-credentials-claude-web).

## Verify Before Connecting

Run these three checks before adding the integration in Claude.ai.

1. OAuth discovery

    ```bash
    curl https://your-domain.ddns.net/.well-known/    oauth-authorization-server
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

1. Token issuance

    ```bash
    curl -X POST https://your-domain.ddns.net/oauth/token \
      -d "grant_type=client_credentials&client_id=YOUR_ID&client_secret=YOUR_SECRET"
    ```

    Expected: `{"access_token": "...", "token_type": "bearer", "expires_in": 3600}`

1. MCP access

    ```bash
    TOKEN=<access_token from above>
    curl -X POST https://your-domain.ddns.net/mcp \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
    ```

    Expected: JSON response listing the `real-estate` tools.

## Add the Integration in Claude.ai

Once all three checks pass:

1. Go to **Settings → Integrations** → **Add Integration**

1. Enter the MCP server URL:
   ```
   https://your-domain.ddns.net/mcp
   ```

1. Select **OAuth** as the authentication type and enter:

   | Field | Value |
   |-------|-------|
   | Client ID | `OAUTH_CLIENT_ID` from `.env` |
   | Client Secret | `OAUTH_CLIENT_SECRET` from `.env` |

1. Confirm the `real-estate` tools appear in the integration tool list.

## Project Instructions (Optional)

For better responses, create a **Project** in Claude.ai and paste the contents of [resources/custom-instructions-ko.md](../resources/custom-instructions-ko.md) into the **Project Instructions** tab.

## Remove

Go to **Settings → Integrations** and delete the `real-estate` integration entry.
