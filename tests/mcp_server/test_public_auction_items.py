"""Unit tests for the get_public_auction_items tool (Onbid next-gen, B010003).

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server.tools.onbid import get_public_auction_items

_ONBID_URL = "https://apis.data.go.kr/B010003/OnbidCltrBidRsltListSrvc/getCltrBidRsltList"

# Shared required args for the API.
_REQ = {
    "opbd_dt_start": "20240101",
    "opbd_dt_end": "20241231",
    "cltr_type_cd": "0001",
    "prpt_div_cd": "0007",
    "dsps_mthod_cd": "0001",
    "bid_div_cd": "0001",
}


class TestGetPublicAuctionItems:
    """Integration tests for get_public_auction_items."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ONBID_API_KEY", "test-onbid-key")

    @respx.mock
    async def test_success_extracts_items(self) -> None:
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
                "body": {
                    "pageNo": 1,
                    "numOfRows": 20,
                    "totalCount": 2,
                    "items": {
                        "item": [
                            {"cltrMngNo": "2024-1100-084555", "pbctCdtnNo": 3621804},
                            {"cltrMngNo": "2024-1100-000001", "pbctCdtnNo": 1},
                        ]
                    },
                },
            }
        }
        respx.get(_ONBID_URL).mock(return_value=Response(200, json=payload))

        result = await get_public_auction_items(**_REQ, page_no=1, num_of_rows=20)

        assert "error" not in result
        assert result["total_count"] == 2
        assert result["page_no"] == 1
        assert len(result["items"]) == 2
        assert result["items"][0]["cltrMngNo"] == "2024-1100-084555"

    @respx.mock
    async def test_api_error_returns_error_dict(self) -> None:
        payload = {
            "response": {
                "header": {"resultCode": "99", "resultMsg": "ERROR"},
                "body": {"totalCount": 0, "items": {"item": []}},
            }
        }
        respx.get(_ONBID_URL).mock(return_value=Response(200, json=payload))

        result = await get_public_auction_items(**_REQ)

        assert result["error"] == "api_error"
        assert result["code"] == "99"

    async def test_missing_key_returns_config_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ONBID_API_KEY", raising=False)
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

        result = await get_public_auction_items(**_REQ)

        assert result["error"] == "config_error"

    async def test_invalid_page_returns_validation_error(self) -> None:
        result = await get_public_auction_items(**_REQ, page_no=0)
        assert result["error"] == "validation_error"

    @respx.mock
    async def test_flat_payload_without_response_wrapper(self) -> None:
        payload = {
            "resultCode": "00",
            "resultMsg": "NORMAL SERVICE",
            "pageNo": 1,
            "numOfRows": 1,
            "totalCount": "1",
            "items": [{"cltrMngNo": "X", "pbctCdtnNo": 1}],
        }
        respx.get(_ONBID_URL).mock(return_value=Response(200, json=payload))

        result = await get_public_auction_items(**_REQ, page_no=1, num_of_rows=1)

        assert "error" not in result
        assert result["total_count"] == 1
        assert result["items"][0]["cltrMngNo"] == "X"

    @respx.mock
    async def test_flat_header_body_response(self) -> None:
        """Real B010003 API returns {"header": {...}, "body": {...}} without "response"."""
        payload = {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
            "body": {
                "pageNo": 1,
                "numOfRows": 2,
                "totalCount": 1,
                "items": {"item": [{"cltrMngNo": "2022-06282-002", "pbctCdtnNo": 5005891}]},
            },
        }
        respx.get(_ONBID_URL).mock(return_value=Response(200, json=payload))

        result = await get_public_auction_items(**_REQ, page_no=1, num_of_rows=2)

        assert "error" not in result
        assert result["total_count"] == 1
        assert result["items"][0]["cltrMngNo"] == "2022-06282-002"

    @respx.mock
    async def test_total_count_parse_error_falls_back_to_zero(self) -> None:
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
                "body": {"pageNo": 1, "numOfRows": 20, "totalCount": "nope", "items": {}},
            }
        }
        respx.get(_ONBID_URL).mock(return_value=Response(200, json=payload))

        result = await get_public_auction_items(**_REQ)

        assert "error" not in result
        assert result["total_count"] == 0

    # --- New: opbd_dt required validation ---

    async def test_empty_opbd_dt_start_returns_validation_error(self) -> None:
        result = await get_public_auction_items(
            opbd_dt_start="",
            opbd_dt_end="20241231",
            cltr_type_cd="0001",
            prpt_div_cd="0007",
            dsps_mthod_cd="0001",
            bid_div_cd="0001",
        )
        assert result["error"] == "validation_error"
        assert "opbd_dt_start" in result["message"]

    async def test_empty_opbd_dt_end_returns_validation_error(self) -> None:
        result = await get_public_auction_items(
            opbd_dt_start="20240101",
            opbd_dt_end="  ",
            cltr_type_cd="0001",
            prpt_div_cd="0007",
            dsps_mthod_cd="0001",
            bid_div_cd="0001",
        )
        assert result["error"] == "validation_error"
        assert "opbd_dt_end" in result["message"]

    # --- New: additional required param validation ---

    async def test_empty_cltr_type_cd_returns_validation_error(self) -> None:
        result = await get_public_auction_items(
            opbd_dt_start="20240101",
            opbd_dt_end="20241231",
            cltr_type_cd="",
            prpt_div_cd="0007",
            dsps_mthod_cd="0001",
            bid_div_cd="0001",
        )
        assert result["error"] == "validation_error"
        assert "cltr_type_cd" in result["message"]

    async def test_empty_prpt_div_cd_returns_validation_error(self) -> None:
        result = await get_public_auction_items(
            opbd_dt_start="20240101",
            opbd_dt_end="20241231",
            cltr_type_cd="0001",
            prpt_div_cd="  ",
            dsps_mthod_cd="0001",
            bid_div_cd="0001",
        )
        assert result["error"] == "validation_error"
        assert "prpt_div_cd" in result["message"]

    async def test_empty_dsps_mthod_cd_returns_validation_error(self) -> None:
        result = await get_public_auction_items(
            opbd_dt_start="20240101",
            opbd_dt_end="20241231",
            cltr_type_cd="0001",
            prpt_div_cd="0007",
            dsps_mthod_cd="",
            bid_div_cd="0001",
        )
        assert result["error"] == "validation_error"
        assert "dsps_mthod_cd" in result["message"]

    async def test_empty_bid_div_cd_returns_validation_error(self) -> None:
        result = await get_public_auction_items(
            opbd_dt_start="20240101",
            opbd_dt_end="20241231",
            cltr_type_cd="0001",
            prpt_div_cd="0007",
            dsps_mthod_cd="0001",
            bid_div_cd="",
        )
        assert result["error"] == "validation_error"
        assert "bid_div_cd" in result["message"]

    # --- New: "result" wrapper error ---

    @respx.mock
    async def test_result_wrapper_error_returns_api_error(self) -> None:
        """B010003 returns {"result": {"resultCode": "11", ...}} on missing params."""
        payload = {
            "result": {
                "resultCode": "11",
                "resultMsg": "NO_MANDATORY_REQUEST_PARAMETERS_ERROR",
            }
        }
        respx.get(_ONBID_URL).mock(return_value=Response(200, json=payload))

        result = await get_public_auction_items(**_REQ)

        assert result["error"] == "api_error"
        assert result["code"] == "11"
        assert "NO_MANDATORY_REQUEST_PARAMETERS_ERROR" in result["message"]

