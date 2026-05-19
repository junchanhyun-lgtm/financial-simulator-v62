import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

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
def render_representative_paths_section(years, sim_assets_pv, sim_returns, tgt_retire):
    final_assets = sim_assets_pv[:, -1]

    top10_idx = np.abs(final_assets - np.percentile(final_assets, 90)).argmin()
    median_idx = np.abs(final_assets - np.percentile(final_assets, 50)).argmin()
    bot10_idx = np.abs(final_assets - np.percentile(final_assets, 10)).argmin()

    paths = {
        "상위 10% (운수 좋은 날)": {
            "ret": sim_returns[top10_idx, :],
            "pv": sim_assets_pv[top10_idx, :],
        },
        "중간값 (가장 현실적)": {
            "ret": sim_returns[median_idx, :],
            "pv": sim_assets_pv[median_idx, :],
        },
        "하위 10% (스트레스)": {
            "ret": sim_returns[bot10_idx, :],
            "pv": sim_assets_pv[bot10_idx, :],
        },
    }

    with st.expander(
        f"📊 [심층 분석] {tgt_retire}세(은퇴) 도달 시점 시나리오별 자산 궤적 3종 비교",
        expanded=False,
    ):
        st.markdown(f"**총 {sim_assets_pv.shape[0]:,}번의 평행우주 중, 자산 성과 기준 대표 궤적입니다.**")

        c_m1, c_m2, c_m3 = st.columns(3)
        cols = [c_m1, c_m2, c_m3]

        comp_data = {"나이": years}
        target_age_idx = years.index(tgt_retire) if tgt_retire in years else -1

        for i, (label, data) in enumerate(paths.items()):
            ret_array = data["ret"]
            pv_array = data["pv"]

            cagr = (np.prod(1 + ret_array) ** (1 / len(years)) - 1) * 100
            tgt_pv_eok = pv_array[target_age_idx] / 100000000 if target_age_idx != -1 else 0

            cols[i].metric(
                label,
                f"{tgt_retire}세 자산 {tgt_pv_eok:.1f}억 원",
                f"연평균(CAGR): {cagr:.2f}%",
                delta_color="off",
            )

            short_label = label.split(" ")[0] + " " + label.split(" ")[1]
            comp_data[f"[{short_label}] 수익률(%)"] = np.round(ret_array * 100, 2)
            comp_data[f"[{short_label}] 자산(억)"] = np.round(pv_array / 100000000, 2)

        st.markdown("---")

        comp_df = pd.DataFrame(comp_data).set_index("나이")

        c_chart1, c_chart2 = st.columns(2)

        with c_chart1:
            st.markdown("###### 📈 연도별 적용 수익률 추이 비교")
            st.line_chart(
                comp_df[[c for c in comp_df.columns if "수익률" in c]],
                height=300,
            )

        with c_chart2:
            st.markdown("###### 💰 연도별 자산 잔고 추이 비교 (현재가치)")
            st.line_chart(
                comp_df[[c for c in comp_df.columns if "자산" in c]],
                height=300,
            )        
def render_stress_budget_section(stress_df, target_ruin, is_dwz):
    colors = [
        "#27AE60" if val <= target_ruin + 0.01
        else "#F1C40F" if val < target_ruin + 10
        else "#E74C3C"
        for val in stress_df["파산 확률(%)"]
    ]

    fig_stress = go.Figure(
        data=[
            go.Bar(
                x=stress_df["라벨"],
                y=stress_df["파산 확률(%)"],
                marker_color=colors,
                text=[f"{val:.1f}%" for val in stress_df["파산 확률(%)"]],
                textposition="auto",
            )
        ]
    )

    title_suffix = (
        f"(81세 컷오프 & {target_ruin:.0f}% 방어)"
        if is_dwz
        else f"({target_ruin:.0f}% 방어)"
    )

    fig_stress.update_layout(
        title=f"<b>월 여유 생활비별 파산 확률 {title_suffix}</b>",
        yaxis_title="파산 확률 (%)",
        height=300,
        plot_bgcolor="rgba(252, 252, 252, 1)",
        margin=dict(l=20, r=20, t=40, b=20),
    )

    fig_stress.add_hline(
        y=target_ruin,
        line_dash="dot",
        line_color="green",
        annotation_text=f"안전 방어선 ({target_ruin:.0f}%)",
    )

    with st.container(border=True):
        st.plotly_chart(fig_stress, use_container_width=True)            