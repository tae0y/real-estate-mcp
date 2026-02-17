"""Unit tests for the get_apartment_rent tool.

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server._helpers import _build_rent_summary
from real_estate.mcp_server.parsers.rent import _parse_apt_rent
from real_estate.mcp_server.tools.rent import get_apartment_rent

_XML_OK = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <aptNm>마포래미안</aptNm>
        <umdNm>합정동</umdNm>
        <excluUseAr>84.97</excluUseAr>
        <floor>12</floor>
        <deposit>50,000</deposit>
        <monthlyRent>0</monthlyRent>
        <contractType>신규</contractType>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>10</dealDay>
        <buildYear>2014</buildYear>
        <cdealType></cdealType>
      </item>
      <item>
        <aptNm>마포자이</aptNm>
        <umdNm>아현동</umdNm>
        <excluUseAr>59.00</excluUseAr>
        <floor>5</floor>
        <deposit>20,000</deposit>
        <monthlyRent>80</monthlyRent>
        <contractType>신규</contractType>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>15</dealDay>
        <buildYear>2010</buildYear>
        <cdealType></cdealType>
      </item>
      <item>
        <aptNm>취소단지</aptNm>
        <umdNm>공덕동</umdNm>
        <excluUseAr>84.00</excluUseAr>
        <floor>3</floor>
        <deposit>45,000</deposit>
        <monthlyRent>0</monthlyRent>
        <contractType>신규</contractType>
        <dealYear>2025</dealYear>
        <dealMonth>1</dealMonth>
        <dealDay>5</dealDay>
        <buildYear>2015</buildYear>
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
  <body><items/><totalCount>0</totalCount></body>
</response>"""

_API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"


class TestParseAptRent:
    """Unit tests for apartment rent XML parsing logic."""

    def test_normal_response_returns_items(self) -> None:
        """Normal XML returns 2 items after excluding the cancelled deal."""
        items, error_code = _parse_apt_rent(_XML_OK)
        assert error_code is None
        assert len(items) == 2

    def test_deposit_parsed_correctly(self) -> None:
        """deposit_10k is parsed from comma-formatted string."""
        items, _ = _parse_apt_rent(_XML_OK)
        assert items[0]["deposit_10k"] == 50000

    def test_monthly_rent_zero_for_jeonse(self) -> None:
        """monthlyRent=0 (전세) is stored as 0."""
        items, _ = _parse_apt_rent(_XML_OK)
        assert items[0]["monthly_rent_10k"] == 0

    def test_monthly_rent_parsed_for_wolse(self) -> None:
        """Non-zero monthlyRent (월세) is parsed correctly."""
        items, _ = _parse_apt_rent(_XML_OK)
        assert items[1]["monthly_rent_10k"] == 80

    def test_cancelled_deal_excluded(self) -> None:
        """Items with cdealType=O are not included."""
        items, _ = _parse_apt_rent(_XML_OK)
        names = [it["unit_name"] for it in items]
        assert "취소단지" not in names

    def test_error_code_returned_on_no_data(self) -> None:
        """A resultCode other than 000 returns error_code."""
        items, error_code = _parse_apt_rent(_XML_NO_DATA)
        assert error_code == "03"
        assert items == []


class TestBuildRentSummary:
    """Unit tests for rent summary statistics calculation."""

    def test_summary_values(self) -> None:
        """Median deposit, min, max, and avg monthly rent are correct."""
        items = [
            {"deposit_10k": 50000, "monthly_rent_10k": 0},
            {"deposit_10k": 20000, "monthly_rent_10k": 80},
        ]
        summary = _build_rent_summary(items)
        assert summary["median_deposit_10k"] == 35000
        assert summary["min_deposit_10k"] == 20000
        assert summary["max_deposit_10k"] == 50000
        assert summary["monthly_rent_avg_10k"] == 40
        assert summary["jeonse_ratio_pct"] is None

    def test_empty_items_returns_zeros(self) -> None:
        """An empty list returns all zeros."""
        summary = _build_rent_summary([])
        assert summary["sample_count"] == 0
        assert summary["median_deposit_10k"] == 0


class TestGetApartmentRent:
    """Integration tests for the get_apartment_rent tool."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set a test API key environment variable."""
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "test-key")

    @respx.mock
    async def test_success_returns_items_and_summary(self) -> None:
        """A successful response returns items and rent summary."""
        respx.get(_API_URL).mock(return_value=Response(200, text=_XML_OK))

        result = await get_apartment_rent("11440", "202501")

        assert "error" not in result
        assert result["total_count"] == 2
        assert len(result["items"]) == 2
        assert "deposit_10k" in result["items"][0]
        assert result["summary"]["sample_count"] == 2

    @respx.mock
    async def test_no_data_returns_api_error(self) -> None:
        """A no-data response returns an error dict."""
        respx.get(_API_URL).mock(return_value=Response(200, text=_XML_NO_DATA))

        result = await get_apartment_rent("11440", "200001")

        assert result["error"] == "api_error"
        assert result["code"] == "03"

    async def test_missing_api_key_returns_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing API key returns a config_error."""
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

        result = await get_apartment_rent("11440", "202501")

        assert result["error"] == "config_error"
