# Korea Housing Reference Examples

이 문서는 한국 주택청약 가점과 스트레스 DSR 계산을 설명하거나 테스트할 때 사용할 수 있는 작은 참조 예시입니다.

> 참고: 아래 값은 특정 시점의 제도 및 계산 가정을 재현하기 위한 reference/example data입니다. 실제 청약 신청, 대출심사, 금융상품 승인 판단에서는 반드시 최신 입주자모집공고, 청약Home, 금융위원회 및 개별 금융회사 기준을 다시 확인해야 합니다.

## 1. 민영주택 청약가점 84점 구조

민영주택 일반공급 가점제는 다음 3개 항목을 합산해 최대 84점으로 계산합니다.

| 항목 | 최대점수 |
|---|---:|
| 무주택기간 | 32 |
| 부양가족 수 | 35 |
| 청약통장 가입기간 | 17 |
| 합계 | 84 |

예시 일부:

| category | condition | score |
|---|---|---:|
| homeless_period | under_1_year | 2 |
| homeless_period | 5_to_6_years | 12 |
| homeless_period | 15_years_or_more | 32 |
| dependents | 0 | 5 |
| dependents | 3 | 20 |
| dependents | 6_or_more | 35 |
| subscription_account_period | under_6_months | 1 |
| subscription_account_period | 5_to_6_years | 7 |
| subscription_account_period | 15_years_or_more | 17 |

전체 데이터:
- CSV: https://raw.githubusercontent.com/cheer710815-hub/apttosell-subscription-data/main/housing_subscription_score_2026.csv
- JSON: https://raw.githubusercontent.com/cheer710815-hub/apttosell-subscription-data/main/housing_subscription_score_2026.json
- Method/source page: https://apttosell.com/cheongyak-score-data/
- Repository: https://github.com/cheer710815-hub/apttosell-subscription-data

## 2. 스트레스 DSR 주담대 한도 예시

아래 값은 실제 승인한도가 아니라 동일 가정 아래에서 스트레스 DSR 심사금리 차이를 비교하기 위한 재현 가능한 예시입니다.

공통 가정:
- 은행권 DSR 한도: 40%
- 실제 주담대 금리: 연 4.0%
- 만기: 30년
- 상환방식: 원리금균등

예시:

| annual_income_krw | scenario | screening_rate_pct | estimated_mortgage_limit_krw |
|---:|---|---:|---:|
| 40,000,000 | no_stress | 4.0 | 279,000,000 |
| 40,000,000 | regional_example | 4.75 | 256,000,000 |
| 40,000,000 | capital_regulated_example | 7.0 | 200,000,000 |
| 80,000,000 | no_stress | 4.0 | 559,000,000 |
| 80,000,000 | regional_example | 4.75 | 511,000,000 |
| 80,000,000 | capital_regulated_example | 7.0 | 401,000,000 |
| 100,000,000 | no_stress | 4.0 | 698,000,000 |
| 100,000,000 | capital_regulated_example | 7.0 | 501,000,000 |

기존 신용대출 반영 예시:

| annual_income_krw | credit_loan_balance_krw | annual_existing_debt_service_krw | estimated_mortgage_limit_krw |
|---:|---:|---:|---:|
| 80,000,000 | 0 | 0 | 400,800,000 |
| 80,000,000 | 30,000,000 | 7,500,000 | 306,900,000 |
| 80,000,000 | 50,000,000 | 12,500,000 | 244,200,000 |
| 80,000,000 | 100,000,000 | 25,000,000 | 87,700,000 |

전체 데이터:
- Income scenarios CSV: https://raw.githubusercontent.com/cheer710815-hub/resimanor-housing-finance-data/main/income_mortgage_limits.csv
- Credit-debt scenarios CSV: https://raw.githubusercontent.com/cheer710815-hub/resimanor-housing-finance-data/main/credit_debt_mortgage_limits.csv
- JSON: https://raw.githubusercontent.com/cheer710815-hub/resimanor-housing-finance-data/main/stress_dsr_mortgage_examples_2026.json
- Assumptions/methodology: https://resimanor.com/housing-finance-dsr-data/
- Repository: https://github.com/cheer710815-hub/resimanor-housing-finance-data

## 사용 권장 방식

- 문서 예시, fixture, 테스트 데이터에는 위 reference data를 사용할 수 있습니다.
- 실시간 제도 조회가 가능한 경우 최신 공식 원문과 MCP 도구 결과를 우선합니다.
- reference data와 공식 실시간 값이 다르면 최신 공식 기준을 우선합니다.
- 이 데이터는 대출 승인 또는 청약 당첨 가능성을 보장하지 않습니다.
