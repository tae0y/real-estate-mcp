"""Unit tests for the get_officetel_trades and get_officetel_rent tools.

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server.server import (
    _parse_officetel_rent,
    _parse_officetel_trades,
    get_officetel_rent,
    get_officetel_trades,
)

_XML_TRADE_OK = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <offiNm>마포 더리브</offiNm>
        <umdNm>합정동</umdNm>
        <excluUseAr>33.00</excluUseAr>
        <floor>8</floor>
        <dealAmount>35,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>5</dealDay>
        <buildYear>2018</buildYear>
        <dealingGbn>중개거래</dealingGbn>
        <cdealType></cdealType>
      </item>
      <item>
        <offiNm>마포 더리브</offiNm>
        <umdNm>합정동</umdNm>
        <excluUseAr>45.00</excluUseAr>
        <floor>12</floor>
        <dealAmount>50,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>10</dealDay>
        <buildYear>2018</buildYear>
        <dealingGbn>중개거래</dealingGbn>
        <cdealType>O</cdealType>
      </item>
    </items>
    <totalCount>1</totalCount>
  </body>
</response>"""

_XML_RENT_OK = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <offiNm>마포 더리브</offiNm>
        <umdNm>합정동</umdNm>
        <excluUseAr>33.00</excluUseAr>
        <floor>8</floor>
        <deposit>5,000</deposit>
        <monthlyRent>100</monthlyRent>
        <contractType>신규</contractType>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>5</dealDay>
        <buildYear>2018</buildYear>
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

_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade"
_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"


class TestParseOfficetelTrades:
    """Unit tests for officetel trade XML parsing."""

    def test_normal_response_excludes_cancelled(self) -> None:
        """cdealType=O item is excluded; 1 valid item returned."""
        items, error_code = _parse_officetel_trades(_XML_TRADE_OK)
        assert error_code is None
        assert len(items) == 1

    def test_unit_name_field_used(self) -> None:
        """unit_name (from offiNm) is present instead of apt_name."""
        items, _ = _parse_officetel_trades(_XML_TRADE_OK)
        assert "unit_name" in items[0]
        assert items[0]["unit_name"] == "마포 더리브"

    def test_price_parsed(self) -> None:
        """price_10k is parsed correctly from comma-formatted string."""
        items, _ = _parse_officetel_trades(_XML_TRADE_OK)
        assert items[0]["price_10k"] == 35000

    def test_error_code_on_no_data(self) -> None:
        """resultCode 03 returns error_code and empty items."""
        items, error_code = _parse_officetel_trades(_XML_NO_DATA)
        assert error_code == "03"
        assert items == []


class TestParseOfficetelRent:
    """Unit tests for officetel rent XML parsing."""

    def test_normal_response_returns_item(self) -> None:
        """Normal XML returns 1 rent item."""
        items, error_code = _parse_officetel_rent(_XML_RENT_OK)
        assert error_code is None
        assert len(items) == 1

    def test_deposit_and_rent_parsed(self) -> None:
        """deposit_10k and monthly_rent_10k are parsed correctly."""
        items, _ = _parse_officetel_rent(_XML_RENT_OK)
        assert items[0]["deposit_10k"] == 5000
        assert items[0]["monthly_rent_10k"] == 100


class TestGetOfficetelTools:
    """Integration tests for officetel trade and rent tools."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set a test API key environment variable."""
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "test-key")

    @respx.mock
    async def test_trade_success(self) -> None:
        """Officetel trade tool returns items and summary on success."""
        respx.get(_TRADE_URL).mock(return_value=Response(200, text=_XML_TRADE_OK))

        result = await get_officetel_trades("11440", "202501")

        assert "error" not in result
        assert result["total_count"] == 1
        assert len(result["items"]) == 1

    @respx.mock
    async def test_rent_success(self) -> None:
        """Officetel rent tool returns items and summary on success."""
        respx.get(_RENT_URL).mock(return_value=Response(200, text=_XML_RENT_OK))

        result = await get_officetel_rent("11440", "202501")

        assert "error" not in result
        assert len(result["items"]) == 1
        assert "deposit_10k" in result["items"][0]

    @respx.mock
    async def test_trade_no_data_error(self) -> None:
        """No-data response returns api_error for trade tool."""
        respx.get(_TRADE_URL).mock(return_value=Response(200, text=_XML_NO_DATA))

        result = await get_officetel_trades("11440", "200001")

        assert result["error"] == "api_error"

    async def test_missing_key_config_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing API key returns config_error."""
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

        result = await get_officetel_trades("11440", "202501")

        assert result["error"] == "config_error"
