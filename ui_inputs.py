import streamlit as st

from config import (
    ANNUAL_TRANSFER_TO_DUAL_MANWON,
    AUTO_APPLY_DWZ_SPENDING,
    AUTO_APPLY_FAT_TAIL,
    AUTO_APPLY_FLEX_SPENDING,
    AUTO_APPLY_INFLATION_SHOCK,
    AUTO_APPLY_PORTFOLIO_TRANSITION,
    DEFAULT_SCENARIO_INDEX,
    DWZ_TARGET_RUIN_PROB,
    ESSENTIAL_SPENDING_RATIO,
    EXPENSE_INFLATION_LINKED,
    FAT_TAIL_DF,
    FLEXIBLE_SPENDING_RATIO,
    INCOME_INFLATION_LINKED,
    INFLATION_SHOCK_ANNUAL_PROBABILITY,
    INFLATION_SHOCK_DURATION_YEARS,
    INFLATION_SHOCK_INFLATION_ADDON,
    INFLATION_SHOCK_RETURN_PENALTY,
    INFLATION_SHOCK_VOL_MULTIPLIER,
    INITIAL_DUAL_MOMENTUM_ASSET_MANWON,
    INITIAL_QUANT_ASSET_MANWON,
    INITIAL_VOO_ASSET_MANWON,
    MEAN_REVERSION_STRENGTH,
    SCENARIO_OPTIONS,
    STANDARD_TARGET_RUIN_PROB,
    WARNING_RUIN_PROB,
)
from data_defaults import get_default_lump_events, get_default_recurring_events


def _drop_model_columns_for_editor(df):
    """입력 UI에서는 내부 모델용 물가연동 컬럼을 노출하지 않습니다."""
    return df.drop(columns=["물가연동"], errors="ignore")


def render_applied_model_preview():
    with st.expander("🧩 현재 자동 적용되는 모델", expanded=False):
        st.caption(
            "아래 항목은 사용자가 켜고 끄는 토글이 아니라, 시뮬레이터 내부에서 기본 적용되는 현실화 가정입니다."
        )
        st.dataframe(
            [
                {
                    "모델": "소득·지출 물가 처리",
                    "적용값": "수입 명목고정 / 지출 물가연동",
                    "의미": "미래 수입은 물가만큼 자동 증가하지 않고, 지출은 현재 생활수준 유지 비용으로 반영합니다.",
                },
                {
                    "모델": "DWZ 지출 구조",
                    "적용값": f"필수 {ESSENTIAL_SPENDING_RATIO * 100:.0f}% / 조정가능 {FLEXIBLE_SPENDING_RATIO * 100:.0f}%",
                    "의미": "나이와 시장 하락에 따른 지출 조정은 조정가능지출에만 적용합니다.",
                },
                {
                    "모델": "포트폴리오 전환",
                    "적용값": f"은퇴 전까지 연 {ANNUAL_TRANSFER_TO_DUAL_MANWON:,}만 원 이동",
                    "의미": "국내퀀트에서 연금저축+ISA로 매년 이체하는 계획을 수익률·변동성 경로에 반영합니다.",
                },
                {
                    "모델": "극단 손실 가능성",
                    "적용값": f"팻테일 t분포 df={FAT_TAIL_DF}",
                    "의미": "정규분포보다 큰 손실이 더 자주 발생하도록 반영합니다.",
                },
                {
                    "모델": "고물가 쇼크",
                    "적용값": f"연 {INFLATION_SHOCK_ANNUAL_PROBABILITY * 100:.1f}% / {INFLATION_SHOCK_DURATION_YEARS}년",
                    "의미": "생애기간 중 고물가·수익률 압박 구간이 확률적으로 발생합니다.",
                },
                {
                    "모델": "평균회귀",
                    "적용값": f"{MEAN_REVERSION_STRENGTH * 100:.1f}%",
                    "의미": "전년도 과도한 상승·하락 후 다음 해 수익률을 약하게 보정합니다.",
                },
                {
                    "모델": "파산확률 기준",
                    "적용값": f"안전 {STANDARD_TARGET_RUIN_PROB:.0f}% / DWZ {DWZ_TARGET_RUIN_PROB:.0f}% / 경고 {WARNING_RUIN_PROB:.0f}%",
                    "의미": "추가 사용 가능액은 DWZ 기준으로 계산하고, 결과에는 안전·경고선을 함께 표시합니다.",
                },
            ],
            use_container_width=True,
            hide_index=True,
        )


def render_input_panel():
    c1, c2, c3 = st.columns(3)

    with c1:
        with st.container(border=True):
            st.subheader("👤 1. 기본 정보")
            current_age = st.number_input(
                "현재 나이",
                20,
                80,
                40,
                key="in_age",
                help="현재 나이를 입력하십시오.",
            )
            retire_age = st.number_input(
                "은퇴 나이",
                current_age,
                90,
                60,
                key="in_ret_age",
                help="소득이 중단되는 시점입니다.",
            )
            death_age = st.number_input(
                "목표 수명",
                80,
                120,
                90,
                key="in_death",
                help="이 나이까지 금융자산이 고갈되지 않는지 확인합니다.",
            )

    with c2:
        with st.container(border=True):
            st.subheader("💵 2. 현금흐름")
            monthly_income = st.number_input(
                "월 수입 (세후/만원)",
                0,
                value=500,
                step=10,
                key="in_income",
                help="은퇴 전 월 세후 수입입니다. 내부 계산에서는 물가연동 없이 명목 고정으로 적용합니다.",
            )
            monthly_expense = st.number_input(
                "월 기본지출 (만원)",
                0,
                value=600,
                step=10,
                key="in_expense",
                help="현재가치 기준 월 기본지출입니다. 내부 계산에서는 물가상승률에 따라 명목 지출이 증가합니다.",
            )

            st.markdown("---")
            col_ret3, col_ret4 = st.columns(2)
            inflation = col_ret3.number_input(
                "평시 물가상승률(%)",
                0.0,
                10.0,
                2.5,
                step=0.1,
                key="in_inf",
                help="모든 결과를 현재가치로 환산하기 위한 기준 물가상승률입니다.",
            )
            tax_fee_rate = col_ret4.number_input(
                "추가 거래비용(연%)",
                0.0,
                5.0,
                0.5,
                step=0.1,
                key="in_tax",
                help="수익률에서 매년 차감하는 추가 비용입니다. 백테스트 비용과 중복되지 않도록 보수적으로 입력하십시오.",
            )

    with c3:
        with st.container(border=True):
            st.subheader("📈 3. 자산·전략")
            current_asset = st.number_input(
                "현재 금융자산 (만원)",
                0,
                value=126000,
                step=100,
                key="in_asset",
                help="국내퀀트, 듀얼모멘텀, VOO 등 현재 운용 금융자산 합계입니다.",
            )

            selected_scenario = st.selectbox(
                "수익률·변동성 가정",
                list(SCENARIO_OPTIONS.keys()),
                index=DEFAULT_SCENARIO_INDEX,
                help=(
                    "국내퀀트 10.7억, 듀얼모멘텀 1.2억, VOO 0.7억의 현재 포트폴리오를 기준으로 "
                    "백테스트 원자료를 할인해 만든 시뮬레이터용 가정입니다."
                ),
            )

            expected_return_pre, vol_pre, expected_return_post, vol_post = SCENARIO_OPTIONS[
                selected_scenario
            ]

            st.info(
                f"은퇴 전 **{expected_return_pre:.1f}% / 변동성 {vol_pre:.1f}%**  ·  "
                f"은퇴 후 **{expected_return_post:.1f}% / 변동성 {vol_post:.1f}%**"
            )
            st.caption(
                f"기준 계좌: 국내퀀트 {INITIAL_QUANT_ASSET_MANWON/10000:.1f}억, "
                f"연금저축+ISA {INITIAL_DUAL_MOMENTUM_ASSET_MANWON/10000:.1f}억, "
                f"VOO {INITIAL_VOO_ASSET_MANWON/10000:.1f}억"
            )

    render_applied_model_preview()

    st.markdown("---")
    st.subheader("📱 4. 이벤트성 추가 수입/지출")
    st.caption(
        "기간성 수입은 명목 고정, 기간성 지출은 현재가치 입력 후 물가연동으로 처리합니다. "
        "시뮬레이터 결과는 모두 현재가치 기준으로 표시됩니다."
    )

    tab1, tab2 = st.tabs(["💸 일회성 목돈", "📅 기간성 수입/지출"])

    with tab1:
        if "lump_df" not in st.session_state:
            st.session_state.lump_df = get_default_lump_events()

        edited_lump_df = st.data_editor(
            st.session_state.lump_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "유형": st.column_config.SelectboxColumn(
                    "유형",
                    options=["수입", "지출"],
                )
            },
        )
        clean_lump_df = edited_lump_df.dropna(subset=["나이", "유형", "금액(만원)"])

    with tab2:
        if "recur_df" not in st.session_state:
            st.session_state.recur_df = _drop_model_columns_for_editor(
                get_default_recurring_events()
            )

        edited_recur_df = st.data_editor(
            st.session_state.recur_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "유형": st.column_config.SelectboxColumn(
                    "유형",
                    options=["수입", "지출"],
                ),
                "확정연금": st.column_config.CheckboxColumn(
                    "확정연금",
                    help="주가에 상관없이 지급되는 안정적 수입",
                ),
            },
        )
        clean_recur_df = edited_recur_df.dropna(
            subset=["시작나이", "기간(년)", "유형", "월금액(만원)"]
        )

    return {
        "current_age": current_age,
        "retire_age": retire_age,
        "death_age": death_age,
        "monthly_income": monthly_income,
        "apply_income_inflation": INCOME_INFLATION_LINKED,
        "monthly_expense": monthly_expense,
        "essential_spending_ratio": ESSENTIAL_SPENDING_RATIO,
        "current_asset": current_asset,
        "expected_return_pre": expected_return_pre,
        "vol_pre": vol_pre,
        "expected_return_post": expected_return_post,
        "vol_post": vol_post,
        "inflation": inflation,
        "tax_fee_rate": tax_fee_rate,
        "use_fat_tail": AUTO_APPLY_FAT_TAIL,
        "use_inflation_shock": AUTO_APPLY_INFLATION_SHOCK,
        "use_flex_spending": AUTO_APPLY_FLEX_SPENDING,
        "dwz_mode": AUTO_APPLY_DWZ_SPENDING,
        "use_portfolio_transition": AUTO_APPLY_PORTFOLIO_TRANSITION,
        "lump_events": clean_lump_df,
        "recurring_events": clean_recur_df,
    }
