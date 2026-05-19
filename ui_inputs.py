import streamlit as st
import pandas as pd

from config import SCENARIO_OPTIONS, DEFAULT_SCENARIO_INDEX
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
                help="본 시스템의 1차 목표 지점입니다. 60세 시점의 자산 방어율을 중점적으로 추적합니다.",
            )
            death_age = st.number_input(
                "목표 수명",
                80,
                120,
                90,
                key="in_death",
                help="이 나이까지 자산이 고갈되지 않아야 파산 확률 0%로 판정합니다.",
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
                help="체크 시, 은퇴 전까지 소득도 물가상승률만큼 동반 상승한다고 가정합니다.",
            )
            monthly_expense = st.number_input(
                "월 필수 지출 (대출 이자 포함/만원)",
                0,
                value=600,
                step=10,
                key="in_expense",
                help="가족 생활비 및 대출 이자가 모두 포함된 총 지출액입니다.",
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
                help="물가 상승으로 인한 구매력 하락을 자산 궤적에 역산하여 반영합니다.",
            )
            tax_fee_rate = col_ret4.number_input(
                "거래세/수수료(연%)",
                0.0,
                5.0,
                0.5,
                step=0.1,
                key="in_tax",
                help="매매 수수료 및 거래세 등을 매년 선제적으로 삭감합니다.",
            )

    with c3:
        with st.container(border=True):
            st.subheader("📈 3. 자산 및 통합 수익률 시나리오")
            current_asset = st.number_input(
                "현재 금융자산 (만원)",
                0,
                value=97000,
                step=100,
                key="in_asset",
                help="대출이 포함된 총 운용 자산입니다. 기대수익률은 대출이자 및 제세금이 블렌딩된 수치로 간주합니다.",
            )

            st.markdown("###### ⚔️ 포트폴리오 통합 시나리오 선택")

            selected_scenario = st.selectbox(
                "성장-방어 통합 궤적 선택",
                list(SCENARIO_OPTIONS.keys()),
                index=DEFAULT_SCENARIO_INDEX,
                help="은퇴 전 수익률 타겟을 선택하면 은퇴 후 안전자산 30% 편입 비율이 자동 연산되어 하드코딩됩니다.",
            )

            expected_return_pre, vol_pre, expected_return_post, vol_post = SCENARIO_OPTIONS[
                selected_scenario
            ]

            st.markdown("###### 🛡️ 은퇴 후 (방어형 자동 스위칭)")
            st.info(
                f"👉 해당 시나리오 적용 시, 은퇴 후 기대수익률은 **{expected_return_post}%**, "
                f"변동성은 **{vol_post}%**로 자동 하강(Glide-Path) 적용됩니다. "
                f"(안전자산 30% 블렌딩)"
            )

    st.markdown("---")

    with st.expander("🔥 **블랙 스완 & 고도화 세팅 (Advanced)**", expanded=True):
        c_adv1, c_adv2 = st.columns(2)

        with c_adv1.container(border=True):
            st.markdown("##### 🏖️ 라이프스타일 최적화")
            dwz_mode = st.checkbox(
                "🔥 Die with Zero 최적화 (파산 확률 20% 타겟)",
                value=True,
                key="in_dwz",
                help="체크 시 기본 15%에서 20%로 타겟 확률을 상향 조정하며 효용을 극대화합니다.",
            )
            use_flex_spending = st.checkbox(
                "🧠 다단계 생존 본능 (시장 5% 하락 시 긴축)",
                value=True,
                key="in_flex",
                help="시장이 하락할 때 지출을 통제하는 동적 인출 로직을 작동시킵니다.",
            )
            use_glide_path = st.checkbox(
                "🛬 동적 글라이드 패스 (은퇴 5년 전부터 연착륙)",
                value=True,
                key="in_glide",
                help="은퇴 시점에 임박하여 수익률과 변동성을 5년에 걸쳐 계단식으로 부드럽게 낮춥니다.",
            )

        with c_adv2.container(border=True):
            st.markdown("##### 🚨 극한 스트레스 테스팅")
            use_fat_tail = st.checkbox(
                "📉 팻 테일(Fat Tail) 대폭락장 적용",
                value=True,
                key="in_fat",
                help="정규 분포를 벗어나는 극단적인 금융위기급 폭락 확률을 시뮬레이션에 포함합니다.",
            )
            use_inflation_shock = st.checkbox(
                "🔥 스태그플레이션 (수익률 영구 타격)",
                value=True,
                key="in_shock",
                help="3년간 고물가 및 수익률 하락이 동시에 오는 블랙스완 시나리오를 적용합니다.",
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
                    help="주가에 상관없이 평생 지급되는 안정적 수입",
                ),
                "물가연동": st.column_config.CheckboxColumn(
                    "물가연동",
                    help="체크 시 매년 물가상승률만큼 수입/지출액 증가. (명목 고정액은 체크 해제)",
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
        "use_glide_path": use_glide_path,
        "lump_events": clean_lump_df,
        "recurring_events": clean_recur_df,
    }