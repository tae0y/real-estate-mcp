# Connect with Claude (Web)

This page describes how to connect the real estate MCP server to [Claude.ai](https://claude.ai) via the Integrations feature.

> **Note:** Claude.ai's MCP integration only supports HTTP transport. The stdio mode is not available.

## Prerequisites

- Claude Pro / Team / Enterprise account (Integrations feature required)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- API key from [공공데이터포털](https://www.data.go.kr)
- A publicly reachable HTTPS URL, or a tunnel tool such as [ngrok](https://ngrok.com) for local testing

## Setup

1. Clone this repository locally.

    ```bash
    git clone <repository_url>
    cd claude-real-estate-openapi
    ```

1. Create a `.env` file in the project root.

    ```bash
    cp .env.example .env
    ```

    Set your API key:

    ```
    DATA_GO_KR_API_KEY=your_api_key_here
    ```

1. Start the server in HTTP mode.

    ```bash
    uv run python src/real_estate/mcp_server/server.py --transport http --host 0.0.0.0 --port 8000
    ```

1. Expose the server over HTTPS if running locally. For example, using ngrok:

    ```bash
    ngrok http 8000
    ```

    Note the forwarding URL (e.g. `https://xxxx.ngrok-free.app`).

1. In Claude.ai, open **Settings → Integrations** and add a new integration with the URL:

    ```
    https://xxxx.ngrok-free.app/mcp
    ```

    If the server has `AUTH_MODE=oauth` enabled, Claude.ai will ask for OAuth credentials.
    Select **OAuth** as the authentication type and enter:

    | Field | Value |
    |-------|-------|
    | OAuth Client ID | value of `OAUTH_CLIENT_ID` from `.env` |
    | OAuth Client Secret | value of `OAUTH_CLIENT_SECRET` from `.env` |

    The token URL used internally is `https://your-domain.com/oauth/token`.

1. Confirm the `real-estate` tools appear in the integration tool list.

1. For better responses, create a **Project** in Claude.ai and paste [prompt.custom-instructions-ko.md](prompt.custom-instructions-ko.md) into the **Project Instructions** tab.

   > Paste it into the **Project Instructions** tab, not the chat input.

## Notes

- The MCP endpoint path is `/mcp` (e.g. `http://127.0.0.1:8000/mcp`).
- For production use, deploy behind a reverse proxy (nginx, Caddy, etc.) with a valid TLS certificate instead of ngrok.
- The Docker setup in this repository already includes a Caddy reverse proxy. See [setup-docker.md](setup-docker.md) for domain + HTTPS configuration.

## Remove

In Claude.ai, open **Settings → Integrations** and delete the `real-estate` integration entry.
