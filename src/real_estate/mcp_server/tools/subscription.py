"""MCP tools for APT subscription (청약) records."""

from __future__ import annotations

import urllib.parse
from typing import Any

from real_estate.mcp_server import mcp
from real_estate.mcp_server._helpers import (
    _APPLYHOME_STAT_BASE_URL,
    _APT_SUBSCRIPTION_INFO_PATH,
    _ODCLOUD_BASE_URL,
    _check_odcloud_key,
    _fetch_json,
    _get_odcloud_key,
)


@mcp.tool()
async def get_apt_subscription_info(
    page: int = 1,
    per_page: int = 100,
    return_type: str = "JSON",
) -> dict[str, Any]:
    """Return Applyhome (청약홈) APT subscription notice metadata.

    Korean keywords: 청약, 분양, 모집공고, 청약 일정, 당첨자 발표, 계약 일정

    Use this tool when the user asks:
      - "청약(분양) 공고를 보고 싶어", "이번 달 모집공고 알려줘"
      - "청약 접수 시작/종료일, 당첨자 발표일이 언제야?"
      - "어떤 단지(주택명)가 분양 예정이야?"

    This tool returns APT notice metadata such as notice number, house name,
    location, schedule dates (announcement, application, winner, contract),
    and operator/constructor information. It is not tied to region_code.

    Authentication:
      - Set ODCLOUD_API_KEY (Authorization header), or
      - Set ODCLOUD_SERVICE_KEY (serviceKey query parameter).

    Args:
        page: Page number (1-based).
        per_page: Items per page.
        return_type: Response type, typically "JSON".

    Returns:
        total_count: Total record count from the API.
        items: Notice metadata records.
        page: Current page.
        per_page: Items per page.
        current_count: Number of returned items in this response.
        match_count: Number of matched items (may differ by API).
        error/message: Present on API/network/config failure.
    """
    if page < 1:
        return {"error": "validation_error", "message": "page must be >= 1"}
    if per_page < 1:
        return {"error": "validation_error", "message": "per_page must be >= 1"}

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

    url = f"{_ODCLOUD_BASE_URL}{_APT_SUBSCRIPTION_INFO_PATH}?{urllib.parse.urlencode(params)}"
    payload, fetch_err = await _fetch_json(url, headers=headers)
    if fetch_err:
        return fetch_err
    if not isinstance(payload, dict):
        return {"error": "parse_error", "message": "Unexpected response type"}

    return {
        "total_count": int(payload.get("totalCount") or 0),
        "items": payload.get("data") or [],
        "page": int(payload.get("page") or page),
        "per_page": int(payload.get("perPage") or per_page),
        "current_count": int(payload.get("currentCount") or 0),
        "match_count": int(payload.get("matchCount") or 0),
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
