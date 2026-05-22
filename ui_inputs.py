import streamlit as st

from config import (
    ALPHA_MODEL_BASE_CAGR,
    ALPHA_MODEL_BASE_MDD,
    ALPHA_MODEL_BASE_VOLATILITY,
    ALPHA_MODEL_CASH_RETURN,
    ALPHA_MODEL_DEFAULT_DISCOUNT_LABEL,
    ALPHA_MODEL_DEFAULT_RETIREMENT_ALLOCATION_LABEL,
    ALPHA_MODEL_DISCOUNT_OPTIONS,
    ALPHA_MODEL_NAME,
    ALPHA_MODEL_PASSIVE_SEASONAL_VOLATILITY,
    ALPHA_MODEL_RETIREMENT_ALLOCATION_OPTIONS,
    ANNUAL_TRANSFER_TO_DUAL_MANWON,
    AUTO_APPLY_DWZ_SPENDING,
    AUTO_APPLY_FAT_TAIL,
    AUTO_APPLY_FLEX_SPENDING,
    AUTO_APPLY_INFLATION_SHOCK,
    AUTO_APPLY_PORTFOLIO_TRANSITION,
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
    MAX_TOTAL_ANNUAL_RETURN,
    MEAN_REVERSION_STRENGTH,
    MIN_TOTAL_ANNUAL_RETURN,
    STANDARD_TARGET_RUIN_PROB,
    WARNING_RUIN_PROB,
)
from data_defaults import get_default_lump_events, get_default_recurring_events


def _drop_model_columns_for_editor(df):
    """입력 UI에서는 내부 모델용 물가연동 컬럼을 노출하지 않습니다."""
    return df.drop(columns=["물가연동"], errors="ignore")


def _build_discount_scenario_table(stock_weight, cash_weight):
    rows = []
    for label, discount_rate in ALPHA_MODEL_DISCOUNT_OPTIONS.items():
        adjusted_cagr = ALPHA_MODEL_BASE_CAGR * (1.0 - float(discount_rate))
        post_return = (adjusted_cagr * stock_weight) + (ALPHA_MODEL_CASH_RETURN * cash_weight)
        rows.append({
            "수익률 시나리오": label,
            "은퇴 전 수익률": adjusted_cagr * 100.0,
            "은퇴 후 수익률": post_return * 100.0,
            "은퇴 전 변동성": ALPHA_MODEL_BASE_VOLATILITY * 100.0,
            "은퇴 후 변동성": ALPHA_MODEL_BASE_VOLATILITY * stock_weight * 100.0,
        })
    return rows


def render_applied_model_preview():
    with st.expander("🧩 현재 자동 적용되는 모델", expanded=False):
        st.caption(
            "아래 항목은 사용자가 켜고 끄는 토글이 아니라, 시뮬레이터 내부에서 기본 적용되는 현실화 가정입니다."
        )
        st.dataframe(
            [
                {
                    "모델": "소득·지출 물가 처리",
                    "적용값": "기본수입 명목고정 / 지출·확정연금 현재가치",
                    "의미": "근로·사업 수입은 명목 고정, 지출과 확정연금성 수입은 현재가치 기준으로 반영합니다.",
                },
                {
                    "모델": "DWZ 지출 구조",
                    "적용값": f"필수 {ESSENTIAL_SPENDING_RATIO * 100:.0f}% / 조정가능 {FLEXIBLE_SPENDING_RATIO * 100:.0f}%",
                    "의미": "나이와 시장 하락에 따른 지출 조정은 조정가능지출에만 적용합니다.",
                },
                {
                    "모델": "포트폴리오 전환",
                    "적용값": f"은퇴 전까지 연 {ANNUAL_TRANSFER_TO_DUAL_MANWON:,}만 원 이동",
                    "의미": "계좌 간 이동은 총 금융자산에는 중립이므로 기본 수익률 경로에는 반영하지 않습니다.",
                },
                {
                    "모델": "극단 손익 가능성",
                    "적용값": f"팻테일 t분포 df={FAT_TAIL_DF}, 하방 {MIN_TOTAL_ANNUAL_RETURN * 100:.0f}% / 상방 +{MAX_TOTAL_ANNUAL_RETURN * 100:.0f}% 보정",
                    "의미": "정규분포보다 두꺼운 꼬리를 반영하되, 총자산 포트폴리오에 비현실적인 초극단값은 양쪽에서 보정합니다.",
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

            discount_labels = list(ALPHA_MODEL_DISCOUNT_OPTIONS.keys())
            default_discount_index = discount_labels.index(ALPHA_MODEL_DEFAULT_DISCOUNT_LABEL)
            selected_discount_label = st.selectbox(
                "수익률",
                discount_labels,
                index=default_discount_index,
                help="후보1 전략의 백테스트 CAGR에 현실화 할인율을 적용합니다.",
            )

            allocation_labels = list(ALPHA_MODEL_RETIREMENT_ALLOCATION_OPTIONS.keys())
            default_allocation_index = allocation_labels.index(
                ALPHA_MODEL_DEFAULT_RETIREMENT_ALLOCATION_LABEL
            )
            selected_allocation_label = st.selectbox(
                "은퇴 후 자산배분",
                allocation_labels,
                index=default_allocation_index,
                help="은퇴 후에는 주식전략과 현금성 자산을 섞어 수익률과 변동성을 계산합니다.",
            )

            selected_discount = ALPHA_MODEL_DISCOUNT_OPTIONS[selected_discount_label]
            allocation = ALPHA_MODEL_RETIREMENT_ALLOCATION_OPTIONS[selected_allocation_label]
            stock_weight = float(allocation["stock_weight"])
            cash_weight = float(allocation["cash_weight"])

            adjusted_cagr = ALPHA_MODEL_BASE_CAGR * (1.0 - selected_discount)
            expected_return_pre = adjusted_cagr * 100.0
            expected_return_post = (
                (adjusted_cagr * stock_weight) + (ALPHA_MODEL_CASH_RETURN * cash_weight)
            ) * 100.0
            vol_pre = ALPHA_MODEL_BASE_VOLATILITY * 100.0
            vol_post = ALPHA_MODEL_BASE_VOLATILITY * stock_weight * 100.0
            reference_mdd_pre = ALPHA_MODEL_BASE_MDD * 100.0
            reference_mdd_post = ALPHA_MODEL_BASE_MDD * stock_weight * 100.0

            st.dataframe(
                _build_discount_scenario_table(stock_weight, cash_weight),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "은퇴 전 수익률": st.column_config.NumberColumn(format="%.2f%%"),
                    "은퇴 후 수익률": st.column_config.NumberColumn(format="%.2f%%"),
                    "은퇴 전 변동성": st.column_config.NumberColumn(format="%.2f%%"),
                    "은퇴 후 변동성": st.column_config.NumberColumn(format="%.2f%%"),
                },
            )

            with st.expander("⚙️ 적용 기준", expanded=False):
                st.caption(
                    f"은퇴 전 변동성은 국내퀀트 합성 원자료의 월수익률 연환산 변동성 {ALPHA_MODEL_PASSIVE_SEASONAL_VOLATILITY * 100:.1f}%를 기준으로 {vol_pre:.1f}%로 설정했습니다."
                )
                st.caption(
                    f"은퇴 후 수익률은 주식전략 {stock_weight * 100:.0f}%와 현금 {cash_weight * 100:.0f}%를 섞어 계산합니다. 현금수익률은 명목 {ALPHA_MODEL_CASH_RETURN * 100:.1f}%로 둡니다."
                )
                st.caption(
                    f"은퇴 후 변동성은 현금 변동성을 0%로 보고 {vol_pre:.1f}% × {stock_weight:.1f} = {vol_post:.1f}%로 계산합니다."
                )

            return_assumption_info = {
                "모델": ALPHA_MODEL_NAME,
                "선택": selected_discount_label,
                "은퇴 후 자산배분": selected_allocation_label,
                "기준 CAGR": ALPHA_MODEL_BASE_CAGR * 100.0,
                "적용 할인율": selected_discount * 100.0,
                "은퇴 후 주식비중": stock_weight * 100.0,
                "은퇴 후 현금비중": cash_weight * 100.0,
                "현금수익률": ALPHA_MODEL_CASH_RETURN * 100.0,
                "은퇴 전 기대수익률": expected_return_pre,
                "은퇴 전 변동성": vol_pre,
                "은퇴 후 기대수익률": expected_return_post,
                "은퇴 후 변동성": vol_post,
                "참고 MDD": reference_mdd_pre,
                "은퇴 후 참고 MDD": reference_mdd_post,
                "설명": "후보1 알파 감소 모델입니다. 은퇴 전은 긍정·보통·보수 수익률 시나리오와 18.5% 변동성을 쓰고, 은퇴 후는 선택한 주식 현금 배분으로 수익률과 변동성을 계산합니다.",
            }

            st.info(
                f"은퇴 전 **{expected_return_pre:.2f}% / 변동성 {vol_pre:.2f}%**  ·  "
                f"은퇴 후 **{expected_return_post:.2f}% / 변동성 {vol_post:.2f}%**"
            )
            st.caption(
                f"은퇴 후 자산배분: {selected_allocation_label} · "
                f"참고 MDD: 은퇴 전 {reference_mdd_pre:.2f}% / 은퇴 후 {reference_mdd_post:.2f}%"
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
        "주택매수는 금융자산이 비유동 주택자산으로 전환되는 것으로 보고 일회성 지출로 처리합니다. "
        "국민연금·주택연금처럼 확정연금에 체크한 수입은 현재가치 기준으로 반영합니다. "
        "건보료·세금은 자동계산하지 않고 보수적 기간성 지출로 입력하는 것을 권장합니다."
    )

    with st.expander("📌 이벤트 입력 기준", expanded=False):
        st.markdown(
            """
            - **주택구입**: 주택 전체 가격이 아니라 금융자산에서 실제 빠져나가는 자기자본·취득비용 기준으로 입력합니다.
            - **주택연금**: 7억 원 일반주택을 빠른 시점에 연금화하는 보수 가정으로, 기본값은 55세부터 월 100만 원입니다.
            - **국민연금·주택연금**: 현재가치 기준 월수입으로 입력하고, `확정연금`에 체크합니다.
            - **건보료·세금**: 제도와 소득구성에 따라 달라지므로 자동계산하지 않고 기간성 지출로 보수 입력합니다.
            - **증여**: 기본 이벤트에서는 제외했습니다. 필요하면 일회성 목돈 지출로 직접 추가하십시오.
            """
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
        "return_assumption_info": return_assumption_info,
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
