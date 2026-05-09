# Korea Real Estate MCP

[English](README.md) | [한국어](README-ko.md)

Connect Claude to Korea's MOLIT real estate API and simulate **buy now / buy later / invest only** scenarios based on your income, savings, and retirement goals.
Provides 14+ tools for live transaction data and financial calculations — apartment, officetel, villa, single-house, and commercial.

> [!WARNING]
> **Deprecation Notice — effective June 1, 2025**
>
> **Caddy reverse proxy** support will be removed. Cloudflare Tunnel is the recommended replacement and is already available in `docker/docker-compose.yml` via `--profile cloudflare`. See [docs/setup-reverse-proxy.md](docs/setup-reverse-proxy.md) for migration instructions.
>
> **Onbid (공매) support** will be removed. Onbid's API has required repeated patches that are no longer sustainable to maintain as a personal project. All `get_public_auction_*` and `get_onbid_*` tools will be deleted.

## Supported Tools

- [x] Apartment trade / rent (`get_apartment_trades`, `get_apartment_rent`)
- [x] Officetel trade / rent (`get_officetel_trades`, `get_officetel_rent`)
- [x] Villa / multi-family housing trade / rent (`get_villa_trades`, `get_villa_rent`)
- [x] Single-house / multi-household trade / rent (`get_single_house_trades`, `get_single_house_rent`)
- [x] Commercial building trades (`get_commercial_trade`)
- [x] Apartment subscription notices / results (`get_apt_subscription_info`, `get_apt_subscription_results`)
- [ ] ~~Onbid public auction bid results (`get_public_auction_items`, `get_public_auction_item_detail`)~~ / 🗑️ Removed June 1, 2025
- [ ] ~~Onbid item lookup (`get_onbid_thing_info_list`)~~ / 🗑️ Removed June 1, 2025
- [ ] ~~Onbid code / address lookup (`get_onbid_*_code_info`, `get_onbid_addr*_info`)~~ / 🗑️ Removed June 1, 2025
- [x] Region code lookup (`get_region_code`)

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- API key from [공공데이터포털](https://www.data.go.kr) — apply for the services below:
  - [국토교통부\_아파트 매매 실거래가 자료](https://www.data.go.kr/data/15126469/openapi.do)
  - [국토교통부\_아파트 전월세 자료](https://www.data.go.kr/data/15126474/openapi.do)
  - [국토교통부\_오피스텔 매매 신고 자료](https://www.data.go.kr/data/15126464/openapi.do)
  - [국토교통부\_오피스텔 전월세 자료](https://www.data.go.kr/data/15126475/openapi.do)
  - [국토교통부\_연립다세대 매매 실거래가 자료](https://www.data.go.kr/data/15126467/openapi.do)
  - [국토교통부\_연립다세대 전월세 실거래가 자료](https://www.data.go.kr/data/15126473/openapi.do)
  - [국토교통부\_단독/다가구 매매 실거래가 자료](https://www.data.go.kr/data/15126465/openapi.do)
  - [국토교통부\_단독/다가구 전월세 자료](https://www.data.go.kr/data/15126472/openapi.do)
  - [국토교통부\_상업업무용 부동산 매매 신고 자료](https://www.data.go.kr/data/15126463/openapi.do)
  - [한국자산관리공사\_온비드 코드 조회서비스](https://www.data.go.kr/data/15000920/openapi.do)
  - [한국자산관리공사\_온비드 물건 정보 조회서비스](https://www.data.go.kr/data/15000837/openapi.do)
  - [한국자산관리공사\_차세대 온비드 물건 입찰결과목록 조회서비스](https://www.data.go.kr/data/15157252/openapi.do)
  - [한국자산관리공사\_차세대 온비드 물건 입찰결과상세 조회서비스](https://www.data.go.kr/data/15157254/openapi.do)
  - [한국부동산원_청약홈_APT 분양정보](https://www.data.go.kr/data/15101046/fileData.do)
  - [한국부동산원_청약홈 청약 신청·당첨자 정보 조회 서비스](https://www.data.go.kr/data/15110812/openapi.do)

> For parsing API specs in hwp or docx format, see [Common Utils Guide](docs/guide-common-utils.md)

## Quick Start: Claude Desktop (stdio)

The fastest way to get started — the server runs as a child process of Claude Desktop.

1. Clone this repository locally.

    ```bash
    git clone <repository_url>
    cd real-estate-mcp
    ```

1. Open the Claude Desktop config file.

    ```bash
    # macOS
    open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    ```

    ```powershell
    # Windows
    notepad %APPDATA%\Claude\claude_desktop_config.json
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

1. Restart Claude Desktop.
   Setup is complete when you can see the `real-estate` server in the tool list.

1. For better responses, create a **Project** in Claude Desktop and paste [resources/custom-instructions-ko.md](resources/custom-instructions-ko.md) into the **Project Instructions** tab.

## Connect with Other Clients

For other clients, transport options, or per-service API key configuration, see the docs below.

| Guide | Transport | Clients |
|-------|-----------|---------|
| [docs/setup-prerequisites.md](docs/setup-prerequisites.md) | — | All clients |
| [docs/setup-with-stdio.md](docs/setup-with-stdio.md) | stdio / local HTTP | Claude Desktop, Claude CLI, Codex CLI |
| [docs/setup-with-http.md](docs/setup-with-http.md) | HTTP (remote) | Claude (web), Claude CLI, Codex CLI |
| [docs/setup-reverse-proxy.md](docs/setup-reverse-proxy.md) | — | Server-side proxy setup (Cloudflare Tunnel / Caddy) |

> **Deprecation notice (April 2025):** ChatGPT support and the Caddy reverse proxy option will be removed at the end of April 2025.
> ChatGPT's required OAuth flow (Auth0 + PKCE + DCR) is too complex to maintain — it will be re-evaluated for a future release.
> Caddy is replaced by [Cloudflare Tunnel](docs/setup-reverse-proxy.md), which requires no port forwarding and no TLS certificate management.

## Contributors

This project exists thanks to all the people who contribute. [[Contributing](https://github.com/tae0y/real-estate-mcp/blob/main/CONTRIBUTING.md)]

<a href="https://github.com/tae0y/real-estate-mcp/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=tae0y/real-estate-mcp" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

## Support

If you find this project useful, buy me a coffee!

<a href="https://www.buymeacoffee.com/tae0y" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>