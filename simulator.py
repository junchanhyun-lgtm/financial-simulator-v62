import numpy as np
import pandas as pd

from config import DWZ_TARGET_RUIN_PROB, STANDARD_TARGET_RUIN_PROB
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
        target_ruin_prob = DWZ_TARGET_RUIN_PROB if is_dwz else STANDARD_TARGET_RUIN_PROB

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
