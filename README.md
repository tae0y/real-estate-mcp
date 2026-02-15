# Korea Real Estate OpenAPI for Claude

MCP server for querying Korea's apartment trade data (국토교통부 실거래가 API) through Claude.

## Prerequisites: Environment Variables

Set the API key before running the MCP server.

Create a `.env` file in the project root:

```
DATA_GO_KR_API_KEY=your_api_key_here
```

Obtain the API key from [공공데이터포털](https://www.data.go.kr).
Service name: 국토교통부_아파트매매_실거래가_자료

This project reuses `DATA_GO_KR_API_KEY` for Applyhome(odcloud) and Onbid(B010003) by default.
If you want to override:
- Applyhome: `ODCLOUD_API_KEY` (Authorization header) or `ODCLOUD_SERVICE_KEY` (query param)
- Onbid: `ONBID_API_KEY`

`.env` is listed in `.gitignore` and will not be committed.
Both MCP Inspector and Claude Desktop require this key to function correctly.

## Testing with MCP Inspector

Test the MCP tools directly over the MCP protocol locally.

```bash
uv run mcp dev src/real_estate/mcp_server/server.py
```

Open `http://localhost:6274` in a browser, then:

1. Add `DATA_GO_KR_API_KEY` under **Environment Variables**
2. Click **Connect**
3. Call `get_region_code` first, then `get_apartment_trades`

Inspector does not load `.env` automatically — the API key must be entered directly in the UI.

## Registering with Claude Desktop

Open the config file:

```bash
open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

Add the `real-estate` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "real-estate": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/Users/bachtaeyeong/10_SrcHub/claude-real-estate-openapi",
        "python", "src/real_estate/mcp_server/server.py"
      ],
      "env": {
        "DATA_GO_KR_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

Restart Claude Desktop after saving. The `real-estate` server will appear in the tool list.
