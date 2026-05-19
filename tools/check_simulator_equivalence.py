import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from simulator import FinancialSimulator as NewFinancialSimulator


def load_old_financial_simulator():
    old_app_path = ROOT_DIR / "backups" / "app_v59_original.py"

    spec = importlib.util.spec_from_file_location("old_app_v59_original", old_app_path)
    old_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_module)

    return old_module.FinancialSimulator


def build_test_params():
    lump_events = pd.DataFrame([
        {"나이": 41, "유형": "지출", "내용": "대출상환", "금액(만원)": 10000},
        {"나이": 50, "유형": "지출", "내용": "주택구입", "금액(만원)": 32000},
        {"나이": 70, "유형": "수입", "내용": "기타수입", "금액(만원)": 5000},
    ])

    recurring_events = pd.DataFrame([
        {
            "시작나이": 40,
            "기간(년)": 10,
            "유형": "수입",
            "내용": "추가근무",
            "월금액(만원)": 200,
            "확정연금": False,
            "물가연동": False,
        },
        {
            "시작나이": 60,
            "기간(년)": 30,
            "유형": "지출",
            "내용": "건보료",
            "월금액(만원)": 50,
            "확정연금": False,
            "물가연동": True,
        },
        {
            "시작나이": 70,
            "기간(년)": 20,
            "유형": "수입",
            "내용": "국민연금",
            "월금액(만원)": 100,
            "확정연금": True,
            "물가연동": True,
        },
    ])

    return {
        "current_age": 40,
        "death_age": 90,
        "current_asset": 126000,
        "monthly_income": 500,
        "apply_income_inflation": False,
        "monthly_expense": 700,
        "expected_return_pre": 15.61,
        "vol_pre": 18.13,
        "expected_return_post": 11.98,
        "vol_post": 12.71,
        "inflation": 2.5,
        "tax_fee_rate": 0.5,
        "retire_age": 60,
        "lump_events": lump_events,
        "recurring_events": recurring_events,
        "use_fat_tail": True,
        "use_inflation_shock": True,
        "use_flex_spending": True,
        "dwz_mode": True,
        "use_glide_path": True,
    }


def assert_array_close(name, old_value, new_value):
    if not np.allclose(old_value, new_value, rtol=1e-10, atol=1e-10):
        raise AssertionError(f"{name} mismatch")


def main():
    OldFinancialSimulator = load_old_financial_simulator()
    params = build_test_params()

    old_sim = OldFinancialSimulator(params)
    new_sim = NewFinancialSimulator(params)

    np.random.seed(1234)
    old_years, old_pv, old_nom, old_returns = old_sim.run_monte_carlo(
        n_simulations=300,
        override_extra_margin=100,
    )

    np.random.seed(1234)
    new_years, new_pv, new_nom, new_returns = new_sim.run_monte_carlo(
        n_simulations=300,
        override_extra_margin=100,
    )

    if old_years != new_years:
        raise AssertionError("years mismatch")

    assert_array_close("sim_assets_pv", old_pv, new_pv)
    assert_array_close("sim_assets_nom", old_nom, new_nom)
    assert_array_close("sim_returns", old_returns, new_returns)

    np.random.seed(5678)
    old_hybrid = old_sim.run_hybrid_analysis(main_sims=300, search_sims=80)

    np.random.seed(5678)
    new_hybrid = new_sim.run_hybrid_analysis(main_sims=300, search_sims=80)

    for index, name in enumerate([
        "years",
        "main_pv",
        "main_nom",
        "main_returns",
        "safe_extra",
        "base_ruin",
        "stress_df",
        "target_ruin_prob",
    ]):
        old_value = old_hybrid[index]
        new_value = new_hybrid[index]

        if isinstance(old_value, pd.DataFrame):
            pd.testing.assert_frame_equal(old_value, new_value, check_exact=False, rtol=1e-10, atol=1e-10)
        elif isinstance(old_value, np.ndarray):
            assert_array_close(name, old_value, new_value)
        else:
            if old_value != new_value:
                raise AssertionError(f"{name} mismatch: {old_value} != {new_value}")

    print("OK: simulator equivalence check passed.")


if __name__ == "__main__":
    main()