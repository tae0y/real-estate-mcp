"""Additional unit tests for Onbid tools added in server.py.

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server.server import (
    _get_total_count_onbid,
    _onbid_extract_items,
    _parse_onbid_thing_info_list_xml,
    get_onbid_thing_info_list,
    get_public_auction_item_detail,
)

_ONBID_DETAIL_URL = (
    "http://apis.data.go.kr/B010003/OnbidCltrBidRsltDtlSrvc/getCltrBidRsltDtl"
)
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


class TestOnbidHelpers:
    """Unit tests for small Onbid helper functions."""

    def test_get_total_count_onbid_accepts_lowercase_tag(self) -> None:
        xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<response><body><totalCount>2</totalCount></body></response>"""
        from defusedxml.ElementTree import fromstring as _fromstring

        root = _fromstring(xml_text)
        assert _get_total_count_onbid(root) == 2

    def test_onbid_extract_items_handles_dict_and_list(self) -> None:
        payload_dict = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": {"item": {"a": 1}}},
            }
        }
        code, _body, items = _onbid_extract_items(payload_dict)
        assert code == "00"
        assert items == [{"a": 1}]

        payload_list = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": {"item": [{"a": 1}, {"b": 2}]}},
            }
        }
        code, _body, items = _onbid_extract_items(payload_list)
        assert code == "00"
        assert items == [{"a": 1}, {"b": 2}]


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
