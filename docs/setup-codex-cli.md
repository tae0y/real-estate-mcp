# Connect with Codex CLI

This page describes how to connect the real estate MCP server to [Codex CLI](https://github.com/openai/codex).

## Prerequisites

- [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- API key from [공공데이터포털](https://www.data.go.kr)

## Option 1: stdio (recommended)

The server runs as a child process of Codex CLI. No separate server process is needed.

1. Clone this repository locally.

    ```bash
    git clone <repository_url>
    cd claude-real-estate-openapi
    ```

1. Register this MCP server in Codex CLI.

    ```bash
    codex mcp add real-estate \
      --env DATA_GO_KR_API_KEY=your_api_key_here \
      -- uv run --directory /path/to/claude-real-estate-openapi \
      python src/real_estate/mcp_server/server.py
    ```

    Replace `/path/to/claude-real-estate-openapi` with the actual path to your cloned repository.

    If you want separate keys per service, add more `--env` options:

    ```bash
    codex mcp add real-estate \
      --env DATA_GO_KR_API_KEY=... \
      --env ODCLOUD_API_KEY=... \
      --env ODCLOUD_SERVICE_KEY=... \
      --env ONBID_API_KEY=... \
      -- uv run --directory /path/to/claude-real-estate-openapi \
      python src/real_estate/mcp_server/server.py
    ```

1. Verify that the server is registered.

    ```bash
    codex mcp list
    codex mcp get real-estate
    ```

1. For better responses in Codex CLI, create an `AGENTS.md` file in your working project root and paste [prompt.custom-instructions-ko.md](prompt.custom-instructions-ko.md) into it.

   > In Codex CLI, use `AGENTS.md` (project root) instead of Claude Desktop's **Project Instructions** tab.

## Option 2: HTTP (streamable-http)

The server runs as a standalone HTTP process. Use this when you want to share one running server instance across multiple clients.

1. Clone this repository locally.

    ```bash
    git clone <repository_url>
    cd claude-real-estate-openapi
    ```

1. Create a `.env` file in the project root (the server reads it on startup).

    ```bash
    cp .env.example .env
    ```

    Set your API key:

    ```
    DATA_GO_KR_API_KEY=your_api_key_here
    ```

1. Start the server.

    ```bash
    uv run python src/real_estate/mcp_server/server.py --transport http
    ```

    By default this binds to `http://127.0.0.1:8000`. To change host or port:

    ```bash
    uv run python src/real_estate/mcp_server/server.py --transport http --host 0.0.0.0 --port 9000
    ```

1. Register the server in Codex CLI using the HTTP URL.

    ```bash
    codex mcp add real-estate \
      --transport http \
      --url http://127.0.0.1:8000/mcp
    ```

1. Verify that the server is registered.

    ```bash
    codex mcp list
    codex mcp get real-estate
    ```
