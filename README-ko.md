# Korea Real Estate OpenAPI for Claude

MCP server exposing Korea's MOLIT (국토교통부) real estate transaction API to Claude Desktop.
Provides 13+ tools for querying apartment, officetel, villa, single-house, and commercial trade/rent data, APT subscriptions, and public auctions.

## Supported tools

- [x] 아파트 매매 / 전월세 (`get_apartment_trades`, `get_apartment_rent`)
- [x] 오피스텔 매매 / 전월세 (`get_officetel_trades`, `get_officetel_rent`)
- [x] 빌라·연립다세대 매매 (`get_villa_trades`)
- [x] 단독·다가구 매매 / 전월세 (`get_single_house_trades`, `get_single_house_rent`)
- [x] 상업용 건물 매매 (`get_commercial_trade`)
- [x] 아파트 청약 공고 / 결과 (`get_apt_subscription_info`, `get_apt_subscription_results`)
- [x] 온비드 공매 입찰결과 (`get_public_auction_items`)
- [x] 온비드 물건 조회 (`get_onbid_thing_info_list`)
- [x] 온비드 코드·주소 조회 (`get_onbid_*_code_info`, `get_onbid_addr*_info`)
- [x] 지역코드 조회 (`get_region_code`)

## Prerequisites

- [Claude Desktop](https://claude.ai/download)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [공공데이터포털 API 키](https://www.data.go.kr) (아래 서비스 신청)
  - 국토교통부\_아파트 매매 실거래가 자료
  - 국토교통부\_아파트 전월세 자료
  - 국토교통부\_오피스텔 매매 신고 자료
  - 국토교통부\_오피스텔 전월세 자료
  - 국토교통부\_연립다세대 매매 실거래가 자료
  - 국토교통부\_단독/다가구 매매 실거래가 자료
  - 국토교통부\_단독/다가구 전월세 자료
  - 국토교통부\_상업용건물(오피스) 매매 신고 자료
  - 한국자산관리공사\_온비드 캠코공매물건 조회서비스
  - 한국자산관리공사\_온비드 이용기관 공매물건 조회서비스
  - 한국자산관리공사\_온비드 코드 조회서비스
  - 청약홈 APT 공고 (ApplyhomeInfoSvc, ApplyhomeStatSvc)

## Getting started

### Configure Claude Desktop

1. 저장소를 로컬에 클론한다.

    ```bash
    git clone <저장소_URL>
    cd claude-real-estate-openapi
    ```

1. Claude Desktop 설정 파일(`claude_desktop_config.json`)을 연다.

    ```bash
    open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    ```

1. `mcpServers`에 아래 항목을 추가한다. 이미 다른 서버가 등록되어 있다면 `mcpServers` 객체 안에 `real-estate` 항목만 추가한다.

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

1. Claude Desktop을 재시작한다. 도구 목록에 `real-estate` 서버가 표시되면 설정이 완료된 것이다.

1. 더 정확한 응답을 위해 Claude Desktop에서 **Project**를 만들고, [docs/prompt.custom-instructions-ko.md](docs/prompt.custom-instructions-ko.md) 내용을 **Project Instructions** 탭에 붙여넣는다.

   > 파일을 채팅 입력란이 아니라 **Project Instructions** 탭에 넣어야한다.

### Configure Codex CLI

1. 저장소를 로컬에 클론한다.

    ```bash
    git clone <저장소_URL>
    cd claude-real-estate-openapi
    ```

1. Codex CLI에 MCP 서버를 등록한다.

    ```bash
    codex mcp add real-estate \
      --env DATA_GO_KR_API_KEY=your_api_key_here \
      -- uv run --directory /path/to/claude-real-estate-openapi \
      python src/real_estate/mcp_server/server.py
    ```

    서비스별로 키를 분리하려면 `--env`를 추가한다.

    ```bash
    codex mcp add real-estate \
      --env DATA_GO_KR_API_KEY=... \
      --env ODCLOUD_API_KEY=... \
      --env ODCLOUD_SERVICE_KEY=... \
      --env ONBID_API_KEY=... \
      -- uv run --directory /path/to/claude-real-estate-openapi \
      python src/real_estate/mcp_server/server.py
    ```

1. 서버 등록 상태를 확인한다.

    ```bash
    codex mcp list
    codex mcp get real-estate
    ```

1. Codex CLI에서 더 정확한 응답을 위해 프로젝트 루트에 `AGENTS.md`를 만들고, [docs/prompt.custom-instructions-ko.md](docs/prompt.custom-instructions-ko.md) 내용을 붙여넣는다.

   > Codex CLI에서는 Claude Desktop의 **Project Instructions** 탭 대신 프로젝트 루트의 `AGENTS.md`를 사용한다.

### Configure Claude CLI

1. 저장소를 로컬에 클론한다.

    ```bash
    git clone <저장소_URL>
    cd claude-real-estate-openapi
    ```

1. Claude CLI에 MCP 서버를 등록한다.

    ```bash
    claude mcp add -s local \
      -e DATA_GO_KR_API_KEY=your_api_key_here \
      real-estate -- \
      uv run --directory /path/to/claude-real-estate-openapi \
      python src/real_estate/mcp_server/server.py
    ```

    서비스별로 키를 분리하려면 `-e`를 추가한다.

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

1. 서버 등록 상태를 확인한다.

    ```bash
    claude mcp list
    claude mcp get real-estate
    ```


### Run and Debug Locally

1. 프로젝트 루트에서 `.env` 파일을 만든다.

    ```bash
    cp .env.example .env
    ```

    내부에 API Key를 설정한다.

    ```
    DATA_GO_KR_API_KEY=your_api_key_here
    ```

    `DATA_GO_KR_API_KEY`는 기본적으로 Applyhome(odcloud), Onbid(B010003)에도 함께 사용된다.
    서비스별로 다른 키를 쓰려면 아래 값을 추가로 설정한다.

    ```
    ODCLOUD_API_KEY=...        # Applyhome Authorization 헤더용
    ODCLOUD_SERVICE_KEY=...    # Applyhome query param용
    ONBID_API_KEY=...          # Onbid용
    ```

1. 이미 Inspector가 실행 중이라면 먼저 종료한다.

    ```bash
    PID=$(lsof -ti :6274)
    [ -n "$PID" ] && kill $PID
    ```

1. MCP Inspector를 실행한다.

    ```bash
    uv run mcp dev src/real_estate/mcp_server/server.py
    ```

    실행하면 브라우저가 자동으로 열린다.
    창을 닫았거나 다시 접속해야 하면, 터미널의 `MCP Inspector is up and running at:` 뒤에 출력된 전체 URL로 접속한다.
    (예: `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...`)

1. `get_region_code`를 먼저 실행해서 `LAWD_CD` 법정동 코드를 조회합니다. 이어서 `get_apartment_trades` 아파트 실거래가 조회를 호출하여 원하는 연월 데이터를 조회합니다.
