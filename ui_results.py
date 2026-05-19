import streamlit as st

from utils import calc_rolling_stats


def render_rolling_window_section(sim_returns):
    with st.expander("⏳ [멘탈 방어] 구간별 승률(Rolling Window)", expanded=False):
        st.markdown("###### 📊 우주를 분석한 '보유 기간별' 시스템 승률 (평균회귀 10% 작용)")

        c_r1, c_r2, c_r3, c_r4 = st.columns(4)
        r_windows = [1, 3, 5, 10]
        r_cols = [c_r1, c_r2, c_r3, c_r4]

        for r_w, r_c in zip(r_windows, r_cols):
            w_rate, m_cagr = calc_rolling_stats(sim_returns, r_w)
            r_c.metric(
                f"{r_w}년 유지 시 승률",
                f"{w_rate:.1f}%",
                f"해당 구간 연평균: {m_cagr:.2f}%",
                delta_color="off",
            )

        st.caption(
            "※ 평균 회귀(Mean Reversion) 로직이 탑재되어, 기간이 길어질수록 수익률이 기댓값에 수렴합니다. "
            "(강도: 10%)"
        )