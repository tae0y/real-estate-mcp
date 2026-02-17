"""Unit tests for the get_commercial_trade tool.

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server.parsers.trade import _parse_commercial_trade
from real_estate.mcp_server.tools.trade import get_commercial_trade

_XML_OK = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <buildingType>집합</buildingType>
        <buildingUse>판매시설</buildingUse>
        <landUse>상업지역</landUse>
        <umdNm>합정동</umdNm>
        <buildingAr>120.50</buildingAr>
        <floor>2</floor>
        <dealAmount>85,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>10</dealDay>
        <buildYear>2010</buildYear>
        <dealingGbn>중개거래</dealingGbn>
        <shareDealingType></shareDealingType>
        <cdealtype></cdealtype>
      </item>
      <item>
        <buildingType>일반</buildingType>
        <buildingUse>업무시설</buildingUse>
        <landUse>준주거지역</landUse>
        <umdNm>서교동</umdNm>
        <buildingAr>200.00</buildingAr>
        <floor>5</floor>
        <dealAmount>150,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>15</dealDay>
        <buildYear>2008</buildYear>
        <dealingGbn>직거래</dealingGbn>
        <shareDealingType>지분</shareDealingType>
        <cdealtype>O</cdealtype>
      </item>
    </items>
    <totalCount>1</totalCount>
  </body>
</response>"""

_XML_NO_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>03</resultCode><resultMsg>No Data</resultMsg></header>
  <body><items/><totalCount>0</totalCount></body>
</response>"""

_API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"


class TestParseCommercialTrade:
    """Unit tests for commercial trade XML parsing."""

    def test_cancelled_deal_excluded(self) -> None:
        """cdealtype=O item is excluded; 1 valid item returned."""
        items, error_code = _parse_commercial_trade(_XML_OK)
        assert error_code is None
        assert len(items) == 1

    def test_commercial_specific_fields_present(self) -> None:
        """building_type, building_use, land_use, building_ar are present."""
        items, _ = _parse_commercial_trade(_XML_OK)
        item = items[0]
        assert item["building_type"] == "집합"
        assert item["building_use"] == "판매시설"
        assert item["land_use"] == "상업지역"
        assert item["building_ar"] == 120.5

    def test_price_parsed(self) -> None:
        """price_10k is parsed correctly."""
        items, _ = _parse_commercial_trade(_XML_OK)
        assert items[0]["price_10k"] == 85000

    def test_share_dealing_included(self) -> None:
        """share_dealing field is present (empty string for non-share deals)."""
        items, _ = _parse_commercial_trade(_XML_OK)
        assert "share_dealing" in items[0]
        assert items[0]["share_dealing"] == ""

    def test_no_unit_name_field(self) -> None:
        """Commercial items do not have unit_name or apt_name."""
        items, _ = _parse_commercial_trade(_XML_OK)
        assert "unit_name" not in items[0]
        assert "apt_name" not in items[0]

    def test_error_code_on_no_data(self) -> None:
        """resultCode 03 returns error_code."""
        items, error_code = _parse_commercial_trade(_XML_NO_DATA)
        assert error_code == "03"
        assert items == []


class TestGetCommercialTrade:
    """Integration tests for the get_commercial_trade tool."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set a test API key environment variable."""
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "test-key")

    @respx.mock
    async def test_success_returns_items_and_summary(self) -> None:
        """A successful response returns items and summary."""
        respx.get(_API_URL).mock(return_value=Response(200, text=_XML_OK))

        result = await get_commercial_trade("11440", "202501")

        assert "error" not in result
        assert result["total_count"] == 1
        assert len(result["items"]) == 1
        assert result["summary"]["sample_count"] == 1

    @respx.mock
    async def test_no_data_returns_api_error(self) -> None:
        """No-data response returns api_error."""
        respx.get(_API_URL).mock(return_value=Response(200, text=_XML_NO_DATA))

        result = await get_commercial_trade("11440", "200001")

        assert result["error"] == "api_error"
        assert result["code"] == "03"

    async def test_missing_api_key_returns_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing API key returns config_error."""
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

        result = await get_commercial_trade("11440", "202501")

        assert result["error"] == "config_error"
