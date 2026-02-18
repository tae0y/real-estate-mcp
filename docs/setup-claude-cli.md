# Connect with Claude CLI

This page describes how to connect the real estate MCP server to [Claude CLI](https://github.com/anthropics/claude-code).

## Prerequisites

- [Claude CLI](https://github.com/anthropics/claude-code) (`npm install -g @anthropic-ai/claude-code`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- API key from [공공데이터포털](https://www.data.go.kr)

## Option 1: stdio (recommended)

The server runs as a child process of Claude CLI. No separate server process is needed.

1. Clone this repository locally.

    ```bash
    git clone <repository_url>
    cd claude-real-estate-openapi
    ```

1. Register this MCP server in Claude CLI.

    ```bash
    claude mcp add -s local \
      -e DATA_GO_KR_API_KEY=your_api_key_here \
      real-estate -- \
      uv run --directory /path/to/claude-real-estate-openapi \
      python src/real_estate/mcp_server/server.py
    ```

    Replace `/path/to/claude-real-estate-openapi` with the actual path to your cloned repository.

    If you want separate keys per service, add more `-e` options:

    ```bash
    claude mcp add -s local \
      -e DATA_GO_KR_API_KEY=... \
      -e ODCLOUD_API_KEY=... \
      -e ODCLOUD_SERVICE_KEY=... \
      -e ONBID_API_KEY=... \
      real-estate -- \
      uv run --directory /path/to/claude-real-estate-openapi \
      python src/real_estate/mcp_server/server.py
    ```

1. Verify that the server is registered.

    ```bash
    claude mcp list
    claude mcp get real-estate
    ```

1. For better responses, create a `CLAUDE.md` file in your working project root and paste [prompt.custom-instructions-ko.md](prompt.custom-instructions-ko.md) into it.

   > In Claude CLI, use `CLAUDE.md` (project root) instead of Claude Desktop's **Project Instructions** tab.

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

1. Register the server in Claude CLI using the HTTP URL.

    ```bash
    claude mcp add -s local --transport http \
      real-estate http://127.0.0.1:8000/mcp
    ```

1. Verify that the server is registered.

    ```bash
    claude mcp list
    claude mcp get real-estate
    ```
