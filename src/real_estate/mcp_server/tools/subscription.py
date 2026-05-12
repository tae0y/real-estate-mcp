"""MCP tools for APT subscription (청약) records."""

from __future__ import annotations

import datetime as _dt
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

from real_estate.common_utils.pdf_parser import (
    SupplyPrice,
    extract_supply_prices,
)
from real_estate.mcp_server import mcp
from real_estate.mcp_server._helpers import (
    _APPLYHOME_STAT_BASE_URL,
    _APT_SUBSCRIPTION_INFO_PATH,
    _ODCLOUD_BASE_URL,
    _check_odcloud_key,
    _current_year_month,
    _download_pdf,
    _fetch_json,
    _get_odcloud_key,
    _validate_pblanc_date,
    _validate_year_month,
)


def _normalize_year_month(value: str) -> str | None:
    """Return YYYY-MM if value is YYYYMM, else None."""
    if len(value) == 6 and value.isdigit():
        return f"{value[:4]}-{value[4:]}"
    return None


def _annotate_pre_occupancy(item: dict[str, Any], current_ym: str) -> dict[str, Any]:
    """Attach is_pre_occupancy / expected_move_in_year_month fields to an item."""
    raw = item.get("MVN_PREARNGE_YM")
    if not isinstance(raw, str) or not raw:
        return item
    normalized = _normalize_year_month(raw)
    item["expected_move_in_year_month"] = normalized or raw
    item["is_pre_occupancy"] = raw >= current_ym
    return item


@mcp.tool()
async def get_apt_subscription_info(
    page: int = 1,
    per_page: int = 100,
    return_type: str = "JSON",
    rcrit_pblanc_de_from: str | None = None,
    rcrit_pblanc_de_to: str | None = None,
    mvn_prearnge_ym_from: str | None = None,
    only_pending_occupancy: bool = False,
) -> dict[str, Any]:
    """Return Applyhome (청약홈) APT subscription notice metadata.

    Korean keywords: 청약, 분양, 모집공고, 청약 일정, 당첨자 발표, 계약 일정, 입주 예정

    Use this tool when the user asks:
      - "청약(분양) 공고를 보고 싶어", "이번 달 모집공고 알려줘"
      - "2021년 7월까지의 과거 분양 공고를 보여줘"
      - "입주 예정 단지(실거래가 미확정)만 보여줘"
      - "어떤 단지(주택명)가 분양 예정이야?"

    This tool returns APT notice metadata such as notice number, house name,
    location, schedule dates (announcement, application, winner, contract),
    and operator/constructor information. It is not tied to region_code.

    Filtering (server-side via odcloud cond[] syntax):
      - rcrit_pblanc_de_from / rcrit_pblanc_de_to: 모집공고일 범위 (YYYY-MM-DD).
      - mvn_prearnge_ym_from: 입주예정월 하한 (YYYYMM).
      - only_pending_occupancy: True 일 때 입주예정월이 현재 YYYYMM 이상인
        단지(아직 입주 전, 실거래가 미확정) 만 반환. mvn_prearnge_ym_from 와
        함께 지정되면 더 큰 값(엄격한 쪽)이 적용된다.

    Each item is enriched with `is_pre_occupancy` 와 `expected_move_in_year_month`
    파생 필드를 포함한다 (원본 MVN_PREARNGE_YM 기반).

    Authentication:
      - Set ODCLOUD_API_KEY (Authorization header), or
      - Set ODCLOUD_SERVICE_KEY (serviceKey query parameter).

    Args:
        page: Page number (1-based).
        per_page: Items per page.
        return_type: Response type, typically "JSON".
        rcrit_pblanc_de_from: 모집공고일 ≥ YYYY-MM-DD.
        rcrit_pblanc_de_to: 모집공고일 ≤ YYYY-MM-DD.
        mvn_prearnge_ym_from: 입주예정월 ≥ YYYYMM.
        only_pending_occupancy: 현재월 이후 입주예정 단지만 반환.

    Returns:
        total_count: Total record count from the API.
        items: Notice metadata records (with derived fields).
        page: Current page.
        per_page: Items per page.
        current_count: Number of returned items in this response.
        match_count: Number of matched items (may differ by API).
        applied_filters: Echo of the filters that were sent to the API.
        error/message: Present on API/network/config failure.
    """
    if page < 1:
        return {"error": "validation_error", "message": "page must be >= 1"}
    if per_page < 1:
        return {"error": "validation_error", "message": "per_page must be >= 1"}

    if rcrit_pblanc_de_from:
        err = _validate_pblanc_date(rcrit_pblanc_de_from, "rcrit_pblanc_de_from")
        if err:
            return err
    if rcrit_pblanc_de_to:
        err = _validate_pblanc_date(rcrit_pblanc_de_to, "rcrit_pblanc_de_to")
        if err:
            return err
    if (
        rcrit_pblanc_de_from
        and rcrit_pblanc_de_to
        and rcrit_pblanc_de_from > rcrit_pblanc_de_to
    ):
        return {
            "error": "validation_error",
            "message": "rcrit_pblanc_de_from must be <= rcrit_pblanc_de_to.",
        }
    if mvn_prearnge_ym_from:
        err = _validate_year_month(mvn_prearnge_ym_from, "mvn_prearnge_ym_from")
        if err:
            return err

    current_ym = _current_year_month()
    effective_mvn_from = mvn_prearnge_ym_from
    if only_pending_occupancy:
        effective_mvn_from = (
            max(mvn_prearnge_ym_from, current_ym) if mvn_prearnge_ym_from else current_ym
        )

    err = _check_odcloud_key()
    if err:
        return err

    mode, key = _get_odcloud_key()
    headers: dict[str, str] | None = None
    params: dict[str, Any] = {"page": page, "perPage": per_page, "returnType": return_type}
    if mode == "authorization":
        headers = {"Authorization": key}
    elif mode == "serviceKey":
        params["serviceKey"] = key

    if rcrit_pblanc_de_from:
        params["cond[RCRIT_PBLANC_DE::GTE]"] = rcrit_pblanc_de_from
    if rcrit_pblanc_de_to:
        params["cond[RCRIT_PBLANC_DE::LTE]"] = rcrit_pblanc_de_to
    if effective_mvn_from:
        params["cond[MVN_PREARNGE_YM::GTE]"] = effective_mvn_from

    url = f"{_ODCLOUD_BASE_URL}{_APT_SUBSCRIPTION_INFO_PATH}?{urllib.parse.urlencode(params)}"
    payload, fetch_err = await _fetch_json(url, headers=headers)
    if fetch_err:
        return fetch_err
    if not isinstance(payload, dict):
        return {"error": "parse_error", "message": "Unexpected response type"}

    raw_items = payload.get("data") or []
    items = [
        _annotate_pre_occupancy(dict(item), current_ym)
        if isinstance(item, dict)
        else item
        for item in raw_items
    ]

    return {
        "total_count": int(payload.get("totalCount") or 0),
        "items": items,
        "page": int(payload.get("page") or page),
        "per_page": int(payload.get("perPage") or per_page),
        "current_count": int(payload.get("currentCount") or 0),
        "match_count": int(payload.get("matchCount") or 0),
        "applied_filters": {
            "rcrit_pblanc_de_from": rcrit_pblanc_de_from,
            "rcrit_pblanc_de_to": rcrit_pblanc_de_to,
            "mvn_prearnge_ym_from": effective_mvn_from,
            "only_pending_occupancy": only_pending_occupancy,
        },
    }


def _supply_price_to_dict(price: SupplyPrice) -> dict[str, Any]:
    return {
        "unit_type": price.unit_type,
        "exclusive_area_sqm": price.exclusive_area_sqm,
        "supply_amount_10k": price.supply_amount_10k,
        "source_page": price.source_page,
    }


async def _lookup_notice_by_house_manage_no(house_manage_no: str) -> dict[str, Any]:
    """Fetch a single subscription notice item by HOUSE_MANAGE_NO."""
    mode, key = _get_odcloud_key()
    headers: dict[str, str] | None = None
    params: dict[str, Any] = {
        "page": 1,
        "perPage": 1,
        "returnType": "JSON",
        "cond[HOUSE_MANAGE_NO::EQ]": house_manage_no,
    }
    if mode == "authorization":
        headers = {"Authorization": key}
    elif mode == "serviceKey":
        params["serviceKey"] = key

    url = f"{_ODCLOUD_BASE_URL}{_APT_SUBSCRIPTION_INFO_PATH}?{urllib.parse.urlencode(params)}"
    payload, err = await _fetch_json(url, headers=headers)
    if err:
        return {"error": err}
    if not isinstance(payload, dict):
        return {"error": {"error": "parse_error", "message": "Unexpected response type"}}
    items = payload.get("data") or []
    if not items or not isinstance(items[0], dict):
        return {
            "error": {
                "error": "not_found",
                "message": f"No subscription notice found for HOUSE_MANAGE_NO={house_manage_no!r}.",
            }
        }
    return {"item": items[0]}


@mcp.tool()
async def get_apt_subscription_supply_prices(
    house_manage_no: str | None = None,
    pblanc_url: str | None = None,
) -> dict[str, Any]:
    """Return 평형별 분양가 extracted from a 청약 공고 PDF.

    Korean keywords: 분양가, 공급금액, 평형별 가격, 청약 공고 PDF

    Use this tool when the user asks:
      - "이 단지의 평형별 분양가가 얼마야?"
      - "84A 공급금액 알려줘"
      - "청약 공고 PDF에서 분양가만 뽑아줘"

    Provide either `house_manage_no` (HOUSE_MANAGE_NO; the tool resolves PBLANC_URL
    from get_apt_subscription_info) OR a direct `pblanc_url` to a PDF.

    The extractor first tries 표 기반(`pdfplumber.extract_tables`) 컬럼 인식
    ("공급금액"/"공급가격"/"분양가" + "주택형"/"타입"/"모델"/"평형" + "전용면적"),
    실패 시 텍스트 정규식 fallback. 공급금액은 원 또는 만원 단위 입력 모두
    자동 정규화되어 `supply_amount_10k`(만원) 로 반환된다. 같은
    (unit_type, exclusive_area_sqm) 키는 중복 제거된다.

    Authentication:
      - Set ODCLOUD_API_KEY or ODCLOUD_SERVICE_KEY only when `house_manage_no`
        is used (for the lookup step). Direct `pblanc_url` does not require
        odcloud credentials.

    Args:
        house_manage_no: 주택관리번호 (HOUSE_MANAGE_NO).
        pblanc_url: 직접 지정한 공고 PDF URL.

    Returns:
        house_name: 단지명 (HOUSE_NM) — only when looked up via house_manage_no.
        house_manage_no: 입력값 echo.
        source_pdf_url: 실제 다운로드에 사용된 URL.
        supply_prices: List[{unit_type, exclusive_area_sqm, supply_amount_10k, source_page}].
        sample_count: supply_prices 길이.
        extracted_at: ISO-8601 UTC timestamp.
        error/message: Present on validation/lookup/download/parse failure.
    """
    if not house_manage_no and not pblanc_url:
        return {
            "error": "validation_error",
            "message": "Provide either house_manage_no or pblanc_url.",
        }

    house_name: str | None = None
    source_url = pblanc_url

    if not source_url:
        err = _check_odcloud_key()
        if err:
            return err
        assert house_manage_no is not None
        lookup = await _lookup_notice_by_house_manage_no(house_manage_no)
        if "error" in lookup:
            return lookup["error"]
        notice = lookup["item"]
        source_url = (notice.get("PBLANC_URL") or "").strip() or None
        if not source_url:
            return {
                "error": "not_found",
                "message": "PBLANC_URL is not available in the lookup result.",
                "house_manage_no": house_manage_no,
            }
        house_name = notice.get("HOUSE_NM") or None

    assert source_url is not None
    body, err = await _download_pdf(source_url)
    if err:
        return {**err, "source_pdf_url": source_url}

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        assert body is not None
        tmp.write(body)
        tmp.flush()
        try:
            prices = extract_supply_prices(Path(tmp.name))
        except ValueError as exc:
            return {
                "error": "parse_error",
                "message": str(exc),
                "source_pdf_url": source_url,
            }

    return {
        "house_name": house_name,
        "house_manage_no": house_manage_no,
        "source_pdf_url": source_url,
        "supply_prices": [_supply_price_to_dict(p) for p in prices],
        "sample_count": len(prices),
        "extracted_at": _dt.datetime.now(_dt.UTC).isoformat(),
    }


@mcp.tool()
async def get_apt_subscription_results(
    stat_kind: str,
    stat_year_month: str | None = None,
    area_code: str | None = None,
    reside_secd: str | None = None,
    page: int = 1,
    per_page: int = 100,
    return_type: str = "JSON",
) -> dict[str, Any]:
    """Return Applyhome (청약홈) subscription stats: requests, winners, rates, and scores.

    Korean keywords: 청약 경쟁률, 청약 신청자, 청약 당첨자, 가점, 가점제

    Use this tool when the user asks:
      - "마포구(서울) 청약 경쟁률이 어때?"
      - "청약 신청자/당첨자 통계가 궁금해"
      - "가점 평균/중앙값/최고점은?"

    This tool provides aggregated statistics, not individual notice schedules.
    For schedules (접수/발표/계약일), use get_apt_subscription_info.

    stat_kind choices:
      - "reqst_area": 지역별 청약 신청자 (연령대별 신청건수)
      - "reqst_age":  연령별 청약 신청자 (연령대별 신청건수)
      - "przwner_area": 지역별 청약 당첨자 (연령대별 당첨건수)
      - "przwner_age":  연령별 청약 당첨자 (연령대별 당첨건수)
      - "cmpetrt_area": 지역별 청약 경쟁률 (특별/일반공급 경쟁률)
      - "aps_przwner":  지역별 청약 가점제 당첨자 (가점 통계)

    Optional filters use odcloud's cond[...] syntax.

    Authentication:
      - Set ODCLOUD_API_KEY (Authorization header), or
      - Set ODCLOUD_SERVICE_KEY (serviceKey query parameter).

    Args:
        stat_kind: Which stats endpoint to call (see choices above).
        stat_year_month: Provided year-month in YYYYMM (maps to STAT_DE).
        area_code: Subscription area code (maps to SUBSCRPT_AREA_CODE).
        reside_secd: Residence section code (maps to RESIDE_SECD, used by some endpoints).
        page: Page number (1-based).
        per_page: Items per page.
        return_type: Response type, typically "JSON".

    Returns:
        total_count/items/page/per_page/current_count/match_count plus the chosen stat_kind.
        error/message: Present on API/network/config failure.
    """
    if page < 1:
        return {"error": "validation_error", "message": "page must be >= 1"}
    if per_page < 1:
        return {"error": "validation_error", "message": "per_page must be >= 1"}

    endpoint_map: dict[str, str] = {
        "reqst_area": "getAPTReqstAreaStat",
        "reqst_age": "getAPTReqstAgeStat",
        "przwner_area": "getAPTPrzwnerAreaStat",
        "przwner_age": "getAPTPrzwnerAgeStat",
        "cmpetrt_area": "getAPTCmpetrtAreaStat",
        "aps_przwner": "getAPTApsPrzwnerStat",
    }
    endpoint = endpoint_map.get(stat_kind)
    if endpoint is None:
        return {
            "error": "validation_error",
            "message": f"Invalid stat_kind. Expected one of: {', '.join(endpoint_map)}",
        }

    err = _check_odcloud_key()
    if err:
        return err

    mode, key = _get_odcloud_key()
    headers: dict[str, str] | None = None
    params: dict[str, Any] = {"page": page, "perPage": per_page, "returnType": return_type}
    if mode == "authorization":
        headers = {"Authorization": key}
    elif mode == "serviceKey":
        params["serviceKey"] = key

    if stat_year_month:
        params["cond[STAT_DE::EQ]"] = stat_year_month
    if area_code:
        params["cond[SUBSCRPT_AREA_CODE::EQ]"] = area_code
    if reside_secd:
        params["cond[RESIDE_SECD::EQ]"] = reside_secd

    url = f"{_APPLYHOME_STAT_BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
    payload, fetch_err = await _fetch_json(url, headers=headers)
    if fetch_err:
        return fetch_err
    if not isinstance(payload, dict):
        return {"error": "parse_error", "message": "Unexpected response type"}

    return {
        "stat_kind": stat_kind,
        "total_count": int(payload.get("totalCount") or 0),
        "items": payload.get("data") or [],
        "page": int(payload.get("page") or page),
        "per_page": int(payload.get("perPage") or per_page),
        "current_count": int(payload.get("currentCount") or 0),
        "match_count": int(payload.get("matchCount") or 0),
    }
