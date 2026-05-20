import numpy as np
import pandas as pd


def _safe_age_index(years, age):
    if age in years:
        return years.index(age)
    years_arr = np.asarray(years)
    return int(np.argmin(np.abs(years_arr - age)))


def _safe_divide(numerator, denominator, default=0.0):
    numerator = np.asarray(numerator, dtype=float)
    denominator = np.asarray(denominator, dtype=float)
    return np.divide(
        numerator,
        denominator,
        out=np.full(np.broadcast_shapes(numerator.shape, denominator.shape), default, dtype=float),
        where=np.abs(denominator) > 1e-12,
    )


def build_real_life_risk_table(res):
    years = res["years"]
    pv = np.asarray(res["pv"], dtype=float)
    returns = np.asarray(res["returns"], dtype=float)
    retire_age = res["retire_age"]

    retire_idx = _safe_age_index(years, retire_age)
    post_assets = pv[:, retire_idx:]

    high_water = np.maximum.accumulate(np.maximum(post_assets, 1.0), axis=1)
    drawdowns = 1.0 - _safe_divide(post_assets, high_water, default=1.0)
    max_drawdowns = np.max(drawdowns, axis=1) * 100.0

    sequence_end = min(len(years), retire_idx + 10)
    sequence_returns = returns[:, retire_idx:sequence_end]
    if sequence_returns.shape[1] > 0:
        sequence_cum_returns = np.prod(1 + sequence_returns, axis=1) - 1
        sequence_bad_rate = np.mean(sequence_cum_returns < 0) * 100.0
    else:
        sequence_bad_rate = 0.0

    retire_assets = np.maximum(pv[:, retire_idx], 1.0)
    half_asset_rate = np.mean(np.min(post_assets, axis=1) <= retire_assets * 0.5) * 100.0

    return pd.DataFrame([
        {
            "지표": "은퇴 후 최대 실질자산 낙폭",
            "값": f"{np.median(max_drawdowns):.1f}%",
            "기준": "중앙값",
            "해석": "은퇴 후 자산이 고점 대비 얼마나 흔들리는지 보는 체감 낙폭 지표입니다.",
        },
        {
            "지표": "은퇴 직후 10년 시퀀스 리스크",
            "값": f"{sequence_bad_rate:.1f}%",
            "기준": "10년 누적수익률 < 0",
            "해석": "은퇴 직후 10년 누적수익률이 음수인 경로 비율입니다.",
        },
        {
            "지표": "은퇴 후 자산 반토막 경험률",
            "값": f"{half_asset_rate:.1f}%",
            "기준": "은퇴시점 대비 50% 이하",
            "해석": "파산하지 않아도 체감상 크게 불안한 경로가 얼마나 있는지 보여줍니다.",
        },
    ])
