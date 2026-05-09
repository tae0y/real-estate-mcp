# Prerequisites

This page describes what you need before connecting the real estate MCP server to any client.

## API Key

1. Sign in to [공공데이터포털](https://www.data.go.kr).

1. Search for **국토교통부 아파트매매 실거래자료** and request an API key.
   The key is typically activated within a few minutes.

1. Note the key — you will add it as `DATA_GO_KR_API_KEY` in the next steps.

   If you want separate keys per service, the server also reads these optional variables (all fall back to `DATA_GO_KR_API_KEY` if not set):

   | Variable | Service |
   |----------|---------|
   | `ODCLOUD_API_KEY` | Applyhome (청약홈) Authorization header |
   | `ODCLOUD_SERVICE_KEY` | Applyhome query param |
   | ~~`ONBID_API_KEY`~~ | ~~Onbid (openapi.onbid.co.kr)~~ — removed June 1, 2025 |

## Install uv

[uv](https://docs.astral.sh/uv/getting-started/installation/) is the Python package manager used to run the server.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Clone the repository

```bash
git clone <repository_url>
cd real-estate-mcp
```

Replace `<repository_url>` with the actual URL of this repository.
