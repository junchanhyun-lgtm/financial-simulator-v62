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
def render_main_asset_path_section(
    years,
    sim_assets_pv,
    base_ruin,
    target_ruin,
    tgt_retire,
    is_dwz,
    res_lump_df,
):
    st.markdown(f"##### 📈 메인 자산 궤적 ({tgt_retire}세 1차 방어선 집중)")

    median_pv = np.median(sim_assets_pv, axis=0) / 100000000
    top_10_pv = np.percentile(sim_assets_pv, 90, axis=0) / 100000000
    bottom_10_pv = np.percentile(sim_assets_pv, 10, axis=0) / 100000000

    idx_target = years.index(tgt_retire) if tgt_retire in years else -1

    k1, k2, k3 = st.columns(3)
    k1.metric("90세 최종 파산 확률", f"{base_ruin:.1f}%")
    k2.metric(f"{tgt_retire}세 예상 자산 (중앙값)", f"{median_pv[idx_target]:.2f}억 원")
    k3.metric(f"최악의 경우 (하위 10%)", f"{bottom_10_pv[idx_target]:.2f}억 원")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=years + years[::-1],
            y=np.concatenate([top_10_pv, bottom_10_pv[::-1]]),
            fill="toself",
            fillcolor="rgba(46, 134, 193, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="신뢰구간(10~90%)",
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=years,
            y=median_pv,
            line=dict(color="#2E86C1", width=3),
            name="중앙값",
            hovertemplate="%{y:.2f}억 원<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=years,
            y=bottom_10_pv,
            line=dict(color="#E74C3C", width=2, dash="dot"),
            name="하위 10%",
            hovertemplate="%{y:.2f}억 원<extra></extra>",
        )
    )

    fig.add_hline(
        y=0,
        line_dash="solid",
        line_color="#333333",
        line_width=1,
    )

    if tgt_retire in years:
        fig.add_vline(
            x=tgt_retire,
            line_dash="dash",
            line_color="#95a5a6",
            annotation_text="은퇴 & 수비형 전환",
        )

    if is_dwz and 81 in years:
        fig.add_vline(
            x=81,
            line_dash="dot",
            line_color="#9b59b6",
            annotation_text="사치 종료",
        )

    for _, row in res_lump_df.iterrows():
        if row["금액(만원)"] >= 10000 and row["나이"] in years:
            fig.add_vline(
                x=row["나이"],
                line_dash="dot",
                line_color="#f39c12",
                annotation_text=row["내용"],
            )

    fig.update_layout(
        xaxis_title="나이",
        yaxis_title="현재 체감 자산 (억 원)",
        height=450,
        plot_bgcolor="rgba(252, 252, 252, 1)",
        hovermode="x unified",
        margin=dict(t=20, l=10, r=10),
    )

    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True)  
def render_sensitivity_section(sens_df):
    st.markdown("##### 🌪️ 변수 민감도 분석 (파산 트리거)")

    sens_df_sorted = sens_df.sort_values(
        by="충격(%)",
        key=abs,
        ascending=True,
    )

    t_colors = [
        "#E74C3C" if val > 0 else "#27AE60"
        for val in sens_df_sorted["충격(%)"]
    ]

    fig_torn = go.Figure(
        go.Bar(
            x=sens_df_sorted["충격(%)"],
            y=sens_df_sorted["시나리오"],
            orientation="h",
            marker_color=t_colors,
            text=[
                f"+{v:.1f}%p" if v > 0 else f"{v:.1f}%p"
                for v in sens_df_sorted["충격(%)"]
            ],
            textposition="auto",
        )
    )

    fig_torn.update_layout(
        title="<b>해당 사건 발생 시 '파산 확률' 증감 폭</b>",
        xaxis_title="파산 확률 변동 폭 (%p)",
        height=250,
        plot_bgcolor="rgba(252, 252, 252, 1)",
        margin=dict(l=20, r=20, t=40, b=20),
    )

    fig_torn.add_vline(
        x=0,
        line_width=2,
        line_color="#333333",
    )

    with st.container(border=True):
        st.plotly_chart(fig_torn, use_container_width=True)              