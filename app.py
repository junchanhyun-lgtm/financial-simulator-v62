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

        with st.spinner("몬테카를로 시뮬레이션 및 추가지출 방어선 계산 중..."):
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
                safe_extra=analysis["safe_extra"],
                base_ruin=analysis["base_ruin"],
                stress_df=analysis["stress_df"],
                dwz_mode=dwz_mode,
                t_ruin=analysis["t_ruin"],
                defense_rate=analysis["defense_rate"],
                clean_lump_df=clean_lump_df,
                retire_age=retire_age,
            )

    if "sim_results" in st.session_state:
        render_results_page(st.session_state["sim_results"])


if __name__ == "__main__":
    main()
