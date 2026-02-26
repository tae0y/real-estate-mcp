# Korea Real Estate MCP

[English](README.md) | [한국어](README-ko.md)

Ask Claude about Korean apartment prices — powered by MOLIT's open API.
Provides 14+ tools for querying apartment, officetel, villa, single-house, and commercial trade/rent data, apartment subscriptions, and public auctions.

## Supported Tools

- [x] Apartment trade / rent (`get_apartment_trades`, `get_apartment_rent`)
- [x] Officetel trade / rent (`get_officetel_trades`, `get_officetel_rent`)
- [x] Villa / multi-family housing trade / rent (`get_villa_trades`, `get_villa_rent`)
- [x] Single-house / multi-household trade / rent (`get_single_house_trades`, `get_single_house_rent`)
- [x] Commercial building trades (`get_commercial_trade`)
- [x] Apartment subscription notices / results (`get_apt_subscription_info`, `get_apt_subscription_results`)
- [ ] Onbid public auction bid results (`get_public_auction_items`)
- [x] Onbid item lookup (`get_onbid_thing_info_list`)
- [x] Onbid code / address lookup (`get_onbid_*_code_info`, `get_onbid_addr*_info`)
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
  - 한국자산관리공사\_온비드 물건 정보 조회서비스 / ⚠️ WIP
  - 한국자산관리공사\_차세대 온비드 물건 입찰결과목록 조회서비스 / ⚠️ WIP
  - 한국자산관리공사\_차세대 온비드 물건 입찰결과상세 조회서비스 / ⚠️ WIP
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

1. Restart Claude Desktop.
   Setup is complete when you can see the `real-estate` server in the tool list.

1. For better responses, create a **Project** in Claude Desktop and paste [resources/custom-instructions-ko.md](resources/custom-instructions-ko.md) into the **Project Instructions** tab.

## Connect with Other Clients

For HTTP mode, other clients, or per-service API key configuration, see the docs below.

| Client | Transport | Guide |
|--------|-----------|-------|
| Claude Desktop | stdio / HTTP | [docs/setup-claude-desktop.md](docs/setup-claude-desktop.md) |
| Claude (web) | HTTP only | [docs/setup-claude-web.md](docs/setup-claude-web.md) |
| Claude CLI | stdio / HTTP | [docs/setup-claude-cli.md](docs/setup-claude-cli.md) |
| Codex CLI | stdio / HTTP | [docs/setup-codex-cli.md](docs/setup-codex-cli.md) |
| ChatGPT (web) | HTTP only | [docs/setup-chatgpt-web.md](docs/setup-chatgpt-web.md) |
| Docker (HTTP + Caddy) | HTTP | [docs/setup-docker.md](docs/setup-docker.md) |
| OAuth (public access) | — | [docs/setup-oauth.md](docs/setup-oauth.md) |

## Contributors

This project exists thanks to all the people who contribute. [[Contributing](https://github.com/tae0y/real-estate-mcp/blob/main/CONTRIBUTING.md)]

<a href="https://github.com/tae0y/real-estate-mcp/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=tae0y/real-estate-mcp" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

## Support

If you find this project useful, buy me a coffee!

<a href="https://www.buymeacoffee.com/tae0y" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>