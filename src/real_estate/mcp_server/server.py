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
  - get_villa_rent: row-house/multi-family lease/rent records + summary stats
  - get_single_house_trades: detached/multi-unit house sale records + summary stats
  - get_single_house_rent: detached/multi-unit house lease/rent records + summary stats
  - get_commercial_trade: commercial/business building sale records + summary stats
  - get_apt_subscription_info: applyhome (청약홈) APT subscription notice metadata
  - get_apt_subscription_results: applyhome (청약홈) subscription stats
    (requests, winners, rates, scores)
  - get_public_auction_items: onbid next-gen bid result list (공매 물건 입찰결과 목록)

Korean housing-type keyword mapping (for tool selection):
  - "아파트" → get_apartment_trades / get_apartment_rent
  - "오피스텔" → get_officetel_trades / get_officetel_rent
  - "빌라", "연립", "다세대", "연립다세대" → get_villa_trades / get_villa_rent
    Note: "빌라" is a market term commonly referring to low-rise 공동주택 such as "다세대/연립".
  - "단독", "다가구", "단독/다가구" → get_single_house_trades / get_single_house_rent
  - "아파트외" (비아파트) → If subtype is not specified, prefer calling:
    get_villa_trades + get_villa_rent + get_single_house_trades + get_single_house_rent
    (and optionally officetel tools if "오피스텔" is included).

Korean "subscription" keyword mapping (for tool selection):
  - "청약", "분양", "모집공고", "청약 일정", "당첨자 발표", "계약 일정"
    → get_apt_subscription_info
  - "청약 경쟁률", "청약 신청자", "청약 당첨자", "가점", "가점제"
    → get_apt_subscription_results

Korean "onbid/public auction" keyword mapping (for tool selection):
  - "온비드", "공매", "입찰", "낙찰", "유찰", "캠코"
    → get_public_auction_items (next-gen bid results list, B010003)
  - "온비드 물건", "온비드 물건조회", "통합용도별물건", "처분방식", "감정가", "최저입찰가"
    → get_onbid_thing_info_list (ThingInfoInquireSvc list)
  - "온비드 코드", "용도 코드", "카테고리 코드", "주소 코드", "시도/시군구/읍면동 코드조회"
    → get_onbid_*_code_info / get_onbid_addr*_info (OnbidCodeInfoInquireSvc)
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import ParseError as XmlParseError
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load .env from project root (ignored if file is absent)
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from real_estate.mcp_server._region import search_region_code  # noqa: E402
from real_estate.mcp_server._helpers import (  # noqa: E402
    _APT_RENT_URL,
    _APT_SUBSCRIPTION_INFO_PATH,
    _APT_TRADE_URL,
    _APPLYHOME_STAT_BASE_URL,
    _COMMERCIAL_TRADE_URL,
    _ODCLOUD_BASE_URL,
    _OFFI_RENT_URL,
    _OFFI_TRADE_URL,
    _ONBID_ADDR1_URL,
    _ONBID_ADDR2_URL,
    _ONBID_ADDR3_URL,
    _ONBID_BID_RESULT_DETAIL_URL,
    _ONBID_BID_RESULT_LIST_URL,
    _ONBID_CODE_BOTTOM_URL,
    _ONBID_CODE_MIDDLE_URL,
    _ONBID_CODE_TOP_URL,
    _ONBID_DTL_ADDR_URL,
    _ONBID_THING_INFO_LIST_URL,
    _SINGLE_RENT_URL,
    _SINGLE_TRADE_URL,
    _VILLA_RENT_URL,
    _VILLA_TRADE_URL,
    _api_error_response,
    _build_rent_summary,
    _build_trade_summary,
    _build_url_with_service_key,
    _check_odcloud_key,
    _check_onbid_api_key,
    _fetch_json,
    _fetch_xml,
    _get_data_go_kr_key_for_onbid,
    _get_odcloud_key,
    _get_total_count,
    _get_total_count_onbid,
    _run_onbid_code_info_tool,
    _run_rent_tool,
    _run_trade_tool,
)
from real_estate.mcp_server.parsers.onbid import (  # noqa: E402
    _onbid_extract_items,
    _parse_onbid_code_info_xml,
    _parse_onbid_thing_info_list_xml,
    _parse_onbid_xml_items,
)
from real_estate.mcp_server.parsers.rent import (  # noqa: E402
    _parse_apt_rent,
    _parse_officetel_rent,
    _parse_single_house_rent,
    _parse_villa_rent,
)
from real_estate.mcp_server.parsers.trade import (  # noqa: E402
    _parse_apt_trades,
    _parse_commercial_trade,
    _parse_officetel_trades,
    _parse_single_house_trades,
    _parse_villa_trades,
)

mcp = FastMCP("real-estate")


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
# Tool 2: apartment sale records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_apartment_trades(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return apartment sale records and summary statistics for a region and month.

    Korean keywords: 아파트

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
        year_month: Target year-month in YYYYMM format (e.g. "202501").
            Call get_current_year_month if not specified by the user.
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

    Korean keywords: 아파트

    Use this alongside get_apartment_trades to compute the jeonse ratio:
      jeonse_ratio = summary.median_deposit_10k / trade summary.median_price_10k
    A ratio above 70% signals high gap-investment risk.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501").
            Call get_current_year_month if not specified by the user.
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

    Korean keywords: 오피스텔

    Use to compare officetel prices against apartment prices in the same area.
    Officetel units are typically smaller and cheaper than apartments,
    suitable for 1-person households or as rental investment.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501").
            Call get_current_year_month if not specified by the user.
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

    Korean keywords: 오피스텔

    Use alongside get_officetel_trades to compute officetel jeonse ratio
    and evaluate rental investment yield.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501").
            Call get_current_year_month if not specified by the user.
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

    Korean keywords: 빌라, 연립, 다세대, 연립다세대, (아파트외 중) 저층 공동주택
    Notes:
      - "빌라" is not a legal housing type; it is commonly used to refer to "다세대/연립".

    Items include house_type ("연립" or "다세대") for distinguishing subtypes.
    Villas are typically cheaper than apartments and may suit budget-constrained buyers.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501").
            Call get_current_year_month if not specified by the user.
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
# Tool 7: row-house / multi-family (연립다세대) lease / rent records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_villa_rent(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return row-house and multi-family (연립다세대) lease/rent records for a region and month.

    Korean keywords: 빌라, 연립, 다세대, 연립다세대, (아파트외 중) 저층 공동주택

    Use alongside get_villa_trades to compute villa jeonse ratio
    and evaluate rental investment yield.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501").
            Call get_current_year_month if not specified by the user.
        num_of_rows: Maximum number of records to return. Default 100.

    Returns:
        total_count: Total record count from the API
        items: Rent list (unit_name, dong, house_type, area_sqm, floor,
               deposit_10k, monthly_rent_10k, contract_type,
               trade_date, build_year)
        summary: median/min/max deposit_10k, monthly_rent_avg_10k,
                 jeonse_ratio_pct (null), sample_count
        error/message: Present on API error or network failure
    """
    return await _run_rent_tool(
        _VILLA_RENT_URL, _parse_villa_rent, region_code, year_month, num_of_rows
    )


# ---------------------------------------------------------------------------
# Tool 8: detached / multi-unit house (단독/다가구) sale records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_single_house_trades(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return detached and multi-unit house (단독/다가구) sale records for a region and month.

    Korean keywords: 단독, 다가구, 단독/다가구, (아파트외 중) 단독/다가구

    No unit name is provided by the API. area_sqm is gross floor area (totalFloorAr).
    house_type distinguishes "단독" from "다가구".

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501").
            Call get_current_year_month if not specified by the user.
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
# Tool 9: detached / multi-unit house lease / rent records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_single_house_rent(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return detached and multi-unit house (단독/다가구) lease/rent records for a region and month.

    Korean keywords: 단독, 다가구, 단독/다가구, (아파트외 중) 단독/다가구

    No unit name is provided. area_sqm is gross floor area (totalFloorAr).
    house_type distinguishes "단독" from "다가구".

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501").
            Call get_current_year_month if not specified by the user.
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
# Tool 10: commercial / business building (상업업무용) sale records
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_commercial_trade(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return commercial and business building (상업업무용) sale records for a region and month.

    Korean keywords: 상업용, 업무용, 상가, 근린생활시설(매매), 상업업무용

    Response structure differs from residential tools:
    building_type, building_use, land_use, building_ar instead of unit_name/area_sqm.
    share_dealing indicates whether the transaction is a partial-share deal.

    Use to evaluate commercial real estate investment options alongside residential data.

    Args:
        region_code: 5-digit legal district code (returned by get_region_code).
        year_month: Target year-month in YYYYMM format (e.g. "202501").
            Call get_current_year_month if not specified by the user.
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


# ---------------------------------------------------------------------------
# Tool 10: applyhome APT subscription notice metadata (odcloud)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_apt_subscription_info(
    page: int = 1,
    per_page: int = 100,
    return_type: str = "JSON",
) -> dict[str, Any]:
    """Return Applyhome (청약홈) APT subscription notice metadata.

    Korean keywords: 청약, 분양, 모집공고, 청약 일정, 당첨자 발표, 계약 일정

    Use this tool when the user asks:
      - "청약(분양) 공고를 보고 싶어", "이번 달 모집공고 알려줘"
      - "청약 접수 시작/종료일, 당첨자 발표일이 언제야?"
      - "어떤 단지(주택명)가 분양 예정이야?"

    This tool returns APT notice metadata such as notice number, house name,
    location, schedule dates (announcement, application, winner, contract),
    and operator/constructor information. It is not tied to region_code.

    Authentication:
      - Set ODCLOUD_API_KEY (Authorization header), or
      - Set ODCLOUD_SERVICE_KEY (serviceKey query parameter).

    Args:
        page: Page number (1-based).
        per_page: Items per page.
        return_type: Response type, typically "JSON".

    Returns:
        total_count: Total record count from the API.
        items: Notice metadata records.
        page: Current page.
        per_page: Items per page.
        current_count: Number of returned items in this response.
        match_count: Number of matched items (may differ by API).
        error/message: Present on API/network/config failure.
    """
    if page < 1:
        return {"error": "validation_error", "message": "page must be >= 1"}
    if per_page < 1:
        return {"error": "validation_error", "message": "per_page must be >= 1"}

    err = _check_odcloud_key()
    if err:
        return err

    mode, key = _get_odcloud_key()
    headers: dict[str, str] | None = None
    params: dict[str, Any] = {"page": page, "perPage": per_page, "returnType": return_type}
    if mode == "authorization":
        headers = {"Authorization": key}
    elif mode == "serviceKey":
        params["serviceKey"] = key

    url = f"{_ODCLOUD_BASE_URL}{_APT_SUBSCRIPTION_INFO_PATH}?{urllib.parse.urlencode(params)}"
    payload, fetch_err = await _fetch_json(url, headers=headers)
    if fetch_err:
        return fetch_err
    if not isinstance(payload, dict):
        return {"error": "parse_error", "message": "Unexpected response type"}

    return {
        "total_count": int(payload.get("totalCount") or 0),
        "items": payload.get("data") or [],
        "page": int(payload.get("page") or page),
        "per_page": int(payload.get("perPage") or per_page),
        "current_count": int(payload.get("currentCount") or 0),
        "match_count": int(payload.get("matchCount") or 0),
    }


# ---------------------------------------------------------------------------
# Tool 11: applyhome subscription stats (odcloud)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_apt_subscription_results(
    stat_kind: str,
    stat_year_month: str | None = None,
    area_code: str | None = None,
    reside_secd: str | None = None,
    page: int = 1,
    per_page: int = 100,
    return_type: str = "JSON",
) -> dict[str, Any]:
    """Return Applyhome (청약홈) subscription stats: requests, winners, rates, and scores.

    Korean keywords: 청약 경쟁률, 청약 신청자, 청약 당첨자, 가점, 가점제

    Use this tool when the user asks:
      - "마포구(서울) 청약 경쟁률이 어때?"
      - "청약 신청자/당첨자 통계가 궁금해"
      - "가점 평균/중앙값/최고점은?"

    This tool provides aggregated statistics, not individual notice schedules.
    For schedules (접수/발표/계약일), use get_apt_subscription_info.

    stat_kind choices:
      - "reqst_area": 지역별 청약 신청자 (연령대별 신청건수)
      - "reqst_age":  연령별 청약 신청자 (연령대별 신청건수)
      - "przwner_area": 지역별 청약 당첨자 (연령대별 당첨건수)
      - "przwner_age":  연령별 청약 당첨자 (연령대별 당첨건수)
      - "cmpetrt_area": 지역별 청약 경쟁률 (특별/일반공급 경쟁률)
      - "aps_przwner":  지역별 청약 가점제 당첨자 (가점 통계)

    Optional filters use odcloud's cond[...] syntax.

    Authentication:
      - Set ODCLOUD_API_KEY (Authorization header), or
      - Set ODCLOUD_SERVICE_KEY (serviceKey query parameter).

    Args:
        stat_kind: Which stats endpoint to call (see choices above).
        stat_year_month: Provided year-month in YYYYMM (maps to STAT_DE).
        area_code: Subscription area code (maps to SUBSCRPT_AREA_CODE).
        reside_secd: Residence section code (maps to RESIDE_SECD, used by some endpoints).
        page: Page number (1-based).
        per_page: Items per page.
        return_type: Response type, typically "JSON".

    Returns:
        total_count/items/page/per_page/current_count/match_count plus the chosen stat_kind.
        error/message: Present on API/network/config failure.
    """
    if page < 1:
        return {"error": "validation_error", "message": "page must be >= 1"}
    if per_page < 1:
        return {"error": "validation_error", "message": "per_page must be >= 1"}

    endpoint_map: dict[str, str] = {
        "reqst_area": "getAPTReqstAreaStat",
        "reqst_age": "getAPTReqstAgeStat",
        "przwner_area": "getAPTPrzwnerAreaStat",
        "przwner_age": "getAPTPrzwnerAgeStat",
        "cmpetrt_area": "getAPTCmpetrtAreaStat",
        "aps_przwner": "getAPTApsPrzwnerStat",
    }
    endpoint = endpoint_map.get(stat_kind)
    if endpoint is None:
        return {
            "error": "validation_error",
            "message": f"Invalid stat_kind. Expected one of: {', '.join(endpoint_map)}",
        }

    err = _check_odcloud_key()
    if err:
        return err

    mode, key = _get_odcloud_key()
    headers: dict[str, str] | None = None
    params: dict[str, Any] = {"page": page, "perPage": per_page, "returnType": return_type}
    if mode == "authorization":
        headers = {"Authorization": key}
    elif mode == "serviceKey":
        params["serviceKey"] = key

    if stat_year_month:
        params["cond[STAT_DE::EQ]"] = stat_year_month
    if area_code:
        params["cond[SUBSCRPT_AREA_CODE::EQ]"] = area_code
    if reside_secd:
        params["cond[RESIDE_SECD::EQ]"] = reside_secd

    url = f"{_APPLYHOME_STAT_BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
    payload, fetch_err = await _fetch_json(url, headers=headers)
    if fetch_err:
        return fetch_err
    if not isinstance(payload, dict):
        return {"error": "parse_error", "message": "Unexpected response type"}

    return {
        "stat_kind": stat_kind,
        "total_count": int(payload.get("totalCount") or 0),
        "items": payload.get("data") or [],
        "page": int(payload.get("page") or page),
        "per_page": int(payload.get("perPage") or per_page),
        "current_count": int(payload.get("currentCount") or 0),
        "match_count": int(payload.get("matchCount") or 0),
    }


# ---------------------------------------------------------------------------
# Tool 12: onbid next-gen bid result list (data.go.kr, B010003)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_public_auction_items(
    page_no: int = 1,
    num_of_rows: int = 20,
    cltr_type_cd: str | None = None,
    prpt_div_cd: str | None = None,
    dsps_mthod_cd: str | None = None,
    bid_div_cd: str | None = None,
    lctn_sdnm: str | None = None,
    lctn_sggnm: str | None = None,
    lctn_emd_nm: str | None = None,
    opbd_dt_start: str | None = None,
    opbd_dt_end: str | None = None,
    apsl_evl_amt_start: int | None = None,
    apsl_evl_amt_end: int | None = None,
    lowst_bid_prc_start: int | None = None,
    lowst_bid_prc_end: int | None = None,
    pbct_stat_cd: str | None = None,
    onbid_cltr_nm: str | None = None,
) -> dict[str, Any]:
    """Return Onbid next-gen (B010003) bid result list for public auction items.

    This tool calls:
      - OnbidCltrBidRsltListSrvc/getCltrBidRsltList

    Natural-language → parameter mapping (for Claude):
      - Users usually do NOT ask for codes directly. When the user says things like
        "온비드 공매 물건", "입찰 결과", "낙찰/유찰", "개찰일", "감정가/최저입찰가 범위" you should:
        1) Extract intent and filters from the user message
        2) Fill the corresponding parameters below
        3) Call this tool to fetch the list

      - Location normalization:
        If the user provides a region in natural language ("서울 강남구", "부산 해운대구"),
        you can optionally call the Onbid address lookup tools first and then plug the
        results into:
          - lctn_sdnm (시/도) ← get_onbid_addr1_info
          - lctn_sggnm (시/군/구) ← get_onbid_addr2_info(addr1)
          - lctn_emd_nm (읍/면/동) ← get_onbid_addr3_info(addr2)

    Authentication:
      - Set ONBID_API_KEY (recommended), or
      - Reuse DATA_GO_KR_API_KEY.

    Args:
        page_no: Page number (1-based).
        num_of_rows: Items per page.
        cltr_type_cd: Item type code (e.g., "0001" real estate).
        prpt_div_cd: Property division code.
        dsps_mthod_cd: Disposal method code (e.g., "0001" sale, "0002" lease).
        bid_div_cd: Bid division code.
        lctn_sdnm/lctn_sggnm/lctn_emd_nm: Location (sido/sgg/emd) names.
        opbd_dt_start/opbd_dt_end: Opening date range (yyyyMMdd).
        apsl_evl_amt_start/end: Appraisal amount range (won).
        lowst_bid_prc_start/end: Lowest bid price range (won).
        pbct_stat_cd: Bid result status code.
        onbid_cltr_nm: Item name keyword.

    Returns:
        total_count: Total record count.
        items: Item list (raw fields from the API).
        page_no: Current page number.
        num_of_rows: Page size.
        error/message: Present on API/network/config failure.
    """
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    err = _check_onbid_api_key()
    if err:
        return err

    service_key = _get_data_go_kr_key_for_onbid()
    params: dict[str, Any] = {
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "resultType": "json",
    }
    if cltr_type_cd:
        params["cltrTypeCd"] = cltr_type_cd
    if prpt_div_cd:
        params["prptDivCd"] = prpt_div_cd
    if dsps_mthod_cd:
        params["dspsMthodCd"] = dsps_mthod_cd
    if bid_div_cd:
        params["bidDivCd"] = bid_div_cd
    if lctn_sdnm:
        params["lctnSdnm"] = lctn_sdnm
    if lctn_sggnm:
        params["lctnSggnm"] = lctn_sggnm
    if lctn_emd_nm:
        params["lctnEmdNm"] = lctn_emd_nm
    if opbd_dt_start:
        params["opbdDtStart"] = opbd_dt_start
    if opbd_dt_end:
        params["opbdDtEnd"] = opbd_dt_end
    if apsl_evl_amt_start is not None:
        params["apslEvlAmtStart"] = apsl_evl_amt_start
    if apsl_evl_amt_end is not None:
        params["apslEvlAmtEnd"] = apsl_evl_amt_end
    if lowst_bid_prc_start is not None:
        params["lowstBidPrcStart"] = lowst_bid_prc_start
    if lowst_bid_prc_end is not None:
        params["lowstBidPrcEnd"] = lowst_bid_prc_end
    if pbct_stat_cd:
        params["pbctStatCd"] = pbct_stat_cd
    if onbid_cltr_nm:
        params["onbidCltrNm"] = onbid_cltr_nm

    url = _build_url_with_service_key(_ONBID_BID_RESULT_LIST_URL, service_key, params)
    payload, fetch_err = await _fetch_json(url)
    if fetch_err:
        return fetch_err
    if not isinstance(payload, dict):
        return {"error": "parse_error", "message": "Unexpected response type"}

    result_code, body, items = _onbid_extract_items(payload)
    if result_code and result_code not in {"00", "000"}:
        return {
            "error": "api_error",
            "code": result_code,
            "message": str((payload.get("resultMsg") or "")).strip() or "Onbid API error",
        }

    try:
        total_count = int(body.get("totalCount") or 0)
    except (TypeError, ValueError):
        total_count = 0

    return {
        "total_count": total_count,
        "items": items,
        "page_no": int(body.get("pageNo") or page_no),
        "num_of_rows": int(body.get("numOfRows") or num_of_rows),
    }


@mcp.tool()
async def get_public_auction_item_detail(
    cltr_mng_no: str,
    pbct_cdtn_no: str,
    page_no: int = 1,
    num_of_rows: int = 20,
) -> dict[str, Any]:
    """Return Onbid next-gen (B010003) bid result detail for a single item.

    This tool calls:
      - OnbidCltrBidRsltDtlSrvc/getCltrBidRsltDtl

    Args:
        cltr_mng_no: 물건관리번호 (cltrMngNo).
        pbct_cdtn_no: 공매조건번호 (pbctCdtnNo).
        page_no: Page number (1-based).
        num_of_rows: Items per page.

    Returns:
        total_count: Total record count.
        items: Detail item list (raw fields from the API).
        page_no: Current page number.
        num_of_rows: Page size.
        error/message: Present on API/network/config failure.
    """
    if not cltr_mng_no.strip():
        return {"error": "validation_error", "message": "cltr_mng_no is required"}
    if not pbct_cdtn_no.strip():
        return {"error": "validation_error", "message": "pbct_cdtn_no is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    err = _check_onbid_api_key()
    if err:
        return err

    service_key = _get_data_go_kr_key_for_onbid()
    params: dict[str, Any] = {
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "resultType": "json",
        "cltrMngNo": cltr_mng_no,
        "pbctCdtnNo": pbct_cdtn_no,
    }

    url = _build_url_with_service_key(_ONBID_BID_RESULT_DETAIL_URL, service_key, params)
    payload, fetch_err = await _fetch_json(url)
    if fetch_err:
        return fetch_err
    if not isinstance(payload, dict):
        return {"error": "parse_error", "message": "Unexpected response type"}

    result_code, body, items = _onbid_extract_items(payload)
    if result_code and result_code not in {"00", "000"}:
        return {
            "error": "api_error",
            "code": result_code,
            "message": str((payload.get("resultMsg") or "")).strip() or "Onbid API error",
        }

    try:
        total_count = int(body.get("totalCount") or 0)
    except (TypeError, ValueError):
        total_count = 0

    return {
        "total_count": total_count,
        "items": items,
        "page_no": int(body.get("pageNo") or page_no),
        "num_of_rows": int(body.get("numOfRows") or num_of_rows),
    }


@mcp.tool()
async def get_onbid_thing_info_list(
    page_no: int = 1,
    num_of_rows: int = 20,
    dpsl_mtd_cd: str | None = None,
    ctgr_hirk_id: str | None = None,
    ctgr_hirk_id_mid: str | None = None,
    sido: str | None = None,
    sgk: str | None = None,
    emd: str | None = None,
    goods_price_from: int | None = None,
    goods_price_to: int | None = None,
    open_price_from: int | None = None,
    open_price_to: int | None = None,
    pbct_begn_dtm: str | None = None,
    pbct_cls_dtm: str | None = None,
    cltr_nm: str | None = None,
) -> dict[str, Any]:
    """Return Onbid ThingInfoInquireSvc (물건정보조회서비스) list items.

    Calls:
      - ThingInfoInquireSvc/getUnifyUsageCltr

    Notes:
      - The guide warns that requests from Python programs may be restricted.
      - Response is XML; this tool returns raw tag->text dicts per item.

    Natural-language → parameter mapping (for Claude):
      - Users typically describe what they want in words ("토지 공매", "주거용 건물", "서울 마포구",
        "감정가 5억 이하", "최저입찰가 3억 이하", "이번 달 입찰 마감") and do NOT ask for codes.
        When the user intent maps to coded parameters, call code-lookup tools to resolve
        values first, then call this tool.

      - Category/usage filters:
        Parameters:
          - CTGR_HIRK_ID (카테고리상위ID)
          - CTGR_HIRK_ID_MID (카테고리상위ID(중간))
        Resolution tools:
          1) get_onbid_top_code_info
          2) get_onbid_middle_code_info(ctgr_id=<CTGR_ID from step 1>)
          3) get_onbid_bottom_code_info(ctgr_id=<CTGR_ID from step 2>)  # optional, more specific
        How to apply:
          - If the user gives a broad category ("부동산", "토지", "주거용건물"):
            Use CTGR_ID from get_onbid_middle_code_info as CTGR_HIRK_ID_MID.
          - If the user gives a more specific subtype ("전", "답", "대지" 등 하위 용도):
            Use CTGR_ID from get_onbid_bottom_code_info as CTGR_HIRK_ID.
        Practical tip:
          - If uncertain, omit CTGR_* filters first, fetch a small list, then refine.

      - Location filters:
        Parameters:
          - SIDO (시/도), SGK (시/군/구), EMD (읍/면/동)
        Resolution tools:
          - get_onbid_addr1_info → returns ADDR1 candidates (시/도)
          - get_onbid_addr2_info(addr1) → returns ADDR2 candidates (시/군/구)
          - get_onbid_addr3_info(addr2) → returns ADDR3 candidates (읍/면/동)
        How to apply:
          - Use the selected ADDR* strings directly as SIDO/SGK/EMD.

    Args:
        page_no: Page number (1-based).
        num_of_rows: Items per page.
        dpsl_mtd_cd: 처분방식코드 ("0001" 매각, "0002" 임대/대부).
        ctgr_hirk_id: 카테고리상위ID.
        ctgr_hirk_id_mid: 카테고리상위ID(중간).
        sido/sgk/emd: 소재지(시도/시군구/읍면동).
        goods_price_from/to: 감정가 범위.
        open_price_from/to: 최저입찰가 범위.
        pbct_begn_dtm/pbct_cls_dtm: 입찰일자 From/To (YYYYMMDD).
        cltr_nm: 물건명 검색어.

    Returns:
        total_count: Total record count.
        items: List of raw records.
        page_no: Current page number.
        num_of_rows: Page size.
        error/message: Present on API/network/config failure.
    """
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    err = _check_onbid_api_key()
    if err:
        return err

    service_key = _get_data_go_kr_key_for_onbid()
    params: dict[str, Any] = {"pageNo": page_no, "numOfRows": num_of_rows}
    if dpsl_mtd_cd:
        params["DPSL_MTD_CD"] = dpsl_mtd_cd
    if ctgr_hirk_id:
        params["CTGR_HIRK_ID"] = ctgr_hirk_id
    if ctgr_hirk_id_mid:
        params["CTGR_HIRK_ID_MID"] = ctgr_hirk_id_mid
    if sido:
        params["SIDO"] = sido
    if sgk:
        params["SGK"] = sgk
    if emd:
        params["EMD"] = emd
    if goods_price_from is not None:
        params["GOODS_PRICE_FROM"] = goods_price_from
    if goods_price_to is not None:
        params["GOODS_PRICE_TO"] = goods_price_to
    if open_price_from is not None:
        params["OPEN_PRICE_FROM"] = open_price_from
    if open_price_to is not None:
        params["OPEN_PRICE_TO"] = open_price_to
    if pbct_begn_dtm:
        params["PBCT_BEGN_DTM"] = pbct_begn_dtm
    if pbct_cls_dtm:
        params["PBCT_CLS_DTM"] = pbct_cls_dtm
    if cltr_nm:
        params["CLTR_NM"] = cltr_nm

    url = _build_url_with_service_key(_ONBID_THING_INFO_LIST_URL, service_key, params)
    xml_text, fetch_err = await _fetch_xml(url)
    if fetch_err:
        return fetch_err
    assert xml_text is not None

    try:
        items, total_count, error_code, error_message = _parse_onbid_thing_info_list_xml(xml_text)
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


# ---------------------------------------------------------------------------
# Onbid code lookup tools (OnbidCodeInfoInquireSvc)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_onbid_top_code_info(
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid top-level usage/category codes.

    Korean keywords: 온비드 코드, 용도 코드, 카테고리 코드, 코드조회, CTGR_HIRK_ID

    Use this tool to discover the top-level CTGR_ID values, then call
    get_onbid_middle_code_info / get_onbid_bottom_code_info to drill down.
    These codes are needed to fill ThingInfoInquireSvc parameters such as
    CTGR_HIRK_ID and CTGR_HIRK_ID_MID.

    Typical usage:
      - User says "온비드에서 토지 공매 보고 싶어"
      - Call get_onbid_top_code_info → find "부동산"(CTGR_ID=10000)
      - Call get_onbid_middle_code_info(ctgr_id="10000") → find "토지"(CTGR_ID=10100)
      - Use CTGR_HIRK_ID_MID="10100" when calling get_onbid_thing_info_list

    Returns raw records containing:
      - CTGR_ID, CTGR_NM, CTGR_HIRK_ID, CTGR_HIRK_NM
    """
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_CODE_TOP_URL, {"pageNo": page_no, "numOfRows": num_of_rows}
    )


@mcp.tool()
async def get_onbid_middle_code_info(
    ctgr_id: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid middle-level usage/category codes under a parent CTGR_ID.

    Korean keywords: 온비드 코드, 용도 중간, 카테고리 중간, 코드조회, CTGR_HIRK_ID_MID

    Args:
        ctgr_id: Parent CTGR_ID from get_onbid_top_code_info (e.g. "10000").
    """
    if not ctgr_id.strip():
        return {"error": "validation_error", "message": "ctgr_id is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_CODE_MIDDLE_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "CTGR_ID": ctgr_id},
    )


@mcp.tool()
async def get_onbid_bottom_code_info(
    ctgr_id: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid bottom-level usage/category codes under a parent CTGR_ID.

    Korean keywords: 온비드 코드, 용도 하위, 카테고리 하위, 코드조회

    Args:
        ctgr_id: Parent CTGR_ID from get_onbid_middle_code_info (e.g. "10100").
    """
    if not ctgr_id.strip():
        return {"error": "validation_error", "message": "ctgr_id is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_CODE_BOTTOM_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "CTGR_ID": ctgr_id},
    )


@mcp.tool()
async def get_onbid_addr1_info(
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid address depth-1 list (시/도).

    Korean keywords: 온비드 주소 코드, 시도, 주소1, 코드조회

    Typical usage:
      - User says "서울 마포구"
      - Call get_onbid_addr1_info → pick ADDR1="서울특별시"
      - Call get_onbid_addr2_info(addr1="서울특별시") → pick ADDR2="마포구"
      - Optionally call get_onbid_addr3_info(addr2="마포구") for 읍/면/동
      - Use SIDO/SGK/EMD when calling get_onbid_thing_info_list
    """
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_ADDR1_URL, {"pageNo": page_no, "numOfRows": num_of_rows}
    )


@mcp.tool()
async def get_onbid_addr2_info(
    addr1: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid address depth-2 list (시/군/구) under addr1.

    Korean keywords: 온비드 주소 코드, 시군구, 주소2, 코드조회
    """
    if not addr1.strip():
        return {"error": "validation_error", "message": "addr1 is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_ADDR2_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "ADDR1": addr1},
    )


@mcp.tool()
async def get_onbid_addr3_info(
    addr2: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid address depth-3 list (읍/면/동) under addr2.

    Korean keywords: 온비드 주소 코드, 읍면동, 주소3, 코드조회
    """
    if not addr2.strip():
        return {"error": "validation_error", "message": "addr2 is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_ADDR3_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "ADDR2": addr2},
    )


@mcp.tool()
async def get_onbid_dtl_addr_info(
    addr3: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid detailed addresses under addr3.

    Korean keywords: 온비드 주소 코드, 상세주소, 코드조회
    """
    if not addr3.strip():
        return {"error": "validation_error", "message": "addr3 is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_DTL_ADDR_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "ADDR3": addr3},
    )


# ---------------------------------------------------------------------------
# Financial calculation tools
# ---------------------------------------------------------------------------


@mcp.tool()
def calculate_loan_payment(
    principal_10k: int,
    annual_rate_pct: float,
    years: int,
) -> dict[str, Any]:
    """Calculate equal principal+interest monthly payment (EMI) in 10k KRW units."""
    if principal_10k < 1:
        return {"error": "validation_error", "message": "principal_10k must be >= 1"}
    if annual_rate_pct < 0:
        return {"error": "validation_error", "message": "annual_rate_pct must be >= 0"}
    if years < 1:
        return {"error": "validation_error", "message": "years must be >= 1"}

    r = annual_rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        monthly = principal_10k / n
    else:
        growth = (1 + r) ** n
        monthly = principal_10k * r * growth / (growth - 1)

    total_payment = monthly * n
    total_interest = total_payment - principal_10k

    return {
        "monthly_payment_10k": round(monthly, 2),
        "total_payment_10k": round(total_payment, 2),
        "total_interest_10k": round(total_interest, 2),
        "principal_10k": principal_10k,
        "annual_rate_pct": annual_rate_pct,
        "years": years,
    }


@mcp.tool()
def calculate_compound_growth(
    initial_10k: int,
    monthly_contribution_10k: float,
    annual_rate_pct: float,
    years: int,
) -> dict[str, Any]:
    """Calculate compounded asset growth with initial capital and monthly contributions."""
    if initial_10k < 0:
        return {"error": "validation_error", "message": "initial_10k must be >= 0"}
    if monthly_contribution_10k < 0:
        return {"error": "validation_error", "message": "monthly_contribution_10k must be >= 0"}
    if annual_rate_pct < 0:
        return {"error": "validation_error", "message": "annual_rate_pct must be >= 0"}
    if years < 1:
        return {"error": "validation_error", "message": "years must be >= 1"}

    r = annual_rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        final = initial_10k + monthly_contribution_10k * n
    else:
        growth = (1 + r) ** n
        final = initial_10k * growth + monthly_contribution_10k * (growth - 1) / r

    total_contributed = initial_10k + monthly_contribution_10k * n
    total_gain = final - total_contributed

    return {
        "final_value_10k": round(final, 2),
        "total_contributed_10k": round(total_contributed, 2),
        "total_gain_10k": round(total_gain, 2),
        "initial_10k": initial_10k,
        "monthly_contribution_10k": monthly_contribution_10k,
        "annual_rate_pct": annual_rate_pct,
        "years": years,
    }


@mcp.tool()
def calculate_monthly_cashflow(
    monthly_income_10k: float,
    monthly_loan_payment_10k: float,
    monthly_living_cost_10k: float,
    other_monthly_costs_10k: float = 0.0,
) -> dict[str, Any]:
    """Calculate monthly free cashflow after debt service and costs."""
    if monthly_income_10k <= 0:
        return {"error": "validation_error", "message": "monthly_income_10k must be > 0"}
    if monthly_loan_payment_10k < 0:
        return {"error": "validation_error", "message": "monthly_loan_payment_10k must be >= 0"}

    living_cost_auto_applied = monthly_living_cost_10k == 0
    living_cost_used = (
        monthly_income_10k * 0.4 if living_cost_auto_applied else monthly_living_cost_10k
    )
    cashflow = (
        monthly_income_10k - monthly_loan_payment_10k - living_cost_used - other_monthly_costs_10k
    )

    return {
        "monthly_cashflow_10k": round(cashflow, 2),
        "monthly_income_10k": monthly_income_10k,
        "monthly_loan_payment_10k": monthly_loan_payment_10k,
        "monthly_living_cost_10k": round(living_cost_used, 2),
        "other_monthly_costs_10k": other_monthly_costs_10k,
        "living_cost_auto_applied": living_cost_auto_applied,
    }


if __name__ == "__main__":
    mcp.run()
