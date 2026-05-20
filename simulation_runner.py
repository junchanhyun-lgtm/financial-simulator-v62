from simulator import FinancialSimulator


def run_simulation_analysis(
    params,
    main_sims,
    search_sims,
):
    simulator = FinancialSimulator(params)

    (
        years,
        main_pv,
        main_nom,
        main_returns,
        safe_extra,
        base_ruin,
        stress_df,
        t_ruin,
    ) = simulator.run_hybrid_analysis(
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

    return {
        "years": years,
        "main_pv": main_pv,
        "main_nom": main_nom,
        "main_returns": main_returns,
        "safe_extra": safe_extra,
        "base_ruin": base_ruin,
        "stress_df": stress_df,
        "t_ruin": t_ruin,
        "defense_rate": defense_rate,
    }
