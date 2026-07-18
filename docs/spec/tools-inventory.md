# MCP Tool Inventory

This document is a reader-friendly reference for the 16 MCP tools exposed by this server, plus the standalone CLI/library utilities under `src/real_estate/common_utils/` that ship alongside them: what parameters each accepts and what it returns to the caller. It is meant to be self-contained: a new contributor, an external integrator evaluating the server, or a future maintainer designing an OpenAPI spec should be able to understand what each tool does and how to call it without reading the source.

For how the server itself calls the underlying public government APIs — the raw HTTP request built, raw XML/JSON field names, and upstream response envelopes — see [Public OpenAPI Spec](public-openapi-spec.md). This document intentionally stops at the tool boundary.

For internal implementation details — test coverage status, known error-path gaps, static-analysis notes — see the repository's internal developer notes (not part of this public document; kept separately to avoid duplication).

Prices throughout are in **만원** (10,000 KRW) units, indicated by the `_10k` field suffix.

Sample responses are shown as JSON so field types are explicit: all `_10k` monetary fields and `floor`/`build_year`/`sample_count`/`total_count`/counts are integers; `area_sqm`/`building_ar` are numbers (may be fractional); `trade_date` is a `YYYY-MM-DD` string; `jeonse_ratio_pct` is always `null`; text fields are strings (empty string `""` where the upstream provides nothing). Sample values are illustrative, not captured from a live call.

Tools are grouped as follows:

- [Trade (매매)](#trade-매매) — 5 tools
- [Rent (임대)](#rent-임대) — 4 tools
- [Subscription (청약)](#subscription-청약) — 2 tools
- [Finance (재무 계산)](#finance-재무-계산) — 3 tools
- [Region / Utility](#region--utility) — 2 tools
- [Common Utils (non-MCP)](#common-utils-non-mcp) — 4 modules, standalone CLI/library, not exposed as MCP tools

---

## Trade (매매)

All 5 tools below query MOLIT (국토교통부) real-estate transaction data via 공공데이터포탈. See [Public OpenAPI Spec](public-openapi-spec.md#molit-traderent-apis-apisdatagokr) for the exact upstream request/response shape.

`region_code` (5-digit `LAWD_CD`) must be obtained first via [`get_region_code`](#get_region_code). `year_month` is a 6-digit `YYYYMM` string.

**Pagination:** `num_of_rows` only controls how many records are requested; there is no way to request additional pages through this tool — if the upstream total exceeds `num_of_rows`, the remaining records are not reachable.

**Error responses:** on failure, these tools return `{"error": "<type>", "message": "..."}` instead of `total_count`/`items`/`summary`. `error` is one of:

| `error` | Meaning | Notes |
|---|---|---|
| `api_error` | The upstream API reported a failure. | Also carries a `code` field with the raw upstream code — see [Public OpenAPI Spec](public-openapi-spec.md#upstream-resultcode-values-surfaced-as-errors) for the exact code list, meanings, and how reliably each one actually fires. |
| `config_error` | `DATA_GO_KR_API_KEY` is not set (checked before any request is made). | No `code` field. |
| `network_error` | The request to the upstream API timed out, failed at the HTTP layer (including a rejected/expired key), or hit a connection error. | No `code` field. |
| `parse_error` | The upstream response body could not be parsed as XML. | No `code` field. |

### `get_apartment_trades`

- **Signature:** `get_apartment_trades(region_code: str, year_month: str, num_of_rows: int = 100) -> dict`
- **Response:** `total_count`, `items[]` (`apt_name, dong, area_sqm, floor, price_10k, trade_date, build_year, deal_type`), `summary` (`median/min/max_price_10k, sample_count`), or `error`/`message` on failure.
- **Upstream API:** `RTMSDataSvcAptTrade` (국토교통부 / 공공데이터포탈) — see [Public OpenAPI Spec](public-openapi-spec.md#endpoints) for the endpoint URL.
- **Sample request:** `get_apartment_trades(region_code="11440", year_month="202501")`
- **Sample response** (a cancelled deal, i.e. `cdealType == "O"`, is filtered out of `items` before it reaches the caller):

  ```json
  {
    "total_count": 2,
    "items": [
      {"apt_name": "마포래미안푸르지오", "dong": "합정동", "area_sqm": 84.97, "floor": 12, "price_10k": 135000, "trade_date": "2025-01-15", "build_year": 2014, "deal_type": "중개거래"},
      {"apt_name": "마포자이", "dong": "아현동", "area_sqm": 59.0, "floor": 5, "price_10k": 90000, "trade_date": "2025-01-20", "build_year": 2010, "deal_type": "직거래"}
    ],
    "summary": {"median_price_10k": 112500, "min_price_10k": 90000, "max_price_10k": 135000, "sample_count": 2}
  }
  ```

### `get_officetel_trades`

- **Signature:** `get_officetel_trades(region_code: str, year_month: str, num_of_rows: int = 100) -> dict`
- **Response:** `total_count`, `items[]` (`unit_name, dong, area_sqm, floor, price_10k, trade_date, build_year, deal_type`), `summary`, or `error`/`message`.
- **Upstream API:** `RTMSDataSvcOffiTrade` (국토교통부 / 공공데이터포탈) — see [Public OpenAPI Spec](public-openapi-spec.md#endpoints) for the endpoint URL.
- **Sample request:** `get_officetel_trades(region_code="11440", year_month="202501")`
- **Sample response:**

  ```json
  {
    "total_count": 1,
    "items": [
      {"unit_name": "마포 더리브", "dong": "합정동", "area_sqm": 33.0, "floor": 8, "price_10k": 35000, "trade_date": "2025-01-05", "build_year": 2018, "deal_type": "중개거래"}
    ],
    "summary": {"median_price_10k": 35000, "min_price_10k": 35000, "max_price_10k": 35000, "sample_count": 1}
  }
  ```

### `get_villa_trades`

- **Signature:** `get_villa_trades(region_code: str, year_month: str, num_of_rows: int = 100) -> dict`
- **Response:** `total_count`, `items[]` (`unit_name, dong, house_type, area_sqm, floor, price_10k, trade_date, build_year, deal_type`), `summary`, or `error`/`message`.
- **Upstream API:** `RTMSDataSvcRHTrade` (국토교통부 / 공공데이터포탈) — see [Public OpenAPI Spec](public-openapi-spec.md#endpoints) for the endpoint URL.
- **Sample request:** `get_villa_trades(region_code="11440", year_month="202501")`
- **Sample response:**

  ```json
  {
    "total_count": 1,
    "items": [
      {"unit_name": "신촌빌라", "dong": "신촌동", "house_type": "다세대", "area_sqm": 49.5, "floor": 3, "price_10k": 25000, "trade_date": "2025-01-08", "build_year": 2005, "deal_type": "중개거래"}
    ],
    "summary": {"median_price_10k": 25000, "min_price_10k": 25000, "max_price_10k": 25000, "sample_count": 1}
  }
  ```

### `get_single_house_trades`

- **Signature:** `get_single_house_trades(region_code: str, year_month: str, num_of_rows: int = 100) -> dict`
- **Response:** `total_count`, `items[]` (`unit_name` always `""`, `dong, house_type, area_sqm` (from `totalFloorAr`), `floor` always `0`, `price_10k, trade_date, build_year, deal_type`), `summary`, or `error`/`message`.
- **Upstream API:** `RTMSDataSvcSHTrade` (국토교통부 / 공공데이터포탈) — see [Public OpenAPI Spec](public-openapi-spec.md#endpoints) for the endpoint URL.
- **Sample request:** `get_single_house_trades(region_code="11440", year_month="202501")`
- **Sample response** (`unit_name` is always `""` and `floor` is always `0` for this tool):

  ```json
  {
    "total_count": 1,
    "items": [
      {"unit_name": "", "dong": "연남동", "house_type": "단독", "area_sqm": 120.0, "floor": 0, "price_10k": 80000, "trade_date": "2025-01-20", "build_year": 1995, "deal_type": "중개거래"}
    ],
    "summary": {"median_price_10k": 80000, "min_price_10k": 80000, "max_price_10k": 80000, "sample_count": 1}
  }
  ```

### `get_commercial_trade`

- **Signature:** `get_commercial_trade(region_code: str, year_month: str, num_of_rows: int = 100) -> dict`
- **Response schema differs from the residential tools above** — no `unit_name`/`area_sqm`: `total_count`, `items[]` (`building_type, building_use, land_use, dong, building_ar, floor, price_10k, trade_date, build_year, deal_type, share_dealing`), `summary`, or `error`/`message`.
- **⚠️ Known bug:** unlike the other 4 trade tools, cancelled deals are **not** filtered out of `items` here — see [Public OpenAPI Spec](public-openapi-spec.md#raw-item-fields--tool-response-fields) for details.
- **Upstream API:** `RTMSDataSvcNrgTrade` (국토교통부 / 공공데이터포탈) — see [Public OpenAPI Spec](public-openapi-spec.md#endpoints) for the endpoint URL.
- **Sample request:** `get_commercial_trade(region_code="11440", year_month="202501")`
- **Sample response:**

  ```json
  {
    "total_count": 1,
    "items": [
      {"building_type": "집합", "building_use": "판매시설", "land_use": "상업지역", "dong": "합정동", "building_ar": 120.5, "floor": 2, "price_10k": 85000, "trade_date": "2025-01-10", "build_year": 2010, "deal_type": "중개거래", "share_dealing": ""}
    ],
    "summary": {"median_price_10k": 85000, "min_price_10k": 85000, "max_price_10k": 85000, "sample_count": 1}
  }
  ```

---

## Rent (임대)

All 4 tools below query MOLIT (국토교통부) lease-transaction data via 공공데이터포탈, sharing the same pagination limitation and upstream error codes as the [trade tools](#trade-매매) above — see [Public OpenAPI Spec](public-openapi-spec.md#molit-traderent-apis-apisdatagokr) for the raw request/response shape. `jeonse_ratio_pct` in `summary` is always `null` — callers compute it themselves from a trade-tool median and a rent-tool median.

### `get_apartment_rent`

- **Signature:** `get_apartment_rent(region_code: str, year_month: str, num_of_rows: int = 100) -> dict`
- **Response:** `total_count`, `items[]` (`unit_name, dong, area_sqm, floor, deposit_10k, monthly_rent_10k, contract_type, trade_date, build_year`), `summary` (`median/min/max_deposit_10k, monthly_rent_avg_10k, jeonse_ratio_pct: null, sample_count`), or `error`/`message`.
- **Upstream API:** `RTMSDataSvcAptRent` (국토교통부 / 공공데이터포탈) — see [Public OpenAPI Spec](public-openapi-spec.md#endpoints) for the endpoint URL.
- **Sample request:** `get_apartment_rent(region_code="11440", year_month="202501")`
- **Sample response** (a jeonse contract has `monthly_rent_10k: 0`):

  ```json
  {
    "total_count": 2,
    "items": [
      {"unit_name": "마포래미안", "dong": "합정동", "area_sqm": 84.97, "floor": 12, "deposit_10k": 50000, "monthly_rent_10k": 0, "contract_type": "신규", "trade_date": "2025-01-10", "build_year": 2014},
      {"unit_name": "마포자이", "dong": "아현동", "area_sqm": 59.0, "floor": 5, "deposit_10k": 20000, "monthly_rent_10k": 80, "contract_type": "신규", "trade_date": "2025-01-15", "build_year": 2010}
    ],
    "summary": {"median_deposit_10k": 35000, "min_deposit_10k": 20000, "max_deposit_10k": 50000, "monthly_rent_avg_10k": 40, "jeonse_ratio_pct": null, "sample_count": 2}
  }
  ```

### `get_officetel_rent`

- **Signature:** `get_officetel_rent(region_code: str, year_month: str, num_of_rows: int = 100) -> dict`
- **Response:** same shape as `get_apartment_rent`.
- **Upstream API:** `RTMSDataSvcOffiRent` (국토교통부 / 공공데이터포탈) — see [Public OpenAPI Spec](public-openapi-spec.md#endpoints) for the endpoint URL.
- **Sample request:** `get_officetel_rent(region_code="11440", year_month="202501")`
- **Sample response:**

  ```json
  {
    "total_count": 1,
    "items": [
      {"unit_name": "마포 더리브", "dong": "합정동", "area_sqm": 33.0, "floor": 8, "deposit_10k": 5000, "monthly_rent_10k": 100, "contract_type": "신규", "trade_date": "2025-01-05", "build_year": 2018}
    ],
    "summary": {"median_deposit_10k": 5000, "min_deposit_10k": 5000, "max_deposit_10k": 5000, "monthly_rent_avg_10k": 100, "jeonse_ratio_pct": null, "sample_count": 1}
  }
  ```

### `get_villa_rent`

- **Signature:** `get_villa_rent(region_code: str, year_month: str, num_of_rows: int = 100) -> dict`
- **Response:** `total_count`, `items[]` (`unit_name, dong, house_type, area_sqm, floor, deposit_10k, monthly_rent_10k, contract_type, trade_date, build_year`), `summary`, or `error`/`message`.
- **Upstream API:** `RTMSDataSvcRHRent` (국토교통부 / 공공데이터포탈) — see [Public OpenAPI Spec](public-openapi-spec.md#endpoints) for the endpoint URL.
- **Sample request:** `get_villa_rent(region_code="11440", year_month="202407")`
- **Sample response** (`floor` may be negative for basement units; `contract_type` may be empty upstream):

  ```json
  {
    "total_count": 1,
    "items": [
      {"unit_name": "북악더테라스2단지", "dong": "신영동", "house_type": "연립", "area_sqm": 84.99, "floor": -1, "deposit_10k": 70000, "monthly_rent_10k": 0, "contract_type": "", "trade_date": "2024-07-10", "build_year": 2019}
    ],
    "summary": {"median_deposit_10k": 70000, "min_deposit_10k": 70000, "max_deposit_10k": 70000, "monthly_rent_avg_10k": 0, "jeonse_ratio_pct": null, "sample_count": 1}
  }
  ```

### `get_single_house_rent`

- **Signature:** `get_single_house_rent(region_code: str, year_month: str, num_of_rows: int = 100) -> dict`
- **Response:** `total_count`, `items[]` (`unit_name` always `""`, `dong, house_type, area_sqm` (from `totalFloorAr`), `deposit_10k, monthly_rent_10k, contract_type, trade_date, build_year`), `summary`, or `error`/`message`. Note: this tool's items have **no `floor` field** at all (the other 3 rent tools include `floor`).
- **Upstream API:** `RTMSDataSvcSHRent` (국토교통부 / 공공데이터포탈) — see [Public OpenAPI Spec](public-openapi-spec.md#endpoints) for the endpoint URL.
- **Sample request:** `get_single_house_rent(region_code="11440", year_month="202501")`
- **Sample response** (`unit_name` always `""`; no `floor` field):

  ```json
  {
    "total_count": 1,
    "items": [
      {"unit_name": "", "dong": "연남동", "house_type": "다가구", "area_sqm": 85.0, "deposit_10k": 15000, "monthly_rent_10k": 60, "contract_type": "신규", "trade_date": "2025-01-15", "build_year": 2000}
    ],
    "summary": {"median_deposit_10k": 15000, "min_deposit_10k": 15000, "max_deposit_10k": 15000, "monthly_rent_avg_10k": 60, "jeonse_ratio_pct": null, "sample_count": 1}
  }
  ```

---

## Subscription (청약)

Both tools below query 한국부동산원 (청약홈) endpoints via `api.odcloud.kr`. Authentication uses `ODCLOUD_API_KEY` if set, else `ODCLOUD_SERVICE_KEY`, else falls back to `DATA_GO_KR_API_KEY`. See [Public OpenAPI Spec](public-openapi-spec.md#applyhome--odcloud-apis-apiodcloudkr) for exactly how the key is transmitted per mode.

**Pagination works normally here** (unlike the MOLIT trade/rent tools above) — `page` and `per_page` are passed through to odcloud and any page can be requested.

**Error responses:** on failure these tools return `{"error": "<type>", "message": "..."}` instead of the fields below. `error` is one of:

| `error` | Meaning |
|---|---|
| `validation_error` | `page < 1`, `per_page < 1`, or (for `get_apt_subscription_results`) an invalid `stat_kind`. Checked before any request or auth check. |
| `config_error` | None of `ODCLOUD_API_KEY` / `ODCLOUD_SERVICE_KEY` / `DATA_GO_KR_API_KEY` is set. |
| `network_error` | The odcloud request timed out or failed at the HTTP layer (including a rejected/expired key). |
| `parse_error` | The response body was not valid JSON, or decoded to a non-dict payload (bare list/scalar). |

Unlike the MOLIT trade/rent tools, these tools **never** return `api_error` — odcloud does not use the `resultCode` failure envelope; upstream failures surface as HTTP status (→ `network_error`) or an unexpected body (→ `parse_error`).

### `get_apt_subscription_info`

- **Signature:** `get_apt_subscription_info(page: int = 1, per_page: int = 100, return_type: str = "JSON") -> dict`
- **Constraints:** `page >= 1`, `per_page >= 1` — violating either returns `{"error": "validation_error", "message": "page must be >= 1"}` (or the `per_page` equivalent). `return_type` is passed through unvalidated (the source dataset serves `"JSON"`; `"XML"` is the only other odcloud value but the tool always parses the body as JSON).
- **Response:** `total_count, items[], page, per_page, current_count, match_count`, or `error`/`message`. `items` are raw dicts from the source dataset (Korean field names, e.g. `공고번호`, `주택명`, `모집공고일`) — kept as-is with no renaming, so their per-field types are whatever odcloud returns and are not fixed by this server.
- **Upstream API:** "한국부동산원_청약홈_APT 분양정보" (한국부동산원) — see [Public OpenAPI Spec](public-openapi-spec.md#get_apt_subscription_info) for the exact URL/params.
- **Sample request:** `get_apt_subscription_info(page=1, per_page=100)`
- **Sample response** (`items` abridged — raw dataset fields, only `공고번호` shown):

  ```json
  {
    "total_count": 2,
    "page": 1,
    "per_page": 100,
    "current_count": 2,
    "match_count": 2,
    "items": [
      {"공고번호": "A-1"},
      {"공고번호": "A-2"}
    ]
  }
  ```

### `get_apt_subscription_results`

- **Signature:** `get_apt_subscription_results(stat_kind: str, stat_year_month: str | None = None, area_code: str | None = None, reside_secd: str | None = None, page: int = 1, per_page: int = 100, return_type: str = "JSON") -> dict`
- **Constraints:** `page >= 1`, `per_page >= 1` (same validation errors as `get_apt_subscription_info`, checked first). `stat_kind` must be one of the 6 values below — any other value returns `{"error": "validation_error", "message": "Invalid stat_kind. Expected one of: reqst_area, reqst_age, przwner_area, przwner_age, cmpetrt_area, aps_przwner"}`. The optional filters (`stat_year_month`, `area_code`, `reside_secd`) are passed through unvalidated as odcloud `cond[FIELD::EQ]` query params when non-empty.
- **Response:** `stat_kind, total_count, items[], page, per_page, current_count, match_count`, or `error`/`message`. As above, `items` are raw dataset dicts kept without renaming.
- `stat_kind` selects one of 6 underlying endpoints: `reqst_area`, `reqst_age`, `przwner_area`, `przwner_age`, `cmpetrt_area`, `aps_przwner`.
- **Upstream API:** "청약홈 청약 신청·당첨자 정보 조회 서비스" (한국부동산원) — see [Public OpenAPI Spec](public-openapi-spec.md#get_apt_subscription_results) for the `stat_kind`→endpoint mapping and exact URL/params.
- **Sample request:** `get_apt_subscription_results(stat_kind="reqst_area", stat_year_month="202501", area_code="01", page=1, per_page=10)`
- **Sample response** (`items` abridged — raw dataset fields; `stat_kind` is echoed from the request, not derived from the payload):

  ```json
  {
    "stat_kind": "reqst_area",
    "total_count": 1,
    "page": 1,
    "per_page": 10,
    "current_count": 1,
    "match_count": 1,
    "items": [
      {"STAT_DE": "202501", "SUBSCRPT_AREA_CODE": "01", "AGE_30": 10}
    ]
  }
  ```

---

## Finance (재무 계산)

These 3 tools are pure calculators — no external API call, no network dependency.

### `calculate_loan_payment`

- **Signature:** `calculate_loan_payment(principal_10k: int, annual_rate_pct: float, years: int) -> dict`
- **Constraints:** `principal_10k >= 1`, `annual_rate_pct >= 0`, `years >= 1`. Violating any returns `{"error": "validation_error", "message": "<param> must be >= <bound>"}` (checked in that order — the first violated constraint is reported).
- **Response:** `monthly_payment_10k, total_payment_10k, total_interest_10k, principal_10k, annual_rate_pct, years`.
- **Original API:** none — standard equal-monthly-installment (EMI) amortization formula.
- **Sample request:** `calculate_loan_payment(principal_10k=30000, annual_rate_pct=3.5, years=30)`
- **Sample response:**

  ```json
  {
    "monthly_payment_10k": 134.71,
    "total_payment_10k": 48496.83,
    "total_interest_10k": 18496.83,
    "principal_10k": 30000,
    "annual_rate_pct": 3.5,
    "years": 30
  }
  ```

### `calculate_compound_growth`

- **Signature:** `calculate_compound_growth(initial_10k: int, monthly_contribution_10k: float, annual_rate_pct: float, years: int) -> dict`
- **Constraints:** `initial_10k >= 0`, `monthly_contribution_10k >= 0`, `annual_rate_pct >= 0`, `years >= 1`. Violating any returns `{"error": "validation_error", "message": "<param> must be >= <bound>"}` (checked in that order).
- **Response:** `final_value_10k, total_contributed_10k, total_gain_10k, initial_10k, monthly_contribution_10k, annual_rate_pct, years`.
- **Original API:** none — standard compound-interest formula with monthly contributions.
- **Sample request:** `calculate_compound_growth(initial_10k=5000, monthly_contribution_10k=50, annual_rate_pct=5.0, years=10)`
- **Sample response:**

  ```json
  {
    "final_value_10k": 15999.16,
    "total_contributed_10k": 11000,
    "total_gain_10k": 4999.16,
    "initial_10k": 5000,
    "monthly_contribution_10k": 50,
    "annual_rate_pct": 5.0,
    "years": 10
  }
  ```

### `calculate_monthly_cashflow`

- **Signature:** `calculate_monthly_cashflow(monthly_income_10k: float, monthly_loan_payment_10k: float, monthly_living_cost_10k: float, other_monthly_costs_10k: float = 0.0) -> dict`
- **Constraints:** `monthly_income_10k > 0`, `monthly_loan_payment_10k >= 0`. Violating either returns `{"error": "validation_error", "message": "<param> must be > 0" | "must be >= 0"}` (checked in that order). `monthly_living_cost_10k` and `other_monthly_costs_10k` are unvalidated (no lower bound enforced).
- **Response:** `monthly_cashflow_10k, monthly_income_10k, monthly_loan_payment_10k, monthly_living_cost_10k, other_monthly_costs_10k, living_cost_auto_applied`.
- **Original API:** none. If `monthly_living_cost_10k` is `0`, it is auto-replaced with `monthly_income_10k * 0.4` and `living_cost_auto_applied` is set to `true`. Note: the returned `monthly_living_cost_10k` is the value **actually used** in the calculation — when auto-applied, it reflects the substituted `monthly_income_10k * 0.4`, not the `0` you passed.
- **Sample request:** `calculate_monthly_cashflow(monthly_income_10k=500, monthly_loan_payment_10k=134.67, monthly_living_cost_10k=200)`
- **Sample response:**

  ```json
  {
    "monthly_cashflow_10k": 165.33,
    "monthly_income_10k": 500,
    "monthly_loan_payment_10k": 134.67,
    "monthly_living_cost_10k": 200,
    "other_monthly_costs_10k": 0.0,
    "living_cost_auto_applied": false
  }
  ```

---

## Region / Utility

These 2 tools don't call any government API — `get_region_code` looks up a bundled local dataset, and `get_current_year_month` reads the system clock.

### `get_region_code`

- **Signature:** `get_region_code(query: str) -> dict`
- **Matching algorithm:** `query` is trimmed and split on whitespace into tokens. A row matches if **every** token is a substring of that row's name (order-independent, case-sensitive, no fuzzy/typo tolerance). Only rows whose status column is `존재` (currently active) are loaded from the file at all. Among matches, gu/gun-level rows (10-digit code ending in `00000`) sort first and the top one becomes `region_code`/`full_name`; if none are gu/gun-level, the first match (sorted by code) is used instead.
- **Response:** `region_code` (5-digit `LAWD_CD`), `full_name`, `matches[]` (`{code, name}`, all matches, not just the chosen one), or `error`/`message`. Must be called first to obtain the `region_code` used by all trade/rent tools above.
- **Errors:** `{"error": "invalid_input", ...}` if `query` is empty/whitespace-only; `{"error": "file_not_found", ...}` if `region_codes.txt` is missing; `{"error": "no_match", ...}` if no row satisfies all tokens.
- **Original API:** none — matches against `src/real_estate/resources/region_codes.txt` (tab-separated legal-district codes bundled with the server).
- **Sample request:** `get_region_code(query="마포구")`
- **Sample response** (`matches` truncated to 2 of 27 entries):

  ```json
  {
    "region_code": "11440",
    "full_name": "서울특별시 마포구",
    "matches": [
      {"code": "1144000000", "name": "서울특별시 마포구"},
      {"code": "1144010100", "name": "서울특별시 마포구 아현동"}
    ]
  }
  ```

### `get_current_year_month`

- **Signature:** `get_current_year_month() -> dict`
- **Response:** `{"year_month": "YYYYMM"}` for the current UTC date. Call this when the user asks about recent transactions without specifying a period.
- **Original API:** none — derived from `datetime.now(timezone.utc)`.
- **Sample request:** `get_current_year_month()`
- **Sample response:**

  ```json
  {"year_month": "202607"}
  ```

---

## Common Utils (non-MCP)

The 4 modules below live under `src/real_estate/common_utils/` and are **not** registered as `@mcp.tool()` functions — Claude Desktop cannot call them. They are standalone Python library functions / CLI scripts, invoked directly (`uv run python src/real_estate/common_utils/<script>.py ...` or imported as a library). Listed here for completeness; see [Common Utils Guide](../guide-common-utils.md) for full CLI usage.

### `docx_parser.extract_text`

- **Signature:** `extract_text(docx_path: str | Path, *, keep_empty_paragraphs: bool = False) -> str`
- **Kind:** Library function (importable), not a CLI entry point.
- **Response:** Extracted plain text, paragraphs joined by `\n`. Empty paragraphs are dropped unless `keep_empty_paragraphs=True`.
- **Errors:** raises `FileNotFoundError` if the path doesn't exist; raises `ValueError` if the file isn't a valid `.docx` zip container, is missing `word/document.xml`, or that entry exceeds a 25 MB guardrail.
- **Original API:** none — parses the `.docx` zip container's `word/document.xml` directly via `defusedxml`.
- **Sample usage:** `extract_text("/path/to/file.docx")`

### `docx_parser.extract_dir_to_txt`

- **Signature:** `extract_dir_to_txt(input_dir: str | Path, *, output_dir: str | Path | None = None, pattern: str = "**/*.docx", encoding: str = "utf-8", overwrite: bool = False, keep_empty_paragraphs: bool = False) -> list[DocxToTxtResult]`
- **Kind:** Library function; wrapped by the `docx_bulk_parser.py` CLI below.
- **Response:** A list of `DocxToTxtResult(input_path, output_path, written: bool)` — one per matched `.docx` file. `written=False` means the `.txt` already existed and `overwrite=False` skipped it. If `output_dir` is omitted, each `.txt` is written next to its source `.docx`; otherwise the input directory's relative structure is mirrored under `output_dir`.
- **Errors:** raises `FileNotFoundError` if `input_dir` doesn't exist; raises `NotADirectoryError` if it isn't a directory.
- **Original API:** none.
- **Sample usage:** `extract_dir_to_txt("/path/to/input_dir", overwrite=False)`

### `docx_bulk_parser` (CLI)

- **Invocation:** `uv run python src/real_estate/common_utils/docx_bulk_parser.py <input_dir> [--output-dir DIR] [--pattern GLOB] [--encoding ENC] [--overwrite] [--keep-empty-paragraphs]`
- **Kind:** CLI wrapper around `docx_parser.extract_dir_to_txt`.
- **Args:** `input_dir` (positional, required) — directory scanned recursively for `.docx` files. `--output-dir` (default: none, writes next to source). `--pattern` (default `**/*.docx`). `--encoding` (default `utf-8`). `--overwrite` (flag, default off). `--keep-empty-paragraphs` (flag, default off).
- **Output:** prints one `WROTE <path>` line per written file, then one `SKIP <path>` line per skipped file (written lines first, then skipped — not interleaved in scan order), then a summary line `Done. written=<n> skipped=<n> total=<n>`. Exit code `0` always (no failure path distinct from per-file skip).
- **Original API:** none.

### `hwp_parser.extract_text`

- **Signature:** `extract_text(hwp_path: str | Path) -> str`
- **Kind:** Library function (importable), not a CLI entry point.
- **Response:** Raw extracted paragraph text from the `BodyText/Section0` OLE stream, joined by `\n`, with no further post-processing (no empty-paragraph filtering, no whitespace normalization).
- **Errors:** raises `FileNotFoundError` if the path doesn't exist; raises `ValueError` if the `BodyText/Section0` stream is missing (e.g. wrong file format).
- **Original API:** none — reads the HWP binary OLE container via `olefile`, decompresses the section stream (zlib, if the file header's compression flag is set), and extracts text from `HWPTAG_PARA_TEXT` (tag `67`) records, decoded as UTF-16LE.
- **Sample usage:** `extract_text("/path/to/file.hwp")`

### `opendata_bulk_collector` (CLI)

- **Invocation:** `uv run python src/real_estate/common_utils/opendata_bulk_collector.py [--property-type {apartment,villa}] [--region-code CODE] [--start YYYYMM] [--end YYYYMM] [--num-of-rows N] [--output-root DIR]`
- **Kind:** CLI script. Calls the MCP rent tools' underlying functions directly (`get_apartment_rent` / `get_villa_rent` from [`tools/rent.py`](#rent-임대)) month by month — not a network call of its own; it reuses the same MOLIT rent request path documented in [Public OpenAPI Spec](public-openapi-spec.md#molit-traderent-apis-apisdatagokr).
- **Args:** `--property-type` (default `apartment`; choices `apartment`, `villa`). `--region-code` (default `11740`, 5-digit `LAWD_CD`). `--start`/`--end` (default `202207`/`202601`, `YYYYMM`, inclusive range; raises `ValueError` if either isn't 6 digits or `start > end`). `--num-of-rows` (default `2000`, passed through to the rent tool per month). `--output-root` (default `localdocs/assets/data`).
- **Output:** one `<YYYYMM>.json` file per month under `<output-root>/<property_type>_rent/<region_code>/`, each containing `{region_code, year_month, collected_at_utc, data: <rent tool response>}`. An `index.json` is written to the same directory with top-level run metadata (`property_type, region_code, start, end, num_of_rows, generated_at_utc`) and a `results[]` array of per-month objects (`{year_month, ok, total_count, sample_count, error, message, file}`). Prints one `[OK]`/`[ERR]` progress line per month, then an `Index written: <path>` line and a completion summary.
- **Exit code:** `1` if any month's tool call returned an `error` field (network/config/API failure) — the run still completes and writes `index.json` for the successful months; `0` if every month succeeded.
- **Original API:** none directly — see the [Public OpenAPI Spec](public-openapi-spec.md#molit-traderent-apis-apisdatagokr) entry for `RTMSDataSvcAptRent`/`RTMSDataSvcRHRent`, called once per `YYYYMM` in the range.
