"""Unit tests for Applyhome (odcloud) subscription tools.

HTTP calls are mocked with respx so the real API is never called.
"""

import urllib.parse
from pathlib import Path
from unittest.mock import patch

import pytest
import respx
from httpx import Response

from real_estate.common_utils.pdf_parser import SupplyPrice
from real_estate.mcp_server._helpers import (
    _current_year_month,
    _validate_pblanc_date,
    _validate_year_month,
)
from real_estate.mcp_server.tools.subscription import (
    _annotate_pre_occupancy,
    _build_default_filename,
    _normalize_year_month,
    download_subscription_pdf,
    get_apt_subscription_info,
    get_apt_subscription_results,
    get_apt_subscription_supply_prices,
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

    @respx.mock
    async def test_enriches_items_with_pre_occupancy_fields(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "real_estate.mcp_server.tools.subscription._current_year_month",
            lambda: "202605",
        )
        payload = {
            "currentCount": 2,
            "data": [
                {"HOUSE_NM": "future", "MVN_PREARNGE_YM": "202712"},
                {"HOUSE_NM": "past", "MVN_PREARNGE_YM": "202209"},
            ],
            "matchCount": 2,
            "page": 1,
            "perPage": 100,
            "totalCount": 2,
        }
        respx.get(_INFO_URL).mock(return_value=Response(200, json=payload))

        result = await get_apt_subscription_info()

        assert result["items"][0]["is_pre_occupancy"] is True
        assert result["items"][0]["expected_move_in_year_month"] == "2027-12"
        assert result["items"][1]["is_pre_occupancy"] is False
        assert result["items"][1]["expected_move_in_year_month"] == "2022-09"

    @respx.mock
    async def test_date_range_filter_passed_to_api(self) -> None:
        payload = {
            "currentCount": 0,
            "data": [],
            "matchCount": 0,
            "page": 1,
            "perPage": 100,
            "totalCount": 0,
        }
        route = respx.get(_INFO_URL).mock(return_value=Response(200, json=payload))

        await get_apt_subscription_info(
            rcrit_pblanc_de_from="2021-01-01",
            rcrit_pblanc_de_to="2021-07-31",
        )

        assert route.called
        query = dict(urllib.parse.parse_qsl(route.calls[0].request.url.query.decode()))
        assert query["cond[RCRIT_PBLANC_DE::GTE]"] == "2021-01-01"
        assert query["cond[RCRIT_PBLANC_DE::LTE]"] == "2021-07-31"

    async def test_invalid_date_format_rejected(self) -> None:
        result = await get_apt_subscription_info(rcrit_pblanc_de_from="2021/07/01")
        assert result["error"] == "validation_error"

    async def test_from_after_to_rejected(self) -> None:
        result = await get_apt_subscription_info(
            rcrit_pblanc_de_from="2024-01-01",
            rcrit_pblanc_de_to="2021-07-01",
        )
        assert result["error"] == "validation_error"

    async def test_invalid_year_month_rejected(self) -> None:
        result = await get_apt_subscription_info(mvn_prearnge_ym_from="202113")
        assert result["error"] == "validation_error"

    @respx.mock
    async def test_only_pending_occupancy_uses_current_month(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "real_estate.mcp_server.tools.subscription._current_year_month",
            lambda: "202605",
        )
        payload = {
            "currentCount": 0,
            "data": [],
            "matchCount": 0,
            "page": 1,
            "perPage": 100,
            "totalCount": 0,
        }
        route = respx.get(_INFO_URL).mock(return_value=Response(200, json=payload))

        result = await get_apt_subscription_info(only_pending_occupancy=True)

        query = dict(urllib.parse.parse_qsl(route.calls[0].request.url.query.decode()))
        assert query["cond[MVN_PREARNGE_YM::GTE]"] == "202605"
        assert result["applied_filters"]["only_pending_occupancy"] is True
        assert result["applied_filters"]["mvn_prearnge_ym_from"] == "202605"

    @respx.mock
    async def test_only_pending_prefers_stricter_bound(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "real_estate.mcp_server.tools.subscription._current_year_month",
            lambda: "202605",
        )
        payload = {
            "currentCount": 0,
            "data": [],
            "matchCount": 0,
            "page": 1,
            "perPage": 100,
            "totalCount": 0,
        }
        route = respx.get(_INFO_URL).mock(return_value=Response(200, json=payload))

        await get_apt_subscription_info(
            mvn_prearnge_ym_from="202401", only_pending_occupancy=True
        )

        query = dict(urllib.parse.parse_qsl(route.calls[0].request.url.query.decode()))
        # Current month (202605) > 202401 → current wins.
        assert query["cond[MVN_PREARNGE_YM::GTE]"] == "202605"


class TestSubscriptionPureHelpers:
    """Pure helper unit tests (no HTTP)."""

    def test_pblanc_date_accepts_valid(self) -> None:
        assert _validate_pblanc_date("2021-07-31", "f") is None

    def test_pblanc_date_rejects_bad_format(self) -> None:
        err = _validate_pblanc_date("2021/07/31", "f")
        assert err is not None and err["error"] == "validation_error"

    def test_pblanc_date_rejects_invalid_calendar(self) -> None:
        err = _validate_pblanc_date("2021-02-30", "f")
        assert err is not None

    def test_year_month_accepts_valid(self) -> None:
        assert _validate_year_month("202107", "f") is None

    def test_year_month_rejects_month_zero(self) -> None:
        err = _validate_year_month("202100", "f")
        assert err is not None

    def test_year_month_rejects_short(self) -> None:
        err = _validate_year_month("20210", "f")
        assert err is not None

    def test_annotate_marks_future_as_pending(self) -> None:
        item = _annotate_pre_occupancy({"MVN_PREARNGE_YM": "299912"}, "202605")
        assert item["is_pre_occupancy"] is True
        assert item["expected_move_in_year_month"] == "2999-12"

    def test_annotate_marks_past_as_not_pending(self) -> None:
        item = _annotate_pre_occupancy({"MVN_PREARNGE_YM": "202001"}, "202605")
        assert item["is_pre_occupancy"] is False

    def test_annotate_no_field_leaves_item_alone(self) -> None:
        item = _annotate_pre_occupancy({"HOUSE_NM": "x"}, "202605")
        assert "is_pre_occupancy" not in item

    def test_annotate_non_yyyymm_falls_back_to_raw(self) -> None:
        item = _annotate_pre_occupancy({"MVN_PREARNGE_YM": "미정"}, "202605")
        assert item["expected_move_in_year_month"] == "미정"

    def test_normalize_year_month_converts_six_digit(self) -> None:
        assert _normalize_year_month("202107") == "2021-07"

    def test_normalize_year_month_returns_none_for_non_digit(self) -> None:
        assert _normalize_year_month("미정") is None

    def test_current_year_month_shape(self) -> None:
        ym = _current_year_month()
        assert len(ym) == 6 and ym.isdigit()
        assert 1 <= int(ym[4:]) <= 12


class TestGetAptSubscriptionSupplyPrices:
    """Integration tests for get_apt_subscription_supply_prices."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ODCLOUD_API_KEY", "test-odcloud-key")
        monkeypatch.delenv("ODCLOUD_SERVICE_KEY", raising=False)
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

    async def test_missing_inputs_returns_validation_error(self) -> None:
        result = await get_apt_subscription_supply_prices()
        assert result["error"] == "validation_error"

    @respx.mock
    async def test_pblanc_url_success_returns_supply_prices(self) -> None:
        pdf_url = "https://example.com/notice.pdf"
        pdf_bytes = b"%PDF-1.4\n%fake test pdf body"
        respx.get(pdf_url).mock(
            return_value=Response(
                200, content=pdf_bytes, headers={"content-type": "application/pdf"}
            )
        )

        fake_prices = [
            SupplyPrice("84A", 84.9123, 78500, 3),
            SupplyPrice("59B", 59.5421, 56000, 3),
        ]
        with patch(
            "real_estate.mcp_server.tools.subscription.extract_supply_prices",
            return_value=fake_prices,
        ):
            result = await get_apt_subscription_supply_prices(pblanc_url=pdf_url)

        assert "error" not in result
        assert result["source_pdf_url"] == pdf_url
        assert result["sample_count"] == 2
        assert result["supply_prices"][0] == {
            "unit_type": "84A",
            "exclusive_area_sqm": 84.9123,
            "supply_amount_10k": 78500,
            "source_page": 3,
        }
        assert result["house_name"] is None  # not looked up
        assert "extracted_at" in result

    @respx.mock
    async def test_house_manage_no_lookup_then_download(self) -> None:
        lookup_payload = {
            "currentCount": 1,
            "data": [
                {
                    "HOUSE_MANAGE_NO": "2024000123",
                    "HOUSE_NM": "더샵 인테그리티",
                    "PBLANC_URL": "https://example.com/notice.pdf",
                }
            ],
            "matchCount": 1,
            "page": 1,
            "perPage": 1,
            "totalCount": 1,
        }
        respx.get(_INFO_URL).mock(return_value=Response(200, json=lookup_payload))
        pdf_bytes = b"%PDF-1.4\n%fake"
        respx.get("https://example.com/notice.pdf").mock(
            return_value=Response(
                200, content=pdf_bytes, headers={"content-type": "application/pdf"}
            )
        )

        with patch(
            "real_estate.mcp_server.tools.subscription.extract_supply_prices",
            return_value=[SupplyPrice("84A", 84.9123, 78500, 3)],
        ):
            result = await get_apt_subscription_supply_prices(house_manage_no="2024000123")

        assert result["house_name"] == "더샵 인테그리티"
        assert result["house_manage_no"] == "2024000123"
        assert result["sample_count"] == 1

    @respx.mock
    async def test_lookup_not_found_returns_not_found(self) -> None:
        respx.get(_INFO_URL).mock(
            return_value=Response(
                200,
                json={
                    "currentCount": 0,
                    "data": [],
                    "matchCount": 0,
                    "page": 1,
                    "perPage": 1,
                    "totalCount": 0,
                },
            )
        )

        result = await get_apt_subscription_supply_prices(house_manage_no="9999999999")
        assert result["error"] == "not_found"

    @respx.mock
    async def test_pdf_download_rejects_non_pdf_content(self) -> None:
        pdf_url = "https://example.com/not-a-pdf.html"
        respx.get(pdf_url).mock(
            return_value=Response(
                200, content=b"<html>nope</html>", headers={"content-type": "text/html"}
            )
        )

        result = await get_apt_subscription_supply_prices(pblanc_url=pdf_url)
        assert result["error"] == "parse_error"
        assert result["source_pdf_url"] == pdf_url

    @respx.mock
    async def test_parse_error_is_surfaced(self) -> None:
        pdf_url = "https://example.com/notice.pdf"
        respx.get(pdf_url).mock(
            return_value=Response(
                200, content=b"%PDF-1.4\n", headers={"content-type": "application/pdf"}
            )
        )

        with patch(
            "real_estate.mcp_server.tools.subscription.extract_supply_prices",
            side_effect=ValueError("OCR may be required: scanned PDF detected"),
        ):
            result = await get_apt_subscription_supply_prices(pblanc_url=pdf_url)

        assert result["error"] == "parse_error"
        assert "OCR" in result["message"]


class TestDownloadSubscriptionPdf:
    """Integration tests for download_subscription_pdf."""

    @pytest.fixture(autouse=True)
    def set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ODCLOUD_API_KEY", "test-odcloud-key")
        monkeypatch.delenv("ODCLOUD_SERVICE_KEY", raising=False)
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)

    async def test_missing_save_dir_returns_validation_error(self) -> None:
        result = await download_subscription_pdf(save_dir="", pblanc_url="https://x/y.pdf")
        assert result["error"] == "validation_error"

    async def test_missing_source_inputs_returns_validation_error(self, tmp_path) -> None:
        result = await download_subscription_pdf(save_dir=str(tmp_path))
        assert result["error"] == "validation_error"

    async def test_blank_filename_rejected(self, tmp_path) -> None:
        result = await download_subscription_pdf(
            save_dir=str(tmp_path),
            pblanc_url="https://example.com/a.pdf",
            filename="   ",
        )
        assert result["error"] == "validation_error"

    @respx.mock
    async def test_direct_url_writes_file_with_default_filename(self, tmp_path) -> None:
        pdf_url = "https://example.com/notice.pdf"
        pdf_bytes = b"%PDF-1.4\nfake body"
        respx.get(pdf_url).mock(
            return_value=Response(
                200, content=pdf_bytes, headers={"content-type": "application/pdf"}
            )
        )

        result = await download_subscription_pdf(
            save_dir=str(tmp_path), pblanc_url=pdf_url
        )

        assert "error" not in result
        saved = Path(result["saved_path"])
        assert saved.exists()
        assert saved.read_bytes() == pdf_bytes
        assert result["file_size_bytes"] == len(pdf_bytes)
        assert result["overwrote"] is False
        # Default filename starts with "subscription_notice" when no metadata.
        assert saved.name.endswith(".pdf")

    @respx.mock
    async def test_lookup_then_download_uses_house_name_in_filename(self, tmp_path) -> None:
        lookup_payload = {
            "currentCount": 1,
            "data": [
                {
                    "HOUSE_MANAGE_NO": "2024000123",
                    "HOUSE_NM": "더샵 인테그리티",
                    "PBLANC_URL": "https://example.com/notice.pdf",
                }
            ],
            "matchCount": 1,
            "page": 1,
            "perPage": 1,
            "totalCount": 1,
        }
        respx.get(_INFO_URL).mock(return_value=Response(200, json=lookup_payload))
        respx.get("https://example.com/notice.pdf").mock(
            return_value=Response(
                200, content=b"%PDF-1.4\nfake", headers={"content-type": "application/pdf"}
            )
        )

        result = await download_subscription_pdf(
            save_dir=str(tmp_path), house_manage_no="2024000123"
        )

        assert result["house_name"] == "더샵 인테그리티"
        saved = Path(result["saved_path"])
        # 공백이 _ 로 치환되어야 함
        assert "더샵_인테그리티" in saved.name
        assert "2024000123" in saved.name
        assert saved.name.endswith(".pdf")
        assert saved.exists()

    @respx.mock
    async def test_filename_traversal_is_sanitized(self, tmp_path) -> None:
        pdf_url = "https://example.com/a.pdf"
        respx.get(pdf_url).mock(
            return_value=Response(
                200, content=b"%PDF-1.4\n", headers={"content-type": "application/pdf"}
            )
        )

        result = await download_subscription_pdf(
            save_dir=str(tmp_path),
            pblanc_url=pdf_url,
            filename="../../../etc/passwd",
        )

        saved = Path(result["saved_path"])
        # 경로 traversal 가 모두 제거되어야 함 — 결과 파일은 save_dir 안에 있어야 함
        assert saved.parent == tmp_path.resolve()
        assert "/" not in saved.name
        assert ".." not in saved.name

    @respx.mock
    async def test_overwrite_false_uses_numeric_suffix(self, tmp_path) -> None:
        pdf_url = "https://example.com/a.pdf"
        respx.get(pdf_url).mock(
            return_value=Response(
                200, content=b"%PDF-1.4\nv1", headers={"content-type": "application/pdf"}
            )
        )

        # 첫 번째 호출 — 평범한 이름
        first = await download_subscription_pdf(
            save_dir=str(tmp_path), pblanc_url=pdf_url, filename="notice.pdf"
        )
        # 두 번째 호출 — 같은 이름. overwrite=False (기본) → suffix 추가
        respx.get(pdf_url).mock(
            return_value=Response(
                200, content=b"%PDF-1.4\nv2", headers={"content-type": "application/pdf"}
            )
        )
        second = await download_subscription_pdf(
            save_dir=str(tmp_path), pblanc_url=pdf_url, filename="notice.pdf"
        )

        assert Path(first["saved_path"]).name == "notice.pdf"
        assert Path(second["saved_path"]).name == "notice_01.pdf"
        assert second["overwrote"] is False
        assert Path(second["saved_path"]).read_bytes() == b"%PDF-1.4\nv2"

    @respx.mock
    async def test_overwrite_true_replaces_existing_file(self, tmp_path) -> None:
        pdf_url = "https://example.com/a.pdf"
        respx.get(pdf_url).mock(
            return_value=Response(
                200, content=b"%PDF-1.4\nold", headers={"content-type": "application/pdf"}
            )
        )
        await download_subscription_pdf(
            save_dir=str(tmp_path), pblanc_url=pdf_url, filename="notice.pdf"
        )

        respx.get(pdf_url).mock(
            return_value=Response(
                200,
                content=b"%PDF-1.4\nfresh",
                headers={"content-type": "application/pdf"},
            )
        )
        result = await download_subscription_pdf(
            save_dir=str(tmp_path),
            pblanc_url=pdf_url,
            filename="notice.pdf",
            overwrite=True,
        )

        assert Path(result["saved_path"]).name == "notice.pdf"
        assert result["overwrote"] is True
        assert Path(result["saved_path"]).read_bytes() == b"%PDF-1.4\nfresh"

    @respx.mock
    async def test_save_dir_auto_created(self, tmp_path) -> None:
        pdf_url = "https://example.com/a.pdf"
        respx.get(pdf_url).mock(
            return_value=Response(
                200, content=b"%PDF-1.4\n", headers={"content-type": "application/pdf"}
            )
        )

        target_dir = tmp_path / "nested" / "subdir"
        assert not target_dir.exists()

        result = await download_subscription_pdf(save_dir=str(target_dir), pblanc_url=pdf_url)

        assert "error" not in result
        assert target_dir.exists()
        assert Path(result["saved_path"]).parent == target_dir.resolve()

    def test_build_default_filename_with_full_metadata(self) -> None:
        name = _build_default_filename("더샵 인테그리티", "2024000123")
        assert name == "더샵_인테그리티_2024000123.pdf"

    def test_build_default_filename_with_no_metadata(self) -> None:
        name = _build_default_filename(None, None)
        assert name == "subscription_notice.pdf"


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
