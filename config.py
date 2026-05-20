APP_VERSION = "V61-4"

PAGE_TITLE = "My Quant Asset Sim (V61-4)"

MAIN_TITLE = "💰 전담 퀀트 금융자산 종합 관리 시스템 (V61-4)"

UPDATE_MESSAGE = (
    "💡 V61-4 업데이트: 계좌별 추적표를 대표경로 1개가 아니라 "
    "계좌별 중앙값·하위10%·누적이체/인출 기준으로 표시"
)

N_SIMULATIONS = 5000
SEARCH_SIMULATIONS = 500
SENSITIVITY_SIMULATIONS = 1200
SCENARIO_COMPARISON_SIMULATIONS = 1200
SCENARIO_COMPARISON_SEARCH_SIMULATIONS = 400

# 고정 seed 검증 모드
# 개발·검증 단계에서 같은 입력이면 같은 난수 경로가 나오도록 합니다.
# 결과 차이가 코드 변경 때문인지 난수 때문인지 분리하기 위한 장치입니다.
FIXED_RANDOM_SEED_ENABLED = True
RANDOM_SEED = 20260520

# 수익률 분포 현실화 기본값
# 모든 현실화 기능은 토글 없이 기본 적용합니다.
FAT_TAIL_DF = 10
INFLATION_SHOCK_ANNUAL_PROBABILITY = 0.025
INFLATION_SHOCK_DURATION_YEARS = 3
INFLATION_SHOCK_INFLATION_ADDON = 0.04
INFLATION_SHOCK_RETURN_PENALTY = 0.04
INFLATION_SHOCK_VOL_MULTIPLIER = 1.30
MEAN_REVERSION_STRENGTH = 0.05

# 계좌별 연간 수익률 하한선
# t분포 난수는 이론상 -100% 이하 수익률을 만들 수 있습니다.
# 비레버리지 계좌가 수익률만으로 정확히 0원이 되는 현상은 비현실적이므로,
# 연간 손실은 -95%에서 하한 처리합니다. 0원은 인출로만 발생하도록 원인을 분리합니다.
MIN_ACCOUNT_ANNUAL_RETURN = -0.95

# 자동 적용 플래그
# UI에는 노출하지 않고, 시뮬레이터 내부에서 기본 적용합니다.
AUTO_APPLY_DWZ_SPENDING = True
AUTO_APPLY_FLEX_SPENDING = True
AUTO_APPLY_PORTFOLIO_TRANSITION = True
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

# 기존 UI 호환용 통합 시나리오 옵션
# 실제 V61-1 엔진은 아래 ACCOUNT_SCENARIOS를 사용하고,
# 기존 UI에서 선택된 은퇴 전 기대수익률을 기준으로 보수/기본/공격을 매핑합니다.
DEFAULT_SCENARIO_INDEX = 1

SCENARIO_OPTIONS = {
    "보수: 은퇴전 15.0% / 변동성 26.0% ➡️ 은퇴후 10.5% / 17.0%": (
        15.0,
        26.0,
        10.5,
        17.0,
    ),
    "기본: 은퇴전 18.0% / 변동성 25.0% ➡️ 은퇴후 12.0% / 16.0%": (
        18.0,
        25.0,
        12.0,
        16.0,
    ),
    "공격: 은퇴전 20.0% / 변동성 25.0% ➡️ 은퇴후 13.5% / 17.0%": (
        20.0,
        25.0,
        13.5,
        17.0,
    ),
}

# 업로드 자료 기반 원자료 분석 요약
# 국내퀀트 7월말~11월말 단기채 구간은 국내 단기채 월별수익률 자료가 없어 0%로 처리했습니다.
DATA_ANALYSIS_SUMMARY = [
    {
        "자산/전략": "국내퀀트 조합",
        "분석기간": "2006~2025",
        "원자료 CAGR": 26.23,
        "연간수익률 평균": 29.51,
        "연간 변동성": 29.95,
        "월수익률 연환산 변동성": 21.00,
        "MDD": -30.22,
        "비고": "11~3월, 4~5월, 6~7월 전략 합성. 8~11월 단기채 구간은 자료 부재로 0% 처리",
    },
    {
        "자산/전략": "듀얼모멘텀",
        "분석기간": "2006~2025",
        "원자료 CAGR": 15.31,
        "연간수익률 평균": 16.57,
        "연간 변동성": 17.11,
        "월수익률 연환산 변동성": 17.57,
        "MDD": -26.76,
        "비고": "S&P500/나스닥100/금 6개월 모멘텀, 음수면 달러 3개월물. 원화 기준",
    },
    {
        "자산/전략": "VOO 대용 S&P500",
        "분석기간": "2006~2025",
        "원자료 CAGR": 10.85,
        "연간수익률 평균": 11.88,
        "연간 변동성": 15.59,
        "월수익률 연환산 변동성": 13.17,
        "MDD": -23.86,
        "비고": "S&P500 지수 + USD/KRW 환율 반영. 원화 기준",
    },
]

# 계좌별 수익률 시나리오
# 원자료를 그대로 미래값으로 쓰지 않고, 현실적 할인값을 기본값으로 둡니다.
ACCOUNT_SCENARIOS = {
    "보수": {
        "quant_return": 15.0,
        "quant_vol": 30.0,
        "dual_return": 10.0,
        "dual_vol": 17.0,
        "voo_return": 6.5,
        "voo_vol": 16.0,
        "memo": "원자료 CAGR에 큰 할인율을 적용한 방어적 가정",
    },
    "기본": {
        "quant_return": 18.0,
        "quant_vol": 30.0,
        "dual_return": 12.0,
        "dual_vol": 17.0,
        "voo_return": 7.5,
        "voo_vol": 16.0,
        "memo": "V60-7 기본 기대수익률 체계와 자료 기반 계좌분리를 절충",
    },
    "공격": {
        "quant_return": 20.0,
        "quant_vol": 30.0,
        "dual_return": 14.0,
        "dual_vol": 17.0,
        "voo_return": 8.5,
        "voo_vol": 16.0,
        "memo": "자료 기반 상단을 일부 반영하되 국내퀀트 원자료 CAGR은 그대로 쓰지 않음",
    },
    "자료기반 원자료": {
        "quant_return": 26.23,
        "quant_vol": 30.0,
        "dual_return": 15.31,
        "dual_vol": 17.0,
        "voo_return": 10.85,
        "voo_vol": 16.0,
        "memo": "업로드 자료의 CAGR을 거의 그대로 반영한 참고용 상단 가정",
    },
}

ACCOUNT_NAMES = ["quant", "dual", "voo"]
ACCOUNT_LABELS = {
    "quant": "국내퀀트",
    "dual": "연금저축+ISA",
    "voo": "VOO",
}

# 계좌 간 수익률 상관관계 가정
# 국내퀀트는 국내 계절성·팩터 전략, 듀얼모멘텀과 VOO는 해외위험자산 노출이 있어 듀얼/VOO 상관을 높게 둡니다.
ACCOUNT_RETURN_CORRELATION = [
    [1.00, 0.25, 0.25],
    [0.25, 1.00, 0.65],
    [0.25, 0.65, 1.00],
]

# 계좌이동 기반 포트폴리오 전환 기본값
# 현재 금융자산 12.6억 중 국내퀀트 10.7억, 연금저축+ISA 듀얼모멘텀 1.2억, VOO 0.7억.
# 은퇴 전까지 국내퀀트에서 연금저축+ISA로 매년 3,800만 원을 이체한다고 가정합니다.
INITIAL_QUANT_ASSET_MANWON = 107000
INITIAL_DUAL_MOMENTUM_ASSET_MANWON = 12000
INITIAL_VOO_ASSET_MANWON = 7000
ANNUAL_TRANSFER_TO_DUAL_MANWON = 3800

# 국내퀀트 운용규모 페널티
# 단위: 만 원, 페널티는 연 수익률 차감률(decimal)
QUANT_SIZE_PENALTY_TIERS = [
    (150000, 0.000),  # 15억 이하
    (250000, 0.003),  # 15억 초과~25억
    (400000, 0.007),  # 25억 초과~40억
    (700000, 0.012),  # 40억 초과~70억
    (float("inf"), 0.018),  # 70억 초과
]
