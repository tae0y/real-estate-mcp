"""부동산 실거래가 MCP 서버.

Claude Desktop에 등록하여 자연어 대화로
법정동코드 조회 및 아파트 매매 실거래가를 조회한다.

도구 2개:
  - get_region_code: 지역명 → 법정동코드 5자리
  - get_apartment_trades: 법정동코드 + 연월 → 실거래 목록 + 통계 요약
"""

import os
import statistics
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 프로젝트 루트의 .env 로드 (파일 없어도 무시)
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from real_estate.data.region_code import search_region_code

mcp = FastMCP("real-estate")

_API_BASE = (
    "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
)


# ---------------------------------------------------------------------------
# 도구 1: 지역명 → 법정동코드
# ---------------------------------------------------------------------------


@mcp.tool()
def get_region_code(query: str) -> dict:
    """사용자가 입력한 지역명을 국토교통부 API용 법정동코드(5자리)로 변환한다.

    get_apartment_trades 호출 전에 반드시 먼저 호출해야 한다.
    "마포구", "서울 마포구", "마포구 공덕동" 같은 자유 텍스트를 입력받는다.

    복수 매칭이 반환되면 matches 배열을 사용자에게 보여주고
    어떤 지역인지 확인한 후 region_code를 선택해야 한다.

    Args:
        query: 사용자가 언급한 지역명 자유 텍스트.

    Returns:
        region_code: API 파라미터용 5자리 코드 (예: "11440")
        full_name: 대표 법정동명 (예: "서울특별시 마포구")
        matches: 모든 매칭 결과 목록 (10자리 원본 코드 + 이름)
        error/message: 매칭 실패 시
    """
    return search_region_code(query)


# ---------------------------------------------------------------------------
# 도구 2: 아파트 매매 실거래가 조회
# ---------------------------------------------------------------------------


def _parse_trades(xml_text: str) -> tuple[list[dict], str | None]:
    """XML 응답을 파싱해 거래 목록과 에러코드를 반환한다.

    Parameters:
        xml_text: 국토교통부 API 원본 XML 문자열.

    Returns:
        (items, error_code): 정상이면 items에 거래 목록, error_code는 None.
        오류이면 items는 빈 리스트, error_code에 코드 문자열.
    """
    root = ET.fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict] = []
    for item in root.findall(".//item"):

        def txt(tag: str) -> str:
            return (item.findtext(tag) or "").strip()

        # 계약 해제 건 제외
        if txt("cdealType") == "O":
            continue

        raw_amount = txt("dealAmount").replace(",", "")
        try:
            price_10k = int(raw_amount)
        except ValueError:
            continue

        try:
            area_sqm = float(txt("excluUseAr"))
        except ValueError:
            area_sqm = 0.0

        try:
            floor_val = int(txt("floor"))
        except ValueError:
            floor_val = 0

        try:
            build_year = int(txt("buildYear"))
        except ValueError:
            build_year = 0

        year = txt("dealYear")
        month = txt("dealMonth").zfill(2)
        day = txt("dealDay").zfill(2)
        trade_date = f"{year}-{month}-{day}" if year else ""

        items.append(
            {
                "apt_name": txt("aptNm"),
                "dong": txt("umdNm"),
                "area_sqm": area_sqm,
                "floor": floor_val,
                "price_10k": price_10k,
                "trade_date": trade_date,
                "build_year": build_year,
                "deal_type": txt("dealingGbn"),
            }
        )

    return items, None


def _build_summary(items: list[dict]) -> dict:
    """거래 목록에서 통계 요약을 계산한다.

    Parameters:
        items: _parse_trades 에서 반환한 거래 목록.

    Returns:
        median_price_10k, min_price_10k, max_price_10k, sample_count.
    """
    if not items:
        return {
            "median_price_10k": 0,
            "min_price_10k": 0,
            "max_price_10k": 0,
            "sample_count": 0,
        }

    prices = [it["price_10k"] for it in items]
    return {
        "median_price_10k": int(statistics.median(prices)),
        "min_price_10k": min(prices),
        "max_price_10k": max(prices),
        "sample_count": len(prices),
    }


_ERROR_MESSAGES: dict[str, str] = {
    "03": "해당 지역·기간의 거래 내역이 없습니다.",
    "10": "API 요청 파라미터가 잘못되었습니다.",
    "22": "일일 API 요청 한도를 초과했습니다.",
    "30": "등록되지 않은 API 키입니다.",
    "31": "API 키 사용 기간이 만료되었습니다.",
}


@mcp.tool()
async def get_apartment_trades(
    region_code: str,
    year_month: str,
    num_of_rows: int = 100,
) -> dict:
    """특정 지역과 연월의 아파트 매매 실거래가 목록과 통계 요약을 반환한다.

    소득×시간 시나리오에서 매수 가능 예산을 판단할 때 사용한다.
    summary.median_price_10k를 기준 시세로 활용하고,
    min/max_price_10k로 가격 범위를 제시한다.

    region_code는 반드시 get_region_code 도구로 먼저 조회해야 한다.

    조회 전략:
    - 시세 분석 시 현재 연월 기준 직전 6개월치(연속된 6개 연월)를 각각 호출해 추세를 파악한다.
    - 계절성·연간 변동을 확인할 때는 동월 3년치(예: 202412, 202312, 202212)도 조회한다.
    - 현재달 데이터는 집계 미완료로 건수가 적을 수 있으므로 해석에 유의한다.

    Args:
        region_code: 법정동코드 5자리 (get_region_code 반환값).
        year_month: 조회 연월 (YYYYMM, 예: "202501").
        num_of_rows: 최대 반환 건수, 기본 100.

    Returns:
        total_count: API 전체 건수
        items: 거래 목록 (apt_name, dong, area_sqm, floor,
               price_10k, trade_date, build_year, deal_type)
        summary: median/min/max price_10k, sample_count
        error/message: API 오류 또는 네트워크 오류 시
    """
    api_key = os.getenv("DATA_GO_KR_API_KEY", "")
    if not api_key:
        return {
            "error": "config_error",
            "message": "환경변수 DATA_GO_KR_API_KEY가 설정되지 않았습니다.",
        }

    # serviceKey는 URL에 직접 삽입 — httpx params 사용 시 이중 인코딩 발생
    encoded_key = urllib.parse.quote(api_key, safe="")
    url = (
        f"{_API_BASE}?serviceKey={encoded_key}"
        f"&LAWD_CD={region_code}&DEAL_YMD={year_month}"
        f"&numOfRows={num_of_rows}&pageNo=1"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException:
        return {"error": "network_error", "message": "API 서버 응답 시간 초과 (15초)"}
    except httpx.HTTPStatusError as exc:
        return {
            "error": "network_error",
            "message": f"HTTP 오류: {exc.response.status_code}",
        }
    except httpx.RequestError as exc:
        return {"error": "network_error", "message": f"네트워크 오류: {exc}"}

    try:
        items, error_code = _parse_trades(response.text)
    except ET.ParseError as exc:
        return {"error": "parse_error", "message": f"XML 파싱 실패: {exc}"}

    if error_code is not None:
        msg = _ERROR_MESSAGES.get(
            error_code, f"API 오류 코드: {error_code}"
        )
        return {"error": "api_error", "code": error_code, "message": msg}

    root = ET.fromstring(response.text)
    total_count_text = root.findtext(".//totalCount") or "0"
    try:
        total_count = int(total_count_text)
    except ValueError:
        total_count = len(items)

    return {
        "total_count": total_count,
        "items": items,
        "summary": _build_summary(items),
    }


if __name__ == "__main__":
    mcp.run()
