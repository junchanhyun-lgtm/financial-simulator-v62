import html

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
    MAX_TOTAL_ANNUAL_RETURN,
    RANDOM_SEED,
    RETIREMENT_SAVINGS_ANNUAL_CONTRIBUTION_MANWON,
    STANDARD_TARGET_RUIN_PROB,
    TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON,
    TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO,
    WARNING_RUIN_PROB,
    QUANT_SIZE_PENALTY_ANNUAL_RATIO,
    QUANT_STRATEGY_MONTHS_PER_YEAR,
)
from risk_metrics import build_real_life_risk_table
from simulator import build_failure_diagnostics, build_return_distribution_diagnostics


# -----------------------------------------------------------
# 공통 표시 유틸
# -----------------------------------------------------------
def _fmt_eok(value_won):
    if value_won is None or pd.isna(value_won):
        return "-"
    return f"{value_won / 100_000_000:.2f}억 원"


def _fmt_manwon(value_manwon):
    if value_manwon is None or pd.isna(value_manwon):
        return "-"
    val = int(round(float(value_manwon)))
    return f"{val:,}만 원"


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


def _status_tone(base_ruin):
    if base_ruin <= STANDARD_TARGET_RUIN_PROB:
        return "success", "안전 기준 통과", "기준 파산확률이 안전선 안에 있습니다."
    if base_ruin <= DWZ_TARGET_RUIN_PROB:
        return "warning", "DWZ 허용 범위", "엄격한 안전선은 넘지만 DWZ 허용 범위 안입니다."
    if base_ruin < WARNING_RUIN_PROB:
        return "warning", "주의", "추가지출이나 은퇴시점 변경 전 재점검이 필요합니다."
    return "danger", "위험", "파산확률이 위험 경고선을 넘어 지출·은퇴시점 재검토가 필요합니다."


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


def _metric_tone_from_pct(value):
    if value <= STANDARD_TARGET_RUIN_PROB:
        return "success"
    if value < WARNING_RUIN_PROB:
        return "warning"
    return "danger"


def _escape(value):
    return html.escape(str(value))


def _render_kpi_card(title, value, subtitle, tone="neutral"):
    st.markdown(
        f"""
        <div class="kpi-card {tone}">
            <div class="kpi-label">{_escape(title)}</div>
            <div class="kpi-value">{_escape(value)}</div>
            <div class="kpi-subtitle">{_escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_section_header(title, subtitle=None):
    subtitle_html = f"<div class='section-subtitle'>{_escape(subtitle)}</div>" if subtitle else ""
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">{_escape(title)}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _styled_plotly_layout(fig, height=460, title=None):
    fig.update_layout(
        title=title,
        height=height,
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(248, 250, 252, 1)",
        font=dict(family="Arial, sans-serif", color="#0f172a", size=13),
        margin=dict(t=48 if title else 30, l=12, r=12, b=24),
        hoverlabel=dict(bgcolor="#0f172a", font_color="#ffffff"),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148, 163, 184, 0.18)",
        zeroline=False,
        linecolor="rgba(148, 163, 184, 0.35)",
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148, 163, 184, 0.18)",
        zeroline=False,
        linecolor="rgba(148, 163, 184, 0.35)",
    )
    return fig



def _pct_text_to_float(value_text):
    try:
        return float(str(value_text).replace("%", "").strip())
    except (TypeError, ValueError):
        return np.nan


def _normalize_series(values):
    arr = pd.to_numeric(pd.Series(values), errors="coerce").astype(float)
    if arr.empty or arr.isna().all():
        return pd.Series(np.full(len(arr), 50.0), index=arr.index)
    min_val = arr.min()
    max_val = arr.max()
    if np.isclose(max_val, min_val):
        return pd.Series(np.full(len(arr), 50.0), index=arr.index)
    return ((arr - min_val) / (max_val - min_val) * 100.0).clip(0.0, 100.0)


def _decision_grade(base_ruin, half_asset_rate=None):
    half_asset_rate = 0.0 if half_asset_rate is None or pd.isna(half_asset_rate) else float(half_asset_rate)
    if base_ruin <= STANDARD_TARGET_RUIN_PROB and half_asset_rate < 25.0:
        return "매우 안정"
    if base_ruin <= STANDARD_TARGET_RUIN_PROB:
        return "안정"
    if base_ruin <= DWZ_TARGET_RUIN_PROB:
        return "DWZ 허용"
    if base_ruin < WARNING_RUIN_PROB:
        return "주의"
    return "위험"


def _decision_tone_from_grade(grade):
    if grade in ("매우 안정", "안정"):
        return "success"
    if grade in ("DWZ 허용", "주의"):
        return "warning"
    return "danger"


def _top_sensitivity_driver(res):
    sensitivity_df = res.get("sensitivity_df")
    if sensitivity_df is None or sensitivity_df.empty or "기준 대비 변화(%p)" not in sensitivity_df.columns:
        return "민감도 결과 없음"

    df = sensitivity_df.copy()
    df["기준 대비 변화(%p)"] = pd.to_numeric(df["기준 대비 변화(%p)"], errors="coerce")
    df = df.dropna(subset=["기준 대비 변화(%p)"])
    if df.empty:
        return "민감도 결과 없음"

    harmful = df[df["기준 대비 변화(%p)"] > 0].sort_values("기준 대비 변화(%p)", ascending=False)
    if harmful.empty:
        row = df.iloc[df["기준 대비 변화(%p)"].abs().argmax()]
    else:
        row = harmful.iloc[0]

    return f"{row['민감도 항목']} ({row['기준 대비 변화(%p)']:+.1f}%p)"


def _primary_risk_driver(res):
    risk_df = build_real_life_risk_table(res)
    if risk_df is None or risk_df.empty:
        return "현실 리스크 결과 없음"

    def score_row(row):
        value = _pct_text_to_float(row.get("값", ""))
        if pd.isna(value):
            return -1.0
        label = str(row.get("지표", ""))
        if "반토막" in label:
            return value * 1.15
        if "시퀀스" in label:
            return value * 1.05
        return value

    scored = risk_df.copy()
    scored["_score"] = scored.apply(score_row, axis=1)
    row = scored.sort_values("_score", ascending=False).iloc[0]
    return f"{row['지표']} {row['값']}"


def _add_scenario_stability_columns(scenario_df):
    df = scenario_df.copy()
    if df.empty:
        return df

    ruin = pd.to_numeric(df.get("파산확률"), errors="coerce").fillna(100.0)
    half = pd.to_numeric(df.get("은퇴 후 반토막 경험률"), errors="coerce").fillna(100.0)
    retire_p10 = pd.to_numeric(df.get("은퇴시점 하위10%(억)"), errors="coerce").fillna(0.0)
    final_median = pd.to_numeric(df.get("최종 중앙값(억)"), errors="coerce").fillna(0.0)

    ruin_component = (100.0 - ruin * 4.0).clip(0.0, 100.0) * 0.45
    half_component = (100.0 - half * 1.8).clip(0.0, 100.0) * 0.25
    retire_component = _normalize_series(retire_p10) * 0.20
    final_component = _normalize_series(final_median) * 0.10

    score = (ruin_component + half_component + retire_component + final_component).round(1)
    df.insert(1, "종합판정", [
        _decision_grade(r, h) for r, h in zip(ruin, half)
    ])
    df.insert(2, "안정성 점수", score)
    df.insert(3, "추천순위", score.rank(method="min", ascending=False).astype(int))

    return df.sort_values(["추천순위", "파산확률"], ascending=[True, True])


# -----------------------------------------------------------
# 결과 상단 핵심 요약
# -----------------------------------------------------------
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
    p10_final_asset = np.percentile(final_assets, 10)

    tone, status_text, status_sentence = _status_tone(base_ruin)
    badge_class = f"status-badge status-{tone}"

    threshold_text = (
        f"안전 {STANDARD_TARGET_RUIN_PROB:.0f}% · "
        f"DWZ {DWZ_TARGET_RUIN_PROB:.0f}% · "
        f"위험 {WARNING_RUIN_PROB:.0f}%"
    )

    st.markdown(
        f"""
        <div class="result-hero">
            <div class="result-hero-top">
                <div>
                    <div class="result-hero-title">결과 핵심 요약</div>
                    <div class="result-hero-subtitle">
                        모든 자산·지출·여유자금은 현재가치 기준입니다. 핵심 판단 기준은 파산확률, 월 안전 여유자금, 은퇴시점 하위 10% 자산입니다.
                    </div>
                </div>
                <div class="{badge_class}">{_escape(status_text)}</div>
            </div>
            <div class="result-hero-subtitle">
                {status_sentence} 판단 기준: {threshold_text}. DWZ 기준 추가사용 가능액은 월 {_fmt_manwon(safe_extra)}입니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return_assumption_info = res.get("return_assumption_info", {}) or {}
    selected_scenario = return_assumption_info.get("선택", "현재 선택 시나리오")
    selected_allocation = return_assumption_info.get("은퇴 후 자산배분", "현재 선택 배분")
    risk_df_for_decision = build_real_life_risk_table(res)
    half_asset_row = risk_df_for_decision[
        risk_df_for_decision["지표"].astype(str).str.contains("반토막", na=False)
    ]
    half_asset_rate = (
        _pct_text_to_float(half_asset_row.iloc[0]["값"])
        if not half_asset_row.empty
        else np.nan
    )
    decision_grade = _decision_grade(base_ruin, half_asset_rate)
    decision_tone = _decision_tone_from_grade(decision_grade)
    spending_guideline = (
        f"월 {_fmt_manwon(safe_extra)} 이하"
        if safe_extra > 0
        else "추가소비 보류"
    )
    sensitivity_driver = _top_sensitivity_driver(res)
    risk_driver = _primary_risk_driver(res)

    st.markdown(
        f"""
        <div class="decision-panel decision-{decision_tone}">
            <div class="decision-main">
                <div class="decision-label">최종 판단</div>
                <div class="decision-title">{_escape(decision_grade)}</div>
                <div class="decision-text">
                    현재 설정은 {_escape(selected_scenario)} / {_escape(selected_allocation)}입니다.
                    월 추가소비 가이드라인은 <b>{_escape(spending_guideline)}</b>로 보되, 민감도와 현실 리스크를 함께 확인하십시오.
                </div>
            </div>
            <div class="decision-grid">
                <div class="decision-item">
                    <div class="decision-item-label">권장 월 추가소비</div>
                    <div class="decision-item-value">{_escape(spending_guideline)}</div>
                </div>
                <div class="decision-item">
                    <div class="decision-item-label">가장 민감한 변수</div>
                    <div class="decision-item-value small">{_escape(sensitivity_driver)}</div>
                </div>
                <div class="decision-item">
                    <div class="decision-item-label">핵심 체감 리스크</div>
                    <div class="decision-item-value small">{_escape(risk_driver)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _render_kpi_card(
            "파산확률",
            f"{base_ruin:.1f}%",
            f"목표 방어선 {target_ruin:.0f}%",
            _metric_tone_from_pct(base_ruin),
        )
    with c2:
        _render_kpi_card(
            "월 안전 여유자금",
            _fmt_manwon(safe_extra),
            "DWZ 방어선 기준 역산",
            "accent" if safe_extra > 0 else "neutral",
        )
    with c3:
        _render_kpi_card(
            f"{tgt_retire}세 중앙값",
            _fmt_eok(median_retire_asset),
            f"하위 10% {_fmt_eok(p10_retire_asset)}",
            "accent",
        )
    with c4:
        _render_kpi_card(
            f"{years[-1]}세 중앙값",
            _fmt_eok(median_final_asset),
            f"하위 10% {_fmt_eok(p10_final_asset)}",
            "neutral",
        )

    st.caption(
        f"참고 여유자금: 상하위 30% 제외 평균 기준 월 {_fmt_manwon(trimmed_avg_extra)}. "
        f"이 값은 극단적으로 나쁜 경로와 좋은 경로를 제거한 보조 판단값입니다."
    )


# -----------------------------------------------------------
# 근거·가정 표시
# -----------------------------------------------------------
def render_data_assumption_section():
    with st.expander("📌 업로드 자료 기반 수익률·변동성 산출값", expanded=False):
        df = pd.DataFrame(DATA_ANALYSIS_SUMMARY)
        st.dataframe(
            df,
            width="stretch",
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
            "국내퀀트 7월말-11월말 단기채 구간은 별도 국내 단기채 월별 자료가 없어 0%로 두었습니다. "
            "V62-8 기본 엔진은 계좌별 원자료를 직접 합성하지 않고 후보1 수익률 가정의 검토 근거로만 사용합니다."
        )


# -----------------------------------------------------------
# 자산 궤적
# -----------------------------------------------------------
def render_main_asset_path_section(years, sim_assets_pv, tgt_retire, res_lump_df):
    _render_section_header(
        f"현재가치 자산 궤적 · {tgt_retire}세 은퇴 기준",
        "중앙값은 일반 경로, 하위 10%는 불리한 장기 경로입니다. 주택구입 같은 큰 목돈 지출은 세로선으로 표시됩니다.",
    )

    median_pv = np.median(sim_assets_pv, axis=0) / 100000000
    top_10_pv = np.percentile(sim_assets_pv, 90, axis=0) / 100000000
    bottom_10_pv = np.percentile(sim_assets_pv, 10, axis=0) / 100000000

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years + years[::-1],
            y=np.concatenate([top_10_pv, bottom_10_pv[::-1]]),
            fill="toself",
            fillcolor="rgba(37, 99, 235, 0.13)",
            line=dict(color="rgba(255,255,255,0)"),
            name="10-90% 범위",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=median_pv,
            line=dict(color="#1d4ed8", width=3.5),
            name="중앙값",
            hovertemplate="%{y:.2f}억 원<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=bottom_10_pv,
            line=dict(color="#dc2626", width=2.4, dash="dot"),
            name="하위 10%",
            hovertemplate="%{y:.2f}억 원<extra></extra>",
        )
    )

    fig.add_hline(y=0, line_dash="solid", line_color="#334155", line_width=1)

    if tgt_retire in years:
        fig.add_vline(
            x=tgt_retire,
            line_dash="dash",
            line_color="#475569",
            annotation_text="은퇴",
        )

    for _, row in res_lump_df.iterrows():
        if row["금액(만원)"] >= 10000 and row["나이"] in years:
            fig.add_vline(
                x=row["나이"],
                line_dash="dot",
                line_color="#d97706",
                annotation_text=row["내용"],
            )

    fig.update_layout(
        xaxis_title="나이",
        yaxis_title="현재가치 자산 (억 원)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    _styled_plotly_layout(fig, height=520)

    with st.container(border=True):
        st.plotly_chart(fig, width="stretch")
        st.caption("그래프의 모든 금액은 현시점 구매력 기준입니다.")


# -----------------------------------------------------------
# 진단 섹션
# -----------------------------------------------------------
def render_failure_diagnostics_section(res):
    with st.expander("🔍 결과 원인 분해 패널", expanded=True):
        diag = build_failure_diagnostics(res, res["retire_age"])
        st.caption(
            "파산 경로와 생존 경로를 분리해 은퇴시점 자산, 은퇴 직후 수익률, 인플레이션 쇼크, "
            "국내퀀트 페널티, 은퇴 전 순인출을 비교합니다. 결과값 자체를 바꾸지 않는 후처리 진단입니다."
        )
        st.dataframe(diag["diagnostic_df"], width="stretch", hide_index=True)
        st.info(diag["reason_text"])


def render_return_distribution_diagnostics_section(res):
    with st.expander("📐 수익률 분포 검증", expanded=True):
        st.caption(
            f"팻테일 난수의 양쪽 꼬리를 점검합니다. 보정 범위는 "
            f"연 하방 {MIN_TOTAL_ANNUAL_RETURN * 100:.0f}% / 상방 +{MAX_TOTAL_ANNUAL_RETURN * 100:.0f}%입니다. "
            "하방·상방 보정률이 높으면 수익률 가정이나 변동성 가정을 재검토해야 합니다."
        )
        return_diag_df = build_return_distribution_diagnostics(res)
        st.dataframe(return_diag_df, width="stretch", hide_index=True)
        st.info(
            "보정 전 최저·최고는 팻테일 난수가 만든 원래 값입니다. "
            "보정 후 분위수는 실제 자산 계산에 적용된 수익률 기준입니다."
        )


# -----------------------------------------------------------
# 현실 리스크
# -----------------------------------------------------------
def render_real_life_risk_section(res):
    risk_df = build_real_life_risk_table(res)

    _render_section_header(
        "현실 리스크 3대 지표",
        "파산확률만으로 보이지 않는 체감 리스크입니다. 은퇴 후 낙폭, 은퇴 직후 10년 시퀀스, 반토막 경험률을 분리해 봅니다.",
    )

    cols = st.columns(3)
    for col, (_, row) in zip(cols, risk_df.iterrows()):
        with col:
            value_text = str(row["값"])
            tone = "success" if _risk_card_color(value_text) == "normal" else "warning"
            if _risk_card_color(value_text) == "inverse":
                tone = "danger"
            _render_kpi_card(
                row["지표"],
                row["값"],
                f"{row['기준']} · {row['해석']}",
                tone,
            )


# -----------------------------------------------------------
# 시나리오·민감도·스트레스
# -----------------------------------------------------------
def render_scenario_comparison_section(res):
    scenario_df = res.get("scenario_comparison_df")
    if scenario_df is None or scenario_df.empty:
        return

    with st.expander("📊 수익률 시나리오별 결과 비교", expanded=True):
        st.caption(
            "긍정적·보통·보수 수익률 시나리오를 같은 입력값 기준으로 비교합니다. "
            "현재 선택된 시나리오에는 * 표시가 붙습니다."
        )

        display_df = _add_scenario_stability_columns(scenario_df)

        display_cols = st.columns(3)
        best_ruin_row = display_df.loc[display_df["파산확률"].idxmin()]
        best_extra_row = display_df.loc[display_df["안전 여유자금(만원/월)"].idxmax()]
        conservative_candidates = display_df[
            display_df["수익률 시나리오"].astype(str).str.contains("보수", na=False)
        ]
        conservative_row = (
            conservative_candidates.iloc[0]
            if not conservative_candidates.empty
            else display_df.iloc[-1]
        )

        with display_cols[0]:
            _render_kpi_card(
                "최저 파산확률 시나리오",
                f"{best_ruin_row['파산확률']:.1f}%",
                str(best_ruin_row["수익률 시나리오"]).replace(" *", ""),
                _metric_tone_from_pct(float(best_ruin_row["파산확률"])),
            )
        with display_cols[1]:
            _render_kpi_card(
                "최대 안전 여유자금",
                _fmt_manwon(best_extra_row["안전 여유자금(만원/월)"]),
                str(best_extra_row["수익률 시나리오"]).replace(" *", ""),
                "accent",
            )
        with display_cols[2]:
            _render_kpi_card(
                "보수 시나리오 파산확률",
                f"{conservative_row['파산확률']:.1f}%",
                str(conservative_row["수익률 시나리오"]).replace(" *", ""),
                _metric_tone_from_pct(float(conservative_row["파산확률"])),
            )

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "안정성 점수": st.column_config.NumberColumn(format="%.1f"),
                "추천순위": st.column_config.NumberColumn(format="%d"),
                "은퇴 전 수익률": st.column_config.NumberColumn(format="%.2f%%"),
                "은퇴 후 수익률": st.column_config.NumberColumn(format="%.2f%%"),
                "은퇴 전 변동성": st.column_config.NumberColumn(format="%.2f%%"),
                "은퇴 후 변동성": st.column_config.NumberColumn(format="%.2f%%"),
                "파산확률": st.column_config.NumberColumn(format="%.1f%%"),
                "은퇴시점 중앙값(억)": st.column_config.NumberColumn(format="%.2f"),
                "은퇴시점 하위10%(억)": st.column_config.NumberColumn(format="%.2f"),
                "최종 중앙값(억)": st.column_config.NumberColumn(format="%.2f"),
                "은퇴 후 반토막 경험률": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
        st.caption(
            "안정성 점수는 파산확률, 은퇴 후 반토막 경험률, 은퇴시점 하위 10% 자산, 최종 중앙값을 후처리로 조합한 표시용 점수입니다. "
            "시뮬레이션 계산값 자체는 변경하지 않습니다."
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
            width="stretch",
            hide_index=True,
            column_config={
                "파산확률": st.column_config.NumberColumn(format="%.1f%%"),
                "기준 대비 변화(%p)": st.column_config.NumberColumn(format="%.1f"),
            },
        )

        sorted_df = sensitivity_df.sort_values(by="기준 대비 변화(%p)", key=abs, ascending=True)
        bar_colors = ["#dc2626" if v > 0 else "#2563eb" for v in sorted_df["기준 대비 변화(%p)"]]
        fig = go.Figure(
            go.Bar(
                x=sorted_df["기준 대비 변화(%p)"],
                y=sorted_df["민감도 항목"],
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:+.1f}%p" for v in sorted_df["기준 대비 변화(%p)"]],
                textposition="auto",
            )
        )
        fig.add_vline(x=0, line_width=1, line_color="#334155")
        fig.update_layout(
            title="기준 대비 파산확률 변화",
            xaxis_title="파산확률 변화(%p)",
        )
        _styled_plotly_layout(fig, height=380, title="기준 대비 파산확률 변화")
        st.plotly_chart(fig, width="stretch")


def render_stress_budget_section(stress_df, target_ruin):
    with st.expander("💸 월 추가 사용액별 파산확률", expanded=False):
        colors = [
            "#16a34a" if val <= STANDARD_TARGET_RUIN_PROB
            else "#d97706" if val <= DWZ_TARGET_RUIN_PROB
            else "#dc2626" if val >= WARNING_RUIN_PROB
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
            title="추가 사용액별 파산확률",
            yaxis_title="파산확률 (%)",
        )
        fig_stress.add_hline(
            y=STANDARD_TARGET_RUIN_PROB,
            line_dash="dot",
            line_color="#16a34a",
            annotation_text=f"안전 {STANDARD_TARGET_RUIN_PROB:.0f}%",
        )
        fig_stress.add_hline(
            y=target_ruin,
            line_dash="dot",
            line_color="#d97706",
            annotation_text=f"DWZ {target_ruin:.0f}%",
        )
        fig_stress.add_hline(
            y=WARNING_RUIN_PROB,
            line_dash="dot",
            line_color="#dc2626",
            annotation_text=f"위험 {WARNING_RUIN_PROB:.0f}%",
        )
        _styled_plotly_layout(fig_stress, height=330, title="추가 사용액별 파산확률")

        st.plotly_chart(fig_stress, width="stretch")
        st.caption("추가 사용 가능액은 DWZ 방어선 기준으로 역산합니다. 모든 금액은 현재가치 기준입니다.")


# -----------------------------------------------------------
# 자동 적용 모델
# -----------------------------------------------------------
def render_applied_model_section(res):
    defense_rate = res["defense_rate"]
    return_assumption_info = res.get("return_assumption_info", {}) or {}

    if return_assumption_info:
        assumption_setting = (
            f"{return_assumption_info.get('모델', '-')} / {return_assumption_info.get('선택', '-')} / "
            f"{return_assumption_info.get('은퇴 후 자산배분', '-')} / "
            f"은퇴전 {float(return_assumption_info.get('은퇴 전 기대수익률', 0.0)):.2f}%·{float(return_assumption_info.get('은퇴 전 변동성', 0.0)):.2f}% / "
            f"은퇴후 {float(return_assumption_info.get('은퇴 후 기대수익률', 0.0)):.2f}%·{float(return_assumption_info.get('은퇴 후 변동성', 0.0)):.2f}%"
        )
        assumption_meaning = return_assumption_info.get(
            "설명",
            "현재 선택된 수익률·변동성 입력값입니다.",
        )
    else:
        assumption_setting = "후보1 알파 감소 모델"
        assumption_meaning = "긍정·보통·보수 수익률 시나리오와 은퇴 후 주식 현금 자산배분 기준 변동성을 사용합니다."

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
                "모델": "선택 수익률 가정",
                "현재 설정": assumption_setting,
                "의미": assumption_meaning,
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
                "모델": "연간수익률 보정 범위",
                "현재 설정": f"하방 {MIN_TOTAL_ANNUAL_RETURN * 100:.0f}% / 상방 +{MAX_TOTAL_ANNUAL_RETURN * 100:.0f}%",
                "의미": "팻테일 난수가 만드는 비현실적 초극단 손실과 초극단 상승을 양쪽에서 보정합니다.",
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
                "현재 설정": f"후보1 국내퀀트 {QUANT_STRATEGY_MONTHS_PER_YEAR}개월 운용분만 반영",
                "의미": f"은퇴 전은 총자산의 주식전략 전체, 은퇴 후는 선택한 주식비중만 규모 페널티 대상으로 보고 구간별 차감률의 {QUANT_SIZE_PENALTY_ANNUAL_RATIO*100:.1f}%만 적용합니다.",
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
        st.dataframe(model_df, width="stretch", hide_index=True)


# -----------------------------------------------------------
# 고급 분석
# -----------------------------------------------------------
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

    with st.expander("📊 고급 분석: 대표 경로 3종 비교", expanded=True):
        st.caption("상위 10%, 중앙값, 하위 10%에 가까운 실제 경로를 골라 연도별 수익률과 자산 흐름을 비교합니다.")

        c_m1, c_m2, c_m3 = st.columns(3)
        cols = [c_m1, c_m2, c_m3]

        comp_data = {"나이": years}
        target_age_idx = _safe_age_index(years, tgt_retire)

        for i, (label, data) in enumerate(paths.items()):
            ret_array = data["ret"]
            pv_array = data["pv"]

            cagr = (np.prod(1 + ret_array) ** (1 / len(years)) - 1) * 100
            tgt_pv_eok = pv_array[target_age_idx] / 100000000

            with cols[i]:
                tone = "success" if label == "상위 10%" else "accent" if label == "중앙값" else "warning"
                _render_kpi_card(
                    label,
                    f"{tgt_retire}세 {tgt_pv_eok:.1f}억",
                    f"전체기간 CAGR {cagr:.2f}%",
                    tone,
                )

            comp_data[f"[{label}] 수익률(%)"] = np.round(ret_array * 100, 2)
            comp_data[f"[{label}] 자산(억)"] = np.round(pv_array / 100000000, 2)

        comp_df = pd.DataFrame(comp_data).set_index("나이")

        c_chart1, c_chart2 = st.columns(2)
        color_map = {"상위 10%": "#16a34a", "중앙값": "#2563eb", "하위 10%": "#dc2626"}

        with c_chart1:
            st.markdown("###### 연도별 적용 수익률")
            fig_ret = go.Figure()
            for label in paths.keys():
                col_name = f"[{label}] 수익률(%)"
                fig_ret.add_trace(
                    go.Scatter(
                        x=comp_df.index,
                        y=comp_df[col_name],
                        mode="lines",
                        name=label,
                        line=dict(color=color_map[label], width=2.4),
                        hovertemplate="%{y:.2f}%<extra></extra>",
                    )
                )
            fig_ret.add_hline(y=0, line_dash="dot", line_color="#64748b", line_width=1)
            fig_ret.update_layout(yaxis_title="수익률 (%)", hovermode="x unified")
            _styled_plotly_layout(fig_ret, height=320)
            st.plotly_chart(fig_ret, width="stretch")

        with c_chart2:
            st.markdown("###### 연도별 현재가치 자산")
            fig_asset = go.Figure()
            for label in paths.keys():
                col_name = f"[{label}] 자산(억)"
                fig_asset.add_trace(
                    go.Scatter(
                        x=comp_df.index,
                        y=comp_df[col_name],
                        mode="lines",
                        name=label,
                        line=dict(color=color_map[label], width=2.4),
                        hovertemplate="%{y:.2f}억 원<extra></extra>",
                    )
                )
            fig_asset.add_hline(y=0, line_dash="solid", line_color="#64748b", line_width=1)
            fig_asset.update_layout(yaxis_title="현재가치 자산 (억 원)", hovermode="x unified")
            _styled_plotly_layout(fig_asset, height=320)
            st.plotly_chart(fig_asset, width="stretch")


# -----------------------------------------------------------
# 결과 페이지 조립
# -----------------------------------------------------------
def render_results_page(res):
    years = res["years"]
    sim_assets_pv = res["pv"]
    sim_returns = res["returns"]
    stress_df = res["stress_df"]
    target_ruin = res["t_ruin"]
    res_lump_df = res["lump_df"]
    tgt_retire = res["retire_age"]

    render_top_summary_section(res)

    summary_tab, risk_tab, scenario_tab, model_tab, advanced_tab = st.tabs(
        ["핵심 요약", "리스크 진단", "시나리오·민감도", "가정·모델", "고급 분석"]
    )

    with summary_tab:
        render_main_asset_path_section(years, sim_assets_pv, tgt_retire, res_lump_df)
        render_real_life_risk_section(res)
        render_stress_budget_section(stress_df, target_ruin)

    with risk_tab:
        render_failure_diagnostics_section(res)
        render_return_distribution_diagnostics_section(res)

    with scenario_tab:
        render_scenario_comparison_section(res)
        render_sensitivity_section(res)

    with model_tab:
        render_data_assumption_section()
        render_applied_model_section(res)

    with advanced_tab:
        render_representative_paths_section(years, sim_assets_pv, sim_returns, tgt_retire)

