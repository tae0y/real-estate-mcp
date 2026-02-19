# Korea Real Estate MCP

[English](README.md) | [한국어](README-ko.md)

국토교통부 공공데이터 API를 기반으로 Claude에게 한국 부동산 실거래가를 질문할 수 있는 MCP 서버입니다.
국토교통부 실거래가 API를 MCP 서버로 제공하며, 아파트·오피스텔·빌라·단독주택·상업용 건물의 매매·전월세, 청약 공고·결과, 온비드 공매 조회를 포함한 14개 이상의 도구를 제공합니다.

## Supported Tools

- [x] 아파트 매매 / 전월세 (`get_apartment_trades`, `get_apartment_rent`)
- [x] 오피스텔 매매 / 전월세 (`get_officetel_trades`, `get_officetel_rent`)
- [x] 빌라·연립다세대 매매 / 전월세 (`get_villa_trades`, `get_villa_rent`)
- [x] 단독·다가구 매매 / 전월세 (`get_single_house_trades`, `get_single_house_rent`)
- [x] 상업용 건물 매매 (`get_commercial_trade`)
- [x] 아파트 청약 공고 / 결과 (`get_apt_subscription_info`, `get_apt_subscription_results`)
- [x] 온비드 공매 입찰결과 (`get_public_auction_items`)
- [x] 온비드 물건 조회 (`get_onbid_thing_info_list`)
- [x] 온비드 코드·주소 조회 (`get_onbid_*_code_info`, `get_onbid_addr*_info`)
- [x] 지역코드 조회 (`get_region_code`)

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [공공데이터포털 API 키](https://www.data.go.kr) — 아래 서비스를 신청하세요.
  - [국토교통부\_아파트 매매 실거래가 자료](https://www.data.go.kr/data/15126469/openapi.do)
  - [국토교통부\_아파트 전월세 자료](https://www.data.go.kr/data/15126474/openapi.do)
  - [국토교통부\_오피스텔 매매 신고 자료](https://www.data.go.kr/data/15126464/openapi.do)
  - [국토교통부\_오피스텔 전월세 자료](https://www.data.go.kr/data/15126475/openapi.do)
  - [국토교통부\_연립다세대 매매 실거래가 자료](https://www.data.go.kr/data/15126467/openapi.do)
  - [국토교통부\_연립다세대 전월세 실거래가 자료](https://www.data.go.kr/data/15126473/openapi.do)
  - [국토교통부\_단독/다가구 매매 실거래가 자료](https://www.data.go.kr/data/15126465/openapi.do)
  - [국토교통부\_단독/다가구 전월세 자료](https://www.data.go.kr/data/15126472/openapi.do)
  - [국토교통부\_상업업무용 부동산 매매 신고 자료](https://www.data.go.kr/data/15126463/openapi.do)
  - [한국자산관리공사\_온비드 캠코공매물건 조회서비스](https://www.data.go.kr/data/15000851/openapi.do)
  - [한국자산관리공사\_온비드 이용기관 공매물건 조회서비스](https://www.data.go.kr/data/15000849/openapi.do)
  - [한국자산관리공사\_온비드 코드 조회서비스](https://www.data.go.kr/data/15000920/openapi.do)
  - [한국부동산원_청약홈_APT 분양정보](https://www.data.go.kr/data/15101046/fileData.do)
  - [한국부동산원_청약홈 청약 신청·당첨자 정보 조회 서비스](https://www.data.go.kr/data/15110812/openapi.do)

> hwp, docx 포맷 API 명세서 처리 시 다음 문서를 참고하세요: [Common Utils Guide](docs/guide-common-utils.md)

## Quick Start: Claude Desktop (stdio)

가장 빠른 시작 방법입니다 — 서버가 Claude Desktop 하위 프로세스로 동작합니다.

1. 저장소를 클론하세요.

    ```bash
    git clone <repository_url>
    cd real-estate-mcp
    ```

1. Claude Desktop 설정 파일을 여세요.

    ```bash
    open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    ```

1. `mcpServers`에 아래 항목을 추가하세요.

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

1. Claude Desktop을 재시작하세요. 도구 목록에 `real-estate` 서버가 표시되면 완료입니다.

1. 더 정확한 응답을 위해 Claude Desktop에서 **Project**를 생성하고, [resources/custom-instructions-ko.md](resources/custom-instructions-ko.md) 내용을 **Project Instructions** 탭에 붙여넣으세요.

## Connect with Other Clients

HTTP 모드, 다른 클라이언트, 서비스별 API 키 설정은 아래 문서를 참고하세요.

| 클라이언트 | 전송 방식 | 가이드 |
|-----------|----------|--------|
| Claude Desktop | stdio / HTTP | [docs/setup-claude-desktop.md](docs/setup-claude-desktop.md) |
| Claude (웹) | HTTP only | [docs/setup-claude-web.md](docs/setup-claude-web.md) |
| Claude CLI | stdio / HTTP | [docs/setup-claude-cli.md](docs/setup-claude-cli.md) |
| Codex CLI | stdio / HTTP | [docs/setup-codex-cli.md](docs/setup-codex-cli.md) |
| ChatGPT (웹) | HTTP only | [docs/setup-chatgpt-web.md](docs/setup-chatgpt-web.md) |
| Docker (HTTP + Caddy) | HTTP | [docs/setup-docker.md](docs/setup-docker.md) |
| OAuth (공개 접근) | — | [docs/setup-oauth.md](docs/setup-oauth.md) |
