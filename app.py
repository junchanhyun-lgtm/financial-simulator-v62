import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

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
    render_rolling_window_section,
    render_representative_paths_section,
    render_stress_budget_section,
    render_main_asset_path_section,
    render_sensitivity_section,
)

# -----------------------------------------------------------
# 2. 퀀트 시뮬레이션 코어 엔진 (V59)
# -----------------------------------------------------------
class FinancialSimulator:
    def __init__(self, params):
        self.params = params

    def run_monte_carlo(self, n_simulations=5000, override_extra_margin=0):
        current_age = self.params['current_age']
        death_age = self.params['death_age']
        current_asset = self.params['current_asset'] * 10000.0

        base_monthly_income = (self.params['monthly_income'] * 10000) * 12
        apply_income_inflation = self.params['apply_income_inflation']
        base_monthly_expense = self.params['monthly_expense'] * 10000 * 12

        inflation = self.params['inflation'] / 100.0
        friction_cost = self.params['tax_fee_rate'] / 100.0

        use_fat_tail = self.params.get('use_fat_tail', False)
        use_inflation_shock = self.params.get('use_inflation_shock', False)
        use_flex_spending = self.params.get('use_flex_spending', False)
        dwz_mode = self.params.get('dwz_mode', False)

        use_glide_path = self.params.get('use_glide_path', True)

        years = list(range(current_age, death_age + 1))
        simulation_years = len(years)
        retire_idx = max(0, self.params['retire_age'] - current_age)

        inflation_matrix = np.full((n_simulations, simulation_years), inflation)
        shock_mask = np.zeros((n_simulations, simulation_years), dtype=bool)

        if use_inflation_shock:
            max_start = max(retire_idx, min(simulation_years - 3, retire_idx + 9))
            shock_starts = np.random.randint(retire_idx, max_start + 1, size=n_simulations)
            for i in range(3):
                cols = np.clip(shock_starts + i, 0, simulation_years - 1)
                shock_mask[np.arange(n_simulations), cols] = True
                inflation_matrix[np.arange(n_simulations), cols] = 0.07

        discount_factors = np.ones((n_simulations, simulation_years))
        if simulation_years > 1:
            discount_factors[:, 1:] = np.cumprod(1 + inflation_matrix[:, :-1], axis=1)

        recurring_df = self.params['recurring_events']
        lump_df = self.params['lump_events']

        pv_extra_income = np.zeros(simulation_years)
        pv_extra_expense = np.zeros(simulation_years)
        nom_extra_income = np.zeros(simulation_years)
        nom_extra_expense = np.zeros(simulation_years)
        pv_lump_sum = np.zeros(simulation_years)

        for t, age in enumerate(years):
            if not recurring_df.empty:
                for _, row in recurring_df.iterrows():
                    if row['시작나이'] <= age < row['시작나이'] + row['기간(년)']:
                        amt_val = abs(row['월금액(만원)']) * 10000 * 12
                        if row.get('물가연동', False):
                            if row['유형'] == '수입': pv_extra_income[t] += amt_val
                            else: pv_extra_expense[t] += amt_val
                        else:
                            if row['유형'] == '수입': nom_extra_income[t] += amt_val
                            else: nom_extra_expense[t] += amt_val
            if not lump_df.empty:
                for _, row in lump_df.iterrows():
                    if row['나이'] == age:
                        amt_val = abs(row['금액(만원)']) * 10000
                        if row['유형'] == '수입': pv_lump_sum[t] += amt_val
                        else: pv_lump_sum[t] -= amt_val

        mu_base = np.zeros(simulation_years)
        vol_base = np.zeros(simulation_years)

        ret_pre = self.params['expected_return_pre'] / 100.0
        ret_post = self.params['expected_return_post'] / 100.0
        v_pre = self.params['vol_pre'] / 100.0
        v_post = self.params['vol_post'] / 100.0

        transition_years = 5

        for t, age in enumerate(years):
            if not use_glide_path:
                mu_base[t] = ret_post if age >= self.params['retire_age'] else ret_pre
                vol_base[t] = v_post if age >= self.params['retire_age'] else v_pre
            else:
                if age <= self.params['retire_age'] - transition_years:
                    mu_base[t] = ret_pre
                    vol_base[t] = v_pre
                elif age >= self.params['retire_age']:
                    mu_base[t] = ret_post
                    vol_base[t] = v_post
                else:
                    ratio = (age - (self.params['retire_age'] - transition_years)) / transition_years
                    mu_base[t] = ret_pre * (1 - ratio) + ret_post * ratio
                    vol_base[t] = v_pre * (1 - ratio) + v_post * ratio

        mu_matrix = np.tile(mu_base, (n_simulations, 1))
        vol_matrix = np.tile(vol_base, (n_simulations, 1))

        if use_inflation_shock:
            shock_penalty = 0.05
            vol_multiplier = 1.5
            mu_matrix[shock_mask] -= shock_penalty
            vol_matrix[shock_mask] *= vol_multiplier

        if use_fat_tail:
            z_matrix = np.random.standard_t(df=5, size=(n_simulations, simulation_years)) / np.sqrt(5/3)
        else:
            z_matrix = np.random.normal(loc=0.0, scale=1.0, size=(n_simulations, simulation_years))

        temp_returns = z_matrix * vol_matrix + mu_matrix - friction_cost

        sim_returns = np.zeros_like(temp_returns)
        sim_returns[:, 0] = temp_returns[:, 0]
        reversion_strength = 0.10

        for t in range(1, simulation_years):
            excess_prev = sim_returns[:, t-1] - mu_matrix[:, t-1]
            sim_returns[:, t] = temp_returns[:, t] - (reversion_strength * excess_prev)

        market_index_matrix = np.cumprod(1 + sim_returns, axis=1) * 100.0
        high_water_mark_matrix = np.maximum.accumulate(market_index_matrix, axis=1)
        market_drawdown_matrix = (high_water_mark_matrix - market_index_matrix) / high_water_mark_matrix

        sim_assets_pv = np.zeros((n_simulations, simulation_years))
        sim_assets_nom = np.zeros((n_simulations, simulation_years))

        current_assets = np.full(n_simulations, current_asset)

        for t, age in enumerate(years):
            df_factor = discount_factors[:, t]

            extra_inc = (pv_extra_income[t] * df_factor) + nom_extra_income[t]
            extra_exp = (pv_extra_expense[t] * df_factor) + nom_extra_expense[t]
            nom_lump = pv_lump_sum[t] * df_factor

            is_retired = True if age >= self.params['retire_age'] else False
            if not is_retired:
                current_nom_inc = base_monthly_income * df_factor if apply_income_inflation else np.full(n_simulations, base_monthly_income)
            else:
                current_nom_inc = np.zeros(n_simulations)

            decay_factor = 1.0
            yolo_ratio = 1.0

            if dwz_mode:
                # 1. 기본 생활비 점진적 감소 (60세 이후부터 적용, 최대 70% 선까지 하강)
                if age > 60:
                    decay_factor = max(0.70, (1 - 0.015) ** (age - 60))
                
                # 2. YOLO(사치) 예산 연착륙 스무딩 로직
                if age <= 65:
                    yolo_ratio = 1.0
                elif age <= 75:
                    # 66세~75세 구간: 1.0에서 0.3으로 10년간 부드럽게 선형 감소
                    yolo_ratio = 1.0 - ((age - 65) * 0.07)
                elif age <= 80:
                    yolo_ratio = 0.3
                else:
                    yolo_ratio = 0.0
                    decay_factor = 0.60 # 81세 이후 생활비 60%로 추가 삭감 강제

            base_yolo_expense = override_extra_margin * 10000 * 12 * yolo_ratio

            yolo_mult = np.ones(n_simulations)
            if use_flex_spending:
                drawdowns_t = market_drawdown_matrix[:, t]
                yolo_mult = np.where(drawdowns_t < 0.05, 1.0,
                            np.where(drawdowns_t < 0.10, 0.8,
                            np.where(drawdowns_t < 0.15, 0.6,
                            np.where(drawdowns_t < 0.20, 0.4,
                            np.where(drawdowns_t < 0.25, 0.2, 0.0)))))

            actual_yolo_expense = base_yolo_expense * yolo_mult
            base_expense_applied = base_monthly_expense * decay_factor

            target_lifestyle_annual_pv = base_expense_applied + actual_yolo_expense

            total_income_annual = current_nom_inc + extra_inc
            nominal_actual_spending = (target_lifestyle_annual_pv * df_factor) + extra_exp

            net_cashflow = total_income_annual - nominal_actual_spending

            threshold = 1_000_000_000.0
            safe_assets = np.maximum(current_assets, 1.0)
            penalty = np.where(current_assets > threshold, 0.015 * np.log10(safe_assets / threshold), 0.0)

            adj_return = sim_returns[:, t] - penalty

            gain_on_base = current_assets * adj_return
            gain_on_cashflow = net_cashflow * (adj_return / 2.0)

            current_assets = current_assets + gain_on_base + net_cashflow + gain_on_cashflow + nom_lump
            current_assets = np.maximum(current_assets, 0.0)

            sim_assets_nom[:, t] = current_assets
            sim_assets_pv[:, t] = current_assets / df_factor

        return years, sim_assets_pv, sim_assets_nom, sim_returns

    def run_hybrid_analysis(self, main_sims=5000, search_sims=1000):
        is_dwz = self.params.get('dwz_mode', False)
        target_ruin_prob = 20.0 if is_dwz else 15.0

        current_age = self.params['current_age']
        retire_age = self.params['retire_age']

        years, main_pv, main_nom, main_returns = self.run_monte_carlo(n_simulations=main_sims, override_extra_margin=0)

        base_ruin = (np.sum(np.any(main_pv <= 0, axis=1)) / main_sims) * 100

        safe_extra = 0
        if base_ruin <= target_ruin_prob:
            low, high = 0, 5000
            best_extra = 0
            for _ in range(8):
                mid = (low + high) / 2
                _, pv, _, _ = self.run_monte_carlo(n_simulations=search_sims, override_extra_margin=mid)
                ruin = (np.sum(np.any(pv <= 0, axis=1)) / search_sims) * 100
                if ruin <= target_ruin_prob:
                    best_extra = mid
                    low = mid
                else:
                    high = mid
            safe_extra = int(best_extra)

        incs_set = set([0])
        if safe_extra > 0:
            incs_set.update([int(safe_extra * 0.5), safe_extra, safe_extra + 50, safe_extra + 150, safe_extra + 300])
        else:
            incs_set.update([50, 100, 200, 300])

        incs = sorted(list(incs_set))
        results = []
        for inc in incs:
            if inc == 0: ruin = base_ruin
            else:
                _, pv, _, _ = self.run_monte_carlo(n_simulations=search_sims, override_extra_margin=inc)
                ruin = (np.sum(np.any(pv <= 0, axis=1)) / search_sims) * 100
            label = f"+{inc}만 (안전방어선 🚩)" if inc == safe_extra and safe_extra > 0 else "현재 유지 (0만 원)" if inc == 0 else f"+{inc}만 원"
            results.append({'라벨': label, '추가액': inc, '파산 확률(%)': ruin})

        return years, main_pv, main_nom, main_returns, safe_extra, base_ruin, pd.DataFrame(results), target_ruin_prob

    def run_sensitivity(self, base_ruin, sims=2000):
        scenarios = [
            ("수익률 -1%p 하락 (전구간)", 'expected_return', -1.0),
            ("물가상승률 +1%p 폭등", 'inflation', 1.0),
            ("기본생활비 +10% 증가", 'monthly_expense', self.params['monthly_expense'] * 0.1),
        ]
        sens_results = []
        for label, key, delta in scenarios:
            temp_params = self.params.copy()
            if key == 'expected_return':
                temp_params['expected_return_pre'] += delta
                temp_params['expected_return_post'] += delta
            else:
                temp_params[key] += delta

            temp_sim = FinancialSimulator(temp_params)
            _, pv, _, _ = temp_sim.run_monte_carlo(n_simulations=sims, override_extra_margin=0)
            ruin = (np.sum(np.any(pv <= 0, axis=1)) / sims) * 100
            impact = ruin - base_ruin
            sens_results.append({"시나리오": label, "파산확률": ruin, "충격(%)": impact})
        return pd.DataFrame(sens_results)

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
            st.info("💡 **[가치 평가 기준]** 본 시뮬레이터의 모든 결괏값은 인플레이션을 역산한 **'현재 체감 구매력(Present Value)'** 기준으로 완벽히 변환되어 표시됩니다.")

            if safe_extra > 0:
                st.markdown(f"""
                <div class='yolo-box'>
                    <p class='yolo-title'>💰 파산 확률 {t_ruin:.0f}% 방어선 통과</p>
                    <p class='yolo-value'>이번 달 추가로 써도 되는 욜로(YOLO) 예산 = 월 {safe_extra:,}만 원</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"⚠️ **안전 마진 없음:** 기본 파산 확률이 {base_ruin:.1f}%로 타겟({t_ruin:.0f}%)을 초과합니다. 지출 통제가 시급합니다.")

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
        res = st.session_state['sim_results']
        years, sim_assets_pv, sim_returns = res['years'], res['pv'], res['returns']
        base_ruin, stress_df, sens_df = res['base_ruin'], res['stress_df'], res['sens_df']
        is_dwz, target_ruin = res['dwz_mode'], res['t_ruin']
        res_lump_df = res['lump_df']
        tgt_retire = res['retire_age']

        render_rolling_window_section(sim_returns)

        render_representative_paths_section(
            years=years,
            sim_assets_pv=sim_assets_pv,
            sim_returns=sim_returns,
            tgt_retire=tgt_retire,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        g_col, d_col = st.columns([2.5, 1.2])

        with g_col:
            render_stress_budget_section(
                stress_df=stress_df,
                target_ruin=target_ruin,
                is_dwz=is_dwz,
            )

            render_main_asset_path_section(
                years=years,
                sim_assets_pv=sim_assets_pv,
                base_ruin=base_ruin,
                target_ruin=target_ruin,
                tgt_retire=tgt_retire,
                is_dwz=is_dwz,
                res_lump_df=res_lump_df,
            )

            render_sensitivity_section(sens_df)
            
        with d_col:
            with st.container(border=True):
                st.subheader("💡 퀀트 코어 엔진: V59 튜닝 로직")
                st.info(f"""
                **1. 자산 평가 및 연금 방어율 (PV Discounting)**
                모든 시뮬레이션 결과값은 인플레이션을 역산한 **'현재 체감 구매력'**입니다. 현재 월 필수 지출 대비 확정 연금(국민/주택)의 방어율은 **{res['defense_rate']:.1f}%**입니다.

                **2. 자동 글라이드 패스 & 7:3 블렌딩**
                사용자가 선택한 통합 시나리오에 따라, 은퇴 시점에 도달하면 계좌 내 **안전자산(채권 등)의 비중이 30%로 자동 증가**하며 기대수익률과 변동성이 시스템 룰에 맞춰 동시에 하강합니다.

                **3. 기계적 매매 마찰 비용 (Slippage Decay)**
                수익률 모델링과 별개로, 자산 규모가 10억 원을 초과할 때마다 연 4회 리밸런싱에서 발생하는 호가 스프레드 비용을 수식(`0.015 * log10(자산/10억)`)에 따라 매년 자산에서 확정 삭감합니다.

                **4. 상하방 평균 회귀 (Mean Reversion - 10%)**
                자본 시장의 중력을 모사한 자기회귀(AR-1) 모델이 적용되었습니다. 전년도 시장이 폭등/폭락하면, 다음 해의 기대수익률은 기계적으로 역방향(10%)으로 끌어당겨집니다.

                **5. 다단계 생존 본능 (Dynamic Withdrawal)**
                계좌 잔고가 아닌 순수 시장 주가지수가 전고점 대비 5% 하락할 때마다 사치(YOLO) 지출을 20%씩 강제 삭감합니다.
                """)

if __name__ == '__main__':
    main()