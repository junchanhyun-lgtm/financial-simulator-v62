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


def build_real_life_risk_table(res):
    """
    현실 리스크 지표는 세 가지로 제한합니다.
    모든 지표는 현재가치 기준 자산경로에서 파생 계산합니다.
    """
    years = np.asarray(res["years"])
    pv = np.asarray(res["pv"], dtype=float)

    retire_age = res.get("retire_age", years[0])
    retire_idx = _first_index_at_or_after(years, retire_age)

    post_pv = pv[:, retire_idx:]
    retire_assets = pv[:, retire_idx]

    # 1. 은퇴 후 최대 실질자산 낙폭: 나쁜 10% 경로 기준
    post_peak = np.maximum.accumulate(post_pv, axis=1)
    post_drawdown = np.where(post_peak > 0, (post_peak - post_pv) / post_peak, 0.0)
    max_post_drawdown = np.max(post_drawdown, axis=1)
    p90_max_drawdown = np.percentile(max_post_drawdown, 90) * 100

    # 2. 은퇴 직후 10년 시퀀스 리스크: 10년 안에 은퇴시점 자산 대비 30% 이상 훼손
    ten_year_window_len = min(11, post_pv.shape[1])
    post_10y_min_assets = np.min(post_pv[:, :ten_year_window_len], axis=1)
    sequence_risk_prob = np.mean(post_10y_min_assets <= retire_assets * 0.70) * 100

    # 3. 은퇴 후 자산 반토막 경험률
    post_min_assets = np.min(post_pv, axis=1)
    asset_halving_prob = np.mean(post_min_assets <= retire_assets * 0.50) * 100

    rows = [
        {
            "지표": "은퇴 후 최대 실질자산 낙폭",
            "값": _fmt_pct(p90_max_drawdown),
            "기준": "나쁜 10% 경로",
            "해석": "은퇴 후 고점 대비 자산이 얼마나 크게 훼손될 수 있는지 봅니다.",
        },
        {
            "지표": "은퇴 직후 10년 시퀀스 리스크",
            "값": _fmt_pct(sequence_risk_prob),
            "기준": "10년 내 30% 이상 훼손",
            "해석": "은퇴 초반에 자산이 크게 줄어 이후 인출 여력이 약해지는 경로 비율입니다.",
        },
        {
            "지표": "은퇴 후 자산 반토막 경험률",
            "값": _fmt_pct(asset_halving_prob),
            "기준": "은퇴시점 자산 대비 50% 이하",
            "해석": "파산하지 않아도 전략 유지가 심리적으로 어려워질 수 있는 경로 비율입니다.",
        },
    ]

    return pd.DataFrame(rows)
