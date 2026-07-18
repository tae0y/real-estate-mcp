# Public OpenAPI Spec

This document describes exactly how this MCP server calls the underlying public government APIs — the raw HTTP request sent and the raw response shape received, before any mapping into the MCP tool's friendly response fields.

It complements [MCP Tool Inventory](tools-inventory.md), which documents the tool-level interface (what a caller of the MCP tool sends and receives). Use this document when integrating with the upstream APIs directly, debugging a raw response, or auditing what data crosses the wire.

Two upstream providers are involved:

- **MOLIT (국토교통부) trade/rent APIs** — `apis.data.go.kr`, XML responses. Used by the 9 trade/rent tools.
- **Applyhome (청약홈, 한국부동산원)** — `api.odcloud.kr`, JSON responses. Used by the 2 subscription tools.

Finance tools (`calculate_loan_payment`, `calculate_compound_growth`, `calculate_monthly_cashflow`) and `get_region_code`/`get_current_year_month` make no external API call and are not covered here.

---

## MOLIT trade/rent APIs (`apis.data.go.kr`)

### Request shape

All 9 trade/rent tools share one request-building function (`_build_url` in `_helpers.py`):

```
GET {endpoint}?serviceKey={DATA_GO_KR_API_KEY, URL-encoded}&LAWD_CD={region_code}&DEAL_YMD={year_month}&numOfRows={num_of_rows}&pageNo=1
```

| Query param | Source | Notes |
|---|---|---|
| `serviceKey` | `DATA_GO_KR_API_KEY` env var | URL-encoded via `urllib.parse.quote(..., safe="")`; embedded directly in the URL string rather than passed through httpx params, to avoid double-encoding. |
| `LAWD_CD` | tool's `region_code` arg | 5-digit code from `get_region_code`. |
| `DEAL_YMD` | tool's `year_month` arg | 6-digit `YYYYMM`. |
| `numOfRows` | tool's `num_of_rows` arg | Controls records per page only. |
| `pageNo` | hard-coded `1` | Not exposed as a tool parameter — page 2+ is unreachable through this server. |

Transport: `httpx.AsyncClient`, 15s timeout, plain GET, response body read as text and parsed as XML (`defusedxml`).

### Endpoints

| Tool | Endpoint constant | URL |
|---|---|---|
| `get_apartment_trades` | `_APT_TRADE_URL` | `https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade` |
| `get_officetel_trades` | `_OFFI_TRADE_URL` | `https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade` |
| `get_villa_trades` | `_VILLA_TRADE_URL` | `https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade` |
| `get_single_house_trades` | `_SINGLE_TRADE_URL` | `https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade` |
| `get_commercial_trade` | `_COMMERCIAL_TRADE_URL` | `https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade` |
| `get_apartment_rent` | `_APT_RENT_URL` | `https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent` |
| `get_officetel_rent` | `_OFFI_RENT_URL` | `https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent` |
| `get_villa_rent` | `_VILLA_RENT_URL` | `https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent` |
| `get_single_house_rent` | `_SINGLE_RENT_URL` | `https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent` |

### Raw response envelope

```xml
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>...</item>
      <item>...</item>
    </items>
    <totalCount>2</totalCount>
  </body>
</response>
```

- `resultCode` != `"000"` → the server treats the whole call as a failure and returns `{"error": "api_error", "code": "<resultCode>", "message": "..."}` to the MCP caller (no `items`/`total_count` surfaced). See the [code table below](#upstream-resultcode-values-surfaced-as-errors) for what each raw `resultCode` means; see [tools-inventory.md](tools-inventory.md#trade-매매) for the user-facing `error` types this can appear alongside.
- `totalCount` is read from the body and passed through as the tool's `total_count` — it reflects the upstream's full match count, independent of how many `item`s were actually returned on this page.
- Each `<item>` under `<body><items>` is one raw record; field names below vary per endpoint.

### Raw `<item>` fields → tool response fields

All parsers first attempt to drop cancelled deals (`cdealType == "O"`) and drop any item whose amount field fails to parse.

> **⚠️ Live-verified bug (commercial trade):** the upstream `RTMSDataSvcNrgTrade` endpoint returns the cancellation flag as `<cdealType>` (capital `T`), confirmed 2026-07 against a live 202503 마포구 response containing 4 genuinely cancelled deals (`cdealType == "O"`) out of 38 items. `_parse_commercial_trade` (`parsers/trade.py:197`) checks `_txt(item, "cdealtype")` — lowercase `t` — which never matches the real tag, so **`get_commercial_trade` does not actually filter cancelled deals**; they pass through into `items` despite being cancelled. This is a code defect, not an intentional variant.

**Trade endpoints** (`dealAmount` → `price_10k`; comma-formatted, e.g. `"135,000"` → `135000`):

| Raw XML tag | Apt | Officetel | Villa (연립다세대) | Single house (단독/다가구) | Commercial |
|---|---|---|---|---|---|
| Name field | `aptNm` → `apt_name` | `offiNm` → `unit_name` | `mhouseNm` → `unit_name` | *(not provided)* → `unit_name=""` | — |
| `umdNm` | → `dong` | → `dong` | → `dong` | → `dong` | → `dong` |
| `excluUseAr` | → `area_sqm` | → `area_sqm` | → `area_sqm` | — | — |
| `totalFloorAr` | — | — | — | → `area_sqm` | — |
| `houseType` | — | — | → `house_type` | → `house_type` | — |
| `floor` | → `floor` | → `floor` | → `floor` | *(not applicable)* → `floor=0` | → `floor` |
| `dealAmount` | → `price_10k` | → `price_10k` | → `price_10k` | → `price_10k` | → `price_10k` |
| `dealYear`/`dealMonth`/`dealDay` | → `trade_date` (`YYYY-MM-DD`, month/day zero-padded) | same | same | same | same |
| `buildYear` | → `build_year` | → `build_year` | → `build_year` | → `build_year` | → `build_year` |
| `dealingGbn` | → `deal_type` | → `deal_type` | → `deal_type` | → `deal_type` | → `deal_type` |
| `buildingType` | — | — | — | — | → `building_type` |
| `buildingUse` | — | — | — | — | → `building_use` |
| `landUse` | — | — | — | — | → `land_use` |
| `buildingAr` | — | — | — | — | → `building_ar` |
| `shareDealingType` | — | — | — | — | → `share_dealing` |
| `cdealType` | filter only (excluded if `"O"`) | same | same | same | **not effective** — parser reads wrong tag case (`cdealtype`); see warning above |

**Rent endpoints** (`deposit` → `deposit_10k`; `monthlyRent` → `monthly_rent_10k`, empty/unparseable → `0`):

| Raw XML tag | Apt | Officetel | Villa (연립다세대) | Single house (단독/다가구) |
|---|---|---|---|---|
| Name field | `aptNm` → `unit_name` | `offiNm` → `unit_name` | `mhouseNm` → `unit_name` | *(not provided)* → `unit_name=""` |
| `umdNm` | → `dong` | → `dong` | → `dong` | → `dong` |
| `excluUseAr` | → `area_sqm` | → `area_sqm` | → `area_sqm` | — |
| `totalFloorAr` | — | — | — | → `area_sqm` |
| `houseType` | — | — | → `house_type` | → `house_type` |
| `floor` | → `floor` | → `floor` | → `floor` | *(field omitted entirely)* |
| `deposit` | → `deposit_10k` | → `deposit_10k` | → `deposit_10k` | → `deposit_10k` |
| `monthlyRent` | → `monthly_rent_10k` | → `monthly_rent_10k` | → `monthly_rent_10k` | → `monthly_rent_10k` |
| `contractType` | → `contract_type` | → `contract_type` | → `contract_type` | → `contract_type` |
| `dealYear`/`dealMonth`/`dealDay` | → `trade_date` | same | same | same |
| `buildYear` | → `build_year` | → `build_year` | → `build_year` | → `build_year` |

Note: only `_parse_apt_rent` contains a `cdealType == "O"` check; the other 3 rent parsers don't check this field at all. **Live-verified 2026-07:** none of the 4 rent endpoints (apartment/officetel/villa/single-house) return a `cdealType` tag anywhere in their XML — lease/rent transactions have no cancellation flag upstream. This means `_parse_apt_rent`'s check is dead code (`_txt(item, "cdealType")` always returns `""`, which never equals `"O"`), not an active filter — cancelled rent contracts, if they exist upstream at all, are not distinguishable via this field on any rent tool.

`jeonse_ratio_pct` has no raw source field — it is always `null` in the tool response; the upstream API doesn't provide it.

### Pagination limitation

`pageNo` is hard-coded to `1`. If upstream `totalCount` exceeds the number of `<item>` elements actually returned (bounded by `numOfRows`), the remaining records are not reachable — there is no server-side mechanism to request page 2.

### Upstream `resultCode` values surfaced as errors

This server's `_ERROR_MESSAGES` table (`_helpers.py:33-39`) maps these codes, per the 공공데이터포탈 API provider's published documentation:

| `resultCode` | Meaning |
|---|---|
| `03` | No trade records found for the specified region and period. |
| `10` | Invalid API request parameters. |
| `22` | Daily API request limit exceeded. |
| `30` | Unregistered API key. |
| `31` | API key has expired. |

Any other non-`000` code is passed through as `"API error code: <code>"`.

**⚠️ Live-verified: none of these codes are actually reachable through this server's current code path.** Direct live calls to `RTMSDataSvcAptTrade` (with a valid key) produced:

| Scenario tried | Actual live result |
|---|---|
| No matching records (obscure region/period, e.g. `LAWD_CD=11440&DEAL_YMD=199001`) | `resultCode=000` (success), `totalCount=0`, empty `<items/>` — **not** `03`. The tool returns a normal `{total_count: 0, items: [], summary: {...}}`, never an `error`. |
| Malformed `LAWD_CD`/`DEAL_YMD` (non-numeric, or omitted entirely) | Still `resultCode=000`, `totalCount=0` — **not** `10`. The upstream gateway silently treats the malformed/missing value as "no match" rather than rejecting the request. |
| Invalid or missing `serviceKey` | **HTTP 401** with a plain-text `Unauthorized` body — **not** an XML response with `resultCode=30`. `_fetch_xml`'s `response.raise_for_status()` raises `httpx.HTTPStatusError` on this, so the tool actually returns `{"error": "network_error", "message": "HTTP error: 401"}`, not `{"error": "api_error", "code": "30", ...}`. |
| Negative `numOfRows` | `resultCode=999`, `resultMsg="ERROR: LIMIT must not be negative"` — a real generic-error code not present in `_ERROR_MESSAGES`, correctly falls through to the `"API error code: 999"` passthrough message. |

Practical implication: an expired/bad key on this server surfaces to the MCP caller as `error: "network_error"` (not `api_error`/`code: "30"` as the code comments imply), and "no data" is never an error at all — it's a normal empty response. The `03`/`10`/`30`/`31` rows above reflect the *documented* provider contract; treat them as reference for what the codes mean if they ever do appear (e.g. via a different endpoint or a future gateway change), not as behavior you can rely on triggering today. `22` (daily rate limit) was not independently tested here (would require exhausting the day's quota).

---

## Applyhome / odcloud APIs (`api.odcloud.kr`)

### Authentication

Resolved once per call via `_get_odcloud_key()`, in this priority order:

1. `ODCLOUD_API_KEY` set → sent as an `Authorization` HTTP header, raw value, no query param added.
2. else `ODCLOUD_SERVICE_KEY` set → sent as a `serviceKey` query param.
3. else `DATA_GO_KR_API_KEY` set → sent as a `serviceKey` query param (fallback).
4. none set → the tool returns `{"error": "config_error", ...}` before any request is made.

Transport: `httpx.AsyncClient`, 15s timeout, GET, JSON response body (`response.json()`).

### `get_apt_subscription_info`

```
GET https://api.odcloud.kr/api/15101046/v1/uddi:14a46595-03dd-47d3-a418-d64e52820598?page={page}&perPage={per_page}&returnType={return_type}[&serviceKey={key}]
```

| Query param | Source |
|---|---|
| `page` | tool's `page` arg |
| `perPage` | tool's `per_page` arg |
| `returnType` | tool's `return_type` arg |
| `serviceKey` | only added when auth mode is `serviceKey` (see above) |

Raw JSON response shape:

```json
{
  "currentCount": 2,
  "data": [ { "공고번호": "A-1", "주택명": "...", "...": "..." } ],
  "matchCount": 2,
  "page": 1,
  "perPage": 100,
  "totalCount": 2
}
```

| Raw JSON key | Tool response field |
|---|---|
| `totalCount` | `total_count` (missing/null → `0`) |
| `data` | `items` (missing/null → `[]`, records kept as-is with their original Korean keys — no field renaming) |
| `page` | `page` (missing/null → echoes the request's `page` arg) |
| `perPage` | `per_page` (missing/null → echoes the request's `per_page` arg) |
| `currentCount` | `current_count` (missing/null → `0`) |
| `matchCount` | `match_count` (missing/null → `0`) |

A non-dict JSON payload (e.g. a bare list or scalar) is treated as `{"error": "parse_error", "message": "Unexpected response type"}`.

### `get_apt_subscription_results`

`stat_kind` selects one of 6 upstream endpoints under a different base path:

```
GET https://api.odcloud.kr/api/ApplyhomeStatSvc/v1/{endpoint}?page={page}&perPage={per_page}&returnType={return_type}[&serviceKey={key}][&cond[STAT_DE::EQ]={stat_year_month}][&cond[SUBSCRPT_AREA_CODE::EQ]={area_code}][&cond[RESIDE_SECD::EQ]={reside_secd}]
```

| `stat_kind` | Upstream `{endpoint}` |
|---|---|
| `reqst_area` | `getAPTReqstAreaStat` |
| `reqst_age` | `getAPTReqstAgeStat` |
| `przwner_area` | `getAPTPrzwnerAreaStat` |
| `przwner_age` | `getAPTPrzwnerAgeStat` |
| `cmpetrt_area` | `getAPTCmpetrtAreaStat` |
| `aps_przwner` | `getAPTApsPrzwnerStat` |

Optional filter params are added to the query string only when the corresponding tool argument is non-empty, using odcloud's `cond[FIELD::EQ]` syntax (values are not otherwise validated):

| Tool arg | Raw query param | Maps to upstream field |
|---|---|---|
| `stat_year_month` | `cond[STAT_DE::EQ]` | `STAT_DE` |
| `area_code` | `cond[SUBSCRPT_AREA_CODE::EQ]` | `SUBSCRPT_AREA_CODE` |
| `reside_secd` | `cond[RESIDE_SECD::EQ]` | `RESIDE_SECD` |

Raw JSON response shape and field mapping are identical to `get_apt_subscription_info` above (`totalCount`/`data`/`page`/`perPage`/`currentCount`/`matchCount` → `total_count`/`items`/`page`/`per_page`/`current_count`/`match_count`), with `stat_kind` echoed back into the tool response as-is (not derived from the raw payload).
