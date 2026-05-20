import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from config import (
    ANNUAL_TRANSFER_TO_DUAL_MANWON,
    DATA_ANALYSIS_SUMMARY,
    DWZ_TARGET_RUIN_PROB,
    ESSENTIAL_SPENDING_RATIO,
    FAT_TAIL_DF,
    FLEXIBLE_SPENDING_RATIO,
    FIXED_RANDOM_SEED_ENABLED,
    INFLATION_SHOCK_ANNUAL_PROBABILITY,
    INFLATION_SHOCK_DURATION_YEARS,
    INFLATION_SHOCK_INFLATION_ADDON,
    INFLATION_SHOCK_RETURN_PENALTY,
    INFLATION_SHOCK_VOL_MULTIPLIER,
    INITIAL_DUAL_MOMENTUM_ASSET_MANWON,
    INITIAL_QUANT_ASSET_MANWON,
    INITIAL_VOO_ASSET_MANWON,
    ISA_ANNUAL_CONTRIBUTION_MANWON,
    ISA_MATURITY_TO_PENSION_DEFAULT_MANWON,
    MEAN_REVERSION_STRENGTH,
    MIN_TOTAL_ANNUAL_RETURN,
    RANDOM_SEED,
    RETIREMENT_SAVINGS_ANNUAL_CONTRIBUTION_MANWON,
    SCENARIO_OPTIONS,
    STANDARD_TARGET_RUIN_PROB,
    TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON,
    TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO,
    WARNING_RUIN_PROB,
)
from risk_metrics import build_real_life_risk_table
from simulator import build_failure_diagnostics


def _fmt_eok(value_won):
    return f"{value_won / 100_000_000:.2f}억 원"


def _safe_age_index(years, age):
    if age in years:
        return years.index(age)
    years_arr = np.asarray(years)
    return int(np.argmin(np.abs(years_arr - age)))


def _ruin_label(base_ruin):
    if base_ruin <= STANDARD_TARGET_RUIN_PROB:
        return "안전 기준 통과", "normal"
    if base_ruin <= DWZ_TARGET_RUIN_PROB:
        return "DWZ 허용 범위", "off"
    if base_ruin < WARNING_RUIN_PROB:
        return "주의", "off"
    return "위험", "inverse"


def _risk_card_color(value_text):
    try:
        value = float(str(value_text).replace("%", ""))
    except ValueError:
        return "off"
    if value < 20:
        return "normal"
    if value < 40:
        return "off"
    return "inverse"


def render_top_summary_section(res):
    years = res["years"]
    sim_assets_pv = res["pv"]
    base_ruin = res["base_ruin"]
    target_ruin = res["t_ruin"]
    safe_extra = res["safe_extra"]
    trimmed_avg_extra = res.get("trimmed_avg_extra", 0)
    tgt_retire = res["retire_age"]

    retire_idx = _safe_age_index(years, tgt_retire)
    final_assets = sim_assets_pv[:, -1]
    retire_assets = sim_assets_pv[:, retire_idx]

    p10_retire_asset = np.percentile(retire_assets, 10)
    median_retire_asset = np.median(retire_assets)
    median_final_asset = np.median(final_assets)

    status, delta_color = _ruin_label(base_ruin)

    st.info("💡 아래의 자산·지출·추가사용 가능액은 모두 현시점 구매력, 즉 현재가치 기준입니다.")

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "파산확률",
        f"{base_ruin:.1f}%",
        f"{status}",
        delta_color=delta_color,
    )
    m2.metric(
        "안전 여유자금",
        f"{safe_extra:,}만 원" if safe_extra > 0 else "0만 원",
        f"DWZ {target_ruin:.0f}% 방어선",
        delta_color="off",
    )
    m3.metric(
        "상하위 30% 제외 평균 여유자금",
        f"{trimmed_avg_extra:,}만 원" if trimmed_avg_extra > 0 else "0만 원",
        f"최종자산 평균 {TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON/10000:.0f}억 이상",
        delta_color="off",
    )

    st.caption(
        "안전 여유자금은 실제 소비 판단 기준입니다. "
        "상하위 30% 제외 평균 여유자금은 극단적으로 나쁘거나 좋은 경로를 모두 제거한 참고값입니다."
    )

    a1, a2 = st.columns(2)
    a1.metric(
        f"{tgt_retire}세 자산",
        _fmt_eok(median_retire_asset),
        f"하위 10%: {_fmt_eok(p10_retire_asset)}",
        delta_color="off",
    )
    a2.metric(
        f"{years[-1]}세 자산",
        _fmt_eok(median_final_asset),
        "중앙값 · 현재가치",
        delta_color="off",
    )

    threshold_text = (
        f"안전 기준 {STANDARD_TARGET_RUIN_PROB:.0f}% · "
        f"DWZ 기준 {DWZ_TARGET_RUIN_PROB:.0f}% · "
        f"위험 경고선 {WARNING_RUIN_PROB:.0f}%"
    )

    if base_ruin >= WARNING_RUIN_PROB:
        st.error(f"⚠️ 파산확률이 위험 경고선을 넘었습니다. {threshold_text}")
    elif base_ruin > DWZ_TARGET_RUIN_PROB:
        st.warning(f"⚠️ DWZ 허용 기준을 초과했습니다. {threshold_text}")
    elif base_ruin > STANDARD_TARGET_RUIN_PROB:
        st.warning(f"⚠️ 안전 기준은 넘지만 DWZ 허용 범위 안입니다. {threshold_text}")
    else:
        st.success(f"✅ 안전 기준을 통과했습니다. {threshold_text}")


def render_data_assumption_section():
    with st.expander("📌 업로드 자료 기반 수익률·변동성 산출값", expanded=False):
        df = pd.DataFrame(DATA_ANALYSIS_SUMMARY)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "원자료 CAGR": st.column_config.NumberColumn(format="%.2f%%"),
                "연간수익률 평균": st.column_config.NumberColumn(format="%.2f%%"),
                "연간 변동성": st.column_config.NumberColumn(format="%.2f%%"),
                "월수익률 연환산 변동성": st.column_config.NumberColumn(format="%.2f%%"),
                "MDD": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
        st.caption(
            "국내퀀트 7월말~11월말 단기채 구간은 별도 국내 단기채 월별 자료가 없어 0%로 두었습니다. "
            "V62-1 기본 엔진은 계좌별 원자료를 직접 합성하지 않고 통합 시나리오의 검토 근거로만 사용합니다."
        )


def render_main_asset_path_section(years, sim_assets_pv, tgt_retire, res_lump_df):
    st.markdown(f"##### 📈 현재가치 자산 궤적 ({tgt_retire}세 은퇴 기준)")

    median_pv = np.median(sim_assets_pv, axis=0) / 100000000
    top_10_pv = np.percentile(sim_assets_pv, 90, axis=0) / 100000000
    bottom_10_pv = np.percentile(sim_assets_pv, 10, axis=0) / 100000000

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years + years[::-1],
            y=np.concatenate([top_10_pv, bottom_10_pv[::-1]]),
            fill="toself",
            fillcolor="rgba(46, 134, 193, 0.14)",
            line=dict(color="rgba(255,255,255,0)"),
            name="10~90% 범위",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=median_pv,
            line=dict(color="#2563eb", width=3),
            name="중앙값",
            hovertemplate="%{y:.2f}억 원<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=bottom_10_pv,
            line=dict(color="#dc2626", width=2, dash="dot"),
            name="하위 10%",
            hovertemplate="%{y:.2f}억 원<extra></extra>",
        )
    )

    fig.add_hline(y=0, line_dash="solid", line_color="#333333", line_width=1)

    if tgt_retire in years:
        fig.add_vline(
            x=tgt_retire,
            line_dash="dash",
            line_color="#64748b",
            annotation_text="은퇴",
        )

    for _, row in res_lump_df.iterrows():
        if row["금액(만원)"] >= 10000 and row["나이"] in years:
            fig.add_vline(
                x=row["나이"],
                line_dash="dot",
                line_color="#f59e0b",
                annotation_text=row["내용"],
            )

    fig.update_layout(
        xaxis_title="나이",
        yaxis_title="현재가치 자산 (억 원)",
        height=500,
        plot_bgcolor="rgba(252, 252, 252, 1)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=40, l=10, r=10, b=20),
    )

    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "중앙값은 일반적인 경로, 하위 10%는 불리한 장기 경로입니다. "
            "그래프의 모든 금액은 현재가치 기준입니다."
        )


def render_failure_diagnostics_section(res):
    with st.expander("🔍 결과 원인 분해 패널", expanded=True):
        diag = build_failure_diagnostics(res, res["retire_age"])
        st.caption(
            "파산 경로와 생존 경로를 분리해 은퇴시점 자산, 은퇴 직후 수익률, 인플레이션 쇼크, "
            "국내퀀트 페널티, 은퇴 전 순인출을 비교합니다. 결과값 자체를 바꾸지 않는 후처리 진단입니다."
        )
        st.dataframe(diag["diagnostic_df"], use_container_width=True, hide_index=True)
        st.info(diag["reason_text"])


def render_real_life_risk_section(res):
    risk_df = build_real_life_risk_table(res)

    st.markdown("##### 🧭 현실 리스크 3대 지표")
    st.caption(
        "파산확률만으로 보이지 않는 체감 리스크입니다. 지표 수를 세 가지로 줄여 해석력을 높였습니다."
    )

    cols = st.columns(3)
    for col, (_, row) in zip(cols, risk_df.iterrows()):
        with col:
            with st.container(border=True):
                st.metric(
                    row["지표"],
                    row["값"],
                    row["기준"],
                    delta_color=_risk_card_color(row["값"]),
                )
                st.caption(row["해석"])


def render_scenario_comparison_section(res):
    scenario_df = res.get("scenario_comparison_df")
    if scenario_df is None or scenario_df.empty:
        return

    with st.expander("📊 시나리오별 결과 비교", expanded=True):
        st.caption(
            "보수·기본·공격 통합 시나리오를 같은 입력값 기준으로 비교합니다. "
            "현재 선택된 시나리오에는 * 표시가 붙습니다."
        )
        st.dataframe(
            scenario_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "파산확률": st.column_config.NumberColumn(format="%.1f%%"),
                "은퇴시점 중앙값(억)": st.column_config.NumberColumn(format="%.2f"),
                "은퇴시점 하위10%(억)": st.column_config.NumberColumn(format="%.2f"),
                "최종 중앙값(억)": st.column_config.NumberColumn(format="%.2f"),
                "은퇴 후 반토막 경험률": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )


def render_sensitivity_section(res):
    sensitivity_df = res.get("sensitivity_df")
    if sensitivity_df is None or sensitivity_df.empty:
        return

    with st.expander("🌪️ 확장 민감도 분석", expanded=True):
        st.caption(
            "수익률, 변동성, 물가, 지출, 은퇴시점, 주택구입, 주택연금 지연이 파산확률에 미치는 영향을 비교합니다."
        )
        st.dataframe(
            sensitivity_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "파산확률": st.column_config.NumberColumn(format="%.1f%%"),
                "기준 대비 변화(%p)": st.column_config.NumberColumn(format="%.1f"),
            },
        )

        sorted_df = sensitivity_df.sort_values(by="기준 대비 변화(%p)", key=abs, ascending=True)
        fig = go.Figure(
            go.Bar(
                x=sorted_df["기준 대비 변화(%p)"],
                y=sorted_df["민감도 항목"],
                orientation="h",
                text=[f"{v:+.1f}%p" for v in sorted_df["기준 대비 변화(%p)"]],
                textposition="auto",
            )
        )
        fig.add_vline(x=0, line_width=1, line_color="#333333")
        fig.update_layout(
            title="기준 대비 파산확률 변화",
            xaxis_title="파산확률 변화(%p)",
            height=360,
            plot_bgcolor="rgba(252, 252, 252, 1)",
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)


def render_stress_budget_section(stress_df, target_ruin):
    with st.expander("💸 월 추가 사용액별 파산확률", expanded=False):
        colors = [
            "#16a34a" if val <= STANDARD_TARGET_RUIN_PROB
            else "#f59e0b" if val <= DWZ_TARGET_RUIN_PROB
            else "#ef4444" if val >= WARNING_RUIN_PROB
            else "#facc15"
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

        fig_stress.update_layout(
            title="<b>추가 사용액별 파산확률</b>",
            yaxis_title="파산확률 (%)",
            height=300,
            plot_bgcolor="rgba(252, 252, 252, 1)",
            margin=dict(l=20, r=20, t=40, b=20),
        )
        fig_stress.add_hline(
            y=STANDARD_TARGET_RUIN_PROB,
            line_dash="dot",
            line_color="green",
            annotation_text=f"안전 {STANDARD_TARGET_RUIN_PROB:.0f}%",
        )
        fig_stress.add_hline(
            y=target_ruin,
            line_dash="dot",
            line_color="orange",
            annotation_text=f"DWZ {target_ruin:.0f}%",
        )
        fig_stress.add_hline(
            y=WARNING_RUIN_PROB,
            line_dash="dot",
            line_color="red",
            annotation_text=f"위험 {WARNING_RUIN_PROB:.0f}%",
        )

        st.plotly_chart(fig_stress, use_container_width=True)
        st.caption("추가 사용 가능액은 DWZ 방어선 기준으로 역산합니다. 모든 금액은 현재가치 기준입니다.")


def render_applied_model_section(res):
    defense_rate = res["defense_rate"]

    model_df = pd.DataFrame(
        [
            {
                "모델": "결과 표시 기준",
                "현재 설정": "모든 금액 현재가치",
                "의미": "인플레이션을 역산한 현시점 구매력 기준으로 자산·지출·연금·추가사용액을 표시합니다.",
            },
            {
                "모델": "기본 엔진",
                "현재 설정": "총 금융자산 통합 시뮬레이션",
                "의미": "국내퀀트·연금저축/ISA·VOO를 장기 계좌별로 강제 분리하지 않고, 전체 금융자산의 통합 기대수익률·변동성으로 계산합니다.",
            },
            {
                "모델": "시나리오 수익률",
                "현재 설정": "보수/기본/공격 통합 시나리오",
                "의미": "업로드 자료의 원자료 CAGR은 참고값으로만 두고, 미래 알파 감소와 운용 현실성을 반영한 통합 수익률 가정을 사용합니다.",
            },
            {
                "모델": "연금저축 납입",
                "현재 설정": f"연 {RETIREMENT_SAVINGS_ANNUAL_CONTRIBUTION_MANWON:,}만 원",
                "의미": "세액공제 목적의 계좌 내부 이동으로 보며, 총 금융자산 자체를 감소시키는 지출 이벤트로 처리하지 않습니다.",
            },
            {
                "모델": "ISA 신규납입",
                "현재 설정": f"연 {ISA_ANNUAL_CONTRIBUTION_MANWON:,}만 원",
                "의미": "연금저축 과대적립을 피하기 위해 ISA 신규납입은 기본 0원으로 두고, 기존 ISA는 만기 전 연장 또는 일부 연금전환 여부를 별도 판단합니다.",
            },
            {
                "모델": "ISA 만기 연금전환",
                "현재 설정": f"기본 {ISA_MATURITY_TO_PENSION_DEFAULT_MANWON:,}만 원",
                "의미": "총자산 모델에서는 기본값을 0원으로 두며, 필요 시 별도 이벤트/민감도 분석으로 판단합니다.",
            },
            {
                "모델": "계좌이동 기반 전환",
                "현재 설정": f"연 {ANNUAL_TRANSFER_TO_DUAL_MANWON:,}만 원",
                "의미": "V60-7의 연 3,800만 원 이전 가정은 제거했습니다. 계좌 간 이동은 총자산에는 중립이므로 기본 수익률 경로를 흔들지 않습니다.",
            },
            {
                "모델": "고정 seed 검증",
                "현재 설정": f"{'사용' if FIXED_RANDOM_SEED_ENABLED else '미사용'} · seed {RANDOM_SEED}",
                "의미": "같은 입력이면 같은 난수 경로가 재현되어 코드 수정 전후 결과 비교가 안정적입니다.",
            },
            {
                "모델": "파산확률 판단 기준",
                "현재 설정": f"안전 {STANDARD_TARGET_RUIN_PROB:.0f}% / DWZ {DWZ_TARGET_RUIN_PROB:.0f}% / 경고 {WARNING_RUIN_PROB:.0f}%",
                "의미": "안전 기준과 DWZ 허용 기준을 동시에 보여주며, 20% 이상은 지출·은퇴시점 재검토 구간입니다.",
            },
            {
                "모델": "여유자금 산출",
                "현재 설정": f"안전 기준 + 상하위 {TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO*100:.0f}% 제외 평균 기준",
                "의미": f"참고 여유자금은 극단 경로를 제외한 중앙부 최종 현재가치 평균이 {TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON/10000:.0f}억 원 이상 남는 수준입니다.",
            },
            {
                "모델": "수익률 분포",
                "현재 설정": f"팻테일 df={FAT_TAIL_DF}, 평균회귀 {MEAN_REVERSION_STRENGTH * 100:.1f}%",
                "의미": "정규분포보다 극단 손실을 더 반영하되, 폭락 후 자동 회복 가정은 약하게 둡니다.",
            },
            {
                "모델": "연간수익률 하한",
                "현재 설정": f"{MIN_TOTAL_ANNUAL_RETURN * 100:.0f}% 하한",
                "의미": "t분포 난수가 만드는 -100% 이하 비현실적 연간수익률을 차단합니다.",
            },
            {
                "모델": "고물가 쇼크",
                "현재 설정": f"연 {INFLATION_SHOCK_ANNUAL_PROBABILITY * 100:.1f}% / {INFLATION_SHOCK_DURATION_YEARS}년 지속",
                "의미": f"쇼크 중 물가 +{INFLATION_SHOCK_INFLATION_ADDON * 100:.1f}%p, 수익률 -{INFLATION_SHOCK_RETURN_PENALTY * 100:.1f}%p, 변동성 {INFLATION_SHOCK_VOL_MULTIPLIER:.1f}배를 적용합니다.",
            },
            {
                "모델": "DWZ 지출 구조",
                "현재 설정": f"필수 {ESSENTIAL_SPENDING_RATIO * 100:.0f}% / 조정가능 {FLEXIBLE_SPENDING_RATIO * 100:.0f}%",
                "의미": "나이와 시장 하락에 따른 긴축은 조정가능지출에만 적용하고, 필수지출은 자동 삭감하지 않습니다.",
            },
            {
                "모델": "국내퀀트 규모 페널티",
                "현재 설정": f"국내퀀트 시작비중 {INITIAL_QUANT_ASSET_MANWON/(INITIAL_QUANT_ASSET_MANWON+INITIAL_DUAL_MOMENTUM_ASSET_MANWON+INITIAL_VOO_ASSET_MANWON)*100:.1f}% 기준 추정",
                "의미": "총자산 모델에서도 국내퀀트 비중을 추정해 규모별 수익률 차감만 반영합니다.",
            },
            {
                "모델": "주택·연금·세금 처리",
                "현재 설정": "주택은 지출 / 연금은 수입 / 세금·건보료는 이벤트",
                "의미": "주택구입은 금융자산의 비유동자산 전환, 주택연금·국민연금은 현재가치 수입, 건보료·세금은 보수적 지출 이벤트로 처리합니다.",
            },
            {
                "모델": "확정연금 방어율",
                "현재 설정": f"{defense_rate:.1f}%",
                "의미": "현재 월 기본지출 대비 확정연금성 수입의 비율입니다.",
            },
        ]
    )

    with st.expander("🧩 자동 적용 모델과 해석", expanded=True):
        st.dataframe(model_df, use_container_width=True, hide_index=True)

def render_representative_paths_section(years, sim_assets_pv, sim_returns, tgt_retire):
    final_assets = sim_assets_pv[:, -1]

    top10_idx = np.abs(final_assets - np.percentile(final_assets, 90)).argmin()
    median_idx = np.abs(final_assets - np.percentile(final_assets, 50)).argmin()
    bot10_idx = np.abs(final_assets - np.percentile(final_assets, 10)).argmin()

    paths = {
        "상위 10%": {"ret": sim_returns[top10_idx, :], "pv": sim_assets_pv[top10_idx, :]},
        "중앙값": {"ret": sim_returns[median_idx, :], "pv": sim_assets_pv[median_idx, :]},
        "하위 10%": {"ret": sim_returns[bot10_idx, :], "pv": sim_assets_pv[bot10_idx, :]},
    }

    with st.expander("📊 고급 분석: 대표 경로 3종 비교", expanded=False):
        st.caption("기본 화면은 파산확률, 자산 궤적, 현실 리스크 3대 지표 중심으로 정리했습니다.")

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
            st.line_chart(comp_df[[c for c in comp_df.columns if "수익률" in c]], height=300)

        with c_chart2:
            st.markdown("###### 연도별 현재가치 자산")
            st.line_chart(comp_df[[c for c in comp_df.columns if "자산" in c]], height=300)


def render_results_page(res):
    years = res["years"]
    sim_assets_pv = res["pv"]
    sim_returns = res["returns"]
    stress_df = res["stress_df"]
    target_ruin = res["t_ruin"]
    res_lump_df = res["lump_df"]
    tgt_retire = res["retire_age"]

    render_top_summary_section(res)
    render_data_assumption_section()
    st.markdown("---")

    render_main_asset_path_section(years, sim_assets_pv, tgt_retire, res_lump_df)
    st.markdown("---")

    render_failure_diagnostics_section(res)
    render_real_life_risk_section(res)
    render_scenario_comparison_section(res)
    render_sensitivity_section(res)
    render_stress_budget_section(stress_df, target_ruin)
    render_applied_model_section(res)

    render_representative_paths_section(years, sim_assets_pv, sim_returns, tgt_retire)
