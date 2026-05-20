import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from config import (
    FAT_TAIL_DF,
    INFLATION_SHOCK_ANNUAL_PROBABILITY,
    INFLATION_SHOCK_DURATION_YEARS,
    INFLATION_SHOCK_INFLATION_ADDON,
    INFLATION_SHOCK_RETURN_PENALTY,
    INFLATION_SHOCK_VOL_MULTIPLIER,
    MEAN_REVERSION_STRENGTH,
    WARNING_RUIN_PROB,
)
from risk_metrics import build_real_life_risk_table


def _fmt_eok(value_won):
    return f"{value_won / 100_000_000:.2f}억 원"


def _safe_age_index(years, age):
    if age in years:
        return years.index(age)
    years_arr = np.asarray(years)
    return int(np.argmin(np.abs(years_arr - age)))


def _ruin_status(base_ruin, target_ruin):
    if base_ruin <= target_ruin:
        return "기준 통과", "normal"
    if base_ruin >= WARNING_RUIN_PROB:
        return "위험", "inverse"
    return "기준 초과", "off"


def render_simulation_summary_section(safe_extra, base_ruin, target_ruin):
    """
    이전 app.py 호환을 위한 요약 함수입니다.
    현재 app.py에서는 render_results_page() 내부의 요약 카드가 기본 표시됩니다.
    """
    status, delta_color = _ruin_status(base_ruin, target_ruin)

    st.info(
        "💡 모든 결괏값은 인플레이션을 역산한 현재 체감 구매력(Present Value) 기준입니다."
    )

    c1, c2 = st.columns(2)
    c1.metric(
        "기본 파산확률",
        f"{base_ruin:.1f}%",
        f"목표 {target_ruin:.0f}% · {status}",
        delta_color=delta_color,
    )
    c2.metric(
        "월 추가 사용 가능액",
        f"{safe_extra:,}만 원" if safe_extra > 0 else "0만 원",
        "목표 파산확률 방어선 기준",
        delta_color="off",
    )


def render_top_summary_section(res):
    years = res["years"]
    sim_assets_pv = res["pv"]
    base_ruin = res["base_ruin"]
    target_ruin = res["t_ruin"]
    safe_extra = res["safe_extra"]
    tgt_retire = res["retire_age"]

    retire_idx = _safe_age_index(years, tgt_retire)
    final_assets = sim_assets_pv[:, -1]
    retire_assets = sim_assets_pv[:, retire_idx]

    median_retire_asset = np.median(retire_assets)
    p10_retire_asset = np.percentile(retire_assets, 10)
    median_final_asset = np.median(final_assets)

    status, delta_color = _ruin_status(base_ruin, target_ruin)

    st.info(
        "💡 모든 결괏값은 인플레이션을 역산한 현재 체감 구매력(Present Value) 기준입니다."
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "기본 파산확률",
        f"{base_ruin:.1f}%",
        f"목표 {target_ruin:.0f}% · {status}",
        delta_color=delta_color,
    )
    m2.metric(
        "월 추가 사용 가능액",
        f"{safe_extra:,}만 원" if safe_extra > 0 else "0만 원",
        "목표 방어선 기준",
        delta_color="off",
    )
    m3.metric(
        f"{tgt_retire}세 중앙값 자산",
        _fmt_eok(median_retire_asset),
        f"하위 10%: {_fmt_eok(p10_retire_asset)}",
        delta_color="off",
    )
    m4.metric(
        f"{years[-1]}세 중앙값 자산",
        _fmt_eok(median_final_asset),
        "현재가치 기준",
        delta_color="off",
    )

    if base_ruin >= WARNING_RUIN_PROB:
        st.error(
            f"⚠️ 파산확률이 {WARNING_RUIN_PROB:.0f}% 이상입니다. "
            "현재 지출, 은퇴 시점, 수익률 가정 중 하나 이상을 재검토해야 합니다."
        )
    elif base_ruin > target_ruin:
        st.warning(
            f"⚠️ 현재 파산확률이 목표 방어선 {target_ruin:.0f}%를 초과합니다. "
            "추가 소비 여력은 없는 것으로 해석하는 것이 안전합니다."
        )
    else:
        st.success(
            f"✅ 현재 입력값에서는 목표 파산확률 {target_ruin:.0f}% 방어선을 통과했습니다."
        )


def render_stress_budget_section(stress_df, target_ruin, is_dwz):
    st.markdown("##### 💸 월 추가지출 방어선")

    colors = [
        "#27AE60" if val <= target_ruin + 0.01
        else "#F1C40F" if val < WARNING_RUIN_PROB
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
        f"DWZ {target_ruin:.0f}% 방어선"
        if is_dwz
        else f"기본 {target_ruin:.0f}% 방어선"
    )

    fig_stress.update_layout(
        title=f"<b>추가지출별 파산확률 ({title_suffix})</b>",
        yaxis_title="파산확률 (%)",
        height=300,
        plot_bgcolor="rgba(252, 252, 252, 1)",
        margin=dict(l=20, r=20, t=40, b=20),
    )

    fig_stress.add_hline(
        y=target_ruin,
        line_dash="dot",
        line_color="green",
        annotation_text=f"목표 방어선 {target_ruin:.0f}%",
    )
    fig_stress.add_hline(
        y=WARNING_RUIN_PROB,
        line_dash="dot",
        line_color="red",
        annotation_text=f"경고선 {WARNING_RUIN_PROB:.0f}%",
    )

    with st.container(border=True):
        st.plotly_chart(fig_stress, use_container_width=True)
        st.caption(
            "※ 추가지출 가능액은 자산경로가 아니라 목표 파산확률 방어선을 기준으로 역산한 값입니다."
        )


def render_main_asset_path_section(
    years,
    sim_assets_pv,
    target_ruin,
    tgt_retire,
    is_dwz,
    res_lump_df,
):
    st.markdown(f"##### 📈 자산 궤적 ({tgt_retire}세 은퇴 기준)")

    median_pv = np.median(sim_assets_pv, axis=0) / 100000000
    top_10_pv = np.percentile(sim_assets_pv, 90, axis=0) / 100000000
    bottom_10_pv = np.percentile(sim_assets_pv, 10, axis=0) / 100000000

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
            annotation_text="은퇴",
        )

    if is_dwz and 85 in years:
        fig.add_vline(
            x=85,
            line_dash="dot",
            line_color="#9b59b6",
            annotation_text="조정가능지출 25%",
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
        yaxis_title="현재가치 자산 (억 원)",
        height=480,
        plot_bgcolor="rgba(252, 252, 252, 1)",
        hovermode="x unified",
        margin=dict(t=20, l=10, r=10),
    )

    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"녹색 기준선은 목표 파산확률 {target_ruin:.0f}% 방어선이며, "
            "그래프의 하위 10% 경로는 나쁜 장기 경로의 자산 방어력을 확인하기 위한 기준입니다."
        )


def render_real_life_risk_section(res):
    risk_df = build_real_life_risk_table(res)

    with st.container(border=True):
        st.markdown("##### 🧭 현실 리스크 지표")
        st.caption(
            "파산 전 단계에서 실제로 체감할 수 있는 낙폭, 시퀀스 리스크, 자산 훼손 위험입니다. "
            "기존 몬테카를로 결과에서 파생 계산하며 자산경로 계산식은 바꾸지 않습니다."
        )
        st.dataframe(risk_df, use_container_width=True, hide_index=True)


def render_representative_paths_section(years, sim_assets_pv, sim_returns, tgt_retire):
    final_assets = sim_assets_pv[:, -1]

    top10_idx = np.abs(final_assets - np.percentile(final_assets, 90)).argmin()
    median_idx = np.abs(final_assets - np.percentile(final_assets, 50)).argmin()
    bot10_idx = np.abs(final_assets - np.percentile(final_assets, 10)).argmin()

    paths = {
        "상위 10%": {
            "ret": sim_returns[top10_idx, :],
            "pv": sim_assets_pv[top10_idx, :],
        },
        "중앙값": {
            "ret": sim_returns[median_idx, :],
            "pv": sim_assets_pv[median_idx, :],
        },
        "하위 10%": {
            "ret": sim_returns[bot10_idx, :],
            "pv": sim_assets_pv[bot10_idx, :],
        },
    }

    with st.expander("📊 고급 분석: 대표 경로 3종 비교", expanded=False):
        st.caption("민감도 분석과 구간별 승률은 기본 결과 화면에서 제거했습니다.")

        c_m1, c_m2, c_m3 = st.columns(3)
        cols = [c_m1, c_m2, c_m3]

        comp_data = {"나이": years}
        target_age_idx = _safe_age_index(years, tgt_retire)

        for i, (label, data) in enumerate(paths.items()):
            ret_array = data["ret"]
            pv_array = data["pv"]

            cagr = (np.prod(1 + ret_array) ** (1 / len(years)) - 1) * 100
            tgt_pv_eok = pv_array[target_age_idx] / 100000000

            cols[i].metric(
                label,
                f"{tgt_retire}세 {tgt_pv_eok:.1f}억 원",
                f"CAGR {cagr:.2f}%",
                delta_color="off",
            )

            comp_data[f"[{label}] 수익률(%)"] = np.round(ret_array * 100, 2)
            comp_data[f"[{label}] 자산(억)"] = np.round(pv_array / 100000000, 2)

        comp_df = pd.DataFrame(comp_data).set_index("나이")

        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            st.markdown("###### 연도별 적용 수익률")
            st.line_chart(
                comp_df[[c for c in comp_df.columns if "수익률" in c]],
                height=300,
            )

        with c_chart2:
            st.markdown("###### 연도별 자산 잔고")
            st.line_chart(
                comp_df[[c for c in comp_df.columns if "자산" in c]],
                height=300,
            )


def render_engine_notes_section(defense_rate):
    with st.container(border=True):
        st.subheader("💡 현재 모델 해석")
        st.info(
            f"""
            **1. 현재가치 기준**  
            모든 결과는 인플레이션을 역산한 현재 체감 구매력 기준입니다. 현재 월 기본지출 대비 확정연금 방어율은 **{defense_rate:.1f}%**입니다.

            **2. 포트폴리오 수익률 가정**  
            수익률 시나리오는 국내 퀀트 10.7억, 듀얼모멘텀 1.2억, VOO 0.7억의 현재 포트폴리오를 기준으로 보수·기본·공격 3단계로 재정리했습니다.

            **3. 계좌이동 기반 포트폴리오 전환**  
            기존 은퇴 5년 전 강제 글라이드패스 대신, 은퇴 전까지 국내퀀트에서 연금저축+ISA로 매년 3,800만 원을 이체하는 계획을 수익률·변동성 경로에 반영합니다.

            **4. DWZ 지출 구조**  
            월 기본지출을 필수지출과 조정가능지출로 내부 분해합니다. DWZ 나이별 감소와 시장 하락 긴축은 조정가능지출에만 적용하고, 이벤트성 지출은 자동 삭감하지 않습니다.

            **5. 국내퀀트 운용규모 페널티**  
            총자산 기준 로그형 차감 대신 국내퀀트 추정 운용금액 기준 구간형 페널티를 적용합니다. 현재 규모에서는 추가 차감이 거의 없고, 15억 초과 구간부터 단계적으로 차감합니다.

            **6. 파산확률 기준**  
            일반 기준은 10%, DWZ 기준은 15%입니다. 20% 이상은 경고 구간으로 봅니다.

            **7. 수익률 분포 현실화**  
            팻테일은 t분포 자유도 **{FAT_TAIL_DF}**로 완화했습니다. 인플레이션 쇼크는 은퇴 직후 강제 발생이 아니라 생애기간 중 매년 **{INFLATION_SHOCK_ANNUAL_PROBABILITY * 100:.1f}%** 확률로 시작되는 **{INFLATION_SHOCK_DURATION_YEARS}년** 이벤트로 처리합니다. 쇼크 중 물가는 **+{INFLATION_SHOCK_INFLATION_ADDON * 100:.1f}%p**, 기대수익률은 **-{INFLATION_SHOCK_RETURN_PENALTY * 100:.1f}%p**, 변동성은 **{INFLATION_SHOCK_VOL_MULTIPLIER:.1f}배**로 조정합니다. 평균회귀는 **{MEAN_REVERSION_STRENGTH * 100:.1f}%**로 낮춰 폭락 후 자동 회복 가정을 완화했습니다.
            """
        )


def render_results_page(res):
    years = res["years"]
    sim_assets_pv = res["pv"]
    sim_returns = res["returns"]
    stress_df = res["stress_df"]

    is_dwz = res["dwz_mode"]
    target_ruin = res["t_ruin"]
    res_lump_df = res["lump_df"]
    tgt_retire = res["retire_age"]

    render_top_summary_section(res)
    st.markdown("---")

    left_col, right_col = st.columns([2.4, 1.1])

    with left_col:
        render_main_asset_path_section(
            years,
            sim_assets_pv,
            target_ruin,
            tgt_retire,
            is_dwz,
            res_lump_df,
        )
        render_stress_budget_section(
            stress_df,
            target_ruin,
            is_dwz,
        )

    with right_col:
        render_engine_notes_section(res["defense_rate"])

    st.markdown("---")
    render_real_life_risk_section(res)

    render_representative_paths_section(
        years,
        sim_assets_pv,
        sim_returns,
        tgt_retire,
    )
