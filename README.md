# Korea Real Estate OpenAPI for Claude

MCP server exposing Korea's MOLIT (국토교통부) real estate transaction API to Claude Desktop.
Provides 14+ tools for querying apartment, officetel, villa, single-house, and commercial trade/rent data, apartment subscriptions, and public auctions.

Additional project docs:
- [Common Utils Guide](docs/common_utils.md)

## Supported Tools

- [x] Apartment trade / rent (`get_apartment_trades`, `get_apartment_rent`)
- [x] Officetel trade / rent (`get_officetel_trades`, `get_officetel_rent`)
- [x] Villa / multi-family housing trade / rent (`get_villa_trades`, `get_villa_rent`)
- [x] Single-house / multi-household trade / rent (`get_single_house_trades`, `get_single_house_rent`)
- [x] Commercial building trades (`get_commercial_trade`)
- [x] Apartment subscription notices / results (`get_apt_subscription_info`, `get_apt_subscription_results`)
- [x] Onbid public auction bid results (`get_public_auction_items`)
- [x] Onbid item lookup (`get_onbid_thing_info_list`)
- [x] Onbid code / address lookup (`get_onbid_*_code_info`, `get_onbid_addr*_info`)
- [x] Region code lookup (`get_region_code`)

## Prerequisites

- [Claude Desktop](https://claude.ai/download)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [공공데이터포털 API 키](https://www.data.go.kr) (apply for the services below)
  - 국토교통부_아파트 매매 실거래가 자료
  - 국토교통부_아파트 전월세 자료
  - 국토교통부_오피스텔 매매 신고 자료
  - 국토교통부_오피스텔 전월세 자료
  - 국토교통부_연립다세대 매매 실거래가 자료
  - 국토교통부_연립다세대 전월세 실거래가 자료
  - 국토교통부_단독/다가구 매매 실거래가 자료
  - 국토교통부_단독/다가구 전월세 자료
  - 국토교통부_상업용건물(오피스) 매매 신고 자료
  - 한국자산관리공사_온비드 캠코공매물건 조회서비스
  - 한국자산관리공사_온비드 이용기관 공매물건 조회서비스
  - 한국자산관리공사_온비드 코드 조회서비스
  - 청약홈 APT 공고 (ApplyhomeInfoSvc, ApplyhomeStatSvc)

## Getting Started

### Configure Claude Desktop

1. Clone this repository locally.

    ```bash
    git clone <repository_url>
    cd claude-real-estate-openapi
    ```

1. Open the Claude Desktop config file (`claude_desktop_config.json`).

    ```bash
    open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    ```

1. Add the entry below under `mcpServers`.
   If you already have other servers, add only the `real-estate` object inside the existing `mcpServers` object.

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

1. Restart Claude Desktop.
   Setup is complete when you can see the `real-estate` server in the tool list.

1. For better responses, create a **Project** in Claude Desktop and paste [docs/prompt.custom-instructions-ko.md](docs/prompt.custom-instructions-ko.md) into the **Project Instructions** tab.

   > Paste it into the **Project Instructions** tab, not the chat input.

### Configure Codex CLI

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

1. For better responses in Codex CLI, create an `AGENTS.md` file in the project root and paste [docs/prompt.custom-instructions-ko.md](docs/prompt.custom-instructions-ko.md) into it.

   > In Codex CLI, use `AGENTS.md` (project root) instead of Claude Desktop's **Project Instructions** tab.

### Configure Claude CLI

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

### Run and Debug Locally

1. Create a `.env` file in the project root.

    ```bash
    cp .env.example .env
    ```

    Set your API key in the file.

    ```
    DATA_GO_KR_API_KEY=your_api_key_here
    ```

    `DATA_GO_KR_API_KEY` is also used by default for Applyhome (odcloud) and Onbid (B010003).
    If you want different keys per service, set:

    ```
    ODCLOUD_API_KEY=...        # Applyhome Authorization header
    ODCLOUD_SERVICE_KEY=...    # Applyhome query param
    ONBID_API_KEY=...          # Onbid
    ```

1. If Inspector is already running, stop it first.

    ```bash
    PID=$(lsof -ti :6274)
    [ -n "$PID" ] && kill $PID
    ```

1. Run MCP Inspector.

    ```bash
    uv run mcp dev src/real_estate/mcp_server/server.py
    ```

    Your browser opens automatically.
    If the window is closed or you need to reconnect, open the full URL shown after `MCP Inspector is up and running at:` in the terminal.
    (Example: `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...`)

1. Run `get_region_code` first to check `LAWD_CD`, then call tools like `get_apartment_trades` to verify everything works.
