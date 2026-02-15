"""Real estate transaction MCP server.

Register with Claude Desktop to query region codes and
various real estate trade/rent records through natural language.

Tools:
  - get_region_code: region name → 5-digit legal district code
  - get_current_year_month: current year-month in YYYYMM format
  - get_apartment_trades: apartment sale records + summary stats
  - get_apartment_rent: apartment lease/rent records + summary stats
  - get_officetel_trades: officetel sale records + summary stats
  - get_officetel_rent: officetel lease/rent records + summary stats
  - get_villa_trades: row-house/multi-family sale records + summary stats
  - get_single_house_trades: detached/multi-unit house sale records + summary stats
  - get_single_house_rent: detached/multi-unit house lease/rent records + summary stats
  - get_commercial_trade: commercial/business building sale records + summary stats
"""

import os
import statistics
import urllib.parse
from pathlib import Path
from typing import Any

import httpx
from defusedxml.ElementTree import ParseError as XmlParseError
from defusedxml.ElementTree import fromstring as xml_fromstring
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load .env from project root (ignored if file is absent)
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from real_estate.data.region_code import search_region_code  # noqa: E402

mcp = FastMCP("real-estate")

# ---------------------------------------------------------------------------
# API base URLs
# ---------------------------------------------------------------------------

_APT_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
_APT_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
_OFFI_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade"
_OFFI_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
_VILLA_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"
_SINGLE_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade"
_SINGLE_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent"
_COMMERCIAL_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"

_ERROR_MESSAGES: dict[str, str] = {
    "03": "No trade records found for the specified region and period.",
    "10": "Invalid API request parameters.",
    "22": "Daily API request limit exceeded.",
    "30": "Unregistered API key.",
    "31": "API key has expired.",
}

# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------


def _build_url(base: str, region_code: str, year_month: str, num_of_rows: int) -> str:
    """Build a data.go.kr API URL with serviceKey embedded in the path.

    serviceKey must be placed directly in the URL string rather than passed
    via httpx params to avoid double URL-encoding.

    Parameters:
        base: Base endpoint URL.
        region_code: 5-digit legal district code (LAWD_CD).
        year_month: Target year-month in YYYYMM format (DEAL_YMD).
        num_of_rows: Maximum number of records to fetch.

    Returns:
        Fully constructed URL string.
    """
    api_key = os.getenv("DATA_GO_KR_API_KEY", "")
    encoded_key = urllib.parse.quote(api_key, safe="")
    return (
        f"{base}?serviceKey={encoded_key}"
        f"&LAWD_CD={region_code}&DEAL_YMD={year_month}"
        f"&numOfRows={num_of_rows}&pageNo=1"
    )


async def _fetch_xml(url: str) -> tuple[str | None, dict[str, Any] | None]:
    """Perform an async HTTP GET and return the response body or an error dict.

    Parameters:
        url: Fully constructed API URL including serviceKey.

    Returns:
        (xml_text, None) on success.
        (None, error_dict) on timeout, HTTP error, or network failure.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text, None
    except httpx.TimeoutException:
        return None, {"error": "network_error", "message": "API server timed out (15s)"}
    except httpx.HTTPStatusError as exc:
        return None, {
            "error": "network_error",
            "message": f"HTTP error: {exc.response.status_code}",
        }
    except httpx.RequestError as exc:
        return None, {"error": "network_error", "message": f"Network error: {exc}"}


def _check_api_key() -> dict[str, Any] | None:
    """Return an error dict if DATA_GO_KR_API_KEY is not set, else None."""
    if not os.getenv("DATA_GO_KR_API_KEY", ""):
        return {
            "error": "config_error",
            "message": "Environment variable DATA_GO_KR_API_KEY is not set.",
        }
    return None


def _get_total_count(root: Any) -> int:
    """Extract totalCount from a parsed XML root element."""
    try:
        return int(root.findtext(".//totalCount") or "0")
    except ValueError:
        return 0


def _txt(item: Any, tag: str) -> str:
    """Extract and strip text content from an XML element."""
    return (item.findtext(tag) or "").strip()


def _parse_amount(raw: str) -> int | None:
    """Parse a comma-formatted amount string to int. Returns None on failure."""
    try:
        return int(raw.replace(",", ""))
    except ValueError:
        return None


def _parse_float(raw: str) -> float:
    """Parse a string to float, returning 0.0 on failure."""
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _parse_int(raw: str) -> int:
    """Parse a string to int, returning 0 on failure."""
    try:
        return int(raw)
    except ValueError:
        return 0


def _make_date(item: Any) -> str:
    """Construct a YYYY-MM-DD date string from dealYear/Month/Day elements."""
    year = _txt(item, "dealYear")
    month = _txt(item, "dealMonth").zfill(2)
    day = _txt(item, "dealDay").zfill(2)
    return f"{year}-{month}-{day}" if year else ""


def _build_trade_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute sale price summary statistics.

    Parameters:
        items: Trade records containing price_10k field.

    Returns:
        median/min/max price_10k and sample_count.
    """
    if not items:
        return {
            "median_price_10k": 0,
            "min_price_10k": 0,
            "max_price_10k": 0,
            "sample_count": 0,
        }
    prices = [it["price_10k"] for it in items]
    return {
        "median_price_10k": int(statistics.median(prices)),
        "min_price_10k": min(prices),
        "max_price_10k": max(prices),
        "sample_count": len(prices),
    }


def _build_rent_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute lease/rent deposit summary statistics.

    Parameters:
        items: Rent records containing deposit_10k and monthly_rent_10k fields.

    Returns:
        median/min/max deposit_10k, monthly_rent_avg_10k, and sample_count.
        jeonse_ratio_pct is always null here — caller must compute with trade data.
    """
    if not items:
        return {
            "median_deposit_10k": 0,
            "min_deposit_10k": 0,
            "max_deposit_10k": 0,
            "monthly_rent_avg_10k": 0,
            "jeonse_ratio_pct": None,
            "sample_count": 0,
        }
    deposits = [it["deposit_10k"] for it in items]
    rents = [it["monthly_rent_10k"] for it in items]
    return {
        "median_deposit_10k": int(statistics.median(deposits)),
        "min_deposit_10k": min(deposits),
        "max_deposit_10k": max(deposits),
        "monthly_rent_avg_10k": int(statistics.mean(rents)) if rents else 0,
        "jeonse_ratio_pct": None,
        "sample_count": len(deposits),
    }


def _api_error_response(error_code: str) -> dict[str, Any]:
    """Build a standardised API error response dict."""
    msg = _ERROR_MESSAGES.get(error_code, f"API error code: {error_code}")
    return {"error": "api_error", "code": error_code, "message": msg}


# ---------------------------------------------------------------------------
# Tool 1: region name → legal district code
# ---------------------------------------------------------------------------


@mcp.tool()
def get_region_code(query: str) -> dict[str, Any]:
    """Convert a user-supplied region name to a 5-digit legal district code for the MOLIT API.

    Must be called before any trade or rent tool.
    Accepts free-form text such as "마포구", "서울 마포구", or "마포구 공덕동".

    If multiple matches are returned, show the matches array to the user
    and confirm which region they mean before selecting a region_code.

    Args:
        query: Free-form region name text supplied by the user.

    Returns:
        region_code: 5-digit code for the API parameter (e.g. "11440")
        full_name: Representative legal district name (e.g. "서울특별시 마포구")
        matches: List of all matching results (10-digit original code + name)
        error/message: Present when no match is found
    """
    return search_region_code(query)


# ---------------------------------------------------------------------------
# Tool 2: current year-month
# ---------------------------------------------------------------------------


@mcp.tool()
def get_current_year_month() -> dict[str, str]:
    """Return the current year and month in YYYYMM format for use with trade/rent tools.

    Call this tool when the user asks about current or recent transactions
    without specifying a year_month.

    Returns:
        year_month: Current year-month string in YYYYMM format (e.g. "202602")
    """
    from datetime import datetime, timezone

    now = datetime.now(tz=timezone.utc)
    return {"year_month": now.strftime("%Y%m")}


# ---------------------------------------------------------------------------
# Parsers: sale (trade) records
# ---------------------------------------------------------------------------


def _parse_apt_trades(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse apartment sale XML response.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        if _txt(item, "cdealType") == "O":
            continue
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "apt_name": _txt(item, "aptNm"),
                "dong": _txt(item, "umdNm"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
            }
        )
    return items, None


def _parse_officetel_trades(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse officetel sale XML response.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        if _txt(item, "cdealType") == "O":
            continue
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "unit_name": _txt(item, "offiNm"),
                "dong": _txt(item, "umdNm"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
            }
        )
    return items, None


def _parse_villa_trades(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse row-house / multi-family (연립다세대) sale XML response.

    Includes house_type ("연립" or "다세대") for distinguishing subtypes.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        if _txt(item, "cdealType") == "O":
            continue
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "unit_name": _txt(item, "mhouseNm"),
                "dong": _txt(item, "umdNm"),
                "house_type": _txt(item, "houseType"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
            }
        )
    return items, None


def _parse_single_house_trades(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse detached / multi-unit house (단독/다가구) sale XML response.

    No unit name in the API response; area is totalFloorAr (gross floor area).
    jibun may be absent — handled as empty string.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        if _txt(item, "cdealType") == "O":
            continue
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "unit_name": "",  # not provided by this API
                "dong": _txt(item, "umdNm"),
                "house_type": _txt(item, "houseType"),
                "area_sqm": _parse_float(_txt(item, "totalFloorAr")),
                "floor": 0,  # not applicable for detached houses
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
            }
        )
    return items, None


def _parse_commercial_trade(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse commercial / business building (상업업무용) sale XML response.

    Returns a different structure from residential tools:
    building_type, building_use, land_use, building_ar instead of unit_name/area_sqm.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        if _txt(item, "cdealtype") == "O":
            continue
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "building_type": _txt(item, "buildingType"),
                "building_use": _txt(item, "buildingUse"),
                "land_use": _txt(item, "landUse"),
                "dong": _txt(item, "umdNm"),
                "building_ar": _parse_float(_txt(item, "buildingAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
                "share_dealing": _txt(item, "shareDealingType"),
            }
        )
    return items, None


# ---------------------------------------------------------------------------
# Parsers: lease / rent records
# ---------------------------------------------------------------------------


def _parse_apt_rent(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse apartment lease/rent XML response.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        if _txt(item, "cdealType") == "O":
            continue
        deposit = _parse_amount(_txt(item, "deposit"))
        if deposit is None:
            continue
        monthly_rent_raw = _txt(item, "monthlyRent")
        monthly_rent = _parse_amount(monthly_rent_raw) if monthly_rent_raw else 0
        items.append(
            {
                "unit_name": _txt(item, "aptNm"),
                "dong": _txt(item, "umdNm"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "deposit_10k": deposit,
                "monthly_rent_10k": monthly_rent or 0,
                "contract_type": _txt(item, "contractType"),
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
            }
        )
    return items, None


def _parse_officetel_rent(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse officetel lease/rent XML response.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        deposit = _parse_amount(_txt(item, "deposit"))
        if deposit is None:
            continue
        monthly_rent_raw = _txt(item, "monthlyRent")
        monthly_rent = _parse_amount(monthly_rent_raw) if monthly_rent_raw else 0
        items.append(
            {
                "unit_name": _txt(item, "offiNm"),
                "dong": _txt(item, "umdNm"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "deposit_10k": deposit,
                "monthly_rent_10k": monthly_rent or 0,
                "contract_type": _txt(item, "contractType"),
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
            }
        )
    return items, None


def _parse_single_house_rent(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse detached / multi-unit house lease/rent XML response.

    Area is totalFloorAr (gross floor area). No unit name provided.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        deposit = _parse_amount(_txt(item, "deposit"))
        if deposit is None:
            continue
        monthly_rent_raw = _txt(item, "monthlyRent")
        monthly_rent = _parse_amount(monthly_rent_raw) if monthly_rent_raw else 0
        items.append(
            {
                "unit_name": "",  # not provided by this API
                "dong": _txt(item, "umdNm"),
                "house_type": _txt(item, "houseType"),
                "area_sqm": _parse_float(_txt(item, "totalFloorAr")),
                "deposit_10k": deposit,
                "monthly_rent_10k": monthly_rent or 0,
                "contract_type": _txt(item, "contractType"),
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
            }
        )
    return items, None


# ---------------------------------------------------------------------------
# Common tool body helper
# ---------------------------------------------------------------------------


async def _run_trade_tool(
    base_url: str,
    parser: Any,
    region_code: str,
    year_month: str,
    num_of_rows: int,
) -> dict[str, Any]:
    """Fetch, parse, and summarise a sale (trade) API response.

    Parameters:
        base_url: Endpoint URL constant for the specific property type.
        parser: Parser function matching _parse_*_trades signature.
        region_code: 5-digit legal district code.
        year_month: YYYYMM string.
        num_of_rows: Max records to fetch.

    Returns:
        Standardised trade response dict or error dict.
    """
    err = _check_api_key()
    if err:
        return err

    url = _build_url(base_url, region_code, year_month, num_of_rows)
    xml_text, fetch_err = await _fetch_xml(url)
    if fetch_err:
        return fetch_err
    assert xml_text is not None  # guaranteed: fetch_err is None only when xml_text is str

    try:
        items, error_code = parser(xml_text)
    except XmlParseError as exc:
        return {"error": "parse_error", "message": f"XML parse failed: {exc}"}

    if error_code is not None:
        return _api_error_response(error_code)

    root = xml_fromstring(xml_text)
    return {
        "total_count": _get_total_count(root),
        "items": items,
        "summary": _build_trade_summary(items),
    }


async def _run_rent_tool(
    base_url: str,
    parser: Any,
    region_code: str,
    year_month: str,
    num_of_rows: int,
) -> dict[str, Any]:
    """Fetch, parse, and summarise a lease/rent API response.

    Parameters:
        base_url: Endpoint URL constant for the specific property type.
        parser: Parser function matching _parse_*_rent signature.
        region_code: 5-digit legal district code.
        year_month: YYYYMM string.
        num_of_rows: Max records to fetch.

    Returns:
        Standardised rent response dict or error dict.
    """
    err = _check_api_key()
    if err:
        return err

    url = _build_url(base_url, region_code, year_month, num_of_rows)
    xml_text, fetch_err = await _fetch_xml(url)
    if fetch_err:
        return fetch_err
    assert xml_text is not None  # guaranteed: fetch_err is None only when xml_text is str

    try:
        items, error_code = parser(xml_text)
    except XmlParseError as exc:
        return {"error": "parse_error", "message": f"XML parse failed: {exc}"}

    if error_code is not None:
        return _api_error_response(error_code)

    root = xml_fromstring(xml_text)
    return {
        "total_count": _get_total_count(root),
        "items": items,
        "summary": _build_rent_summary(items),
    }


# ---------------------------------------------------------------------------
# Tool 2: apartment sale records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_apartment_trades(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return apartment sale records and summary statistics for a region and month.

    Use summary.median_price_10k as the reference price and
    min/max_price_10k to present the price range.

    To compute jeonse ratio, call get_apartment_rent for the same region and
    month, then divide rent summary.median_deposit_10k by this
    summary.median_price_10k.

    region_code must be obtained first via the get_region_code tool.

    Query strategy:
    - For price trend analysis, call this tool for each of the 6 consecutive
      months preceding the current month.
    - To check year-over-year changes, also query the same month across
      3 years (e.g. 202412, 202312, 202212).

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501"). Call get_current_year_month if not specified by the user.
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Trade list (apt_name, dong, area_sqm, floor,
               price_10k, trade_date, build_year, deal_type)
        summary: median/min/max price_10k, sample_count
        error/message: Present on API error or network failure
    """
    return await _run_trade_tool(
        _APT_TRADE_URL, _parse_apt_trades, region_code, year_month, num_of_rows
    )


# ---------------------------------------------------------------------------
# Tool 3: apartment lease / rent records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_apartment_rent(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return apartment lease and monthly-rent records for a region and month.

    Use this alongside get_apartment_trades to compute the jeonse ratio:
      jeonse_ratio = summary.median_deposit_10k / trade summary.median_price_10k
    A ratio above 70% signals high gap-investment risk.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501"). Call get_current_year_month if not specified by the user.
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Rent list (unit_name, dong, area_sqm, floor,
               deposit_10k, monthly_rent_10k, contract_type,
               trade_date, build_year)
        summary: median/min/max deposit_10k, monthly_rent_avg_10k,
                 jeonse_ratio_pct (null — compute from trade data),
                 sample_count
        error/message: Present on API error or network failure
    """
    return await _run_rent_tool(
        _APT_RENT_URL, _parse_apt_rent, region_code, year_month, num_of_rows
    )


# ---------------------------------------------------------------------------
# Tool 4: officetel sale records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_officetel_trades(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return officetel sale records and summary statistics for a region and month.

    Use to compare officetel prices against apartment prices in the same area.
    Officetel units are typically smaller and cheaper than apartments,
    suitable for 1-person households or as rental investment.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501"). Call get_current_year_month if not specified by the user.
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Trade list (unit_name, dong, area_sqm, floor,
               price_10k, trade_date, build_year, deal_type)
        summary: median/min/max price_10k, sample_count
        error/message: Present on API error or network failure
    """
    return await _run_trade_tool(
        _OFFI_TRADE_URL, _parse_officetel_trades, region_code, year_month, num_of_rows
    )


# ---------------------------------------------------------------------------
# Tool 5: officetel lease / rent records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_officetel_rent(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return officetel lease and monthly-rent records for a region and month.

    Use alongside get_officetel_trades to compute officetel jeonse ratio
    and evaluate rental investment yield.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501"). Call get_current_year_month if not specified by the user.
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Rent list (unit_name, dong, area_sqm, floor,
               deposit_10k, monthly_rent_10k, contract_type,
               trade_date, build_year)
        summary: median/min/max deposit_10k, monthly_rent_avg_10k,
                 jeonse_ratio_pct (null), sample_count
        error/message: Present on API error or network failure
    """
    return await _run_rent_tool(
        _OFFI_RENT_URL, _parse_officetel_rent, region_code, year_month, num_of_rows
    )


# ---------------------------------------------------------------------------
# Tool 6: row-house / multi-family (연립다세대) sale records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_villa_trades(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return row-house and multi-family (연립다세대) sale records for a region and month.

    Items include house_type ("연립" or "다세대") for distinguishing subtypes.
    Villas are typically cheaper than apartments and may suit budget-constrained buyers.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501"). Call get_current_year_month if not specified by the user.
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Trade list (unit_name, dong, house_type, area_sqm, floor,
               price_10k, trade_date, build_year, deal_type)
        summary: median/min/max price_10k, sample_count
        error/message: Present on API error or network failure
    """
    return await _run_trade_tool(
        _VILLA_TRADE_URL, _parse_villa_trades, region_code, year_month, num_of_rows
    )


# ---------------------------------------------------------------------------
# Tool 7: detached / multi-unit house (단독/다가구) sale records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_single_house_trades(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return detached and multi-unit house (단독/다가구) sale records for a region and month.

    No unit name is provided by the API. area_sqm is gross floor area (totalFloorAr).
    house_type distinguishes "단독" from "다가구".

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501"). Call get_current_year_month if not specified by the user.
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Trade list (unit_name="", dong, house_type, area_sqm, floor=0,
               price_10k, trade_date, build_year, deal_type)
        summary: median/min/max price_10k, sample_count
        error/message: Present on API error or network failure
    """
    return await _run_trade_tool(
        _SINGLE_TRADE_URL, _parse_single_house_trades, region_code, year_month, num_of_rows
    )


# ---------------------------------------------------------------------------
# Tool 8: detached / multi-unit house lease / rent records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_single_house_rent(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return detached and multi-unit house (단독/다가구) lease/rent records for a region and month.

    No unit name is provided. area_sqm is gross floor area (totalFloorAr).
    house_type distinguishes "단독" from "다가구".

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501"). Call get_current_year_month if not specified by the user.
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Rent list (unit_name="", dong, house_type, area_sqm,
               deposit_10k, monthly_rent_10k, contract_type,
               trade_date, build_year)
        summary: median/min/max deposit_10k, monthly_rent_avg_10k,
                 jeonse_ratio_pct (null), sample_count
        error/message: Present on API error or network failure
    """
    return await _run_rent_tool(
        _SINGLE_RENT_URL, _parse_single_house_rent, region_code, year_month, num_of_rows
    )


# ---------------------------------------------------------------------------
# Tool 9: commercial / business building (상업업무용) sale records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_commercial_trade(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return commercial and business building (상업업무용) sale records for a region and month.

    Response structure differs from residential tools:
    building_type, building_use, land_use, building_ar instead of unit_name/area_sqm.
    share_dealing indicates whether the transaction is a partial-share deal.

    Use to evaluate commercial real estate investment options alongside residential data.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501"). Call get_current_year_month if not specified by the user.
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Trade list (building_type, building_use, land_use, dong,
               building_ar, floor, price_10k, trade_date, build_year,
               deal_type, share_dealing)
        summary: median/min/max price_10k, sample_count
        error/message: Present on API error or network failure
    """
    return await _run_trade_tool(
        _COMMERCIAL_TRADE_URL, _parse_commercial_trade, region_code, year_month, num_of_rows
    )


if __name__ == "__main__":
    mcp.run()
