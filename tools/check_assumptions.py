import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (  # noqa: E402
    ANNUAL_TRANSFER_TO_DUAL_MANWON,
    DEFAULT_SCENARIO_INDEX,
    DEFAULT_SPENDING_PROFILE_INDEX,
    DWZ_TARGET_RUIN_PROB,
    INITIAL_DUAL_MOMENTUM_ASSET_MANWON,
    INITIAL_QUANT_ASSET_MANWON,
    INITIAL_VOO_ASSET_MANWON,
    QUANT_SIZE_PENALTY_TIERS,
    SCENARIO_OPTIONS,
    SPENDING_PROFILE_OPTIONS,
    STANDARD_TARGET_RUIN_PROB,
    WARNING_RUIN_PROB,
)
from simulator import FinancialSimulator  # noqa: E402


def assert_equal(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name} mismatch: {actual} != {expected}")


def assert_close(name, actual, expected, tol=1e-9):
    if abs(float(actual) - float(expected)) > tol:
        raise AssertionError(f"{name} mismatch: {actual} != {expected}")


def assert_close_tuple(name, actual, expected):
    if len(actual) != len(expected):
        raise AssertionError(f"{name} length mismatch: {len(actual)} != {len(expected)}")
    for idx, (a, e) in enumerate(zip(actual, expected)):
        assert_close(f"{name}[{idx}]", a, e)


def build_params(dwz_mode=False, use_portfolio_transition=True):
    scenario_values = list(SCENARIO_OPTIONS.values())[DEFAULT_SCENARIO_INDEX]
    expected_return_pre, vol_pre, expected_return_post, vol_post = scenario_values
    essential_spending_ratio = list(SPENDING_PROFILE_OPTIONS.values())[DEFAULT_SPENDING_PROFILE_INDEX]

    return {
        "current_age": 40,
        "death_age": 90,
        "current_asset": 126000,
        "monthly_income": 800,
        "apply_income_inflation": False,
        "monthly_expense": 700,
        "essential_spending_ratio": essential_spending_ratio,
        "expected_return_pre": expected_return_pre,
        "vol_pre": vol_pre,
        "expected_return_post": expected_return_post,
        "vol_post": vol_post,
        "inflation": 2.5,
        "tax_fee_rate": 0.5,
        "retire_age": 60,
        "lump_events": pd.DataFrame(),
        "recurring_events": pd.DataFrame(),
        "use_fat_tail": True,
        "use_inflation_shock": True,
        "use_flex_spending": True,
        "dwz_mode": dwz_mode,
        "use_portfolio_transition": use_portfolio_transition,
    }


def check_config_assumptions():
    assert_equal("STANDARD_TARGET_RUIN_PROB", STANDARD_TARGET_RUIN_PROB, 10.0)
    assert_equal("DWZ_TARGET_RUIN_PROB", DWZ_TARGET_RUIN_PROB, 15.0)
    assert_equal("WARNING_RUIN_PROB", WARNING_RUIN_PROB, 20.0)
    assert_equal("DEFAULT_SCENARIO_INDEX", DEFAULT_SCENARIO_INDEX, 1)
    assert_equal("SCENARIO_OPTIONS length", len(SCENARIO_OPTIONS), 3)

    values = list(SCENARIO_OPTIONS.values())
    assert_close_tuple("conservative scenario", values[0], (15.0, 26.0, 10.5, 17.0))
    assert_close_tuple("base scenario", values[1], (18.0, 25.0, 12.0, 16.0))
    assert_close_tuple("aggressive scenario", values[2], (20.0, 25.0, 13.5, 17.0))

    assert_equal("DEFAULT_SPENDING_PROFILE_INDEX", DEFAULT_SPENDING_PROFILE_INDEX, 1)
    assert_equal("SPENDING_PROFILE_OPTIONS length", len(SPENDING_PROFILE_OPTIONS), 3)
    spending_values = list(SPENDING_PROFILE_OPTIONS.values())
    assert_close("conservative essential ratio", spending_values[0], 0.80)
    assert_close("base essential ratio", spending_values[1], 0.70)
    assert_close("flexible essential ratio", spending_values[2], 0.60)

    assert_equal("INITIAL_QUANT_ASSET_MANWON", INITIAL_QUANT_ASSET_MANWON, 107000)
    assert_equal("INITIAL_DUAL_MOMENTUM_ASSET_MANWON", INITIAL_DUAL_MOMENTUM_ASSET_MANWON, 12000)
    assert_equal("INITIAL_VOO_ASSET_MANWON", INITIAL_VOO_ASSET_MANWON, 7000)
    assert_equal("ANNUAL_TRANSFER_TO_DUAL_MANWON", ANNUAL_TRANSFER_TO_DUAL_MANWON, 3800)
    assert_equal("QUANT_SIZE_PENALTY_TIERS length", len(QUANT_SIZE_PENALTY_TIERS), 5)


def check_target_ruin_probability():
    normal_result = FinancialSimulator(build_params(dwz_mode=False)).run_hybrid_analysis(
        main_sims=20,
        search_sims=5,
    )
    dwz_result = FinancialSimulator(build_params(dwz_mode=True)).run_hybrid_analysis(
        main_sims=20,
        search_sims=5,
    )

    assert_equal("normal target_ruin_prob", normal_result[-1], STANDARD_TARGET_RUIN_PROB)
    assert_equal("dwz target_ruin_prob", dwz_result[-1], DWZ_TARGET_RUIN_PROB)


def check_portfolio_transition_and_penalty_helpers():
    sim = FinancialSimulator(build_params(use_portfolio_transition=True))

    ratio_40, quant_share_40 = sim._portfolio_transition_ratio_and_quant_share(
        current_asset_manwon=126000,
        current_age=40,
        retire_age=60,
        age=40,
        use_portfolio_transition=True,
    )
    ratio_60, quant_share_60 = sim._portfolio_transition_ratio_and_quant_share(
        current_asset_manwon=126000,
        current_age=40,
        retire_age=60,
        age=60,
        use_portfolio_transition=True,
    )

    assert_close("transition ratio at current age", ratio_40, 0.0)
    assert_close("transition ratio at retirement", ratio_60, 1.0)
    if quant_share_60 >= quant_share_40:
        raise AssertionError("quant share should decline under portfolio transition")

    penalty = sim._quant_size_penalty(
        pd.Series([100000, 200000, 300000, 500000, 800000], dtype=float).to_numpy()
    )
    expected = [0.000, 0.003, 0.007, 0.012, 0.018]
    for idx, (actual, exp) in enumerate(zip(penalty, expected)):
        assert_close(f"quant size penalty[{idx}]", actual, exp)


def check_monte_carlo_shapes():
    years, pv, nom, returns = FinancialSimulator(build_params(dwz_mode=True)).run_monte_carlo(
        n_simulations=30,
        override_extra_margin=100,
    )
    expected_shape = (30, len(years))
    assert_equal("pv shape", pv.shape, expected_shape)
    assert_equal("nom shape", nom.shape, expected_shape)
    assert_equal("returns shape", returns.shape, expected_shape)


def main():
    check_config_assumptions()
    check_target_ruin_probability()
    check_portfolio_transition_and_penalty_helpers()
    check_monte_carlo_shapes()
    print("OK: portfolio transition and spending assumptions checks passed.")


if __name__ == "__main__":
    main()
