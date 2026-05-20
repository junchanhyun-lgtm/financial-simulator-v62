import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (  # noqa: E402
    ANNUAL_TRANSFER_TO_DUAL_MANWON,
    AUTO_APPLY_DWZ_SPENDING,
    AUTO_APPLY_FAT_TAIL,
    AUTO_APPLY_FLEX_SPENDING,
    AUTO_APPLY_INFLATION_SHOCK,
    AUTO_APPLY_PORTFOLIO_TRANSITION,
    DEFAULT_SCENARIO_INDEX,
    DWZ_TARGET_RUIN_PROB,
    ESSENTIAL_SPENDING_RATIO,
    EXPENSE_INFLATION_LINKED,
    FAT_TAIL_DF,
    INCOME_INFLATION_LINKED,
    INFLATION_SHOCK_ANNUAL_PROBABILITY,
    INFLATION_SHOCK_DURATION_YEARS,
    INFLATION_SHOCK_INFLATION_ADDON,
    INFLATION_SHOCK_RETURN_PENALTY,
    INFLATION_SHOCK_VOL_MULTIPLIER,
    INITIAL_DUAL_MOMENTUM_ASSET_MANWON,
    INITIAL_QUANT_ASSET_MANWON,
    INITIAL_VOO_ASSET_MANWON,
    MEAN_REVERSION_STRENGTH,
    QUANT_SIZE_PENALTY_TIERS,
    SCENARIO_OPTIONS,
    STANDARD_TARGET_RUIN_PROB,
    TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON,
    TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO,
    TRIMMED_AVERAGE_UPPER_EXCLUSION_RATIO,
    WARNING_RUIN_PROB,
)
from risk_metrics import build_real_life_risk_table  # noqa: E402
from data_defaults import get_default_lump_events, get_default_recurring_events  # noqa: E402
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


def build_params(dwz_mode=AUTO_APPLY_DWZ_SPENDING, use_portfolio_transition=True):
    scenario_values = list(SCENARIO_OPTIONS.values())[DEFAULT_SCENARIO_INDEX]
    expected_return_pre, vol_pre, expected_return_post, vol_post = scenario_values

    return {
        "current_age": 40,
        "death_age": 90,
        "current_asset": 126000,
        "monthly_income": 800,
        "apply_income_inflation": INCOME_INFLATION_LINKED,
        "monthly_expense": 700,
        "essential_spending_ratio": ESSENTIAL_SPENDING_RATIO,
        "expected_return_pre": expected_return_pre,
        "vol_pre": vol_pre,
        "expected_return_post": expected_return_post,
        "vol_post": vol_post,
        "inflation": 2.5,
        "tax_fee_rate": 0.5,
        "retire_age": 60,
        "lump_events": pd.DataFrame(),
        "recurring_events": pd.DataFrame(),
        "use_fat_tail": AUTO_APPLY_FAT_TAIL,
        "use_inflation_shock": AUTO_APPLY_INFLATION_SHOCK,
        "use_flex_spending": AUTO_APPLY_FLEX_SPENDING,
        "dwz_mode": dwz_mode,
        "use_portfolio_transition": use_portfolio_transition,
    }


def check_config_assumptions():
    assert_equal("STANDARD_TARGET_RUIN_PROB", STANDARD_TARGET_RUIN_PROB, 10.0)
    assert_equal("DWZ_TARGET_RUIN_PROB", DWZ_TARGET_RUIN_PROB, 15.0)
    assert_equal("WARNING_RUIN_PROB", WARNING_RUIN_PROB, 20.0)
    assert_close("TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO", TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO, 0.30)
    assert_close("TRIMMED_AVERAGE_UPPER_EXCLUSION_RATIO", TRIMMED_AVERAGE_UPPER_EXCLUSION_RATIO, 0.30)
    assert_equal("TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON", TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON, 10000)
    assert_equal("DEFAULT_SCENARIO_INDEX", DEFAULT_SCENARIO_INDEX, 1)
    assert_equal("SCENARIO_OPTIONS length", len(SCENARIO_OPTIONS), 3)

    values = list(SCENARIO_OPTIONS.values())
    assert_close_tuple("conservative scenario", values[0], (15.0, 26.0, 10.5, 17.0))
    assert_close_tuple("base scenario", values[1], (18.0, 25.0, 12.0, 16.0))
    assert_close_tuple("aggressive scenario", values[2], (20.0, 25.0, 13.5, 17.0))

    assert_close("ESSENTIAL_SPENDING_RATIO", ESSENTIAL_SPENDING_RATIO, 0.70)
    assert_equal("INCOME_INFLATION_LINKED", INCOME_INFLATION_LINKED, False)
    assert_equal("EXPENSE_INFLATION_LINKED", EXPENSE_INFLATION_LINKED, True)

    assert_equal("AUTO_APPLY_DWZ_SPENDING", AUTO_APPLY_DWZ_SPENDING, True)
    assert_equal("AUTO_APPLY_FLEX_SPENDING", AUTO_APPLY_FLEX_SPENDING, True)
    assert_equal("AUTO_APPLY_PORTFOLIO_TRANSITION", AUTO_APPLY_PORTFOLIO_TRANSITION, True)
    assert_equal("AUTO_APPLY_FAT_TAIL", AUTO_APPLY_FAT_TAIL, True)
    assert_equal("AUTO_APPLY_INFLATION_SHOCK", AUTO_APPLY_INFLATION_SHOCK, True)

    assert_equal("INITIAL_QUANT_ASSET_MANWON", INITIAL_QUANT_ASSET_MANWON, 107000)
    assert_equal("INITIAL_DUAL_MOMENTUM_ASSET_MANWON", INITIAL_DUAL_MOMENTUM_ASSET_MANWON, 12000)
    assert_equal("INITIAL_VOO_ASSET_MANWON", INITIAL_VOO_ASSET_MANWON, 7000)
    assert_equal("ANNUAL_TRANSFER_TO_DUAL_MANWON", ANNUAL_TRANSFER_TO_DUAL_MANWON, 3800)
    assert_equal("QUANT_SIZE_PENALTY_TIERS length", len(QUANT_SIZE_PENALTY_TIERS), 5)

    assert_equal("FAT_TAIL_DF", FAT_TAIL_DF, 10)
    assert_close("INFLATION_SHOCK_ANNUAL_PROBABILITY", INFLATION_SHOCK_ANNUAL_PROBABILITY, 0.025)
    assert_equal("INFLATION_SHOCK_DURATION_YEARS", INFLATION_SHOCK_DURATION_YEARS, 3)
    assert_close("INFLATION_SHOCK_INFLATION_ADDON", INFLATION_SHOCK_INFLATION_ADDON, 0.04)
    assert_close("INFLATION_SHOCK_RETURN_PENALTY", INFLATION_SHOCK_RETURN_PENALTY, 0.04)
    assert_close("INFLATION_SHOCK_VOL_MULTIPLIER", INFLATION_SHOCK_VOL_MULTIPLIER, 1.30)
    assert_close("MEAN_REVERSION_STRENGTH", MEAN_REVERSION_STRENGTH, 0.05)


def check_target_ruin_probability():
    auto_result = FinancialSimulator(build_params()).run_hybrid_analysis(
        main_sims=20,
        search_sims=5,
    )
    assert_equal("hybrid analysis tuple length", len(auto_result), 9)
    assert_equal("auto DWZ target_ruin_prob", auto_result[-1], DWZ_TARGET_RUIN_PROB)
    if not isinstance(auto_result[-2], int):
        raise AssertionError("top excluded average extra should be an integer month amount")

    normal_result = FinancialSimulator(build_params(dwz_mode=False)).run_hybrid_analysis(
        main_sims=20,
        search_sims=5,
    )
    assert_equal("standard target_ruin_prob", normal_result[-1], STANDARD_TARGET_RUIN_PROB)


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

    trimmed_sample = pd.DataFrame({"final": list(range(1, 11))}).to_numpy(dtype=float)
    trimmed_mean = FinancialSimulator._middle_trimmed_average_final_asset(
        trimmed_sample,
        lower_exclusion_ratio=0.30,
        upper_exclusion_ratio=0.30,
    )
    assert_close("middle trimmed average helper", trimmed_mean, 5.5)


def check_inflation_shock_mask_helper():
    empty_mask = FinancialSimulator._build_inflation_shock_mask(
        n_simulations=3,
        simulation_years=12,
        annual_probability=0.0,
        duration_years=INFLATION_SHOCK_DURATION_YEARS,
    )
    if empty_mask.any():
        raise AssertionError("inflation shock mask should be empty when probability is zero")

    full_mask = FinancialSimulator._build_inflation_shock_mask(
        n_simulations=3,
        simulation_years=12,
        annual_probability=1.0,
        duration_years=INFLATION_SHOCK_DURATION_YEARS,
    )
    if not full_mask.all():
        raise AssertionError("inflation shock mask should fully cover all years when probability is one")


def check_monte_carlo_shapes():
    years, pv, nom, returns = FinancialSimulator(build_params()).run_monte_carlo(
        n_simulations=30,
        override_extra_margin=100,
    )
    expected_shape = (30, len(years))
    assert_equal("pv shape", pv.shape, expected_shape)
    assert_equal("nom shape", nom.shape, expected_shape)
    assert_equal("returns shape", returns.shape, expected_shape)

    res = {
        "years": years,
        "pv": pv,
        "returns": returns,
        "retire_age": 60,
    }
    risk_df = build_real_life_risk_table(res)
    assert_equal("risk metric count", len(risk_df), 3)



def check_default_events():
    lump_df = get_default_lump_events()
    recurring_df = get_default_recurring_events()

    if lump_df["내용"].astype(str).str.contains("증여").any():
        raise AssertionError("default gift events should be removed")

    housing = lump_df[lump_df["내용"] == "주택구입"]
    assert_equal("housing purchase event count", len(housing), 1)
    assert_equal("housing purchase age", int(housing.iloc[0]["나이"]), 45)
    assert_equal("housing purchase amount", int(housing.iloc[0]["금액(만원)"]), 32000)

    home_pension = recurring_df[recurring_df["내용"] == "주택연금"]
    assert_equal("home pension event count", len(home_pension), 1)
    assert_equal("home pension start age", int(home_pension.iloc[0]["시작나이"]), 55)
    assert_equal("home pension amount", int(home_pension.iloc[0]["월금액(만원)"]), 100)
    assert_equal("home pension guaranteed flag", bool(home_pension.iloc[0]["확정연금"]), True)

    car_payment = recurring_df[recurring_df["내용"] == "자동차 할부금"]
    assert_equal("car payment event count", len(car_payment), 1)
    assert_equal("car payment start age", int(car_payment.iloc[0]["시작나이"]), 47)
    assert_equal("car payment duration", int(car_payment.iloc[0]["기간(년)"]), 5)
    assert_equal("car payment amount", int(car_payment.iloc[0]["월금액(만원)"]), 200)

    national_pension = recurring_df[recurring_df["내용"] == "국민연금"]
    assert_equal("national pension start age", int(national_pension.iloc[0]["시작나이"]), 70)
    assert_equal("national pension amount", int(national_pension.iloc[0]["월금액(만원)"]), 100)
    assert_equal("national pension guaranteed flag", bool(national_pension.iloc[0]["확정연금"]), True)

def main():
    check_config_assumptions()
    check_default_events()
    check_target_ruin_probability()
    check_portfolio_transition_and_penalty_helpers()
    check_inflation_shock_mask_helper()
    check_monte_carlo_shapes()
    print("OK: V60-7 middle-trimmed budget and automatic model checks passed.")


if __name__ == "__main__":
    main()
