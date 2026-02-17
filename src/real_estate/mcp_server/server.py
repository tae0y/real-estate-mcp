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

from typing import Any

import real_estate.mcp_server.tools.finance  # noqa: F401 — registers @mcp.tool()
import real_estate.mcp_server.tools.onbid  # noqa: F401
import real_estate.mcp_server.tools.rent  # noqa: F401
import real_estate.mcp_server.tools.subscription  # noqa: F401
import real_estate.mcp_server.tools.trade  # noqa: F401
from real_estate.mcp_server import mcp
from real_estate.mcp_server._region import search_region_code


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


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Real Estate MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    args = parser.parse_args()

    if args.transport == "http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
