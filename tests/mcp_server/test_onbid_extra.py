"""Additional unit tests for Onbid tools added in server.py.

HTTP calls are mocked with respx so the real API is never called.
"""

from typing import Any

import pytest
import respx
from httpx import Response

from real_estate.mcp_server._helpers import _get_total_count_onbid
from real_estate.mcp_server.parsers.onbid import (
    _onbid_extract_items,
    _parse_onbid_thing_info_list_xml,
)
from real_estate.mcp_server.tools.onbid import (
    get_onbid_thing_info_list,
    get_public_auction_item_detail,
)

_ONBID_DETAIL_URL = "https://apis.data.go.kr/B010003/OnbidCltrBidRsltDtlSrvc/getCltrBidRsltDtl"
_ONBID_THING_LIST_URL = (
    "http://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr"
)

_THING_XML_OK = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <CLTR_NO>1120369</CLTR_NO>
        <PBCT_NO>9238013</PBCT_NO>
        <CLTR_NM>서울특별시 송파구 석촌동 242-15 짜투리 대지</CLTR_NM>
        <DPSL_MTD_CD>0001</DPSL_MTD_CD>
      </item>
    </items>
    <TotalCount>1</TotalCount>
  </body>
</response>
"""

_THING_XML_ERR = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>99</resultCode>
    <resultMsg>ERROR</resultMsg>
  </header>
  <body>
    <items/>
    <TotalCount>0</TotalCount>
  </body>
</response>
"""

_THING_XML_MULTI = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <CLTR_NO>111</CLTR_NO>
        <DPSL_MTD_CD>0001</DPSL_MTD_CD>
      </item>
      <item>
        <CLTR_NO>222</CLTR_NO>
        <DPSL_MTD_CD>0002</DPSL_MTD_CD>
      </item>
    </items>
    <TotalCount>2</TotalCount>
  </body>
</response>
"""

_THING_XML_EMPTY_SUCCESS = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items/>
    <totalcount>0</totalcount>
  </body>
</response>
"""


class TestOnbidHelpers:
    """Unit tests for small Onbid helper functions."""

    def test_get_total_count_onbid_accepts_lowercase_tag(self) -> None:
        xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<response><body><totalCount>2</totalCount></body></response>"""
        from defusedxml.ElementTree import fromstring as _fromstring

        root = _fromstring(xml_text)
        assert _get_total_count_onbid(root) == 2

    def test_onbid_extract_items_handles_dict_and_list(self) -> None:
        payload_dict: dict[str, Any] = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": {"item": {"a": 1}}},
            }
        }
        code, _body, items = _onbid_extract_items(payload_dict)
        assert code == "00"
        assert items == [{"a": 1}]

        payload_list: dict[str, Any] = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": {"item": [{"a": 1}, {"b": 2}]}},
            }
        }
        code, _body, items = _onbid_extract_items(payload_list)
        assert code == "00"
        assert items == [{"a": 1}, {"b": 2}]

    def test_onbid_extract_items_handles_flat_header_body(self) -> None:
        """B010003 actual API returns {"header": {...}, "body": {...}} without "response"."""
        payload: dict[str, Any] = {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
            "body": {
                "items": {"item": [{"cltrMngNo": "X"}]},
                "totalCount": 1,
            },
        }
        code, body, items = _onbid_extract_items(payload)
        assert code == "00"
        assert items == [{"cltrMngNo": "X"}]
        assert body.get("totalCount") == 1

    def test_onbid_extract_items_handles_result_wrapper(self) -> None:
        """API error responses may use {"result": {...}} instead of {"response": {...}}."""
        payload: dict[str, Any] = {
            "result": {
                "resultCode": "11",
                "resultMsg": "NO_MANDATORY_REQUEST_PARAMETERS_ERROR",
            }
        }
        code, body, items = _onbid_extract_items(payload)
        assert code == "11"
        assert items == []
        assert body.get("resultMsg") == "NO_MANDATORY_REQUEST_PARAMETERS_ERROR"


class TestParseOnbidThingInfoListXml:
    """Unit tests for Onbid ThingInfoInquireSvc XML parsing."""

    def test_ok_response_parses_items_and_total_count(self) -> None:
        items, total_count, error_code, error_message = _parse_onbid_thing_info_list_xml(
            _THING_XML_OK
        )
        assert error_code is None
        assert error_message is None
        assert total_count == 1
        assert len(items) == 1
        assert items[0]["CLTR_NO"] == "1120369"

    def test_error_response_returns_error_code_and_message(self) -> None:
        items, total_count, error_code, error_message = _parse_onbid_thing_info_list_xml(
            _THING_XML_ERR
        )
        assert items == []
        assert total_count == 0
        assert error_code == "99"
        assert error_message == "ERROR"

    def test_multiple_items_parsed(self) -> None:
        items, total_count, error_code, error_message = _parse_onbid_thing_info_list_xml(
            _THING_XML_MULTI
        )
        assert error_code is None
        assert total_count == 2
        assert len(items) == 2
        assert items[0]["CLTR_NO"] == "111"
        assert items[1]["CLTR_NO"] == "222"

    def test_empty_items_on_success_returns_empty_list(self) -> None:
        items, total_count, error_code, error_message = _parse_onbid_thing_info_list_xml(
            _THING_XML_EMPTY_SUCCESS
        )
        assert error_code is None
        assert total_count == 0
        assert items == []

    def test_totalcount_lowercase_tag_is_parsed(self) -> None:
        # _THING_XML_EMPTY_SUCCESS uses <totalcount> (all lowercase)
        items, total_count, error_code, _ = _parse_onbid_thing_info_list_xml(
            _THING_XML_EMPTY_SUCCESS
        )
        assert error_code is None
        assert total_count == 0  # not -1 or garbage


class TestGetPublicAuctionItemDetail:
    """Integration tests for get_public_auction_item_detail."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ONBID_API_KEY", "test-onbid-key")

    @respx.mock
    async def test_success_returns_items(self) -> None:
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
                "body": {
                    "pageNo": 1,
                    "numOfRows": 20,
                    "totalCount": 1,
                    "items": {"item": {"cltrMngNo": "X", "pbctCdtnNo": "1"}},
                },
            }
        }
        respx.get(_ONBID_DETAIL_URL).mock(return_value=Response(200, json=payload))

        result = await get_public_auction_item_detail("X", "1")

        assert "error" not in result
        assert result["total_count"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["cltrMngNo"] == "X"

    async def test_missing_required_fields_return_validation_error(self) -> None:
        result = await get_public_auction_item_detail("", "")
        assert result["error"] == "validation_error"


class TestGetOnbidThingInfoList:
    """Integration tests for get_onbid_thing_info_list."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ONBID_API_KEY", "test-onbid-key")

    @respx.mock
    async def test_success_returns_items(self) -> None:
        respx.get(_ONBID_THING_LIST_URL).mock(return_value=Response(200, text=_THING_XML_OK))

        result = await get_onbid_thing_info_list(page_no=1, num_of_rows=10, dpsl_mtd_cd="0001")

        assert "error" not in result
        assert result["total_count"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["DPSL_MTD_CD"] == "0001"

    @respx.mock
    async def test_api_error_returns_error_dict(self) -> None:
        respx.get(_ONBID_THING_LIST_URL).mock(return_value=Response(200, text=_THING_XML_ERR))

        result = await get_onbid_thing_info_list()

        assert result["error"] == "api_error"
        assert result["code"] == "99"

    async def test_page_no_zero_returns_validation_error(self) -> None:
        result = await get_onbid_thing_info_list(page_no=0)
        assert result["error"] == "validation_error"

    async def test_num_of_rows_zero_returns_validation_error(self) -> None:
        result = await get_onbid_thing_info_list(num_of_rows=0)
        assert result["error"] == "validation_error"

    async def test_missing_api_key_returns_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ONBID_API_KEY", raising=False)
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)
        result = await get_onbid_thing_info_list()
        assert result["error"] == "config_error"

    @respx.mock
    async def test_network_timeout_returns_error(self) -> None:
        import httpx as _httpx

        respx.get(_ONBID_THING_LIST_URL).mock(side_effect=_httpx.TimeoutException("timeout"))

        result = await get_onbid_thing_info_list()

        assert result["error"] == "network_error"
        assert "timed out" in result["message"]

    @respx.mock
    async def test_http_500_returns_network_error(self) -> None:
        respx.get(_ONBID_THING_LIST_URL).mock(return_value=Response(500))

        result = await get_onbid_thing_info_list()

        assert result["error"] == "network_error"
        assert "500" in result["message"]

    @respx.mock
    async def test_malformed_xml_returns_parse_error(self) -> None:
        respx.get(_ONBID_THING_LIST_URL).mock(return_value=Response(200, text="<not valid xml<<<"))

        result = await get_onbid_thing_info_list()

        assert result["error"] == "parse_error"

    @respx.mock
    async def test_multiple_items_returned(self) -> None:
        respx.get(_ONBID_THING_LIST_URL).mock(return_value=Response(200, text=_THING_XML_MULTI))

        result = await get_onbid_thing_info_list(page_no=1, num_of_rows=10)

        assert "error" not in result
        assert result["total_count"] == 2
        assert len(result["items"]) == 2
        assert result["items"][0]["CLTR_NO"] == "111"
        assert result["items"][1]["CLTR_NO"] == "222"

    @respx.mock
    async def test_optional_params_included_in_request_url(self) -> None:
        respx.get(_ONBID_THING_LIST_URL).mock(return_value=Response(200, text=_THING_XML_OK))

        await get_onbid_thing_info_list(sido="서울특별시", sgk="강남구", dpsl_mtd_cd="0001")

        called_url = str(respx.calls.last.request.url)
        assert "SIDO=" in called_url
        assert "SGK=" in called_url
        assert "DPSL_MTD_CD=0001" in called_url
