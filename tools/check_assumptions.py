import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (  # noqa: E402
    DEFAULT_SCENARIO_INDEX,
    DWZ_TARGET_RUIN_PROB,
    SCENARIO_OPTIONS,
    STANDARD_TARGET_RUIN_PROB,
    WARNING_RUIN_PROB,
)
from simulator import FinancialSimulator  # noqa: E402


def assert_equal(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name} mismatch: {actual} != {expected}")


def assert_close_tuple(name, actual, expected):
    if len(actual) != len(expected):
        raise AssertionError(f"{name} length mismatch: {len(actual)} != {len(expected)}")
    for idx, (a, e) in enumerate(zip(actual, expected)):
        if abs(float(a) - float(e)) > 1e-9:
            raise AssertionError(f"{name}[{idx}] mismatch: {a} != {e}")


def build_params(dwz_mode=False):
    scenario_values = list(SCENARIO_OPTIONS.values())[DEFAULT_SCENARIO_INDEX]
    expected_return_pre, vol_pre, expected_return_post, vol_post = scenario_values

    return {
        "current_age": 40,
        "death_age": 90,
        "current_asset": 126000,
        "monthly_income": 800,
        "apply_income_inflation": False,
        "monthly_expense": 700,
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
        "use_glide_path": True,
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


def main():
    check_config_assumptions()
    check_target_ruin_probability()
    print("OK: portfolio assumptions checks passed.")


if __name__ == "__main__":
    main()
