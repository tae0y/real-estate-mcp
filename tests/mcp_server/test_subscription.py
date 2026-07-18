"""Unit tests for Applyhome (odcloud) subscription tools.

HTTP calls are mocked with respx so the real API is never called.
"""

import pytest
import respx
from httpx import Response

from real_estate.mcp_server.tools.subscription import (
    get_apt_subscription_info,
    get_apt_subscription_results,
)

_INFO_URL = "https://api.odcloud.kr/api/15101046/v1/uddi:14a46595-03dd-47d3-a418-d64e52820598"
_STAT_BASE_URL = "https://api.odcloud.kr/api/ApplyhomeStatSvc/v1"


class TestGetAptSubscriptionInfo:
    """Integration tests for get_apt_subscription_info."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ODCLOUD_API_KEY", "test-odcloud-key")
        monkeypatch.delenv("ODCLOUD_SERVICE_KEY", raising=False)

    @respx.mock
    async def test_success_maps_to_standard_response(self) -> None:
        payload = {
            "currentCount": 2,
            "data": [{"공고번호": "A-1"}, {"공고번호": "A-2"}],
            "matchCount": 2,
            "page": 1,
            "perPage": 100,
            "totalCount": 2,
        }
        respx.get(_INFO_URL).mock(return_value=Response(200, json=payload))

        result = await get_apt_subscription_info(page=1, per_page=100)

        assert "error" not in result
        assert result["total_count"] == 2
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["per_page"] == 100

    async def test_missing_key_returns_config_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ODCLOUD_API_KEY", raising=False)
        monkeypatch.delenv("ODCLOUD_SERVICE_KEY", raising=False)
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

        result = await get_apt_subscription_info()

        assert result["error"] == "config_error"

    async def test_invalid_page_returns_validation_error(self) -> None:
        result = await get_apt_subscription_info(page=0)
        assert result["error"] == "validation_error"

    @respx.mock
    async def test_timeout_returns_network_error(self) -> None:
        import httpx as _httpx

        respx.get(_INFO_URL).mock(side_effect=_httpx.TimeoutException("timeout"))

        result = await get_apt_subscription_info()

        assert result["error"] == "network_error"

    @respx.mock
    async def test_service_key_mode_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ODCLOUD_API_KEY", raising=False)
        monkeypatch.setenv("ODCLOUD_SERVICE_KEY", "test-service-key")

        payload = {
            "currentCount": 0,
            "data": [],
            "matchCount": 0,
            "page": 1,
            "perPage": 100,
            "totalCount": 0,
        }
        respx.get(_INFO_URL).mock(return_value=Response(200, json=payload))

        result = await get_apt_subscription_info()

        assert "error" not in result
        assert result["total_count"] == 0

    @respx.mock
    async def test_fallback_to_data_go_kr_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ODCLOUD_API_KEY", raising=False)
        monkeypatch.delenv("ODCLOUD_SERVICE_KEY", raising=False)
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "test-fallback-key")

        payload = {
            "currentCount": 0,
            "data": [],
            "matchCount": 0,
            "page": 1,
            "perPage": 100,
            "totalCount": 0,
        }
        respx.get(_INFO_URL).mock(return_value=Response(200, json=payload))

        result = await get_apt_subscription_info()

        assert "error" not in result
        assert result["total_count"] == 0


class TestGetAptSubscriptionResults:
    """Integration tests for get_apt_subscription_results."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ODCLOUD_API_KEY", "test-odcloud-key")
        monkeypatch.delenv("ODCLOUD_SERVICE_KEY", raising=False)
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

    @respx.mock
    async def test_success_reqst_area(self) -> None:
        payload = {
            "currentCount": 1,
            "data": [{"STAT_DE": "202501", "SUBSCRPT_AREA_CODE": "01", "AGE_30": 10}],
            "matchCount": 1,
            "page": 1,
            "perPage": 10,
            "totalCount": 1,
        }
        respx.get(f"{_STAT_BASE_URL}/getAPTReqstAreaStat").mock(
            return_value=Response(200, json=payload)
        )

        result = await get_apt_subscription_results(
            stat_kind="reqst_area",
            stat_year_month="202501",
            area_code="01",
            page=1,
            per_page=10,
        )

        assert "error" not in result
        assert result["stat_kind"] == "reqst_area"
        assert result["total_count"] == 1
        assert result["items"][0]["STAT_DE"] == "202501"

    async def test_invalid_stat_kind_returns_validation_error(self) -> None:
        result = await get_apt_subscription_results(stat_kind="nope")
        assert result["error"] == "validation_error"

    @respx.mock
    async def test_success_reqst_age(self) -> None:
        payload = {
            "currentCount": 1,
            "data": [{"STAT_DE": "202501", "AGE_30": 5}],
            "matchCount": 1,
            "page": 1,
            "perPage": 10,
            "totalCount": 1,
        }
        respx.get(f"{_STAT_BASE_URL}/getAPTReqstAgeStat").mock(
            return_value=Response(200, json=payload)
        )

        result = await get_apt_subscription_results(stat_kind="reqst_age")

        assert "error" not in result
        assert result["stat_kind"] == "reqst_age"
        assert result["total_count"] == 1

    @respx.mock
    async def test_success_przwner_area(self) -> None:
        payload = {
            "currentCount": 1,
            "data": [{"STAT_DE": "202501", "SUBSCRPT_AREA_CODE": "01"}],
            "matchCount": 1,
            "page": 1,
            "perPage": 10,
            "totalCount": 1,
        }
        respx.get(f"{_STAT_BASE_URL}/getAPTPrzwnerAreaStat").mock(
            return_value=Response(200, json=payload)
        )

        result = await get_apt_subscription_results(stat_kind="przwner_area")

        assert "error" not in result
        assert result["stat_kind"] == "przwner_area"
        assert result["total_count"] == 1

    @respx.mock
    async def test_success_przwner_age(self) -> None:
        payload = {
            "currentCount": 1,
            "data": [{"STAT_DE": "202501", "AGE_30": 3}],
            "matchCount": 1,
            "page": 1,
            "perPage": 10,
            "totalCount": 1,
        }
        respx.get(f"{_STAT_BASE_URL}/getAPTPrzwnerAgeStat").mock(
            return_value=Response(200, json=payload)
        )

        result = await get_apt_subscription_results(stat_kind="przwner_age")

        assert "error" not in result
        assert result["stat_kind"] == "przwner_age"
        assert result["total_count"] == 1

    @respx.mock
    async def test_success_cmpetrt_area(self) -> None:
        payload = {
            "currentCount": 1,
            "data": [{"STAT_DE": "202501", "SUBSCRPT_AREA_CODE": "01", "CMPET_RATE": "3.5"}],
            "matchCount": 1,
            "page": 1,
            "perPage": 10,
            "totalCount": 1,
        }
        respx.get(f"{_STAT_BASE_URL}/getAPTCmpetrtAreaStat").mock(
            return_value=Response(200, json=payload)
        )

        result = await get_apt_subscription_results(stat_kind="cmpetrt_area")

        assert "error" not in result
        assert result["stat_kind"] == "cmpetrt_area"
        assert result["total_count"] == 1

    async def test_invalid_page_returns_validation_error(self) -> None:
        result = await get_apt_subscription_results(stat_kind="reqst_area", page=0)
        assert result["error"] == "validation_error"

    @respx.mock
    async def test_service_key_mode_and_reside_filter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ODCLOUD_API_KEY", raising=False)
        monkeypatch.setenv("ODCLOUD_SERVICE_KEY", "test-service-key")

        payload = {
            "currentCount": 1,
            "data": [{"STAT_DE": "202501", "RESIDE_SECD": "01", "AVRG_SCORE": 50.1}],
            "matchCount": 1,
            "page": 1,
            "perPage": 10,
            "totalCount": 1,
        }
        respx.get(f"{_STAT_BASE_URL}/getAPTApsPrzwnerStat").mock(
            return_value=Response(200, json=payload)
        )

        result = await get_apt_subscription_results(
            stat_kind="aps_przwner",
            stat_year_month="202501",
            reside_secd="01",
            page=1,
            per_page=10,
        )

        assert "error" not in result
        assert result["stat_kind"] == "aps_przwner"
        assert result["items"][0]["RESIDE_SECD"] == "01"

    @respx.mock
    async def test_fallback_to_data_go_kr_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ODCLOUD_API_KEY", raising=False)
        monkeypatch.delenv("ODCLOUD_SERVICE_KEY", raising=False)
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "test-fallback-key")

        payload = {
            "currentCount": 1,
            "data": [{"STAT_DE": "202501", "SUBSCRPT_AREA_CODE": "01", "AGE_30": 10}],
            "matchCount": 1,
            "page": 1,
            "perPage": 10,
            "totalCount": 1,
        }
        respx.get(f"{_STAT_BASE_URL}/getAPTReqstAreaStat").mock(
            return_value=Response(200, json=payload)
        )

        result = await get_apt_subscription_results(
            stat_kind="reqst_area",
            stat_year_month="202501",
            area_code="01",
            page=1,
            per_page=10,
        )

        assert "error" not in result
        assert result["total_count"] == 1

    @respx.mock
    async def test_timeout_returns_network_error(self) -> None:
        import httpx as _httpx

        respx.get(f"{_STAT_BASE_URL}/getAPTReqstAreaStat").mock(
            side_effect=_httpx.TimeoutException("timeout")
        )

        result = await get_apt_subscription_results(stat_kind="reqst_area")

        assert result["error"] == "network_error"
