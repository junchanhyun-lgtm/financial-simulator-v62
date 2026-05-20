APP_VERSION = "V60-3"

PAGE_TITLE = "My Quant Asset Sim (V60-3)"

MAIN_TITLE = "💰 전담 퀀트 금융자산 종합 관리 시스템 (V60-3)"

UPDATE_MESSAGE = (
    "💡 V60-3 업데이트: 팻테일 강도, 인플레이션 쇼크, 평균회귀를 "
    "현재 포트폴리오 기준에 맞게 현실화"
)

N_SIMULATIONS = 5000
SEARCH_SIMULATIONS = 500

# 수익률 분포 현실화 기본값
# - 팻테일: 기존 df=5보다 완화한 df=10을 사용해 정규분포보다 두꺼운 꼬리는 유지하되 과도한 극단 손실은 줄입니다.
# - 인플레이션 쇼크: 은퇴 후 강제 3년이 아니라 생애기간 중 확률적으로 발생하는 고물가·수익률 압박 이벤트로 처리합니다.
# - 평균회귀: 기존 10%보다 약한 5%로 낮춰 폭락 후 자동 회복 가정을 완화합니다.
FAT_TAIL_DF = 10
INFLATION_SHOCK_ANNUAL_PROBABILITY = 0.025
INFLATION_SHOCK_DURATION_YEARS = 3
INFLATION_SHOCK_INFLATION_ADDON = 0.04
INFLATION_SHOCK_RETURN_PENALTY = 0.04
INFLATION_SHOCK_VOL_MULTIPLIER = 1.30
MEAN_REVERSION_STRENGTH = 0.05

# 파산확률 판단 기준
# - 일반 모드: 안정 은퇴 기준 10%
# - DWZ 모드: 효용 확대를 허용하되 15%를 방어선으로 사용
# - 20% 이상: 경고 구간
STANDARD_TARGET_RUIN_PROB = 10.0
DWZ_TARGET_RUIN_PROB = 15.0
WARNING_RUIN_PROB = 20.0

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

# 지출 구조 프리셋
# 기본 입력은 월 기본지출 1개만 유지하고, 내부에서 필수지출/조정가능지출로 분해합니다.
DEFAULT_SPENDING_PROFILE_INDEX = 1

SPENDING_PROFILE_OPTIONS = {
    "보수형: 필수 80% / 조정가능 20%": 0.80,
    "기본형: 필수 70% / 조정가능 30%": 0.70,
    "유연형: 필수 60% / 조정가능 40%": 0.60,
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
