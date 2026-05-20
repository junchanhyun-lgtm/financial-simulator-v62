import streamlit as st

from config import (
    ANNUAL_TRANSFER_TO_DUAL_MANWON,
    DEFAULT_SCENARIO_INDEX,
    DEFAULT_SPENDING_PROFILE_INDEX,
    FAT_TAIL_DF,
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
    SPENDING_PROFILE_OPTIONS,
)
from data_defaults import get_default_lump_events, get_default_recurring_events


def render_input_panel():
    c1, c2, c3 = st.columns(3)

    with c1:
        with st.container(border=True):
            st.subheader("👤 1. 기본 정보 & 은퇴 설정")
            current_age = st.number_input(
                "현재 나이",
                20,
                80,
                40,
                key="in_age",
                help="현재 나이를 입력하십시오.",
            )
            retire_age = st.number_input(
                "은퇴 나이 (소득 중단 시점)",
                current_age,
                90,
                60,
                key="in_ret_age",
                help="본 시스템의 1차 목표 지점입니다. 은퇴 시점의 자산 방어율을 중점적으로 추적합니다.",
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
            st.subheader("💵 2. 기본 수입 및 지출")
            col_inc1, col_inc2 = st.columns(2)

            monthly_income = col_inc1.number_input(
                "월 수입 (세후/만원)",
                0,
                value=500,
                step=10,
                key="in_income",
                help="한의원 순수익입니다.",
            )
            apply_income_inflation = col_inc2.checkbox(
                "수입 물가연동",
                value=False,
                key="in_inc_inf",
                help="체크 시 은퇴 전까지 소득도 물가상승률만큼 동반 상승한다고 가정합니다.",
            )
            monthly_expense = st.number_input(
                "월 기본지출 (만원)",
                0,
                value=600,
                step=10,
                key="in_expense",
                help="기본 생활비, 가족 생활비, 대출 이자 등이 포함된 월 기본지출입니다. 내부에서 필수지출과 조정가능지출로 자동 분해합니다.",
            )

            st.markdown("---")
            col_ret3, col_ret4 = st.columns(2)

            inflation = col_ret3.number_input(
                "평시 물가 상승률(%)",
                0.0,
                10.0,
                2.5,
                step=0.1,
                key="in_inf",
                help="물가 상승으로 인한 구매력 하락을 현재가치 기준으로 역산합니다.",
            )
            tax_fee_rate = col_ret4.number_input(
                "거래세/수수료(연%)",
                0.0,
                5.0,
                0.5,
                step=0.1,
                key="in_tax",
                help="시뮬레이터 내부에서 매년 수익률에서 차감하는 추가 비용입니다. 백테스트 비용과 중복되지 않도록 보수적으로 입력하십시오.",
            )

    with c3:
        with st.container(border=True):
            st.subheader("📈 3. 자산 및 포트폴리오 시나리오")
            current_asset = st.number_input(
                "현재 금융자산 (만원)",
                0,
                value=126000,
                step=100,
                key="in_asset",
                help="국내 퀀트, 듀얼모멘텀, VOO 등 현재 운용 금융자산 합계입니다.",
            )

            st.markdown("###### ⚔️ 현재 포트폴리오 기준 시나리오")

            selected_scenario = st.selectbox(
                "수익률·변동성 가정 선택",
                list(SCENARIO_OPTIONS.keys()),
                index=DEFAULT_SCENARIO_INDEX,
                help=(
                    "국내 퀀트 10.7억, 듀얼모멘텀 1.2억, VOO 0.7억의 현재 포트폴리오를 기준으로 "
                    "백테스트 원자료를 할인해 만든 시뮬레이터용 가정입니다."
                ),
            )

            expected_return_pre, vol_pre, expected_return_post, vol_post = SCENARIO_OPTIONS[
                selected_scenario
            ]

            st.info(
                f"선택값: 은퇴 전 **{expected_return_pre:.1f}% / 변동성 {vol_pre:.1f}%**, "
                f"은퇴 후 **{expected_return_post:.1f}% / 변동성 {vol_post:.1f}%**"
            )
            st.caption(
                "※ 은퇴 전후 전환은 은퇴 5년 전 강제 전환이 아니라, "
                "국내퀀트 → 연금저축+ISA 계좌이동 계획을 반영해 완만하게 적용합니다."
            )

    st.markdown("---")

    with st.expander("🔥 **블랙 스완 & 고도화 세팅 (Advanced)**", expanded=True):
        c_adv1, c_adv2 = st.columns(2)

        with c_adv1.container(border=True):
            st.markdown("##### 🏖️ 라이프스타일 최적화")
            dwz_mode = st.checkbox(
                "🔥 Die with Zero 최적화 (파산 확률 15% 방어선)",
                value=True,
                key="in_dwz",
                help="체크 시 일반 안정 기준 10%보다 높은 15% 파산확률 방어선을 사용해 추가 소비 여력을 계산합니다.",
            )
            selected_spending_profile = st.selectbox(
                "지출 구조 자동분해",
                list(SPENDING_PROFILE_OPTIONS.keys()),
                index=DEFAULT_SPENDING_PROFILE_INDEX,
                key="in_spending_profile",
                help="월 기본지출을 필수지출과 조정가능지출로 내부 분해합니다. DWZ와 긴축은 조정가능지출에만 적용합니다.",
            )
            essential_spending_ratio = SPENDING_PROFILE_OPTIONS[selected_spending_profile]

            use_flex_spending = st.checkbox(
                "🧠 시장 하락 시 조정가능지출 긴축",
                value=True,
                key="in_flex",
                help="시장 하락률이 커질수록 조정가능지출만 단계적으로 줄입니다. 필수지출과 이벤트성 지출은 자동 삭감하지 않습니다.",
            )
            use_portfolio_transition = st.checkbox(
                "🛬 계좌이동 기반 포트폴리오 전환",
                value=True,
                key="in_portfolio_transition",
                help=(
                    f"은퇴 전까지 국내퀀트에서 연금저축+ISA로 매년 {ANNUAL_TRANSFER_TO_DUAL_MANWON:,}만 원을 이체하는 계획을 "
                    "수익률·변동성 경로에 반영합니다."
                ),
            )
            st.caption(
                f"기준 계좌: 국내퀀트 {INITIAL_QUANT_ASSET_MANWON/10000:.1f}억, "
                f"연금저축+ISA {INITIAL_DUAL_MOMENTUM_ASSET_MANWON/10000:.1f}억, "
                f"VOO {INITIAL_VOO_ASSET_MANWON/10000:.1f}억"
            )

        with c_adv2.container(border=True):
            st.markdown("##### 🚨 극한 스트레스 테스팅")
            use_fat_tail = st.checkbox(
                "📉 팻테일 꼬리위험 반영",
                value=True,
                key="in_fat",
                help=f"정규분포보다 극단적 수익률이 더 자주 나오는 t분포를 사용합니다. 기본 자유도는 {FAT_TAIL_DF}입니다.",
            )
            use_inflation_shock = st.checkbox(
                "🔥 확률형 인플레이션 쇼크 반영",
                value=True,
                key="in_shock",
                help=(
                    f"생애 기간 중 매년 {INFLATION_SHOCK_ANNUAL_PROBABILITY * 100:.1f}% 확률로 "
                    f"{INFLATION_SHOCK_DURATION_YEARS}년 고물가·수익률 압박 구간을 반영합니다. "
                    f"쇼크 중 물가는 +{INFLATION_SHOCK_INFLATION_ADDON * 100:.1f}%p, "
                    f"기대수익률은 -{INFLATION_SHOCK_RETURN_PENALTY * 100:.1f}%p, "
                    f"변동성은 {INFLATION_SHOCK_VOL_MULTIPLIER:.1f}배로 조정됩니다."
                ),
            )
            st.caption(
                f"수익률 분포 보정: 팻테일 df={FAT_TAIL_DF}, "
                f"평균회귀 {MEAN_REVERSION_STRENGTH * 100:.1f}%"
            )

    st.markdown("---")
    st.subheader("📱 4. 이벤트성 추가 수입/지출")

    tab1, tab2 = st.tabs(["💸 일회성 목돈 (상속/구입 등)", "📅 기간성 수입/지출 (연금/초과근무 등)"])

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
            st.session_state.recur_df = get_default_recurring_events()

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
                "물가연동": st.column_config.CheckboxColumn(
                    "물가연동",
                    help="체크 시 매년 물가상승률만큼 수입/지출액 증가. 명목 고정액은 체크 해제합니다.",
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
        "apply_income_inflation": apply_income_inflation,
        "monthly_expense": monthly_expense,
        "essential_spending_ratio": essential_spending_ratio,
        "current_asset": current_asset,
        "expected_return_pre": expected_return_pre,
        "vol_pre": vol_pre,
        "expected_return_post": expected_return_post,
        "vol_post": vol_post,
        "inflation": inflation,
        "tax_fee_rate": tax_fee_rate,
        "use_fat_tail": use_fat_tail,
        "use_inflation_shock": use_inflation_shock,
        "use_flex_spending": use_flex_spending,
        "dwz_mode": dwz_mode,
        "use_portfolio_transition": use_portfolio_transition,
        "lump_events": clean_lump_df,
        "recurring_events": clean_recur_df,
    }
