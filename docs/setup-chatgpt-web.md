# Connect with ChatGPT (Web)

This page describes how to connect the real estate MCP server to [ChatGPT](https://chatgpt.com) via the deep research / connector feature.

> **Note:** ChatGPT's MCP connector only supports HTTP transport. The stdio mode is not available.

## Prerequisites

- ChatGPT Plus / Pro / Team / Enterprise account (MCP connector feature required)
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

1. In ChatGPT, open **Settings → Connectors** (or the equivalent MCP integration page) and add a new connector with the URL:

    ```
    https://xxxx.ngrok-free.app/mcp
    ```

    If the server has `AUTH_MODE=oauth` enabled, ChatGPT will ask for OAuth credentials.
    Select **OAuth** as the authentication type and enter:

    | Field | Value |
    |-------|-------|
    | OAuth Client ID | value of `OAUTH_CLIENT_ID` from `.env` |
    | OAuth Client Secret | value of `OAUTH_CLIENT_SECRET` from `.env` |

    The token URL used internally is `https://your-domain.com/oauth/token`.

1. Confirm the `real-estate` tools appear in the connector tool list.

## Notes

- The MCP endpoint path is `/mcp` (e.g. `http://127.0.0.1:8000/mcp`).
- For production use, deploy behind a reverse proxy (nginx, Caddy, etc.) with a valid TLS certificate instead of ngrok.
- ChatGPT does not support `AGENTS.md` or **Project Instructions** in the same way as Claude clients. Add any custom instructions directly in the ChatGPT system prompt or custom instructions settings.

## Remove

In ChatGPT, open **Settings → Connectors** and delete the `real-estate` connector entry.
