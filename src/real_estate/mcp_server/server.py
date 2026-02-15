"""Real estate transaction MCP server.

Register with Claude Desktop to query region codes and
apartment trade records through natural language.

Tools:
  - get_region_code: region name → 5-digit legal district code
  - get_apartment_trades: legal district code + year-month → trade list + summary stats
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

from real_estate.data.region_code import RegionResult, search_region_code  # noqa: E402

mcp = FastMCP("real-estate")

_API_BASE = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"


# ---------------------------------------------------------------------------
# Tool 1: region name → legal district code
# ---------------------------------------------------------------------------


@mcp.tool()
def get_region_code(query: str) -> RegionResult:
    """Convert a user-supplied region name to a 5-digit legal district code for the MOLIT API.

    Must be called before get_apartment_trades.
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
# Tool 2: apartment trade records
# ---------------------------------------------------------------------------


def _parse_trades(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse an XML response and return a trade list and error code.

    Parameters:
        xml_text: Raw XML string from the MOLIT API.

    Returns:
        (items, error_code): On success, items contains the trade list and error_code is None.
        On error, items is an empty list and error_code holds the code string.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):

        def txt(tag: str) -> str:
            return (item.findtext(tag) or "").strip()

        # Skip cancelled deals
        if txt("cdealType") == "O":
            continue

        raw_amount = txt("dealAmount").replace(",", "")
        try:
            price_10k = int(raw_amount)
        except ValueError:
            continue

        try:
            area_sqm = float(txt("excluUseAr"))
        except ValueError:
            area_sqm = 0.0

        try:
            floor_val = int(txt("floor"))
        except ValueError:
            floor_val = 0

        try:
            build_year = int(txt("buildYear"))
        except ValueError:
            build_year = 0

        year = txt("dealYear")
        month = txt("dealMonth").zfill(2)
        day = txt("dealDay").zfill(2)
        trade_date = f"{year}-{month}-{day}" if year else ""

        items.append(
            {
                "apt_name": txt("aptNm"),
                "dong": txt("umdNm"),
                "area_sqm": area_sqm,
                "floor": floor_val,
                "price_10k": price_10k,
                "trade_date": trade_date,
                "build_year": build_year,
                "deal_type": txt("dealingGbn"),
            }
        )

    return items, None


def _build_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute summary statistics from a trade list.

    Parameters:
        items: Trade list returned by _parse_trades.

    Returns:
        median_price_10k, min_price_10k, max_price_10k, sample_count.
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


_ERROR_MESSAGES: dict[str, str] = {
    "03": "No trade records found for the specified region and period.",
    "10": "Invalid API request parameters.",
    "22": "Daily API request limit exceeded.",
    "30": "Unregistered API key.",
    "31": "API key has expired.",
}


@mcp.tool()
async def get_apartment_trades(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return apartment trade records and summary statistics for a region and month.

    Use summary.median_price_10k as the reference price and
    min/max_price_10k to present the price range.

    region_code must be obtained first via the get_region_code tool.

    Query strategy:
    - For price trend analysis, call this tool for each of the 6 consecutive months
      preceding the current month.
    - To check seasonality or year-over-year changes, also query the same month across
      3 years (e.g. 202412, 202312, 202212).
    - The current month's data may have fewer records due to incomplete aggregation.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501").
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Trade list (apt_name, dong, area_sqm, floor,
               price_10k, trade_date, build_year, deal_type)
        summary: median/min/max price_10k, sample_count
        error/message: Present on API error or network failure
    """
    api_key = os.getenv("DATA_GO_KR_API_KEY", "")
    if not api_key:
        return {
            "error": "config_error",
            "message": "Environment variable DATA_GO_KR_API_KEY is not set.",
        }

    # serviceKey is embedded directly in the URL — using httpx params causes double-encoding
    encoded_key = urllib.parse.quote(api_key, safe="")
    url = (
        f"{_API_BASE}?serviceKey={encoded_key}"
        f"&LAWD_CD={region_code}&DEAL_YMD={year_month}"
        f"&numOfRows={num_of_rows}&pageNo=1"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException:
        return {"error": "network_error", "message": "API server timed out (15s)"}
    except httpx.HTTPStatusError as exc:
        return {
            "error": "network_error",
            "message": f"HTTP error: {exc.response.status_code}",
        }
    except httpx.RequestError as exc:
        return {"error": "network_error", "message": f"Network error: {exc}"}

    try:
        items, error_code = _parse_trades(response.text)
    except XmlParseError as exc:
        return {"error": "parse_error", "message": f"XML parse failed: {exc}"}

    if error_code is not None:
        msg = _ERROR_MESSAGES.get(error_code, f"API error code: {error_code}")
        return {"error": "api_error", "code": error_code, "message": msg}

    root = xml_fromstring(response.text)
    total_count_text = root.findtext(".//totalCount") or "0"
    try:
        total_count = int(total_count_text)
    except ValueError:
        total_count = len(items)

    return {
        "total_count": total_count,
        "items": items,
        "summary": _build_summary(items),
    }


if __name__ == "__main__":
    mcp.run()
