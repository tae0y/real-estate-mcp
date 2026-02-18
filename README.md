# Korea Real Estate OpenAPI for Claude

MCP server exposing Korea's MOLIT (국토교통부) real estate transaction API to Claude Desktop.
Provides 14+ tools for querying apartment, officetel, villa, single-house, and commercial trade/rent data, apartment subscriptions, and public auctions.

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

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- API key from [공공데이터포털](https://www.data.go.kr) — apply for the services below:
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

## Quick Start: Claude Desktop (stdio)

The fastest way to get started — the server runs as a child process of Claude Desktop.

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

1. Restart Claude Desktop.
   Setup is complete when you can see the `real-estate` server in the tool list.

1. For better responses, create a **Project** in Claude Desktop and paste [docs/prompt.custom-instructions-ko.md](docs/prompt.custom-instructions-ko.md) into the **Project Instructions** tab.

For HTTP mode, other clients, or per-service API key configuration, see the docs below.

## Connect with Other Clients

| Client | Transport | Guide |
|--------|-----------|-------|
| Claude Desktop | stdio / HTTP | [docs/setup-claude-desktop.md](docs/setup-claude-desktop.md) |
| Claude CLI | stdio / HTTP | [docs/setup-claude-cli.md](docs/setup-claude-cli.md) |
| Codex CLI | stdio / HTTP | [docs/setup-codex-cli.md](docs/setup-codex-cli.md) |
| ChatGPT (web) | HTTP only | [docs/setup-chatgpt-web.md](docs/setup-chatgpt-web.md) |

## Run on Local Machine

1. Get the repository root.

    ```bash
    # bash/zsh
    REPOSITORY_ROOT=$(git rev-parse --show-toplevel)
    ```

    ```powershell
    # PowerShell
    $REPOSITORY_ROOT = git rev-parse --show-toplevel
    ```

1. Create a `.env` file in the project root.

    ```bash
    cp .env.example .env
    ```

    Set your API key:

    ```
    DATA_GO_KR_API_KEY=your_api_key_here
    ```

    `DATA_GO_KR_API_KEY` is also used by default for Applyhome (odcloud) and Onbid.
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

1. Run `get_region_code` first to check `LAWD_CD`, then call tools like `get_apartment_trades` to verify everything works.

## Run in Docker

Packages the MCP server + Caddy reverse proxy as containers.
Use this to serve over HTTP for ChatGPT or other remote clients.

1. Get the repository root.

    ```bash
    # bash/zsh
    REPOSITORY_ROOT=$(git rev-parse --show-toplevel)
    ```

    ```powershell
    # PowerShell
    $REPOSITORY_ROOT = git rev-parse --show-toplevel
    ```

1. Create a `.env` file in the project root (same as local setup above).

1. Build and start the containers.

    ```bash
    # bash/zsh
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d --build
    ```

    ```powershell
    # PowerShell
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml up -d --build
    ```

1. Verify the MCP server is running.

    ```bash
    curl http://localhost/mcp
    ```

1. To stop the containers:

    ```bash
    # bash/zsh
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml down
    ```

    ```powershell
    # PowerShell
    docker compose -f $REPOSITORY_ROOT/docker/docker-compose.yml down
    ```

For domain + HTTPS setup (home server deployment), see [docs/setup-docker.md](docs/setup-docker.md).

## Additional Docs

- [Common Utils Guide](docs/common_utils.md)
