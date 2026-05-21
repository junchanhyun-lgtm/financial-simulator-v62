from config import SCENARIO_COMPARISON_SEARCH_SIMULATIONS, SCENARIO_COMPARISON_SIMULATIONS, SENSITIVITY_SIMULATIONS
from simulator import FinancialSimulator


def run_simulation_analysis(
    params,
    main_sims,
    search_sims,
):
    simulator = FinancialSimulator(params)
    analysis = simulator.run_hybrid_analysis(
        main_sims=main_sims,
        search_sims=search_sims,
    )

    recurring_events = params["recurring_events"]
    monthly_expense = params["monthly_expense"]

    total_pension = 0
    if "확정연금" in recurring_events.columns:
        pension_df = recurring_events[
            (recurring_events["유형"] == "수입")
            & (recurring_events["확정연금"] == True)
        ]
        total_pension = pension_df["월금액(만원)"].sum()

    defense_rate = (
        total_pension / monthly_expense * 100
        if monthly_expense > 0
        else 0
    )

    sensitivity_df = simulator.run_sensitivity(
        base_ruin=analysis["base_ruin"],
        sims=SENSITIVITY_SIMULATIONS,
    )
    scenario_comparison_df = simulator.run_scenario_comparison(
        sims=SCENARIO_COMPARISON_SIMULATIONS,
        search_sims=SCENARIO_COMPARISON_SEARCH_SIMULATIONS,
    )

    return {
        **analysis,
        "main_pv": analysis["pv"],
        "main_nom": analysis["nom"],
        "main_returns": analysis["returns"],
        "t_ruin": analysis["target_ruin_prob"],
        "defense_rate": defense_rate,
        "sensitivity_df": sensitivity_df,
        "scenario_comparison_df": scenario_comparison_df,
        "return_assumption_info": params.get("return_assumption_info", {}),
    }
