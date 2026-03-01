"""Unit tests for OnbidCodeInfoInquireSvc tools.

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server.parsers.onbid import _parse_onbid_code_info_xml
from real_estate.mcp_server.tools.onbid import (
    get_onbid_addr1_info,
    get_onbid_addr2_info,
    get_onbid_addr3_info,
    get_onbid_bottom_code_info,
    get_onbid_dtl_addr_info,
    get_onbid_middle_code_info,
    get_onbid_top_code_info,
)

_TOP_URL = (
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidTopCodeInfo"
)
_MIDDLE_URL = (
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidMiddleCodeInfo"
)
_ADDR1_URL = (
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidAddr1Info"
)
_ADDR2_URL = (
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidAddr2Info"
)
_ADDR3_URL = (
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidAddr3Info"
)
_DTL_ADDR_URL = (
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidDtlAddrInfo"
)
_BOTTOM_URL = (
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidBottomCodeInfo"
)

_XML_OK_TOP = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <CTGR_ID>10000</CTGR_ID>
        <CTGR_NM>부동산</CTGR_NM>
        <CTGR_HIRK_ID>1</CTGR_HIRK_ID>
        <CTGR_HIRK_NM>ONBID</CTGR_HIRK_NM>
      </item>
    </items>
    <totalCount>1</totalCount>
    <pageNo>1</pageNo>
    <numOfRows>10</numOfRows>
  </body>
</response>
"""

_XML_ERR = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>99</resultCode>
    <resultMsg>ERROR</resultMsg>
  </header>
  <body>
    <items/>
    <totalCount>0</totalCount>
  </body>
</response>
"""

_XML_OK_ADDR1 = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item><ADDR1>서울특별시</ADDR1></item>
      <item><ADDR1>경기도</ADDR1></item>
    </items>
    <TotalCount>2</TotalCount>
  </body>
</response>
"""

_XML_OK_ADDR2 = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item><ADDR2>강남구</ADDR2></item>
    </items>
    <totalCount>1</totalCount>
  </body>
</response>
"""

_XML_OK_ADDR3 = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item><ADDR3>삼성</ADDR3></item>
    </items>
    <TotalCount>1</TotalCount>
  </body>
</response>
"""

_XML_OK_DTL_ADDR = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item><DTL_ADDR>삼성동 1-1</DTL_ADDR></item>
    </items>
    <TotalCount>1</TotalCount>
  </body>
</response>
"""

_XML_OK_BOTTOM = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <CTGR_ID>10101</CTGR_ID>
        <CTGR_NM>전</CTGR_NM>
        <CTGR_HIRK_ID>10100</CTGR_HIRK_ID>
        <CTGR_HIRK_NM>토지</CTGR_HIRK_NM>
      </item>
    </items>
    <totalCount>1</totalCount>
  </body>
</response>
"""


class TestParseOnbidCodeInfoXml:
    """Unit tests for parsing code lookup XML."""

    def test_parse_ok_returns_items(self) -> None:
        items, total_count, error_code, error_message = _parse_onbid_code_info_xml(_XML_OK_TOP)
        assert error_code is None
        assert error_message is None
        assert total_count == 1
        assert items[0]["CTGR_ID"] == "10000"

    def test_parse_error_returns_error_code(self) -> None:
        items, total_count, error_code, error_message = _parse_onbid_code_info_xml(_XML_ERR)
        assert items == []
        assert total_count == 0
        assert error_code == "99"
        assert error_message == "ERROR"


class TestOnbidCodeLookup:
    """Integration tests for code lookup tools."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ONBID_API_KEY", "test-onbid-key")

    @respx.mock
    async def test_top_code_success(self) -> None:
        respx.get(_TOP_URL).mock(return_value=Response(200, text=_XML_OK_TOP))

        result = await get_onbid_top_code_info(page_no=1, num_of_rows=10)

        assert "error" not in result
        assert result["total_count"] == 1
        assert result["items"][0]["CTGR_ID"] == "10000"

    @respx.mock
    async def test_middle_code_api_error(self) -> None:
        respx.get(_MIDDLE_URL).mock(return_value=Response(200, text=_XML_ERR))

        result = await get_onbid_middle_code_info("10000", page_no=1, num_of_rows=10)

        assert result["error"] == "api_error"
        assert result["code"] == "99"

    @respx.mock
    async def test_addr1_success(self) -> None:
        respx.get(_ADDR1_URL).mock(return_value=Response(200, text=_XML_OK_ADDR1))

        result = await get_onbid_addr1_info(page_no=1, num_of_rows=10)

        assert "error" not in result
        assert result["total_count"] == 2
        assert result["items"][0]["ADDR1"] == "서울특별시"

    @respx.mock
    async def test_addr2_addr3_dtl_addr_success(self) -> None:
        respx.get(_ADDR2_URL).mock(return_value=Response(200, text=_XML_OK_ADDR2))
        respx.get(_ADDR3_URL).mock(return_value=Response(200, text=_XML_OK_ADDR3))
        respx.get(_DTL_ADDR_URL).mock(return_value=Response(200, text=_XML_OK_DTL_ADDR))

        result2 = await get_onbid_addr2_info("서울특별시", page_no=1, num_of_rows=10)
        assert "error" not in result2
        assert result2["items"][0]["ADDR2"] == "강남구"

        result3 = await get_onbid_addr3_info("강남구", page_no=1, num_of_rows=10)
        assert "error" not in result3
        assert result3["items"][0]["ADDR3"] == "삼성"

        result4 = await get_onbid_dtl_addr_info("삼성", page_no=1, num_of_rows=10)
        assert "error" not in result4
        assert result4["items"][0]["DTL_ADDR"] == "삼성동 1-1"

    @respx.mock
    async def test_bottom_code_success(self) -> None:
        respx.get(_BOTTOM_URL).mock(return_value=Response(200, text=_XML_OK_BOTTOM))

        result = await get_onbid_bottom_code_info("10100", page_no=1, num_of_rows=10)

        assert "error" not in result
        assert result["items"][0]["CTGR_ID"] == "10101"

    async def test_validation_error(self) -> None:
        result = await get_onbid_top_code_info(page_no=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_top_code_info(num_of_rows=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_middle_code_info("")
        assert result["error"] == "validation_error"

        result = await get_onbid_middle_code_info("10000", page_no=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_middle_code_info("10000", num_of_rows=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_bottom_code_info("")
        assert result["error"] == "validation_error"

        result = await get_onbid_bottom_code_info("10100", page_no=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_bottom_code_info("10100", num_of_rows=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_addr1_info(page_no=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_addr1_info(num_of_rows=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_addr2_info("")
        assert result["error"] == "validation_error"

        result = await get_onbid_addr2_info("서울특별시", page_no=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_addr2_info("서울특별시", num_of_rows=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_addr3_info("")
        assert result["error"] == "validation_error"

        result = await get_onbid_addr3_info("강남구", page_no=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_addr3_info("강남구", num_of_rows=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_dtl_addr_info("")
        assert result["error"] == "validation_error"

        result = await get_onbid_dtl_addr_info("삼성", page_no=0)
        assert result["error"] == "validation_error"

        result = await get_onbid_dtl_addr_info("삼성", num_of_rows=0)
        assert result["error"] == "validation_error"
