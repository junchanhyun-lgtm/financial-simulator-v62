import numpy as np
import pandas as pd

from config import (
    ANNUAL_TRANSFER_TO_DUAL_MANWON,
    DWZ_TARGET_RUIN_PROB,
    FAT_TAIL_DF,
    INFLATION_SHOCK_ANNUAL_PROBABILITY,
    INFLATION_SHOCK_DURATION_YEARS,
    INFLATION_SHOCK_INFLATION_ADDON,
    INFLATION_SHOCK_RETURN_PENALTY,
    INFLATION_SHOCK_VOL_MULTIPLIER,
    INITIAL_DUAL_MOMENTUM_ASSET_MANWON,
    INITIAL_QUANT_ASSET_MANWON,
    INITIAL_VOO_ASSET_MANWON,
    MEAN_REVERSION_STRENGTH,
    QUANT_SIZE_PENALTY_TIERS,
    STANDARD_TARGET_RUIN_PROB,
)


class FinancialSimulator:
    def __init__(self, params):
        self.params = params

    @staticmethod
    def _dwz_flexible_age_multiplier(age):
        """DWZ 지출 감소는 필수지출이 아니라 조정가능지출에만 적용합니다."""
        if age <= 64:
            return 1.00
        if age <= 69:
            return 0.85
        if age <= 74:
            return 0.70
        if age <= 79:
            return 0.55
        if age <= 84:
            return 0.40
        return 0.25

    @staticmethod
    def _drawdown_flexible_multiplier(drawdowns):
        """시장 하락 시 긴축도 조정가능지출에만 적용합니다."""
        return np.where(
            drawdowns < 0.05,
            1.00,
            np.where(
                drawdowns < 0.10,
                0.90,
                np.where(
                    drawdowns < 0.20,
                    0.75,
                    np.where(drawdowns < 0.30, 0.55, 0.35),
                ),
            ),
        )

    @staticmethod
    def _quant_size_penalty(estimated_quant_assets_manwon):
        """국내퀀트 추정 운용금액 기준 구간형 수익률 차감률을 반환합니다."""
        penalty = np.zeros_like(estimated_quant_assets_manwon, dtype=float)
        lower_bound = 0.0

        for upper_bound, tier_penalty in QUANT_SIZE_PENALTY_TIERS:
            mask = (estimated_quant_assets_manwon > lower_bound) & (
                estimated_quant_assets_manwon <= upper_bound
            )
            penalty = np.where(mask, tier_penalty, penalty)
            lower_bound = upper_bound

        return penalty

    @staticmethod
    def _portfolio_transition_ratio_and_quant_share(
        current_asset_manwon,
        current_age,
        retire_age,
        age,
        use_portfolio_transition,
    ):
        """
        국내퀀트 → 연금저축+ISA 이체 계획을 연도별 포트폴리오 전환 비율로 환산합니다.

        1차 모델이므로 계좌별 실제 잔고를 따로 시뮬레이션하지 않고,
        현재 계좌 비중과 은퇴 전까지의 연 3,800만 원 이체 계획으로 연도별 기준 비중을 추정합니다.
        """
        initial_total = (
            INITIAL_QUANT_ASSET_MANWON
            + INITIAL_DUAL_MOMENTUM_ASSET_MANWON
            + INITIAL_VOO_ASSET_MANWON
        )
        if initial_total <= 0 or current_asset_manwon <= 0:
            return 1.0 if age >= retire_age else 0.0, 0.0

        scale = current_asset_manwon / initial_total
        quant_start = INITIAL_QUANT_ASSET_MANWON * scale
        dual_start = INITIAL_DUAL_MOMENTUM_ASSET_MANWON * scale
        voo_start = INITIAL_VOO_ASSET_MANWON * scale
        total_basis = quant_start + dual_start + voo_start

        if total_basis <= 0:
            return 1.0 if age >= retire_age else 0.0, 0.0

        if not use_portfolio_transition:
            quant_share = quant_start / total_basis
            return (1.0 if age >= retire_age else 0.0), quant_share

        years_elapsed = max(0, min(age, retire_age) - current_age)
        years_to_retire = max(0, retire_age - current_age)

        transfer_done = min(
            ANNUAL_TRANSFER_TO_DUAL_MANWON * years_elapsed,
            quant_start,
        )
        transfer_at_retire = min(
            ANNUAL_TRANSFER_TO_DUAL_MANWON * years_to_retire,
            quant_start,
        )

        quant_now = max(0.0, quant_start - transfer_done)
        dual_now = dual_start + transfer_done
        quant_at_retire = max(0.0, quant_start - transfer_at_retire)

        initial_quant_share = quant_start / total_basis
        current_quant_share = quant_now / (quant_now + dual_now + voo_start)
        retire_quant_share = quant_at_retire / total_basis

        denominator = initial_quant_share - retire_quant_share
        if denominator <= 1e-12:
            transition_ratio = 1.0 if age >= retire_age else 0.0
        else:
            transition_ratio = (initial_quant_share - current_quant_share) / denominator
            transition_ratio = float(np.clip(transition_ratio, 0.0, 1.0))

        if age >= retire_age:
            transition_ratio = 1.0
            current_quant_share = retire_quant_share

        return transition_ratio, current_quant_share

    def _build_return_assumption_paths(self, years, current_asset_manwon):
        current_age = self.params["current_age"]
        retire_age = self.params["retire_age"]
        use_portfolio_transition = self.params.get("use_portfolio_transition", True)

        ret_pre = self.params["expected_return_pre"] / 100.0
        ret_post = self.params["expected_return_post"] / 100.0
        v_pre = self.params["vol_pre"] / 100.0
        v_post = self.params["vol_post"] / 100.0

        mu_base = np.zeros(len(years))
        vol_base = np.zeros(len(years))
        quant_share_base = np.zeros(len(years))

        for t, age in enumerate(years):
            transition_ratio, quant_share = self._portfolio_transition_ratio_and_quant_share(
                current_asset_manwon=current_asset_manwon,
                current_age=current_age,
                retire_age=retire_age,
                age=age,
                use_portfolio_transition=use_portfolio_transition,
            )

            mu_base[t] = ret_pre * (1 - transition_ratio) + ret_post * transition_ratio
            vol_base[t] = v_pre * (1 - transition_ratio) + v_post * transition_ratio
            quant_share_base[t] = quant_share

        return mu_base, vol_base, quant_share_base

    @staticmethod
    def _build_inflation_shock_mask(
        n_simulations,
        simulation_years,
        annual_probability=INFLATION_SHOCK_ANNUAL_PROBABILITY,
        duration_years=INFLATION_SHOCK_DURATION_YEARS,
    ):
        """생애기간 중 확률적으로 발생하는 인플레이션 쇼크 구간을 생성합니다.

        기존처럼 은퇴 직후에 강제로 넣지 않고, 매년 쇼크 시작 여부를 판정합니다.
        쇼크가 시작되면 지정된 기간 동안 지속되며, 같은 기간 안에서는 중복 쇼크를 만들지 않습니다.
        """
        shock_mask = np.zeros((n_simulations, simulation_years), dtype=bool)

        if annual_probability <= 0 or duration_years <= 0 or simulation_years <= 0:
            return shock_mask

        duration_years = int(duration_years)

        for sim_idx in range(n_simulations):
            t = 0
            while t < simulation_years:
                if np.random.random() < annual_probability:
                    end = min(t + duration_years, simulation_years)
                    shock_mask[sim_idx, t:end] = True
                    t = end
                else:
                    t += 1

        return shock_mask

    def run_monte_carlo(self, n_simulations=5000, override_extra_margin=0):
        current_age = self.params["current_age"]
        death_age = self.params["death_age"]
        current_asset_manwon = self.params["current_asset"]
        current_asset = current_asset_manwon * 10000.0

        base_monthly_income = (self.params["monthly_income"] * 10000) * 12
        apply_income_inflation = self.params["apply_income_inflation"]
        base_monthly_expense = self.params["monthly_expense"] * 10000 * 12

        essential_spending_ratio = float(self.params.get("essential_spending_ratio", 0.70))
        essential_spending_ratio = float(np.clip(essential_spending_ratio, 0.0, 1.0))
        flexible_spending_ratio = 1.0 - essential_spending_ratio

        base_essential_expense = base_monthly_expense * essential_spending_ratio
        base_flexible_expense = base_monthly_expense * flexible_spending_ratio

        inflation = self.params["inflation"] / 100.0
        friction_cost = self.params["tax_fee_rate"] / 100.0

        use_fat_tail = self.params.get("use_fat_tail", False)
        use_inflation_shock = self.params.get("use_inflation_shock", False)
        use_flex_spending = self.params.get("use_flex_spending", False)
        dwz_mode = self.params.get("dwz_mode", False)

        years = list(range(current_age, death_age + 1))
        simulation_years = len(years)
        inflation_matrix = np.full((n_simulations, simulation_years), inflation)
        shock_mask = np.zeros((n_simulations, simulation_years), dtype=bool)

        if use_inflation_shock:
            shock_mask = self._build_inflation_shock_mask(
                n_simulations=n_simulations,
                simulation_years=simulation_years,
            )
            inflation_matrix[shock_mask] = inflation + INFLATION_SHOCK_INFLATION_ADDON

        discount_factors = np.ones((n_simulations, simulation_years))
        if simulation_years > 1:
            discount_factors[:, 1:] = np.cumprod(1 + inflation_matrix[:, :-1], axis=1)

        recurring_df = self.params["recurring_events"]
        lump_df = self.params["lump_events"]

        pv_extra_income = np.zeros(simulation_years)
        pv_extra_expense = np.zeros(simulation_years)
        nom_extra_income = np.zeros(simulation_years)
        nom_extra_expense = np.zeros(simulation_years)
        pv_lump_sum = np.zeros(simulation_years)

        for t, age in enumerate(years):
            if not recurring_df.empty:
                for _, row in recurring_df.iterrows():
                    if row["시작나이"] <= age < row["시작나이"] + row["기간(년)"]:
                        amt_val = abs(row["월금액(만원)"]) * 10000 * 12
                        if row.get("물가연동", False):
                            if row["유형"] == "수입":
                                pv_extra_income[t] += amt_val
                            else:
                                pv_extra_expense[t] += amt_val
                        else:
                            if row["유형"] == "수입":
                                nom_extra_income[t] += amt_val
                            else:
                                nom_extra_expense[t] += amt_val
            if not lump_df.empty:
                for _, row in lump_df.iterrows():
                    if row["나이"] == age:
                        amt_val = abs(row["금액(만원)"]) * 10000
                        if row["유형"] == "수입":
                            pv_lump_sum[t] += amt_val
                        else:
                            pv_lump_sum[t] -= amt_val

        mu_base, vol_base, quant_share_base = self._build_return_assumption_paths(
            years=years,
            current_asset_manwon=current_asset_manwon,
        )

        mu_matrix = np.tile(mu_base, (n_simulations, 1))
        vol_matrix = np.tile(vol_base, (n_simulations, 1))

        if use_inflation_shock:
            mu_matrix[shock_mask] -= INFLATION_SHOCK_RETURN_PENALTY
            vol_matrix[shock_mask] *= INFLATION_SHOCK_VOL_MULTIPLIER

        if use_fat_tail:
            # t분포는 자유도/(자유도-2)의 분산을 가지므로 표준편차가 1이 되도록 정규화합니다.
            fat_tail_scale = np.sqrt(FAT_TAIL_DF / (FAT_TAIL_DF - 2))
            z_matrix = (
                np.random.standard_t(df=FAT_TAIL_DF, size=(n_simulations, simulation_years))
                / fat_tail_scale
            )
        else:
            z_matrix = np.random.normal(loc=0.0, scale=1.0, size=(n_simulations, simulation_years))

        temp_returns = z_matrix * vol_matrix + mu_matrix - friction_cost

        sim_returns = np.zeros_like(temp_returns)
        sim_returns[:, 0] = temp_returns[:, 0]
        for t in range(1, simulation_years):
            excess_prev = sim_returns[:, t - 1] - mu_matrix[:, t - 1]
            sim_returns[:, t] = temp_returns[:, t] - (MEAN_REVERSION_STRENGTH * excess_prev)

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

            is_retired = age >= self.params["retire_age"]
            if not is_retired:
                current_nom_inc = (
                    base_monthly_income * df_factor
                    if apply_income_inflation
                    else np.full(n_simulations, base_monthly_income)
                )
            else:
                current_nom_inc = np.zeros(n_simulations)

            flexible_age_mult = self._dwz_flexible_age_multiplier(age) if dwz_mode else 1.0

            if use_flex_spending:
                flexible_market_mult = self._drawdown_flexible_multiplier(market_drawdown_matrix[:, t])
            else:
                flexible_market_mult = np.ones(n_simulations)

            flexible_multiplier = flexible_age_mult * flexible_market_mult

            base_expense_applied = base_essential_expense + (
                base_flexible_expense * flexible_multiplier
            )

            extra_lifestyle_expense = (
                override_extra_margin * 10000 * 12 * flexible_multiplier
            )

            target_lifestyle_annual_pv = base_expense_applied + extra_lifestyle_expense

            total_income_annual = current_nom_inc + extra_inc
            nominal_actual_spending = (target_lifestyle_annual_pv * df_factor) + extra_exp

            net_cashflow = total_income_annual - nominal_actual_spending

            estimated_quant_assets_manwon = (current_assets / 10000.0) * quant_share_base[t]
            scale_penalty = self._quant_size_penalty(estimated_quant_assets_manwon)

            adj_return = sim_returns[:, t] - scale_penalty

            gain_on_base = current_assets * adj_return
            gain_on_cashflow = net_cashflow * (adj_return / 2.0)

            current_assets = current_assets + gain_on_base + net_cashflow + gain_on_cashflow + nom_lump
            current_assets = np.maximum(current_assets, 0.0)

            sim_assets_nom[:, t] = current_assets
            sim_assets_pv[:, t] = current_assets / df_factor

        return years, sim_assets_pv, sim_assets_nom, sim_returns

    def run_hybrid_analysis(self, main_sims=5000, search_sims=1000):
        is_dwz = self.params.get("dwz_mode", False)
        target_ruin_prob = DWZ_TARGET_RUIN_PROB if is_dwz else STANDARD_TARGET_RUIN_PROB

        years, main_pv, main_nom, main_returns = self.run_monte_carlo(
            n_simulations=main_sims,
            override_extra_margin=0,
        )

        base_ruin = (np.sum(np.any(main_pv <= 0, axis=1)) / main_sims) * 100

        safe_extra = 0
        if base_ruin <= target_ruin_prob:
            low, high = 0, 5000
            best_extra = 0
            for _ in range(8):
                mid = (low + high) / 2
                _, pv, _, _ = self.run_monte_carlo(
                    n_simulations=search_sims,
                    override_extra_margin=mid,
                )
                ruin = (np.sum(np.any(pv <= 0, axis=1)) / search_sims) * 100
                if ruin <= target_ruin_prob:
                    best_extra = mid
                    low = mid
                else:
                    high = mid
            safe_extra = int(best_extra)

        incs_set = {0}
        if safe_extra > 0:
            incs_set.update(
                [
                    int(safe_extra * 0.5),
                    safe_extra,
                    safe_extra + 50,
                    safe_extra + 150,
                    safe_extra + 300,
                ]
            )
        else:
            incs_set.update([50, 100, 200, 300])

        incs = sorted(list(incs_set))
        results = []
        for inc in incs:
            if inc == 0:
                ruin = base_ruin
            else:
                _, pv, _, _ = self.run_monte_carlo(
                    n_simulations=search_sims,
                    override_extra_margin=inc,
                )
                ruin = (np.sum(np.any(pv <= 0, axis=1)) / search_sims) * 100
            label = (
                f"+{inc}만 (안전방어선 🚩)"
                if inc == safe_extra and safe_extra > 0
                else "현재 유지 (0만 원)"
                if inc == 0
                else f"+{inc}만 원"
            )
            results.append({"라벨": label, "추가액": inc, "파산 확률(%)": ruin})

        return (
            years,
            main_pv,
            main_nom,
            main_returns,
            safe_extra,
            base_ruin,
            pd.DataFrame(results),
            target_ruin_prob,
        )

    def run_sensitivity(self, base_ruin, sims=2000):
        scenarios = [
            ("수익률 -1%p 하락 (전구간)", "expected_return", -1.0),
            ("물가상승률 +1%p 폭등", "inflation", 1.0),
            ("기본생활비 +10% 증가", "monthly_expense", self.params["monthly_expense"] * 0.1),
        ]
        sens_results = []
        for label, key, delta in scenarios:
            temp_params = self.params.copy()
            if key == "expected_return":
                temp_params["expected_return_pre"] += delta
                temp_params["expected_return_post"] += delta
            else:
                temp_params[key] += delta

            temp_sim = FinancialSimulator(temp_params)
            _, pv, _, _ = temp_sim.run_monte_carlo(n_simulations=sims, override_extra_margin=0)
            ruin = (np.sum(np.any(pv <= 0, axis=1)) / sims) * 100
            impact = ruin - base_ruin
            sens_results.append({"시나리오": label, "파산확률": ruin, "충격(%)": impact})
        return pd.DataFrame(sens_results)
