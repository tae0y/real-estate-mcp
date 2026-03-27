# Connect via stdio or Local HTTP

This page describes how to connect the real estate MCP server to a local client using the stdio or local HTTP transport.

## Supported clients

- [x] Claude Desktop — stdio and local HTTP
- [x] Claude CLI — stdio and local HTTP
- [x] Codex CLI — stdio and local HTTP
- [ ] Claude (Web / Claude.ai) — requires a public URL; see [setup-with-http.md](setup-with-http.md)
- [ ] ChatGPT (Web) — requires a public URL; see [setup-with-http.md](setup-with-http.md)

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- API key from [공공데이터포털](https://www.data.go.kr) — see [setup-prerequisites.md](setup-prerequisites.md)
- This repository cloned locally

---

## Option 1: stdio (recommended)

The client launches the server as a child process. No separate server process is needed.

### Claude Desktop

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
            "--directory", "/path/to/real-estate-mcp",
            "python", "src/real_estate/mcp_server/server.py"
          ],
          "env": {
            "DATA_GO_KR_API_KEY": "your_api_key_here"
          }
        }
      }
    }
    ```

    Replace `/path/to/real-estate-mcp` with the actual path to your cloned repository.

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

1. For better responses, create a **Project** in Claude Desktop and paste [resources/custom-instructions-ko.md](../resources/custom-instructions-ko.md) into the **Project Instructions** tab.

   > Paste it into the **Project Instructions** tab, not the chat input.

#### Remove

Open the config file, delete the `real-estate` entry from `mcpServers`, then restart Claude Desktop.

```bash
open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

---

### Claude CLI

1. Register the MCP server.

    ```bash
    claude mcp add -s local \
      -e DATA_GO_KR_API_KEY=your_api_key_here \
      real-estate -- \
      uv run --directory /path/to/real-estate-mcp \
      python src/real_estate/mcp_server/server.py
    ```

    Replace `/path/to/real-estate-mcp` with the actual path to your cloned repository.

    If you want separate keys per service, add more `-e` options:

    ```bash
    claude mcp add -s local \
      -e DATA_GO_KR_API_KEY=... \
      -e ODCLOUD_API_KEY=... \
      -e ODCLOUD_SERVICE_KEY=... \
      -e ONBID_API_KEY=... \
      real-estate -- \
      uv run --directory /path/to/real-estate-mcp \
      python src/real_estate/mcp_server/server.py
    ```

1. Verify that the server is registered.

    ```bash
    claude mcp list
    claude mcp get real-estate
    ```

1. For better responses, create a `CLAUDE.md` file in your working project root and paste [resources/custom-instructions-ko.md](../resources/custom-instructions-ko.md) into it.

   > In Claude CLI, use `CLAUDE.md` (project root) instead of Claude Desktop's **Project Instructions** tab.

#### Remove

```bash
claude mcp remove real-estate
```

---

### Codex CLI

1. Register the MCP server.

    ```bash
    codex mcp add real-estate \
      --env DATA_GO_KR_API_KEY=your_api_key_here \
      -- uv run --directory /path/to/real-estate-mcp \
      python src/real_estate/mcp_server/server.py
    ```

    Replace `/path/to/real-estate-mcp` with the actual path to your cloned repository.

    If you want separate keys per service, add more `--env` options:

    ```bash
    codex mcp add real-estate \
      --env DATA_GO_KR_API_KEY=... \
      --env ODCLOUD_API_KEY=... \
      --env ODCLOUD_SERVICE_KEY=... \
      --env ONBID_API_KEY=... \
      -- uv run --directory /path/to/real-estate-mcp \
      python src/real_estate/mcp_server/server.py
    ```

1. Verify that the server is registered.

    ```bash
    codex mcp list
    codex mcp get real-estate
    ```

1. For better responses, create an `AGENTS.md` file in your working project root and paste [resources/custom-instructions-ko.md](../resources/custom-instructions-ko.md) into it.

   > In Codex CLI, use `AGENTS.md` (project root) instead of Claude Desktop's **Project Instructions** tab.

#### Remove

```bash
codex mcp remove real-estate
```

---

## Option 2: Local HTTP

The server runs as a standalone process and clients connect over a local URL. Use this when you want to share one running server instance across multiple local clients.

> **Note:** Claude Desktop supports local HTTP but does not support public remote servers. For remote access, see [setup-with-http.md](setup-with-http.md).

### Start the server

1. Create a `.env` file in the project root.

    ```bash
    cp .env.example .env
    ```

    Set your API key:

    ```
    DATA_GO_KR_API_KEY=your_api_key_here
    ```

1. Start the server.

    ```bash
    uv run real-estate-mcp --transport http
    ```

    By default this binds to `http://127.0.0.1:8000`. To change host or port:

    ```bash
    uv run real-estate-mcp --transport http --host 0.0.0.0 --port 9000
    ```

    Leave this terminal running while you connect clients below.

### Claude Desktop

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

#### Remove

Open the config file, delete the `real-estate` entry from `mcpServers`, then restart Claude Desktop.

```bash
open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

### Claude CLI

1. Register the server using the HTTP URL.

    ```bash
    claude mcp add -s local --transport http \
      real-estate http://127.0.0.1:8000/mcp
    ```

1. Verify that the server is registered.

    ```bash
    claude mcp list
    claude mcp get real-estate
    ```

#### Remove

```bash
claude mcp remove real-estate
```

### Codex CLI

1. Register the server using the HTTP URL.

    ```bash
    codex mcp add real-estate --url http://127.0.0.1:8000/mcp
    ```

1. Verify that the server is registered.

    ```bash
    codex mcp list
    codex mcp get real-estate
    ```

#### Remove

```bash
codex mcp remove real-estate
```
