"""MCP tools for Onbid (공매) bid results and code lookup."""

from __future__ import annotations

from typing import Any

from defusedxml.ElementTree import ParseError as XmlParseError

from real_estate.mcp_server import mcp
from real_estate.mcp_server._helpers import (
    _ONBID_ADDR1_URL,
    _ONBID_ADDR2_URL,
    _ONBID_ADDR3_URL,
    _ONBID_BID_RESULT_DETAIL_URL,
    _ONBID_BID_RESULT_LIST_URL,
    _ONBID_CODE_BOTTOM_URL,
    _ONBID_CODE_MIDDLE_URL,
    _ONBID_CODE_TOP_URL,
    _ONBID_DTL_ADDR_URL,
    _ONBID_THING_INFO_LIST_URL,
    _build_url_with_service_key,
    _check_onbid_api_key,
    _fetch_json,
    _fetch_xml,
    _get_data_go_kr_key_for_onbid,
    _run_onbid_code_info_tool,
)
from real_estate.mcp_server.parsers.onbid import (
    _onbid_extract_items,
    _parse_onbid_thing_info_list_xml,
)


@mcp.tool()
async def get_public_auction_items(
    page_no: int = 1,
    num_of_rows: int = 20,
    cltr_type_cd: str | None = None,
    prpt_div_cd: str | None = None,
    dsps_mthod_cd: str | None = None,
    bid_div_cd: str | None = None,
    lctn_sdnm: str | None = None,
    lctn_sggnm: str | None = None,
    lctn_emd_nm: str | None = None,
    opbd_dt_start: str | None = None,
    opbd_dt_end: str | None = None,
    apsl_evl_amt_start: int | None = None,
    apsl_evl_amt_end: int | None = None,
    lowst_bid_prc_start: int | None = None,
    lowst_bid_prc_end: int | None = None,
    pbct_stat_cd: str | None = None,
    onbid_cltr_nm: str | None = None,
) -> dict[str, Any]:
    """Return Onbid next-gen (B010003) bid result list for public auction items.

    This tool calls:
      - OnbidCltrBidRsltListSrvc/getCltrBidRsltList

    Natural-language → parameter mapping (for Claude):
      - Users usually do NOT ask for codes directly. When the user says things like
        "온비드 공매 물건", "입찰 결과", "낙찰/유찰", "개찰일", "감정가/최저입찰가 범위" you should:
        1) Extract intent and filters from the user message
        2) Fill the corresponding parameters below
        3) Call this tool to fetch the list

      - Location normalization:
        If the user provides a region in natural language ("서울 강남구", "부산 해운대구"),
        you can optionally call the Onbid address lookup tools first and then plug the
        results into:
          - lctn_sdnm (시/도) ← get_onbid_addr1_info
          - lctn_sggnm (시/군/구) ← get_onbid_addr2_info(addr1)
          - lctn_emd_nm (읍/면/동) ← get_onbid_addr3_info(addr2)

    Authentication:
      - Set ONBID_API_KEY (recommended), or
      - Reuse DATA_GO_KR_API_KEY.

    Args:
        page_no: Page number (1-based).
        num_of_rows: Items per page.
        cltr_type_cd: Item type code (e.g., "0001" real estate).
        prpt_div_cd: Property division code.
        dsps_mthod_cd: Disposal method code (e.g., "0001" sale, "0002" lease).
        bid_div_cd: Bid division code.
        lctn_sdnm/lctn_sggnm/lctn_emd_nm: Location (sido/sgg/emd) names.
        opbd_dt_start/opbd_dt_end: Opening date range (yyyyMMdd).
        apsl_evl_amt_start/end: Appraisal amount range (won).
        lowst_bid_prc_start/end: Lowest bid price range (won).
        pbct_stat_cd: Bid result status code.
        onbid_cltr_nm: Item name keyword.

    Returns:
        total_count: Total record count.
        items: Item list (raw fields from the API).
        page_no: Current page number.
        num_of_rows: Page size.
        error/message: Present on API/network/config failure.
    """
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    err = _check_onbid_api_key()
    if err:
        return err

    service_key = _get_data_go_kr_key_for_onbid()
    params: dict[str, Any] = {
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "resultType": "json",
    }
    if cltr_type_cd:
        params["cltrTypeCd"] = cltr_type_cd
    if prpt_div_cd:
        params["prptDivCd"] = prpt_div_cd
    if dsps_mthod_cd:
        params["dspsMthodCd"] = dsps_mthod_cd
    if bid_div_cd:
        params["bidDivCd"] = bid_div_cd
    if lctn_sdnm:
        params["lctnSdnm"] = lctn_sdnm
    if lctn_sggnm:
        params["lctnSggnm"] = lctn_sggnm
    if lctn_emd_nm:
        params["lctnEmdNm"] = lctn_emd_nm
    if opbd_dt_start:
        params["opbdDtStart"] = opbd_dt_start
    if opbd_dt_end:
        params["opbdDtEnd"] = opbd_dt_end
    if apsl_evl_amt_start is not None:
        params["apslEvlAmtStart"] = apsl_evl_amt_start
    if apsl_evl_amt_end is not None:
        params["apslEvlAmtEnd"] = apsl_evl_amt_end
    if lowst_bid_prc_start is not None:
        params["lowstBidPrcStart"] = lowst_bid_prc_start
    if lowst_bid_prc_end is not None:
        params["lowstBidPrcEnd"] = lowst_bid_prc_end
    if pbct_stat_cd:
        params["pbctStatCd"] = pbct_stat_cd
    if onbid_cltr_nm:
        params["onbidCltrNm"] = onbid_cltr_nm

    url = _build_url_with_service_key(_ONBID_BID_RESULT_LIST_URL, service_key, params)
    payload, fetch_err = await _fetch_json(url)
    if fetch_err:
        return fetch_err
    if not isinstance(payload, dict):
        return {"error": "parse_error", "message": "Unexpected response type"}

    result_code, body, items = _onbid_extract_items(payload)
    if result_code and result_code not in {"00", "000"}:
        return {
            "error": "api_error",
            "code": result_code,
            "message": str((payload.get("resultMsg") or "")).strip() or "Onbid API error",
        }

    try:
        total_count = int(body.get("totalCount") or 0)
    except (TypeError, ValueError):
        total_count = 0

    return {
        "total_count": total_count,
        "items": items,
        "page_no": int(body.get("pageNo") or page_no),
        "num_of_rows": int(body.get("numOfRows") or num_of_rows),
    }


@mcp.tool()
async def get_public_auction_item_detail(
    cltr_mng_no: str,
    pbct_cdtn_no: str,
    page_no: int = 1,
    num_of_rows: int = 20,
) -> dict[str, Any]:
    """Return Onbid next-gen (B010003) bid result detail for a single item.

    This tool calls:
      - OnbidCltrBidRsltDtlSrvc/getCltrBidRsltDtl

    Args:
        cltr_mng_no: 물건관리번호 (cltrMngNo).
        pbct_cdtn_no: 공매조건번호 (pbctCdtnNo).
        page_no: Page number (1-based).
        num_of_rows: Items per page.

    Returns:
        total_count: Total record count.
        items: Detail item list (raw fields from the API).
        page_no: Current page number.
        num_of_rows: Page size.
        error/message: Present on API/network/config failure.
    """
    if not cltr_mng_no.strip():
        return {"error": "validation_error", "message": "cltr_mng_no is required"}
    if not pbct_cdtn_no.strip():
        return {"error": "validation_error", "message": "pbct_cdtn_no is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    err = _check_onbid_api_key()
    if err:
        return err

    service_key = _get_data_go_kr_key_for_onbid()
    params: dict[str, Any] = {
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "resultType": "json",
        "cltrMngNo": cltr_mng_no,
        "pbctCdtnNo": pbct_cdtn_no,
    }

    url = _build_url_with_service_key(_ONBID_BID_RESULT_DETAIL_URL, service_key, params)
    payload, fetch_err = await _fetch_json(url)
    if fetch_err:
        return fetch_err
    if not isinstance(payload, dict):
        return {"error": "parse_error", "message": "Unexpected response type"}

    result_code, body, items = _onbid_extract_items(payload)
    if result_code and result_code not in {"00", "000"}:
        return {
            "error": "api_error",
            "code": result_code,
            "message": str((payload.get("resultMsg") or "")).strip() or "Onbid API error",
        }

    try:
        total_count = int(body.get("totalCount") or 0)
    except (TypeError, ValueError):
        total_count = 0

    return {
        "total_count": total_count,
        "items": items,
        "page_no": int(body.get("pageNo") or page_no),
        "num_of_rows": int(body.get("numOfRows") or num_of_rows),
    }


@mcp.tool()
async def get_onbid_thing_info_list(
    page_no: int = 1,
    num_of_rows: int = 20,
    dpsl_mtd_cd: str | None = None,
    ctgr_hirk_id: str | None = None,
    ctgr_hirk_id_mid: str | None = None,
    sido: str | None = None,
    sgk: str | None = None,
    emd: str | None = None,
    goods_price_from: int | None = None,
    goods_price_to: int | None = None,
    open_price_from: int | None = None,
    open_price_to: int | None = None,
    pbct_begn_dtm: str | None = None,
    pbct_cls_dtm: str | None = None,
    cltr_nm: str | None = None,
) -> dict[str, Any]:
    """Return Onbid ThingInfoInquireSvc (물건정보조회서비스) list items.

    Calls:
      - ThingInfoInquireSvc/getUnifyUsageCltr

    Notes:
      - The guide warns that requests from Python programs may be restricted.
      - Response is XML; this tool returns raw tag->text dicts per item.

    Natural-language → parameter mapping (for Claude):
      - Users typically describe what they want in words ("토지 공매", "주거용 건물", "서울 마포구",
        "감정가 5억 이하", "최저입찰가 3억 이하", "이번 달 입찰 마감") and do NOT ask for codes.
        When the user intent maps to coded parameters, call code-lookup tools to resolve
        values first, then call this tool.

      - Category/usage filters:
        Parameters:
          - CTGR_HIRK_ID (카테고리상위ID)
          - CTGR_HIRK_ID_MID (카테고리상위ID(중간))
        Resolution tools:
          1) get_onbid_top_code_info
          2) get_onbid_middle_code_info(ctgr_id=<CTGR_ID from step 1>)
          3) get_onbid_bottom_code_info(ctgr_id=<CTGR_ID from step 2>)  # optional, more specific
        How to apply:
          - If the user gives a broad category ("부동산", "토지", "주거용건물"):
            Use CTGR_ID from get_onbid_middle_code_info as CTGR_HIRK_ID_MID.
          - If the user gives a more specific subtype ("전", "답", "대지" 등 하위 용도):
            Use CTGR_ID from get_onbid_bottom_code_info as CTGR_HIRK_ID.
        Practical tip:
          - If uncertain, omit CTGR_* filters first, fetch a small list, then refine.

      - Location filters:
        Parameters:
          - SIDO (시/도), SGK (시/군/구), EMD (읍/면/동)
        Resolution tools:
          - get_onbid_addr1_info → returns ADDR1 candidates (시/도)
          - get_onbid_addr2_info(addr1) → returns ADDR2 candidates (시/군/구)
          - get_onbid_addr3_info(addr2) → returns ADDR3 candidates (읍/면/동)
        How to apply:
          - Use the selected ADDR* strings directly as SIDO/SGK/EMD.

    Args:
        page_no: Page number (1-based).
        num_of_rows: Items per page.
        dpsl_mtd_cd: 처분방식코드 ("0001" 매각, "0002" 임대/대부).
        ctgr_hirk_id: 카테고리상위ID.
        ctgr_hirk_id_mid: 카테고리상위ID(중간).
        sido/sgk/emd: 소재지(시도/시군구/읍면동).
        goods_price_from/to: 감정가 범위.
        open_price_from/to: 최저입찰가 범위.
        pbct_begn_dtm/pbct_cls_dtm: 입찰일자 From/To (YYYYMMDD).
        cltr_nm: 물건명 검색어.

    Returns:
        total_count: Total record count.
        items: List of raw records.
        page_no: Current page number.
        num_of_rows: Page size.
        error/message: Present on API/network/config failure.
    """
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    err = _check_onbid_api_key()
    if err:
        return err

    service_key = _get_data_go_kr_key_for_onbid()
    params: dict[str, Any] = {"pageNo": page_no, "numOfRows": num_of_rows}
    if dpsl_mtd_cd:
        params["DPSL_MTD_CD"] = dpsl_mtd_cd
    if ctgr_hirk_id:
        params["CTGR_HIRK_ID"] = ctgr_hirk_id
    if ctgr_hirk_id_mid:
        params["CTGR_HIRK_ID_MID"] = ctgr_hirk_id_mid
    if sido:
        params["SIDO"] = sido
    if sgk:
        params["SGK"] = sgk
    if emd:
        params["EMD"] = emd
    if goods_price_from is not None:
        params["GOODS_PRICE_FROM"] = goods_price_from
    if goods_price_to is not None:
        params["GOODS_PRICE_TO"] = goods_price_to
    if open_price_from is not None:
        params["OPEN_PRICE_FROM"] = open_price_from
    if open_price_to is not None:
        params["OPEN_PRICE_TO"] = open_price_to
    if pbct_begn_dtm:
        params["PBCT_BEGN_DTM"] = pbct_begn_dtm
    if pbct_cls_dtm:
        params["PBCT_CLS_DTM"] = pbct_cls_dtm
    if cltr_nm:
        params["CLTR_NM"] = cltr_nm

    url = _build_url_with_service_key(_ONBID_THING_INFO_LIST_URL, service_key, params)
    xml_text, fetch_err = await _fetch_xml(url)
    if fetch_err:
        return fetch_err
    assert xml_text is not None

    try:
        items, total_count, error_code, error_message = _parse_onbid_thing_info_list_xml(xml_text)
    except XmlParseError as exc:
        return {"error": "parse_error", "message": f"XML parse failed: {exc}"}

    if error_code is not None:
        return {
            "error": "api_error",
            "code": error_code,
            "message": error_message or "Onbid API error",
        }

    return {
        "total_count": total_count,
        "items": items,
        "page_no": page_no,
        "num_of_rows": num_of_rows,
    }


@mcp.tool()
async def get_onbid_top_code_info(
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid top-level usage/category codes.

    Korean keywords: 온비드 코드, 용도 코드, 카테고리 코드, 코드조회, CTGR_HIRK_ID

    Use this tool to discover the top-level CTGR_ID values, then call
    get_onbid_middle_code_info / get_onbid_bottom_code_info to drill down.
    These codes are needed to fill ThingInfoInquireSvc parameters such as
    CTGR_HIRK_ID and CTGR_HIRK_ID_MID.

    Typical usage:
      - User says "온비드에서 토지 공매 보고 싶어"
      - Call get_onbid_top_code_info → find "부동산"(CTGR_ID=10000)
      - Call get_onbid_middle_code_info(ctgr_id="10000") → find "토지"(CTGR_ID=10100)
      - Use CTGR_HIRK_ID_MID="10100" when calling get_onbid_thing_info_list

    Returns raw records containing:
      - CTGR_ID, CTGR_NM, CTGR_HIRK_ID, CTGR_HIRK_NM
    """
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_CODE_TOP_URL, {"pageNo": page_no, "numOfRows": num_of_rows}
    )


@mcp.tool()
async def get_onbid_middle_code_info(
    ctgr_id: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid middle-level usage/category codes under a parent CTGR_ID.

    Korean keywords: 온비드 코드, 용도 중간, 카테고리 중간, 코드조회, CTGR_HIRK_ID_MID

    Args:
        ctgr_id: Parent CTGR_ID from get_onbid_top_code_info (e.g. "10000").
    """
    if not ctgr_id.strip():
        return {"error": "validation_error", "message": "ctgr_id is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_CODE_MIDDLE_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "CTGR_ID": ctgr_id},
    )


@mcp.tool()
async def get_onbid_bottom_code_info(
    ctgr_id: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid bottom-level usage/category codes under a parent CTGR_ID.

    Korean keywords: 온비드 코드, 용도 하위, 카테고리 하위, 코드조회

    Args:
        ctgr_id: Parent CTGR_ID from get_onbid_middle_code_info (e.g. "10100").
    """
    if not ctgr_id.strip():
        return {"error": "validation_error", "message": "ctgr_id is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_CODE_BOTTOM_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "CTGR_ID": ctgr_id},
    )


@mcp.tool()
async def get_onbid_addr1_info(
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid address depth-1 list (시/도).

    Korean keywords: 온비드 주소 코드, 시도, 주소1, 코드조회

    Typical usage:
      - User says "서울 마포구"
      - Call get_onbid_addr1_info → pick ADDR1="서울특별시"
      - Call get_onbid_addr2_info(addr1="서울특별시") → pick ADDR2="마포구"
      - Optionally call get_onbid_addr3_info(addr2="마포구") for 읍/면/동
      - Use SIDO/SGK/EMD when calling get_onbid_thing_info_list
    """
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_ADDR1_URL, {"pageNo": page_no, "numOfRows": num_of_rows}
    )


@mcp.tool()
async def get_onbid_addr2_info(
    addr1: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid address depth-2 list (시/군/구) under addr1.

    Korean keywords: 온비드 주소 코드, 시군구, 주소2, 코드조회
    """
    if not addr1.strip():
        return {"error": "validation_error", "message": "addr1 is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_ADDR2_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "ADDR1": addr1},
    )


@mcp.tool()
async def get_onbid_addr3_info(
    addr2: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid address depth-3 list (읍/면/동) under addr2.

    Korean keywords: 온비드 주소 코드, 읍면동, 주소3, 코드조회
    """
    if not addr2.strip():
        return {"error": "validation_error", "message": "addr2 is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_ADDR3_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "ADDR2": addr2},
    )


@mcp.tool()
async def get_onbid_dtl_addr_info(
    addr3: str,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """Return Onbid detailed addresses under addr3.

    Korean keywords: 온비드 주소 코드, 상세주소, 코드조회
    """
    if not addr3.strip():
        return {"error": "validation_error", "message": "addr3 is required"}
    if page_no < 1:
        return {"error": "validation_error", "message": "page_no must be >= 1"}
    if num_of_rows < 1:
        return {"error": "validation_error", "message": "num_of_rows must be >= 1"}

    return await _run_onbid_code_info_tool(
        _ONBID_DTL_ADDR_URL,
        {"pageNo": page_no, "numOfRows": num_of_rows, "ADDR3": addr3},
    )
