"""MCP tools for real estate lease/rent records."""

from __future__ import annotations

from typing import Any

from real_estate.mcp_server import mcp
from real_estate.mcp_server._helpers import (
    _APT_RENT_URL,
    _OFFI_RENT_URL,
    _SINGLE_RENT_URL,
    _VILLA_RENT_URL,
    _run_rent_tool,
)
from real_estate.mcp_server.parsers.rent import (
    _parse_apt_rent,
    _parse_officetel_rent,
    _parse_single_house_rent,
    _parse_villa_rent,
)


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
