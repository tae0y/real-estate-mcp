"""Unit tests for villa (연립다세대) and single house (단독/다가구) tools.

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server.server import (
    _parse_single_house_rent,
    _parse_single_house_trades,
    _parse_villa_trades,
    get_single_house_rent,
    get_single_house_trades,
    get_villa_trades,
)

# ---------------------------------------------------------------------------
# Villa (연립다세대) XML fixtures
# ---------------------------------------------------------------------------

_XML_VILLA_OK = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <mhouseNm>신촌빌라</mhouseNm>
        <umdNm>신촌동</umdNm>
        <houseType>다세대</houseType>
        <excluUseAr>49.50</excluUseAr>
        <floor>3</floor>
        <dealAmount>25,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>8</dealDay>
        <buildYear>2005</buildYear>
        <dealingGbn>중개거래</dealingGbn>
        <cdealType></cdealType>
      </item>
      <item>
        <mhouseNm>취소빌라</mhouseNm>
        <umdNm>신촌동</umdNm>
        <houseType>연립</houseType>
        <excluUseAr>60.00</excluUseAr>
        <floor>2</floor>
        <dealAmount>30,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>12</dealDay>
        <buildYear>2003</buildYear>
        <dealingGbn>중개거래</dealingGbn>
        <cdealType>O</cdealType>
      </item>
    </items>
    <totalCount>1</totalCount>
  </body>
</response>"""

# ---------------------------------------------------------------------------
# Single house (단독/다가구) XML fixtures
# ---------------------------------------------------------------------------

_XML_SINGLE_TRADE_OK = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <umdNm>연남동</umdNm>
        <houseType>단독</houseType>
        <totalFloorAr>120.00</totalFloorAr>
        <dealAmount>80,000</dealAmount>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>20</dealDay>
        <buildYear>1995</buildYear>
        <dealingGbn>중개거래</dealingGbn>
        <cdealType></cdealType>
        <jibun></jibun>
      </item>
    </items>
    <totalCount>1</totalCount>
  </body>
</response>"""

_XML_SINGLE_RENT_OK = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <umdNm>연남동</umdNm>
        <houseType>다가구</houseType>
        <totalFloorAr>85.00</totalFloorAr>
        <deposit>15,000</deposit>
        <monthlyRent>60</monthlyRent>
        <contractType>신규</contractType>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>15</dealDay>
        <buildYear>2000</buildYear>
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

_VILLA_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"
_SINGLE_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade"
_SINGLE_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent"


# ---------------------------------------------------------------------------
# Villa parse tests
# ---------------------------------------------------------------------------


class TestParseVillaTrades:
    """Unit tests for villa (연립다세대) trade XML parsing."""

    def test_cancelled_deal_excluded(self) -> None:
        """cdealType=O item is excluded; 1 valid item returned."""
        items, error_code = _parse_villa_trades(_XML_VILLA_OK)
        assert error_code is None
        assert len(items) == 1

    def test_house_type_included(self) -> None:
        """house_type field is present and correctly parsed."""
        items, _ = _parse_villa_trades(_XML_VILLA_OK)
        assert items[0]["house_type"] == "다세대"

    def test_unit_name_from_mhouse_nm(self) -> None:
        """unit_name is populated from mhouseNm."""
        items, _ = _parse_villa_trades(_XML_VILLA_OK)
        assert items[0]["unit_name"] == "신촌빌라"

    def test_error_code_on_no_data(self) -> None:
        """resultCode 03 returns error_code."""
        items, error_code = _parse_villa_trades(_XML_NO_DATA)
        assert error_code == "03"
        assert items == []


# ---------------------------------------------------------------------------
# Single house parse tests
# ---------------------------------------------------------------------------


class TestParseSingleHouseTrades:
    """Unit tests for detached/multi-unit house trade XML parsing."""

    def test_normal_response_returns_item(self) -> None:
        """Normal XML returns 1 item."""
        items, error_code = _parse_single_house_trades(_XML_SINGLE_TRADE_OK)
        assert error_code is None
        assert len(items) == 1

    def test_unit_name_is_empty_string(self) -> None:
        """unit_name is always empty string (not provided by this API)."""
        items, _ = _parse_single_house_trades(_XML_SINGLE_TRADE_OK)
        assert items[0]["unit_name"] == ""

    def test_floor_is_zero(self) -> None:
        """floor is always 0 (not applicable for detached houses)."""
        items, _ = _parse_single_house_trades(_XML_SINGLE_TRADE_OK)
        assert items[0]["floor"] == 0

    def test_area_from_total_floor_ar(self) -> None:
        """area_sqm uses totalFloorAr (gross floor area)."""
        items, _ = _parse_single_house_trades(_XML_SINGLE_TRADE_OK)
        assert items[0]["area_sqm"] == 120.0

    def test_empty_jibun_handled(self) -> None:
        """Empty jibun field does not cause an error."""
        items, _ = _parse_single_house_trades(_XML_SINGLE_TRADE_OK)
        assert len(items) == 1  # no exception raised

    def test_house_type_included(self) -> None:
        """house_type field is parsed correctly."""
        items, _ = _parse_single_house_trades(_XML_SINGLE_TRADE_OK)
        assert items[0]["house_type"] == "단독"


class TestParseSingleHouseRent:
    """Unit tests for detached/multi-unit house rent XML parsing."""

    def test_normal_response_returns_item(self) -> None:
        """Normal XML returns 1 rent item."""
        items, error_code = _parse_single_house_rent(_XML_SINGLE_RENT_OK)
        assert error_code is None
        assert len(items) == 1

    def test_deposit_and_rent_parsed(self) -> None:
        """deposit_10k and monthly_rent_10k are parsed correctly."""
        items, _ = _parse_single_house_rent(_XML_SINGLE_RENT_OK)
        assert items[0]["deposit_10k"] == 15000
        assert items[0]["monthly_rent_10k"] == 60

    def test_unit_name_is_empty_string(self) -> None:
        """unit_name is always empty string."""
        items, _ = _parse_single_house_rent(_XML_SINGLE_RENT_OK)
        assert items[0]["unit_name"] == ""


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestVillaSingleHouseTools:
    """Integration tests for villa and single house tools."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set a test API key environment variable."""
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "test-key")

    @respx.mock
    async def test_villa_trades_success(self) -> None:
        """Villa trade tool returns items and summary on success."""
        respx.get(_VILLA_URL).mock(return_value=Response(200, text=_XML_VILLA_OK))

        result = await get_villa_trades("11440", "202501")

        assert "error" not in result
        assert len(result["items"]) == 1
        assert result["items"][0]["house_type"] == "다세대"

    @respx.mock
    async def test_single_house_trades_success(self) -> None:
        """Single house trade tool returns items and summary on success."""
        respx.get(_SINGLE_TRADE_URL).mock(return_value=Response(200, text=_XML_SINGLE_TRADE_OK))

        result = await get_single_house_trades("11440", "202501")

        assert "error" not in result
        assert len(result["items"]) == 1
        assert result["items"][0]["unit_name"] == ""

    @respx.mock
    async def test_single_house_rent_success(self) -> None:
        """Single house rent tool returns items and summary on success."""
        respx.get(_SINGLE_RENT_URL).mock(return_value=Response(200, text=_XML_SINGLE_RENT_OK))

        result = await get_single_house_rent("11440", "202501")

        assert "error" not in result
        assert len(result["items"]) == 1
        assert "deposit_10k" in result["items"][0]

    @respx.mock
    async def test_villa_no_data_error(self) -> None:
        """No-data response returns api_error."""
        respx.get(_VILLA_URL).mock(return_value=Response(200, text=_XML_NO_DATA))

        result = await get_villa_trades("11440", "200001")

        assert result["error"] == "api_error"

    async def test_missing_key_config_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing API key returns config_error."""
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

        result = await get_villa_trades("11440", "202501")

        assert result["error"] == "config_error"
