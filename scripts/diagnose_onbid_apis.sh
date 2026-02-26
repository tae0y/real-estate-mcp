#!/usr/bin/env bash
# diagnose_onbid_apis.sh — Onbid API 진단 스크립트
#
# 1단계: curl로 각 API 엔드포인트를 직접 호출하여 응답 확인
# 2단계: pytest로 E2E 테스트를 실행하여 tool 함수 정상 동작 확인
#
# Usage:
#   ./scripts/diagnose_onbid_apis.sh
#   # or
#   bash scripts/diagnose_onbid_apis.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── .env 로드 ──────────────────────────────────────────────────────
ENV_FILE="$PROJECT_ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: .env 파일이 없습니다 ($ENV_FILE)"
    exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

# API 키 결정: ONBID_API_KEY > DATA_GO_KR_API_KEY
SERVICE_KEY="${ONBID_API_KEY:-${DATA_GO_KR_API_KEY:-}}"
if [[ -z "$SERVICE_KEY" ]]; then
    echo "ERROR: ONBID_API_KEY 또는 DATA_GO_KR_API_KEY 가 .env에 설정되어 있지 않습니다."
    exit 1
fi

# URL-encode the key (+ → %2B, = → %3D, / → %2F)
ENCODED_KEY=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$SERVICE_KEY")

# ── 공통 함수 ──────────────────────────────────────────────────────
PASS=0
FAIL=0

check_api() {
    local label="$1"
    local url="$2"
    local expected_content_type="${3:-}"  # "json" or "xml"

    echo ""
    echo "── $label ──"
    echo "   URL: ${url%%serviceKey=*}serviceKey=***"

    if ! HTTP_CODE=$(curl -s -o /tmp/diagnose_response.txt -w "%{http_code}" --max-time 20 "$url" 2>/dev/null); then
        HTTP_CODE="000"
    fi

    if [[ "$HTTP_CODE" == "000" ]]; then
        echo "   결과: FAIL (timeout 또는 네트워크 오류)"
        FAIL=$((FAIL + 1))
        return
    fi

    if [[ "$HTTP_CODE" != "200" ]]; then
        echo "   결과: FAIL (HTTP $HTTP_CODE)"
        FAIL=$((FAIL + 1))
        return
    fi

    # 응답 내용 확인
    BODY=$(cat /tmp/diagnose_response.txt)
    if [[ "$expected_content_type" == "json" ]]; then
        # JSON: resultCode "00" 또는 totalCount 존재 여부
        if echo "$BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
# Check various wrapper formats
if 'response' in data:
    code = data['response'].get('header', {}).get('resultCode', '')
elif 'header' in data:
    code = data['header'].get('resultCode', '')
elif 'result' in data:
    code = data['result'].get('resultCode', '')
else:
    code = data.get('resultCode', '')
if code in ('00', '000', ''):
    sys.exit(0)
else:
    print(f'resultCode={code}', file=sys.stderr)
    sys.exit(1)
" 2>/tmp/diagnose_err.txt; then
            echo "   결과: 정상 (HTTP 200, API 응답 OK)"
            PASS=$((PASS + 1))
        else
            ERR_MSG=$(cat /tmp/diagnose_err.txt 2>/dev/null || echo "unknown")
            echo "   결과: FAIL (HTTP 200 but API error: $ERR_MSG)"
            echo "   응답 앞부분: $(echo "$BODY" | head -c 200)"
            FAIL=$((FAIL + 1))
        fi
    elif [[ "$expected_content_type" == "xml" ]]; then
        # XML: resultCode 00 확인
        if echo "$BODY" | python3 -c "
import sys
from defusedxml.ElementTree import fromstring
root = fromstring(sys.stdin.read())
code_el = root.find('.//resultCode')
code = code_el.text if code_el is not None else ''
if code in ('00', '000', ''):
    sys.exit(0)
else:
    print(f'resultCode={code}', file=sys.stderr)
    sys.exit(1)
" 2>/tmp/diagnose_err.txt; then
            echo "   결과: 정상 (HTTP 200, API 응답 OK)"
            PASS=$((PASS + 1))
        else
            ERR_MSG=$(cat /tmp/diagnose_err.txt 2>/dev/null || echo "unknown")
            echo "   결과: FAIL (HTTP 200 but API error: $ERR_MSG)"
            echo "   응답 앞부분: $(echo "$BODY" | head -c 200)"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "   결과: 정상 (HTTP 200)"
        PASS=$((PASS + 1))
    fi
}

# ── 날짜 범위 설정 (이번 달) ────────────────────────────────────────
YEAR_MONTH=$(date +%Y%m)
DT_START="${YEAR_MONTH}01"
DT_END=$(date +%Y%m%d)

echo "======================================================================"
echo " Onbid API 진단 스크립트"
echo " 조회 기간: $DT_START ~ $DT_END"
echo "======================================================================"

# ── 1단계: curl로 API 직접 호출 ────────────────────────────────────

echo ""
echo "▶ 1단계: curl로 API 엔드포인트 직접 호출"
echo "----------------------------------------------------------------------"

# 1) B010003 입찰결과 목록
check_api \
    "B010003 입찰결과 목록 (getCltrBidRsltList)" \
    "https://apis.data.go.kr/B010003/OnbidCltrBidRsltListSrvc/getCltrBidRsltList?serviceKey=${ENCODED_KEY}&pageNo=1&numOfRows=1&resultType=json&cltrTypeCd=0001&prptDivCd=0007&dspsMthodCd=0001&bidDivCd=0001&opbdDtStart=${DT_START}&opbdDtEnd=${DT_END}" \
    "json"

# 2) B010003 입찰결과 상세 (목록에서 가져온 번호 필요 — 임의값으로 형식만 확인)
# 상세는 목록 결과가 있어야 호출 가능하므로, 목록에서 첫 번째 아이템을 추출
CLTR_MNG_NO=""
PBCT_CDTN_NO=""
if [[ -f /tmp/diagnose_response.txt ]]; then
    eval "$(python3 -c "
import json, sys
try:
    data = json.load(open('/tmp/diagnose_response.txt'))
    body = None
    if 'response' in data:
        body = data['response'].get('body', {})
    elif 'header' in data and 'body' in data:
        body = data.get('body', {})
    if body:
        items_raw = body.get('items', {})
        if isinstance(items_raw, dict):
            items = items_raw.get('item', [])
        else:
            items = items_raw
        if isinstance(items, dict):
            items = [items]
        if items:
            print(f'CLTR_MNG_NO=\"{items[0].get(\"cltrMngNo\", \"\")}\"')
            print(f'PBCT_CDTN_NO=\"{items[0].get(\"pbctCdtnNo\", \"\")}\"')
except Exception:
    pass
" 2>/dev/null || true)"
fi

if [[ -n "$CLTR_MNG_NO" && -n "$PBCT_CDTN_NO" ]]; then
    check_api \
        "B010003 입찰결과 상세 (getCltrBidRsltDtl)" \
        "https://apis.data.go.kr/B010003/OnbidCltrBidRsltDtlSrvc/getCltrBidRsltDtl?serviceKey=${ENCODED_KEY}&pageNo=1&numOfRows=1&resultType=json&cltrMngNo=${CLTR_MNG_NO}&pbctCdtnNo=${PBCT_CDTN_NO}" \
        "json"
else
    echo ""
    echo "── B010003 입찰결과 상세 (getCltrBidRsltDtl) ──"
    echo "   결과: SKIP (목록에서 유효한 아이템을 가져오지 못함)"
fi

# 3) ThingInfoInquireSvc (openapi.onbid.co.kr) — XML
check_api \
    "ThingInfoInquireSvc 물건정보 목록 (getUnifyUsageCltr)" \
    "http://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr?serviceKey=${ENCODED_KEY}&pageNo=1&numOfRows=1" \
    "xml"

# 4) 코드 조회 — 상위
check_api \
    "OnbidCodeInfoInquireSvc 코드 상위 (getOnbidTopCodeInfo)" \
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidTopCodeInfo?serviceKey=${ENCODED_KEY}&pageNo=1&numOfRows=5" \
    "xml"

# 5) 코드 조회 — 중간 (부동산=10000)
check_api \
    "OnbidCodeInfoInquireSvc 코드 중간 (getOnbidMiddleCodeInfo)" \
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidMiddleCodeInfo?serviceKey=${ENCODED_KEY}&pageNo=1&numOfRows=5&CTGR_ID=10000" \
    "xml"

# 6) 주소 조회 — 시도
check_api \
    "OnbidCodeInfoInquireSvc 주소 시도 (getOnbidAddr1Info)" \
    "http://openapi.onbid.co.kr/openapi/services/OnbidCodeInfoInquireSvc/getOnbidAddr1Info?serviceKey=${ENCODED_KEY}&pageNo=1&numOfRows=5" \
    "xml"

# ── 2단계: E2E 테스트 (tool 함수 호출) ─────────────────────────────

echo ""
echo ""
echo "▶ 2단계: tool 함수 E2E 테스트 (pytest)"
echo "----------------------------------------------------------------------"
echo ""

cd "$PROJECT_ROOT"
uv run pytest tests/mcp_server/test_onbid_e2e.py -v -m e2e --no-header --override-ini="addopts=" 2>&1 || true

# ── 결과 요약 ──────────────────────────────────────────────────────

echo ""
echo "======================================================================"
echo " 1단계 curl 결과 요약: 정상=$PASS / 실패=$FAIL"
echo "======================================================================"

rm -f /tmp/diagnose_response.txt /tmp/diagnose_err.txt
