"""Unit tests for the get_public_auction_items tool (Onbid next-gen, B010003).

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server.server import get_public_auction_items

_ONBID_URL = (
    "http://apis.data.go.kr/B010003/OnbidCltrBidRsltListSrvc/getCltrBidRsltList"
)


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

        result = await get_public_auction_items(page_no=1, num_of_rows=20)

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

        result = await get_public_auction_items()

        assert result["error"] == "api_error"
        assert result["code"] == "99"

    async def test_missing_key_returns_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ONBID_API_KEY", raising=False)
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

        result = await get_public_auction_items()

        assert result["error"] == "config_error"

    async def test_invalid_page_returns_validation_error(self) -> None:
        result = await get_public_auction_items(page_no=0)
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

        result = await get_public_auction_items(page_no=1, num_of_rows=1)

        assert "error" not in result
        assert result["total_count"] == 1
        assert result["items"][0]["cltrMngNo"] == "X"

    @respx.mock
    async def test_total_count_parse_error_falls_back_to_zero(self) -> None:
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
                "body": {"pageNo": 1, "numOfRows": 20, "totalCount": "nope", "items": {}},
            }
        }
        respx.get(_ONBID_URL).mock(return_value=Response(200, json=payload))

        result = await get_public_auction_items()

        assert "error" not in result
        assert result["total_count"] == 0
