def build_simulation_params(input_values):
    return {
        "current_age": input_values["current_age"],
        "death_age": input_values["death_age"],
        "current_asset": input_values["current_asset"],

        "monthly_income": input_values["monthly_income"],
        "apply_income_inflation": input_values["apply_income_inflation"],
        "monthly_expense": input_values["monthly_expense"],

        "expected_return_pre": input_values["expected_return_pre"],
        "vol_pre": input_values["vol_pre"],
        "expected_return_post": input_values["expected_return_post"],
        "vol_post": input_values["vol_post"],

        "inflation": input_values["inflation"],
        "tax_fee_rate": input_values["tax_fee_rate"],
        "retire_age": input_values["retire_age"],

        "lump_events": input_values["lump_events"],
        "recurring_events": input_values["recurring_events"],

        "use_fat_tail": input_values["use_fat_tail"],
        "use_inflation_shock": input_values["use_inflation_shock"],
        "use_flex_spending": input_values["use_flex_spending"],
        "dwz_mode": input_values["dwz_mode"],
        "use_glide_path": input_values["use_glide_path"],
    }