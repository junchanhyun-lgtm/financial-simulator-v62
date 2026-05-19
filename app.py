import streamlit as st

from config import (
    PAGE_TITLE,
    MAIN_TITLE,
    UPDATE_MESSAGE,
    N_SIMULATIONS,
    SEARCH_SIMULATIONS,
    SENSITIVITY_SIMULATIONS,
    DEFAULT_SCENARIO_INDEX,
    SCENARIO_OPTIONS,
)
from data_defaults import get_default_lump_events, get_default_recurring_events
from simulator import FinancialSimulator
from ui_inputs import render_input_panel
from utils import format_won, calc_rolling_stats
from params_builder import build_simulation_params
from ui_layout import render_page_layout
from simulation_runner import run_simulation_analysis
from result_state import build_sim_results_state
from ui_results import (
    render_simulation_summary_section,
    render_results_page,
)


# -----------------------------------------------------------
# 3. Streamlit UI (V59 Final)
# -----------------------------------------------------------
def main():
    render_page_layout()

    input_values = render_input_panel()

    retire_age = input_values["retire_age"]
    monthly_expense = input_values["monthly_expense"]
    dwz_mode = input_values["dwz_mode"]

    clean_lump_df = input_values["lump_events"]
    clean_recur_df = input_values["recurring_events"]

    if st.button("🚀 5,000회 연산 및 정밀 스트레스 테스트 시작", type="primary", use_container_width=True):
        st.divider()
        n_sims = N_SIMULATIONS
        params = build_simulation_params(input_values)

        with st.spinner("복합 조세 모듈 및 글라이드 패스 연산 수행 중..."):
            analysis = run_simulation_analysis(
                params=params,
                main_sims=N_SIMULATIONS,
                search_sims=SEARCH_SIMULATIONS,
                sensitivity_sims=SENSITIVITY_SIMULATIONS,
            )

            years = analysis["years"]
            main_pv = analysis["main_pv"]
            main_nom = analysis["main_nom"]
            main_returns = analysis["main_returns"]
            safe_extra = analysis["safe_extra"]
            base_ruin = analysis["base_ruin"]
            stress_df = analysis["stress_df"]
            sens_df = analysis["sens_df"]
            t_ruin = analysis["t_ruin"]
            defense_rate = analysis["defense_rate"]

            render_simulation_summary_section(safe_extra, base_ruin, t_ruin)
            
            st.session_state["sim_results"] = build_sim_results_state(
                years=years,
                main_pv=main_pv,
                main_nom=main_nom,
                main_returns=main_returns,
                n_sims=n_sims,
                safe_extra=safe_extra,
                base_ruin=base_ruin,
                stress_df=stress_df,
                sens_df=sens_df,
                dwz_mode=dwz_mode,
                t_ruin=t_ruin,
                defense_rate=defense_rate,
                clean_lump_df=clean_lump_df,
                retire_age=retire_age,
            )

    if 'sim_results' in st.session_state:
        render_results_page(st.session_state["sim_results"])

if __name__ == '__main__':
    main()