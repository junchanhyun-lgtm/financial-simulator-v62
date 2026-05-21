import streamlit as st

from config import N_SIMULATIONS, SEARCH_SIMULATIONS
from ui_inputs import render_input_panel
from params_builder import build_simulation_params
from ui_layout import render_page_layout
from simulation_runner import run_simulation_analysis
from result_state import build_sim_results_state
from ui_results import render_results_page


# -----------------------------------------------------------
# 3. Streamlit UI
# -----------------------------------------------------------
def main():
    render_page_layout()

    input_values = render_input_panel()

    retire_age = input_values["retire_age"]
    dwz_mode = input_values["dwz_mode"]
    clean_lump_df = input_values["lump_events"]

    if st.button("🚀 5,000회 연산 및 정밀 스트레스 테스트 시작", type="primary", use_container_width=True):
        st.divider()
        params = build_simulation_params(input_values)

        with st.spinner("통합자산 몬테카를로, 원인분해, 시나리오 비교, 민감도 분석 수행 중..."):
            analysis = run_simulation_analysis(
                params=params,
                main_sims=N_SIMULATIONS,
                search_sims=SEARCH_SIMULATIONS,
            )

            st.session_state["sim_results"] = build_sim_results_state(
                years=analysis["years"],
                main_pv=analysis["main_pv"],
                main_nom=analysis["main_nom"],
                main_returns=analysis["main_returns"],
                n_sims=N_SIMULATIONS,
                raw_returns=analysis.get("raw_returns"),
                safe_extra=analysis["safe_extra"],
                trimmed_avg_extra=analysis["trimmed_avg_extra"],
                base_ruin=analysis["base_ruin"],
                stress_df=analysis["stress_df"],
                dwz_mode=dwz_mode,
                t_ruin=analysis["t_ruin"],
                defense_rate=analysis["defense_rate"],
                clean_lump_df=clean_lump_df,
                retire_age=retire_age,
                shock_mask=analysis.get("shock_mask"),
                inflation_matrix=analysis.get("inflation_matrix"),
                quant_penalty=analysis.get("quant_penalty"),
                spending_pv=analysis.get("spending_pv"),
                net_cashflow_pv=analysis.get("net_cashflow_pv"),
                withdrawal_pv=analysis.get("withdrawal_pv"),
                return_floor_mask=analysis.get("return_floor_mask"),
                return_ceiling_mask=analysis.get("return_ceiling_mask"),
                market_index=analysis.get("market_index"),
                sensitivity_df=analysis.get("sensitivity_df"),
                scenario_comparison_df=analysis.get("scenario_comparison_df"),
            )

    if "sim_results" in st.session_state:
        render_results_page(st.session_state["sim_results"])


if __name__ == "__main__":
    main()
