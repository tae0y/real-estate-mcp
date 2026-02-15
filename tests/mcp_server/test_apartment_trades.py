"""Unit tests for the get_apartment_trades tool.

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server.server import (
    _build_trade_summary,
    _parse_apt_trades,
    get_apartment_trades,
)

# ---------------------------------------------------------------------------
# Test fixtures: sample XML responses
# ---------------------------------------------------------------------------

_XML_OK = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <aptNm>마포래미안푸르지오</aptNm>
        <umdNm>합정동</umdNm>
        <excluUseAr>84.97</excluUseAr>
        <floor>12</floor>
        <dealAmount>135,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>15</dealDay>
        <buildYear>2014</buildYear>
        <dealingGbn>중개거래</dealingGbn>
        <cdealType></cdealType>
      </item>
      <item>
        <aptNm>마포자이</aptNm>
        <umdNm>아현동</umdNm>
        <excluUseAr>59.00</excluUseAr>
        <floor>5</floor>
        <dealAmount>90,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>20</dealDay>
        <buildYear>2010</buildYear>
        <dealingGbn>직거래</dealingGbn>
        <cdealType></cdealType>
      </item>
      <item>
        <aptNm>취소단지</aptNm>
        <umdNm>공덕동</umdNm>
        <excluUseAr>84.00</excluUseAr>
        <floor>3</floor>
        <dealAmount>100,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>10</dealDay>
        <buildYear>2015</buildYear>
        <dealingGbn>중개거래</dealingGbn>
        <cdealType>O</cdealType>
      </item>
    </items>
    <totalCount>2</totalCount>
  </body>
</response>"""

_XML_NO_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>03</resultCode>
    <resultMsg>No Data</resultMsg>
  </header>
  <body>
    <items/>
    <totalCount>0</totalCount>
  </body>
</response>"""

_API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"


# ---------------------------------------------------------------------------
# _parse_apt_trades unit tests
# ---------------------------------------------------------------------------


class TestParseAptTrades:
    """Unit tests for apartment trade XML parsing logic."""

    def test_normal_response_returns_items(self) -> None:
        """Normal XML returns 2 items after excluding the cancelled deal."""
        items, error_code = _parse_apt_trades(_XML_OK)
        assert error_code is None
        assert len(items) == 2  # cdealType=O item excluded

    def test_deal_amount_comma_removed(self) -> None:
        """Commas in dealAmount are stripped and converted to int."""
        items, _ = _parse_apt_trades(_XML_OK)
        assert items[0]["price_10k"] == 135000

    def test_trade_date_formatted(self) -> None:
        """Trade date is combined into YYYY-MM-DD format."""
        items, _ = _parse_apt_trades(_XML_OK)
        assert items[0]["trade_date"] == "2025-01-15"

    def test_cancelled_deal_excluded(self) -> None:
        """Items with cdealType=O are not included in the result."""
        items, _ = _parse_apt_trades(_XML_OK)
        names = [it["apt_name"] for it in items]
        assert "취소단지" not in names

    def test_error_code_returned_on_no_data(self) -> None:
        """A resultCode other than 000 returns an error_code."""
        items, error_code = _parse_apt_trades(_XML_NO_DATA)
        assert error_code == "03"
        assert items == []


# ---------------------------------------------------------------------------
# _build_trade_summary unit tests
# ---------------------------------------------------------------------------


class TestBuildTradeSummary:
    """Unit tests for trade summary statistics calculation."""

    def test_summary_values(self) -> None:
        """Median, min, max, and count are calculated correctly."""
        items = [{"price_10k": 90000}, {"price_10k": 135000}]
        summary = _build_trade_summary(items)
        assert summary["median_price_10k"] == 112500
        assert summary["min_price_10k"] == 90000
        assert summary["max_price_10k"] == 135000
        assert summary["sample_count"] == 2

    def test_empty_items_returns_zeros(self) -> None:
        """An empty list returns all zeros."""
        summary = _build_trade_summary([])
        assert summary["sample_count"] == 0
        assert summary["median_price_10k"] == 0


# ---------------------------------------------------------------------------
# get_apartment_trades integration tests (respx mock)
# ---------------------------------------------------------------------------


class TestGetApartmentTrades:
    """Integration tests for the get_apartment_trades tool."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set a test API key environment variable."""
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "test-key")

    @respx.mock
    async def test_success_returns_items_and_summary(self) -> None:
        """A successful response returns items and summary."""
        respx.get(_API_URL).mock(return_value=Response(200, text=_XML_OK))

        result = await get_apartment_trades("11440", "202501")

        assert "error" not in result
        assert result["total_count"] == 2
        assert len(result["items"]) == 2
        assert result["summary"]["sample_count"] == 2

    @respx.mock
    async def test_no_data_returns_api_error(self) -> None:
        """A no-data response (code 03) returns an error dict."""
        respx.get(_API_URL).mock(return_value=Response(200, text=_XML_NO_DATA))

        result = await get_apartment_trades("11440", "200001")

        assert result["error"] == "api_error"
        assert result["code"] == "03"

    @respx.mock
    async def test_timeout_returns_network_error(self) -> None:
        """A timeout returns a network_error."""
        import httpx as _httpx

        respx.get(_API_URL).mock(side_effect=_httpx.TimeoutException("timeout"))

        result = await get_apartment_trades("11440", "202501")

        assert result["error"] == "network_error"

    async def test_missing_api_key_returns_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing API key returns a config_error."""
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

        result = await get_apartment_trades("11440", "202501")

        assert result["error"] == "config_error"
