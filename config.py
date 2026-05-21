APP_VERSION = "V62-7"

PAGE_TITLE = "My Quant Asset Sim (V62-7)"

MAIN_TITLE = "💰 전담 퀀트 금융자산 종합 관리 시스템 (V62-7)"

UPDATE_MESSAGE = (
    "💡 V62-7 업데이트: 할인율별 수익률 모델에 은퇴 후 주식 7 현금 3 또는 주식 6 현금 4 자산배분을 적용"
)

N_SIMULATIONS = 5000
SEARCH_SIMULATIONS = 500
SENSITIVITY_SIMULATIONS = 1200
SCENARIO_COMPARISON_SIMULATIONS = 1200
SCENARIO_COMPARISON_SEARCH_SIMULATIONS = 400

# 고정 seed 검증 모드
# 개발·검증 단계에서 같은 입력이면 같은 난수 경로가 나오도록 합니다.
FIXED_RANDOM_SEED_ENABLED = True
RANDOM_SEED = 20260520

# 수익률 분포 현실화 기본값
# 모든 현실화 기능은 토글 없이 기본 적용합니다.
# 팻테일 난수는 유지하되, 총 금융자산 포트폴리오에 비현실적인 초극단값은
# 하방·상방을 모두 보정해 결과 해석 왜곡을 줄입니다.
FAT_TAIL_DF = 10
MIN_TOTAL_ANNUAL_RETURN = -0.60
MAX_TOTAL_ANNUAL_RETURN = 1.00
INFLATION_SHOCK_ANNUAL_PROBABILITY = 0.025
INFLATION_SHOCK_DURATION_YEARS = 3
INFLATION_SHOCK_INFLATION_ADDON = 0.04
INFLATION_SHOCK_RETURN_PENALTY = 0.04
INFLATION_SHOCK_VOL_MULTIPLIER = 1.30
MEAN_REVERSION_STRENGTH = 0.05

# 자동 적용 플래그
# V62-7에서는 계좌이동 기반 포트폴리오 전환을 기본 엔진에서 제거합니다.
AUTO_APPLY_DWZ_SPENDING = True
AUTO_APPLY_FLEX_SPENDING = True
AUTO_APPLY_PORTFOLIO_TRANSITION = False
AUTO_APPLY_FAT_TAIL = True
AUTO_APPLY_INFLATION_SHOCK = True

# 소득·지출 물가 반영 원칙
# - 수입은 명목 고정: 물가상승률만큼 자동 증가하지 않는 보수적 가정
# - 지출은 현재가치 입력: 기본지출과 기간성 지출은 명목상 물가만큼 증가한다고 가정
INCOME_INFLATION_LINKED = False
EXPENSE_INFLATION_LINKED = True

# 지출 구조 고정값
# 기본 입력은 월 기본지출 1개만 유지하고, 내부에서 필수지출/조정가능지출로 분해합니다.
ESSENTIAL_SPENDING_RATIO = 0.70
FLEXIBLE_SPENDING_RATIO = 1.0 - ESSENTIAL_SPENDING_RATIO

# 파산확률 판단 기준
# 추가지출 가능액은 DWZ 허용 기준 15%를 기준으로 계산합니다.
# 결과 화면에는 안전 기준 10%, DWZ 기준 15%, 위험 경고선 20%를 함께 표시합니다.
STANDARD_TARGET_RUIN_PROB = 10.0
DWZ_TARGET_RUIN_PROB = 15.0
WARNING_RUIN_PROB = 20.0

# 상하위 30% 제외 평균 기준 여유자금
# 극단적으로 나쁜 경로와 극단적으로 좋은 경로를 모두 제외하고, 중앙 40% 경로의 평균을 계산합니다.
# 참고용 여유자금은 이 절사평균 최종자산이 현재가치 1억 원 이상 남는 월 추가지출로 계산합니다.
TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO = 0.30
TRIMMED_AVERAGE_UPPER_EXCLUSION_RATIO = 0.30
TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON = 10000

# 현재 포트폴리오 기준:
# 국내 퀀트 10.7억 + 연금저축/ISA 듀얼모멘텀 1.2억 + VOO 0.7억 = 총 12.6억
# V62-7 기본 엔진은 계좌별 잔고를 따로 굴리지 않고 총 금융자산 통합 시뮬레이션을 수행합니다.
# 후보1 알파 감소 모델
# 전략명: 국내퀀트 11월말-7월말 + VOO 7월말-11월말
# 분석기간: 2006년 11월말-2024년 11월말, 2024년 12월-2026년 4월 제외
# 변동성은 코스피200 8개월 + S&P500 4개월 패시브 계절 포트폴리오 17.4%를 기준으로 약간 상향한 18.5%를 사용합니다.
ALPHA_MODEL_NAME = "후보1 국내퀀트 11-7 + VOO 7-11"
ALPHA_MODEL_BASE_CAGR = 0.3077
ALPHA_MODEL_PASSIVE_SEASONAL_VOLATILITY = 0.1740
ALPHA_MODEL_BASE_VOLATILITY = 0.1850
ALPHA_MODEL_BASE_MDD = -0.2227

ALPHA_MODEL_DISCOUNT_OPTIONS = {
    "10% 할인": 0.10,
    "20% 할인": 0.20,
    "30% 할인": 0.30,
    "40% 할인": 0.40,
    "50% 할인": 0.50,
}
ALPHA_MODEL_DEFAULT_DISCOUNT_LABEL = "30% 할인"

# 은퇴 후에는 전략을 100% 유지하지 않고, 주식전략과 현금성 자산을 섞은 배분으로 계산합니다.
# 현금수익률은 명목 기준 보수적 중립값으로 두며, 현금 변동성은 0%로 봅니다.
ALPHA_MODEL_CASH_RETURN = 0.025
ALPHA_MODEL_DEFAULT_RETIREMENT_ALLOCATION_LABEL = "주식 7 현금 3"
ALPHA_MODEL_RETIREMENT_ALLOCATION_OPTIONS = {
    "주식 7 현금 3": {"stock_weight": 0.70, "cash_weight": 0.30},
    "주식 6 현금 4": {"stock_weight": 0.60, "cash_weight": 0.40},
}

# 업로드 자료 기반 원자료 분석 요약
# V62-7에서는 계좌별 엔진을 기본으로 쓰지 않지만, 수익률 가정 검토용 참고값으로 유지합니다.
DATA_ANALYSIS_SUMMARY = [
    {
        "자산/전략": "국내퀀트 조합",
        "분석기간": "2006-2025",
        "원자료 CAGR": 26.23,
        "연간수익률 평균": 29.51,
        "연간 변동성": 29.95,
        "월수익률 연환산 변동성": 21.00,
        "MDD": -30.22,
        "비고": "11-3월, 4-5월, 6-7월 전략 합성. 8-11월 단기채 구간은 자료 부재로 0% 처리",
    },
    {
        "자산/전략": "듀얼모멘텀",
        "분석기간": "2006-2025",
        "원자료 CAGR": 15.31,
        "연간수익률 평균": 16.57,
        "연간 변동성": 17.11,
        "월수익률 연환산 변동성": 17.57,
        "MDD": -26.76,
        "비고": "S&P500/나스닥100/금 6개월 모멘텀, 음수면 달러 3개월물. 원화 기준",
    },
    {
        "자산/전략": "VOO 대용 S&P500",
        "분석기간": "2006-2025",
        "원자료 CAGR": 10.85,
        "연간수익률 평균": 11.88,
        "연간 변동성": 15.59,
        "월수익률 연환산 변동성": 13.17,
        "MDD": -23.86,
        "비고": "S&P500 지수 + USD/KRW 환율 반영. 원화 기준",
    },
]

# 계좌 관련 현재 기준값
# 총자산 시뮬레이션에서 계좌 간 이동은 총 금융자산을 바꾸지 않으므로 별도 현금흐름으로 차감하지 않습니다.
INITIAL_QUANT_ASSET_MANWON = 107000
INITIAL_PENSION_ASSET_MANWON = 12000
INITIAL_ISA_ASSET_MANWON = 0
INITIAL_DUAL_MOMENTUM_ASSET_MANWON = INITIAL_PENSION_ASSET_MANWON + INITIAL_ISA_ASSET_MANWON
INITIAL_VOO_ASSET_MANWON = 7000

# 최종 정책: 연금저축은 세액공제 목적의 연 600만 원만 납입, ISA 신규 납입은 기본 0원.
RETIREMENT_SAVINGS_ANNUAL_CONTRIBUTION_MANWON = 600
ISA_ANNUAL_CONTRIBUTION_MANWON = 0
ISA_MATURITY_TO_PENSION_DEFAULT_MANWON = 0

# 과거 V60-7의 3,800만 원 이전 가정은 제거합니다. 호환용 상수는 0으로 둡니다.
ANNUAL_TRANSFER_TO_DUAL_MANWON = 0

# 국내퀀트 운용규모 페널티
# 통합자산 모델에서는 현재 국내퀀트 시작비중을 기준으로 추정 국내퀀트 운용금액을 산출합니다.
# 단위: 만 원, 페널티는 연 수익률 차감률(decimal)
QUANT_SIZE_PENALTY_TIERS = [
    (150000, 0.000),  # 15억 이하
    (250000, 0.003),  # 15억 초과-25억
    (400000, 0.007),  # 25억 초과-40억
    (700000, 0.012),  # 40억 초과-70억
    (float("inf"), 0.018),  # 70억 초과
]
