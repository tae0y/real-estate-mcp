# Connect with Claude Desktop

This page describes how to connect the real estate MCP server to [Claude Desktop](https://claude.ai/download).

## Prerequisites

- [Claude Desktop](https://claude.ai/download)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- API key from [공공데이터포털](https://www.data.go.kr)

## Option 1: stdio (recommended)

The server runs as a child process of Claude Desktop. No separate server process is needed.

1. Clone this repository locally.

    ```bash
    git clone <repository_url>
    cd claude-real-estate-openapi
    ```

1. Open the Claude Desktop config file.

    ```bash
    open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    ```

1. Add the entry below under `mcpServers`.

    ```json
    {
      "mcpServers": {
        "real-estate": {
          "command": "uv",
          "args": [
            "run",
            "--directory", "/path/to/claude-real-estate-openapi",
            "python", "src/real_estate/mcp_server/server.py"
          ],
          "env": {
            "DATA_GO_KR_API_KEY": "your_api_key_here"
          }
        }
      }
    }
    ```

    Replace `/path/to/claude-real-estate-openapi` with the actual path to your cloned repository.

    If you want separate keys per service, add more entries under `env`:

    ```json
    "env": {
      "DATA_GO_KR_API_KEY": "...",
      "ODCLOUD_API_KEY": "...",
      "ODCLOUD_SERVICE_KEY": "...",
      "ONBID_API_KEY": "..."
    }
    ```

1. Restart Claude Desktop.
   Setup is complete when you can see the `real-estate` server in the tool list.

1. For better responses, create a **Project** in Claude Desktop and paste [prompt.custom-instructions-ko.md](prompt.custom-instructions-ko.md) into the **Project Instructions** tab.

   > Paste it into the **Project Instructions** tab, not the chat input.

## Option 2: HTTP (streamable-http)

The server runs as a standalone HTTP process. Claude Desktop connects to it over a local URL. Use this when you want to share one running server instance across multiple clients.

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

1. Open the Claude Desktop config file.

    ```bash
    open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    ```

1. Add the entry below under `mcpServers`.

    ```json
    {
      "mcpServers": {
        "real-estate": {
          "type": "http",
          "url": "http://127.0.0.1:8000/mcp"
        }
      }
    }
    ```

1. Restart Claude Desktop.
   Setup is complete when you can see the `real-estate` server in the tool list.
