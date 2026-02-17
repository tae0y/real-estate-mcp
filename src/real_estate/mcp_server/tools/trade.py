"""MCP tools for real estate sale (trade) records."""

from __future__ import annotations

from typing import Any

from real_estate.mcp_server import mcp
from real_estate.mcp_server._helpers import (
    _APT_TRADE_URL,
    _COMMERCIAL_TRADE_URL,
    _OFFI_TRADE_URL,
    _SINGLE_TRADE_URL,
    _VILLA_TRADE_URL,
    _run_trade_tool,
)
from real_estate.mcp_server.parsers.trade import (
    _parse_apt_trades,
    _parse_commercial_trade,
    _parse_officetel_trades,
    _parse_single_house_trades,
    _parse_villa_trades,
)


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
