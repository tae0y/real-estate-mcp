"""E2E tests for Onbid tool functions — calls real APIs.

These tests are NOT mocked. They require a valid API key in .env.
Skip marker: all tests are marked with ``pytest.mark.e2e`` so they are
excluded from the default ``uv run pytest`` run.

Run manually:
    uv run pytest tests/mcp_server/test_onbid_e2e.py -v -m e2e

The diagnostic shell script (scripts/diagnose_onbid_apis.sh) also invokes
this file as its second stage.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from real_estate.mcp_server.tools.onbid import (
    get_onbid_addr1_info,
    get_onbid_addr2_info,
    get_onbid_bottom_code_info,
    get_onbid_middle_code_info,
    get_onbid_thing_info_list,
    get_onbid_top_code_info,
    get_public_auction_item_detail,
    get_public_auction_items,
)

# All tests require a real API key.
_has_key = bool(os.getenv("ONBID_API_KEY") or os.getenv("DATA_GO_KR_API_KEY"))
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not _has_key, reason="ONBID_API_KEY / DATA_GO_KR_API_KEY not set"),
]

# Date range: current month
_now = datetime.now(tz=timezone.utc)
_DT_START = _now.strftime("%Y%m") + "01"
_DT_END = _now.strftime("%Y%m%d")


class TestGetPublicAuctionItemsE2E:
    """E2E: get_public_auction_items (B010003 입찰결과 목록)."""

    async def test_returns_items_for_real_estate_sale(self) -> None:
        result = await get_public_auction_items(
            opbd_dt_start=_DT_START,
            opbd_dt_end=_DT_END,
            cltr_type_cd="0001",  # 부동산
            prpt_div_cd="0007",  # 압류재산
            dsps_mthod_cd="0001",  # 매각
            bid_div_cd="0001",  # 인터넷입찰
            page_no=1,
            num_of_rows=5,
        )
        assert "error" not in result, f"API error: {result}"
        assert isinstance(result["total_count"], int)
        assert result["total_count"] >= 0
        assert isinstance(result["items"], list)
        assert result["page_no"] == 1
        assert result["num_of_rows"] == 5


class TestGetPublicAuctionItemDetailE2E:
    """E2E: get_public_auction_item_detail (B010003 입찰결과 상세)."""

    async def test_detail_for_item_from_list(self) -> None:
        """Fetch list first, then fetch detail for the first item."""
        list_result = await get_public_auction_items(
            opbd_dt_start=_DT_START,
            opbd_dt_end=_DT_END,
            cltr_type_cd="0001",
            prpt_div_cd="0007",
            dsps_mthod_cd="0001",
            bid_div_cd="0001",
            page_no=1,
            num_of_rows=1,
        )
        if "error" in list_result or not list_result.get("items"):
            pytest.skip("목록 조회에서 아이템을 가져오지 못함")

        item = list_result["items"][0]
        cltr_mng_no = str(item.get("cltrMngNo", ""))
        pbct_cdtn_no = str(item.get("pbctCdtnNo", ""))
        if not cltr_mng_no or not pbct_cdtn_no:
            pytest.skip("목록 아이템에 cltrMngNo/pbctCdtnNo 없음")

        detail_result = await get_public_auction_item_detail(
            cltr_mng_no=cltr_mng_no,
            pbct_cdtn_no=pbct_cdtn_no,
            page_no=1,
            num_of_rows=5,
        )
        assert "error" not in detail_result, f"API error: {detail_result}"
        assert isinstance(detail_result["total_count"], int)
        assert isinstance(detail_result["items"], list)


class TestGetOnbidThingInfoListE2E:
    """E2E: get_onbid_thing_info_list (ThingInfoInquireSvc)."""

    async def test_returns_items(self) -> None:
        result = await get_onbid_thing_info_list(
            page_no=1,
            num_of_rows=3,
            dpsl_mtd_cd="0001",  # 매각
        )
        assert "error" not in result, f"API error: {result}"
        assert isinstance(result["total_count"], int)
        assert isinstance(result["items"], list)


class TestOnbidCodeInfoE2E:
    """E2E: 코드 조회 tools (top / middle / bottom)."""

    async def test_top_code_returns_items(self) -> None:
        result = await get_onbid_top_code_info(page_no=1, num_of_rows=10)
        assert "error" not in result, f"API error: {result}"
        assert isinstance(result["items"], list)
        assert result["total_count"] > 0

    async def test_middle_code_returns_items(self) -> None:
        result = await get_onbid_middle_code_info(ctgr_id="10000", page_no=1, num_of_rows=10)
        assert "error" not in result, f"API error: {result}"
        assert isinstance(result["items"], list)

    async def test_bottom_code_returns_items(self) -> None:
        # 10100 = 부동산 > 토지
        result = await get_onbid_bottom_code_info(ctgr_id="10100", page_no=1, num_of_rows=10)
        assert "error" not in result, f"API error: {result}"
        assert isinstance(result["items"], list)


class TestOnbidAddrInfoE2E:
    """E2E: 주소 조회 tools (addr1 / addr2)."""

    async def test_addr1_returns_sido_list(self) -> None:
        result = await get_onbid_addr1_info(page_no=1, num_of_rows=20)
        assert "error" not in result, f"API error: {result}"
        assert isinstance(result["items"], list)
        assert result["total_count"] > 0

    async def test_addr2_returns_sgg_list(self) -> None:
        result = await get_onbid_addr2_info(addr1="서울특별시", page_no=1, num_of_rows=30)
        assert "error" not in result, f"API error: {result}"
        assert isinstance(result["items"], list)
