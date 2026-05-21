from config import (
    AUTO_APPLY_DWZ_SPENDING,
    AUTO_APPLY_FAT_TAIL,
    AUTO_APPLY_FLEX_SPENDING,
    AUTO_APPLY_INFLATION_SHOCK,
    AUTO_APPLY_PORTFOLIO_TRANSITION,
    ESSENTIAL_SPENDING_RATIO,
    INCOME_INFLATION_LINKED,
)


def build_simulation_params(input_values):
    return {
        "current_age": input_values["current_age"],
        "death_age": input_values["death_age"],
        "current_asset": input_values["current_asset"],

        "monthly_income": input_values["monthly_income"],
        "apply_income_inflation": INCOME_INFLATION_LINKED,
        "monthly_expense": input_values["monthly_expense"],
        "essential_spending_ratio": input_values.get(
            "essential_spending_ratio",
            ESSENTIAL_SPENDING_RATIO,
        ),

        "expected_return_pre": input_values["expected_return_pre"],
        "vol_pre": input_values["vol_pre"],
        "expected_return_post": input_values["expected_return_post"],
        "vol_post": input_values["vol_post"],
        "return_assumption_info": input_values.get("return_assumption_info", {}),

        "inflation": input_values["inflation"],
        "tax_fee_rate": input_values["tax_fee_rate"],
        "retire_age": input_values["retire_age"],

        "lump_events": input_values["lump_events"],
        "recurring_events": input_values["recurring_events"],

        # 현실화 모델은 UI 토글 없이 기본 적용합니다.
        "use_fat_tail": AUTO_APPLY_FAT_TAIL,
        "use_inflation_shock": AUTO_APPLY_INFLATION_SHOCK,
        "use_flex_spending": AUTO_APPLY_FLEX_SPENDING,
        "dwz_mode": AUTO_APPLY_DWZ_SPENDING,
        "use_portfolio_transition": AUTO_APPLY_PORTFOLIO_TRANSITION,
    }
