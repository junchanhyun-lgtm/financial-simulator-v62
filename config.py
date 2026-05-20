APP_VERSION = "V60-7"

PAGE_TITLE = "My Quant Asset Sim (V60-7)"

MAIN_TITLE = "💰 전담 퀀트 금융자산 종합 관리 시스템 (V60-7)"

UPDATE_MESSAGE = (
    "💡 V60-7 업데이트: 상하위 30% 극단 경로를 제외한 평균 여유자금과 "
    "자동차 할부 기본값 현실화"
)

N_SIMULATIONS = 5000
SEARCH_SIMULATIONS = 500

# 수익률 분포 현실화 기본값
# 모든 현실화 기능은 토글 없이 기본 적용합니다.
FAT_TAIL_DF = 10
INFLATION_SHOCK_ANNUAL_PROBABILITY = 0.025
INFLATION_SHOCK_DURATION_YEARS = 3
INFLATION_SHOCK_INFLATION_ADDON = 0.04
INFLATION_SHOCK_RETURN_PENALTY = 0.04
INFLATION_SHOCK_VOL_MULTIPLIER = 1.30
MEAN_REVERSION_STRENGTH = 0.05

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

# 현재 포트폴리오 기준:
# 국내 퀀트 10.7억 + 듀얼모멘텀 1.2억 + VOO 0.7억
# 백테스트 원자료를 그대로 쓰지 않고 미래 알파 감소, 운용규모, 슬리피지 가능성을 반영한 시뮬레이터용 가정값.
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

# 계좌이동 기반 포트폴리오 전환 기본값
# 현재 금융자산 12.6억 중 국내퀀트 10.7억, 연금저축+ISA 듀얼모멘텀 1.2억, VOO 0.7억.
# 은퇴 전까지 국내퀀트에서 연금저축+ISA로 매년 3,800만 원을 이체한다고 가정합니다.
INITIAL_QUANT_ASSET_MANWON = 107000
INITIAL_DUAL_MOMENTUM_ASSET_MANWON = 12000
INITIAL_VOO_ASSET_MANWON = 7000
ANNUAL_TRANSFER_TO_DUAL_MANWON = 3800

# 국내퀀트 운용규모 페널티
# 백테스트에는 매도수수료 1.33%가 이미 반영되어 있으므로 현재 규모에서는 추가 차감을 걸지 않고,
# 국내퀀트 추정 운용금액이 커지는 구간부터 단계적으로 수익률을 낮춥니다.
# 단위: 만 원, 페널티는 연 수익률 차감률(decimal)
QUANT_SIZE_PENALTY_TIERS = [
    (150000, 0.000),  # 15억 이하
    (250000, 0.003),  # 15억 초과~25억
    (400000, 0.007),  # 25억 초과~40억
    (700000, 0.012),  # 40억 초과~70억
    (float("inf"), 0.018),  # 70억 초과
]
