"""Shared helpers, URL constants, and tool runners for the MCP server."""

from __future__ import annotations

import os
import statistics
import urllib.parse
from typing import Any

import httpx
from defusedxml.ElementTree import ParseError as XmlParseError
from defusedxml.ElementTree import fromstring as xml_fromstring

# ---------------------------------------------------------------------------
# API base URLs
# ---------------------------------------------------------------------------

_APT_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
_APT_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
_OFFI_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade"
_OFFI_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
_VILLA_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"
_VILLA_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent"
_SINGLE_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade"
_SINGLE_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent"
_COMMERCIAL_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"

_ODCLOUD_BASE_URL = "https://api.odcloud.kr/api"
_APT_SUBSCRIPTION_INFO_PATH = "/15101046/v1/uddi:14a46595-03dd-47d3-a418-d64e52820598"

_APPLYHOME_STAT_BASE_URL = "https://api.odcloud.kr/api/ApplyhomeStatSvc/v1"

_ONBID_BID_RESULT_LIST_URL = (
    "http://apis.data.go.kr/B010003/OnbidCltrBidRsltListSrvc/getCltrBidRsltList"
)
_ONBID_BID_RESULT_DETAIL_URL = (
    "http://apis.data.go.kr/B010003/OnbidCltrBidRsltDtlSrvc/getCltrBidRsltDtl"
)

_ONBID_THING_INFO_LIST_URL = (
    "http://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr"
)

_ONBID_CODE_INFO_BASE_URL = "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc"
_ONBID_CODE_TOP_URL = f"{_ONBID_CODE_INFO_BASE_URL}/getOnbidTopCodeInfo"
_ONBID_CODE_MIDDLE_URL = f"{_ONBID_CODE_INFO_BASE_URL}/getOnbidMiddleCodeInfo"
_ONBID_CODE_BOTTOM_URL = f"{_ONBID_CODE_INFO_BASE_URL}/getOnbidBottomCodeInfo"
_ONBID_ADDR1_URL = f"{_ONBID_CODE_INFO_BASE_URL}/getOnbidAddr1Info"
_ONBID_ADDR2_URL = f"{_ONBID_CODE_INFO_BASE_URL}/getOnbidAddr2Info"
_ONBID_ADDR3_URL = f"{_ONBID_CODE_INFO_BASE_URL}/getOnbidAddr3Info"
_ONBID_DTL_ADDR_URL = f"{_ONBID_CODE_INFO_BASE_URL}/getOnbidDtlAddrInfo"

_ERROR_MESSAGES: dict[str, str] = {
    "03": "No trade records found for the specified region and period.",
    "10": "Invalid API request parameters.",
    "22": "Daily API request limit exceeded.",
    "30": "Unregistered API key.",
    "31": "API key has expired.",
}

# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------


def _build_url_with_service_key(base: str, service_key: str, params: dict[str, Any]) -> str:
    """Build a URL with a URL-encoded serviceKey embedded directly in the string."""
    encoded_key = urllib.parse.quote(service_key, safe="")
    encoded_params = urllib.parse.urlencode(params, doseq=True)
    if encoded_params:
        return f"{base}?serviceKey={encoded_key}&{encoded_params}"
    return f"{base}?serviceKey={encoded_key}"


def _build_url(base: str, region_code: str, year_month: str, num_of_rows: int) -> str:
    """Build a data.go.kr API URL with serviceKey embedded in the path."""
    api_key = os.getenv("DATA_GO_KR_API_KEY", "")
    encoded_key = urllib.parse.quote(api_key, safe="")
    return (
        f"{base}?serviceKey={encoded_key}"
        f"&LAWD_CD={region_code}&DEAL_YMD={year_month}"
        f"&numOfRows={num_of_rows}&pageNo=1"
    )


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


async def _fetch_xml(url: str) -> tuple[str | None, dict[str, Any] | None]:
    """Perform an async HTTP GET and return the response body or an error dict."""
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


async def _fetch_json(
    url: str,
    headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any] | list[Any] | None, dict[str, Any] | None]:
    """Perform an async HTTP GET and return decoded JSON or an error dict."""
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json(), None
    except httpx.TimeoutException:
        return None, {"error": "network_error", "message": "API server timed out (15s)"}
    except httpx.HTTPStatusError as exc:
        return None, {
            "error": "network_error",
            "message": f"HTTP error: {exc.response.status_code}",
        }
    except ValueError as exc:
        return None, {"error": "parse_error", "message": f"JSON parse failed: {exc}"}
    except httpx.RequestError as exc:
        return None, {"error": "network_error", "message": f"Network error: {exc}"}


# ---------------------------------------------------------------------------
# API key helpers
# ---------------------------------------------------------------------------


def _check_api_key() -> dict[str, Any] | None:
    """Return an error dict if DATA_GO_KR_API_KEY is not set, else None."""
    if not os.getenv("DATA_GO_KR_API_KEY", ""):
        return {
            "error": "config_error",
            "message": "Environment variable DATA_GO_KR_API_KEY is not set.",
        }
    return None


def _get_data_go_kr_key_for_onbid() -> str:
    """Return the service key to use for Onbid APIs."""
    return os.getenv("ONBID_API_KEY", "") or os.getenv("DATA_GO_KR_API_KEY", "")


def _check_onbid_api_key() -> dict[str, Any] | None:
    """Return an error dict if Onbid API key is not set, else None."""
    if not _get_data_go_kr_key_for_onbid():
        return {
            "error": "config_error",
            "message": "Environment variable ONBID_API_KEY (or DATA_GO_KR_API_KEY) is not set.",
        }
    return None


def _get_odcloud_key() -> tuple[str, str]:
    """Return (mode, key) for odcloud authentication."""
    api_key = os.getenv("ODCLOUD_API_KEY", "")
    if api_key:
        return "authorization", api_key
    service_key = os.getenv("ODCLOUD_SERVICE_KEY", "")
    if service_key:
        return "serviceKey", service_key
    fallback_key = os.getenv("DATA_GO_KR_API_KEY", "")
    if fallback_key:
        return "serviceKey", fallback_key
    return "", ""


def _check_odcloud_key() -> dict[str, Any] | None:
    """Return an error dict if odcloud key is not set, else None."""
    mode, key = _get_odcloud_key()
    if not mode or not key:
        return {
            "error": "config_error",
            "message": (
                "Environment variable ODCLOUD_API_KEY "
                "(or ODCLOUD_SERVICE_KEY, or DATA_GO_KR_API_KEY) "
                "is not set."
            ),
        }
    return None


# ---------------------------------------------------------------------------
# XML / data helpers
# ---------------------------------------------------------------------------


def _get_total_count(root: Any) -> int:
    """Extract totalCount from a parsed XML root element."""
    try:
        return int(root.findtext(".//totalCount") or "0")
    except ValueError:
        return 0


def _get_total_count_onbid(root: Any) -> int:
    """Extract total count from an Onbid ThingInfoInquireSvc XML response."""
    for tag in ("TotalCount", "totalCount", "totalcount"):
        raw = root.findtext(f".//{tag}")
        if raw:
            try:
                return int(raw)
            except ValueError:
                return 0
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


def _parse_monthly_rent(item: Any) -> int:
    """Parse monthlyRent field from an XML item. Empty or invalid values return 0."""
    monthly_rent_raw = _txt(item, "monthlyRent")
    if not monthly_rent_raw:
        return 0
    return _parse_amount(monthly_rent_raw) or 0


def _make_date(item: Any) -> str:
    """Construct a YYYY-MM-DD date string from dealYear/Month/Day elements."""
    year = _txt(item, "dealYear")
    month = _txt(item, "dealMonth").zfill(2)
    day = _txt(item, "dealDay").zfill(2)
    return f"{year}-{month}-{day}" if year else ""


def _build_trade_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute sale price summary statistics."""
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
    """Compute lease/rent deposit summary statistics."""
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
# Tool runners
# ---------------------------------------------------------------------------


async def _run_trade_tool(
    base_url: str,
    parser: Any,
    region_code: str,
    year_month: str,
    num_of_rows: int,
) -> dict[str, Any]:
    """Fetch, parse, and summarise a sale (trade) API response."""
    return await _run_molit_xml_tool(
        base_url=base_url,
        parser=parser,
        region_code=region_code,
        year_month=year_month,
        num_of_rows=num_of_rows,
        summary_builder=_build_trade_summary,
    )


async def _run_rent_tool(
    base_url: str,
    parser: Any,
    region_code: str,
    year_month: str,
    num_of_rows: int,
) -> dict[str, Any]:
    """Fetch, parse, and summarise a lease/rent API response."""
    return await _run_molit_xml_tool(
        base_url=base_url,
        parser=parser,
        region_code=region_code,
        year_month=year_month,
        num_of_rows=num_of_rows,
        summary_builder=_build_rent_summary,
    )


async def _run_molit_xml_tool(
    *,
    base_url: str,
    parser: Any,
    region_code: str,
    year_month: str,
    num_of_rows: int,
    summary_builder: Any,
) -> dict[str, Any]:
    """Shared execution flow for MOLIT trade/rent XML tools."""
    err = _check_api_key()
    if err:
        return err

    url = _build_url(base_url, region_code, year_month, num_of_rows)
    xml_text, fetch_err = await _fetch_xml(url)
    if fetch_err:
        return fetch_err
    assert xml_text is not None

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
        "summary": summary_builder(items),
    }


async def _run_onbid_code_info_tool(
    endpoint_url: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Fetch and parse an OnbidCodeInfoInquireSvc response."""
    from real_estate.mcp_server.parsers.onbid import _parse_onbid_code_info_xml

    err = _check_onbid_api_key()
    if err:
        return err

    page_no = int(params.get("pageNo") or 1)
    num_of_rows = int(params.get("numOfRows") or 10)

    service_key = _get_data_go_kr_key_for_onbid()
    url = _build_url_with_service_key(endpoint_url, service_key, params)
    xml_text, fetch_err = await _fetch_xml(url)
    if fetch_err:
        return fetch_err
    assert xml_text is not None

    try:
        items, total_count, error_code, error_message = _parse_onbid_code_info_xml(xml_text)
    except XmlParseError as exc:
        return {"error": "parse_error", "message": f"XML parse failed: {exc}"}

    if error_code is not None:
        return {
            "error": "api_error",
            "code": error_code,
            "message": error_message or "Onbid API error",
        }

    return {
        "total_count": total_count,
        "items": items,
        "page_no": page_no,
        "num_of_rows": num_of_rows,
    }
