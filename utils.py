import numpy as np


def format_won(value_in_manwon):
    val = int(value_in_manwon)

    if val >= 10000:
        eok = val // 10000
        man = val % 10000

        if man > 0:
            return f"{eok}억 {man}만 원"
        return f"{eok}억 원"

    return f"{val}만 원"


def calc_rolling_stats(returns_matrix, window_years):
    n_sims, n_cols = returns_matrix.shape

    if window_years > n_cols:
        return 0.0, 0.0

    cum_rets = []

    for start in range(n_cols - window_years + 1):
        window_slice = returns_matrix[:, start:start + window_years]
        geom_ret = np.prod(1 + window_slice, axis=1) - 1
        cum_rets.append(geom_ret)

    cum_rets = np.array(cum_rets).flatten()

    win_rate = (np.sum(cum_rets > 0) / len(cum_rets)) * 100
    median_cagr = (np.median(cum_rets + 1) ** (1 / window_years) - 1) * 100

    return win_rate, median_cagr