import numpy as np
import pandas as pd


def _first_index_at_or_after(years, target_age):
    years_arr = np.asarray(years)
    matches = np.where(years_arr >= target_age)[0]
    if len(matches) == 0:
        return len(years_arr) - 1
    return int(matches[0])


def _fmt_pct(value):
    return f"{value:.1f}%"


def _fmt_eok(value_won):
    return f"{value_won / 100_000_000:.2f}억 원"


def build_real_life_risk_table(res):
    """
    기존 시뮬레이션 결과(res)에서 현실 리스크 지표만 파생 계산합니다.
    FinancialSimulator의 수익률/자산 계산 로직은 변경하지 않습니다.
    """
    years = np.asarray(res["years"])
    pv = np.asarray(res["pv"], dtype=float)
    returns = np.asarray(res["returns"], dtype=float)

    retire_age = res.get("retire_age", years[0])
    retire_idx = _first_index_at_or_after(years, retire_age)

    post_pv = pv[:, retire_idx:]
    post_returns = returns[:, retire_idx:]

    retire_assets = pv[:, retire_idx]
    final_assets = pv[:, -1]

    # 은퇴 후 최대 실질자산 낙폭
    post_peak = np.maximum.accumulate(post_pv, axis=1)
    post_drawdown = np.where(post_peak > 0, (post_peak - post_pv) / post_peak, 0.0)
    max_post_drawdown = np.max(post_drawdown, axis=1)

    median_max_dd = np.median(max_post_drawdown) * 100
    p90_max_dd = np.percentile(max_post_drawdown, 90) * 100

    # 은퇴 직후 5년 / 10년 수익률 순서 리스크
    first_5y_len = min(5, post_returns.shape[1])
    first_10y_len = min(10, post_returns.shape[1])

    first_5y_cum = np.prod(1 + post_returns[:, :first_5y_len], axis=1) - 1
    first_10y_cum = np.prod(1 + post_returns[:, :first_10y_len], axis=1) - 1

    bad_first_5y_prob = np.mean(first_5y_cum <= -0.20) * 100
    bad_first_10y_prob = np.mean(first_10y_cum <= -0.30) * 100

    p10_first_5y = np.percentile(first_5y_cum, 10) * 100
    p10_first_10y = np.percentile(first_10y_cum, 10) * 100

    # 은퇴 후 자산 훼손 리스크
    post_min_assets = np.min(post_pv, axis=1)
    asset_halving_prob = np.mean(post_min_assets <= retire_assets * 0.5) * 100
    asset_30pct_damage_prob = np.mean(post_min_assets <= retire_assets * 0.7) * 100

    # 하위 10% 경로의 최소 은퇴 후 자산
    p10_min_post_asset = np.percentile(post_min_assets, 10)

    # 최종 자산 기준 하위 10% 경로
    bottom_10_cutoff = np.percentile(final_assets, 10)
    bottom_10_mask = final_assets <= bottom_10_cutoff
    bottom_10_min_asset = np.min(post_min_assets[bottom_10_mask]) if np.any(bottom_10_mask) else np.nan

    # 멘탈 방어 실패 가능성: 큰 낙폭 또는 은퇴초기 악순환
    mental_stress_prob = np.mean(
        (max_post_drawdown >= 0.30) |
        (first_5y_cum <= -0.20) |
        (post_min_assets <= retire_assets * 0.7)
    ) * 100

    rows = [
        {
            "지표": "은퇴 후 최대 실질자산 낙폭 중앙값",
            "값": _fmt_pct(median_max_dd),
            "해석": "일반적인 경로에서 은퇴 후 겪는 최대 체감 손실폭입니다.",
        },
        {
            "지표": "은퇴 후 최대 실질자산 낙폭 상위 10%",
            "값": _fmt_pct(p90_max_dd),
            "해석": "심리적으로 버티기 어려운 나쁜 경로의 자산 훼손 강도입니다.",
        },
        {
            "지표": "은퇴 직후 5년 누적수익률 하위 10%",
            "값": _fmt_pct(p10_first_5y),
            "해석": "은퇴 초기에 나쁜 순서의 수익률을 만났을 때의 충격입니다.",
        },
        {
            "지표": "은퇴 직후 10년 누적수익률 하위 10%",
            "값": _fmt_pct(p10_first_10y),
            "해석": "은퇴 초반 장기 침체를 만났을 때의 시퀀스 리스크입니다.",
        },
        {
            "지표": "은퇴 직후 5년 -20% 이하 경로",
            "값": _fmt_pct(bad_first_5y_prob),
            "해석": "은퇴 직후 소비 삭감이나 전략 이탈 유혹이 커지는 경로 비율입니다.",
        },
        {
            "지표": "은퇴 직후 10년 -30% 이하 경로",
            "값": _fmt_pct(bad_first_10y_prob),
            "해석": "은퇴 초반 장기 약세장에 노출되는 경로 비율입니다.",
        },
        {
            "지표": "은퇴 후 자산 30% 이상 훼손 경로",
            "값": _fmt_pct(asset_30pct_damage_prob),
            "해석": "파산하지 않아도 소비 위축이 발생할 가능성이 큰 경로입니다.",
        },
        {
            "지표": "은퇴 후 자산 반토막 경험 경로",
            "값": _fmt_pct(asset_halving_prob),
            "해석": "전략 유지가 심리적으로 어려워질 수 있는 극단 경로입니다.",
        },
        {
            "지표": "하위 10% 경로의 은퇴 후 최소자산",
            "값": _fmt_eok(p10_min_post_asset),
            "해석": "나쁜 경로에서도 생활방어선이 어느 정도 남는지 확인합니다.",
        },
        {
            "지표": "최종 하위 10% 경로 중 최저자산",
            "값": _fmt_eok(bottom_10_min_asset),
            "해석": "가장 불리한 장기 경로의 체감 바닥권입니다.",
        },
        {
            "지표": "멘탈 방어 실패 가능성",
            "값": _fmt_pct(mental_stress_prob),
            "해석": "큰 낙폭, 은퇴초기 손실, 자산 훼손 중 하나라도 겪는 경로 비율입니다.",
        },
    ]

    return pd.DataFrame(rows)