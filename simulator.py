import numpy as np
import pandas as pd

from config import (
    ACCOUNT_LABELS,
    ACCOUNT_NAMES,
    ACCOUNT_RETURN_CORRELATION,
    ACCOUNT_SCENARIOS,
    ANNUAL_TRANSFER_TO_DUAL_MANWON,
    DWZ_TARGET_RUIN_PROB,
    FAT_TAIL_DF,
    FIXED_RANDOM_SEED_ENABLED,
    INFLATION_SHOCK_ANNUAL_PROBABILITY,
    INFLATION_SHOCK_DURATION_YEARS,
    INFLATION_SHOCK_INFLATION_ADDON,
    INFLATION_SHOCK_RETURN_PENALTY,
    INFLATION_SHOCK_VOL_MULTIPLIER,
    INITIAL_DUAL_MOMENTUM_ASSET_MANWON,
    INITIAL_QUANT_ASSET_MANWON,
    INITIAL_VOO_ASSET_MANWON,
    MEAN_REVERSION_STRENGTH,
    MIN_ACCOUNT_ANNUAL_RETURN,
    QUANT_SIZE_PENALTY_TIERS,
    RANDOM_SEED,
    SCENARIO_COMPARISON_SEARCH_SIMULATIONS,
    SCENARIO_COMPARISON_SIMULATIONS,
    SENSITIVITY_SIMULATIONS,
    STANDARD_TARGET_RUIN_PROB,
    TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON,
    TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO,
    TRIMMED_AVERAGE_UPPER_EXCLUSION_RATIO,
)


def _safe_divide(numerator, denominator, default=0.0):
    numerator = np.asarray(numerator, dtype=float)
    denominator = np.asarray(denominator, dtype=float)
    return np.divide(
        numerator,
        denominator,
        out=np.full(np.broadcast_shapes(numerator.shape, denominator.shape), default, dtype=float),
        where=np.abs(denominator) > 1e-12,
    )


def format_manwon(value_manwon):
    if value_manwon is None or pd.isna(value_manwon):
        return "-"
    val = int(round(float(value_manwon)))
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 10000:
        eok = val // 10000
        man = val % 10000
        return f"{sign}{eok}억 {man:,}만 원" if man else f"{sign}{eok}억 원"
    return f"{sign}{val:,}만 원"


def format_won(value_won):
    if value_won is None or pd.isna(value_won):
        return "-"
    return format_manwon(float(value_won) / 10000.0)


def format_pct(value, digits=1):
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.{digits}f}%"


class FinancialSimulator:
    def __init__(self, params):
        self.params = params.copy()
        self.scenario_name = self._resolve_account_scenario_name()
        self.scenario = ACCOUNT_SCENARIOS[self.scenario_name].copy()
        self._apply_scenario_shifts()

    def _resolve_account_scenario_name(self):
        explicit = self.params.get("account_scenario")
        if explicit in ACCOUNT_SCENARIOS:
            return explicit

        expected_return_pre = float(self.params.get("expected_return_pre", 18.0))
        if expected_return_pre <= 16.0:
            return "보수"
        if expected_return_pre >= 19.0:
            return "공격"
        return "기본"

    def _apply_scenario_shifts(self):
        return_shift = float(self.params.get("return_shift", 0.0))
        vol_shift = float(self.params.get("vol_shift", 0.0))

        for key in ["quant_return", "dual_return", "voo_return"]:
            self.scenario[key] = max(-50.0, float(self.scenario[key]) + return_shift)
        for key in ["quant_vol", "dual_vol", "voo_vol"]:
            self.scenario[key] = max(0.0, float(self.scenario[key]) + vol_shift)

    def _rng(self, seed_offset=0):
        if not bool(self.params.get("fixed_seed_enabled", FIXED_RANDOM_SEED_ENABLED)):
            return np.random.default_rng()
        seed = int(self.params.get("random_seed", RANDOM_SEED)) + int(seed_offset)
        return np.random.default_rng(seed)

    @staticmethod
    def _years(current_age, death_age):
        return list(range(int(current_age), int(death_age) + 1))

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
    def _quant_size_penalty(quant_assets_manwon):
        """국내퀀트 추정 운용금액 기준 구간형 수익률 차감률을 반환합니다."""
        quant_assets_manwon = np.asarray(quant_assets_manwon, dtype=float)
        penalty = np.zeros_like(quant_assets_manwon, dtype=float)
        lower_bound = 0.0

        for upper_bound, tier_penalty in QUANT_SIZE_PENALTY_TIERS:
            mask = (quant_assets_manwon > lower_bound) & (quant_assets_manwon <= upper_bound)
            penalty = np.where(mask, tier_penalty, penalty)
            lower_bound = upper_bound

        return penalty

    @staticmethod
    def _build_inflation_shock_mask(
        n_simulations,
        simulation_years,
        rng=None,
        annual_probability=INFLATION_SHOCK_ANNUAL_PROBABILITY,
        duration_years=INFLATION_SHOCK_DURATION_YEARS,
    ):
        """생애기간 중 확률적으로 발생하는 인플레이션 쇼크 구간을 생성합니다."""
        if rng is None:
            rng = np.random.default_rng(RANDOM_SEED)

        shock_mask = np.zeros((n_simulations, simulation_years), dtype=bool)

        if annual_probability <= 0 or duration_years <= 0 or simulation_years <= 0:
            return shock_mask

        duration_years = int(duration_years)

        for sim_idx in range(n_simulations):
            t = 0
            while t < simulation_years:
                if rng.random() < annual_probability:
                    end = min(t + duration_years, simulation_years)
                    shock_mask[sim_idx, t:end] = True
                    t = end
                else:
                    t += 1

        return shock_mask

    @staticmethod
    def _middle_trimmed_average_final_asset(
        sim_assets_pv,
        lower_exclusion_ratio=TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO,
        upper_exclusion_ratio=TRIMMED_AVERAGE_UPPER_EXCLUSION_RATIO,
    ):
        """최종 현재가치 자산에서 상하위 극단 경로를 제외한 평균을 계산합니다."""
        final_assets = np.asarray(sim_assets_pv, dtype=float)[:, -1]
        if final_assets.size == 0:
            return 0.0

        lower_exclusion_ratio = float(np.clip(lower_exclusion_ratio, 0.0, 0.49))
        upper_exclusion_ratio = float(np.clip(upper_exclusion_ratio, 0.0, 0.49))

        sorted_assets = np.sort(final_assets)
        n_assets = sorted_assets.size
        lower_cut = int(np.floor(n_assets * lower_exclusion_ratio))
        upper_cut = int(np.floor(n_assets * upper_exclusion_ratio))
        start_idx = lower_cut
        end_idx = n_assets - upper_cut

        if start_idx >= end_idx:
            return float(np.median(sorted_assets))

        return float(np.mean(sorted_assets[start_idx:end_idx]))

    def _initial_account_assets_manwon(self):
        default_total = (
            INITIAL_QUANT_ASSET_MANWON
            + INITIAL_DUAL_MOMENTUM_ASSET_MANWON
            + INITIAL_VOO_ASSET_MANWON
        )
        current_asset = float(self.params.get("current_asset", default_total))

        quant = self.params.get("quant_asset")
        dual = self.params.get("dual_asset")
        voo = self.params.get("voo_asset")

        if quant is not None and dual is not None and voo is not None:
            return float(quant), float(dual), float(voo)

        if default_total <= 0:
            return current_asset, 0.0, 0.0

        scale = current_asset / default_total
        return (
            INITIAL_QUANT_ASSET_MANWON * scale,
            INITIAL_DUAL_MOMENTUM_ASSET_MANWON * scale,
            INITIAL_VOO_ASSET_MANWON * scale,
        )

    def _build_event_arrays(self, years):
        simulation_years = len(years)
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
                        if row["유형"] == "수입":
                            if bool(row.get("물가연동", False)):
                                pv_extra_income[t] += amt_val
                            else:
                                nom_extra_income[t] += amt_val
                        else:
                            if bool(row.get("물가연동", False)):
                                pv_extra_expense[t] += amt_val
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

        return {
            "pv_extra_income": pv_extra_income,
            "pv_extra_expense": pv_extra_expense,
            "nom_extra_income": nom_extra_income,
            "nom_extra_expense": nom_extra_expense,
            "pv_lump_sum": pv_lump_sum,
        }

    def _build_account_returns(self, n_simulations, simulation_years, shock_mask, rng):
        account_mu = np.array(
            [
                self.scenario["quant_return"],
                self.scenario["dual_return"],
                self.scenario["voo_return"],
            ],
            dtype=float,
        ) / 100.0
        account_vol = np.array(
            [
                self.scenario["quant_vol"],
                self.scenario["dual_vol"],
                self.scenario["voo_vol"],
            ],
            dtype=float,
        ) / 100.0

        correlation = np.asarray(ACCOUNT_RETURN_CORRELATION, dtype=float)
        chol = np.linalg.cholesky(correlation)
        raw = rng.normal(size=(n_simulations, simulation_years, len(ACCOUNT_NAMES))) @ chol.T

        use_fat_tail = self.params.get("use_fat_tail", False)
        if use_fat_tail:
            # 다변량 t분포 근사: 공통 카이제곱 스케일을 적용해 계좌 간 동시 충격을 반영합니다.
            fat_tail_scale = rng.chisquare(
                df=FAT_TAIL_DF,
                size=(n_simulations, simulation_years, 1),
            ) / FAT_TAIL_DF
            z_matrix = raw / np.sqrt(fat_tail_scale)
            z_matrix = z_matrix / np.sqrt(FAT_TAIL_DF / (FAT_TAIL_DF - 2))
        else:
            z_matrix = raw

        mu_matrix = np.tile(account_mu.reshape(1, 1, -1), (n_simulations, simulation_years, 1))
        vol_matrix = np.tile(account_vol.reshape(1, 1, -1), (n_simulations, simulation_years, 1))

        if self.params.get("use_inflation_shock", False):
            mu_matrix[shock_mask, :] -= INFLATION_SHOCK_RETURN_PENALTY
            vol_matrix[shock_mask, :] *= INFLATION_SHOCK_VOL_MULTIPLIER

        friction_cost = self.params["tax_fee_rate"] / 100.0
        temp_returns = z_matrix * vol_matrix + mu_matrix - friction_cost

        account_returns = np.zeros_like(temp_returns)
        account_returns[:, 0, :] = temp_returns[:, 0, :]
        for t in range(1, simulation_years):
            excess_prev = account_returns[:, t - 1, :] - mu_matrix[:, t - 1, :]
            account_returns[:, t, :] = temp_returns[:, t, :] - (
                MEAN_REVERSION_STRENGTH * excess_prev
            )

        return account_returns

    @staticmethod
    def _withdraw_from_accounts(account_assets, withdrawal_amount):
        """지출 부족분은 국내퀀트 → VOO → 연금저축+ISA 순서로 인출합니다."""
        remaining = np.maximum(withdrawal_amount, 0.0)
        withdrawn = np.zeros_like(account_assets)

        take_quant = np.minimum(account_assets[:, 0], remaining)
        account_assets[:, 0] -= take_quant
        withdrawn[:, 0] = take_quant
        remaining -= take_quant

        take_voo = np.minimum(account_assets[:, 2], remaining)
        account_assets[:, 2] -= take_voo
        withdrawn[:, 2] = take_voo
        remaining -= take_voo

        take_dual = np.minimum(account_assets[:, 1], remaining)
        account_assets[:, 1] -= take_dual
        withdrawn[:, 1] = take_dual
        remaining -= take_dual

        return remaining, withdrawn

    def run_monte_carlo(self, n_simulations=5000, override_extra_margin=0, seed_offset=0):
        current_age = self.params["current_age"]
        death_age = self.params["death_age"]
        retire_age = self.params["retire_age"]

        years = self._years(current_age, death_age)
        simulation_years = len(years)
        rng = self._rng(seed_offset=seed_offset)

        base_monthly_income = (self.params["monthly_income"] * 10000) * 12
        apply_income_inflation = self.params["apply_income_inflation"]
        base_monthly_expense = self.params["monthly_expense"] * 10000 * 12

        essential_spending_ratio = float(self.params.get("essential_spending_ratio", 0.70))
        essential_spending_ratio = float(np.clip(essential_spending_ratio, 0.0, 1.0))
        flexible_spending_ratio = 1.0 - essential_spending_ratio

        base_essential_expense = base_monthly_expense * essential_spending_ratio
        base_flexible_expense = base_monthly_expense * flexible_spending_ratio

        inflation = self.params["inflation"] / 100.0
        use_inflation_shock = self.params.get("use_inflation_shock", False)
        use_flex_spending = self.params.get("use_flex_spending", False)
        dwz_mode = self.params.get("dwz_mode", False)
        use_portfolio_transition = self.params.get("use_portfolio_transition", True)

        inflation_matrix = np.full((n_simulations, simulation_years), inflation)
        shock_mask = np.zeros((n_simulations, simulation_years), dtype=bool)

        if use_inflation_shock:
            shock_mask = self._build_inflation_shock_mask(
                n_simulations=n_simulations,
                simulation_years=simulation_years,
                rng=rng,
                annual_probability=float(
                    self.params.get(
                        "inflation_shock_probability",
                        INFLATION_SHOCK_ANNUAL_PROBABILITY,
                    )
                ),
                duration_years=INFLATION_SHOCK_DURATION_YEARS,
            )
            inflation_matrix[shock_mask] = inflation + INFLATION_SHOCK_INFLATION_ADDON

        discount_factors = np.ones((n_simulations, simulation_years))
        if simulation_years > 1:
            discount_factors[:, 1:] = np.cumprod(1 + inflation_matrix[:, :-1], axis=1)

        account_returns = self._build_account_returns(
            n_simulations=n_simulations,
            simulation_years=simulation_years,
            shock_mask=shock_mask,
            rng=rng,
        )

        event_arrays = self._build_event_arrays(years)

        quant_asset, dual_asset, voo_asset = self._initial_account_assets_manwon()
        account_assets = np.zeros((n_simulations, len(ACCOUNT_NAMES)), dtype=float)
        account_assets[:, 0] = quant_asset * 10000.0
        account_assets[:, 1] = dual_asset * 10000.0
        account_assets[:, 2] = voo_asset * 10000.0
        initial_account_assets = account_assets.copy()

        annual_transfer = float(self.params.get("annual_transfer_to_dual", ANNUAL_TRANSFER_TO_DUAL_MANWON))
        annual_transfer_won = annual_transfer * 10000.0

        account_assets_nom = np.zeros((n_simulations, simulation_years, len(ACCOUNT_NAMES)))
        account_assets_pv = np.zeros((n_simulations, simulation_years, len(ACCOUNT_NAMES)))
        sim_assets_nom = np.zeros((n_simulations, simulation_years))
        sim_assets_pv = np.zeros((n_simulations, simulation_years))
        sim_returns = np.zeros((n_simulations, simulation_years))
        quant_penalty_matrix = np.zeros((n_simulations, simulation_years))
        transfer_matrix = np.zeros((n_simulations, simulation_years))
        withdrawal_matrix = np.zeros((n_simulations, simulation_years, len(ACCOUNT_NAMES)))
        return_floor_mask = np.zeros((n_simulations, simulation_years, len(ACCOUNT_NAMES)), dtype=bool)
        spending_pv_matrix = np.zeros((n_simulations, simulation_years))

        market_index_matrix = np.ones((n_simulations, simulation_years)) * 100.0
        market_index = np.ones(n_simulations) * 100.0
        market_high = np.ones(n_simulations) * 100.0

        for t, age in enumerate(years):
            df_factor = discount_factors[:, t]

            if use_portfolio_transition and age < retire_age and annual_transfer_won > 0:
                transfer = np.minimum(account_assets[:, 0], annual_transfer_won)
                account_assets[:, 0] -= transfer
                account_assets[:, 1] += transfer
                transfer_matrix[:, t] = transfer

            account_total_before_return = account_assets.sum(axis=1)
            weights_before_return = _safe_divide(
                account_assets,
                account_total_before_return.reshape(-1, 1),
                default=0.0,
            )

            adj_account_returns = account_returns[:, t, :].copy()
            quant_penalty = self._quant_size_penalty(account_assets[:, 0] / 10000.0)
            adj_account_returns[:, 0] -= quant_penalty
            quant_penalty_matrix[:, t] = quant_penalty

            pre_return_assets = account_assets.copy()
            return_floor_mask[:, t, :] = (adj_account_returns < MIN_ACCOUNT_ANNUAL_RETURN) & (
                pre_return_assets > 0
            )
            adj_account_returns = np.maximum(adj_account_returns, MIN_ACCOUNT_ANNUAL_RETURN)

            weighted_return = np.sum(weights_before_return * adj_account_returns, axis=1)
            sim_returns[:, t] = weighted_return

            account_assets *= (1.0 + adj_account_returns)

            market_index *= np.maximum(1.0 + weighted_return, 0.0)
            market_high = np.maximum(market_high, market_index)
            market_drawdown = 1.0 - _safe_divide(market_index, market_high, default=1.0)
            market_index_matrix[:, t] = market_index

            extra_inc = (
                event_arrays["pv_extra_income"][t] * df_factor
                + event_arrays["nom_extra_income"][t]
            )
            extra_exp = (
                event_arrays["pv_extra_expense"][t] * df_factor
                + event_arrays["nom_extra_expense"][t]
            )
            nom_lump = event_arrays["pv_lump_sum"][t] * df_factor

            is_retired = age >= retire_age
            if not is_retired:
                current_nom_inc = (
                    base_monthly_income * df_factor
                    if apply_income_inflation
                    else np.full(n_simulations, base_monthly_income)
                )
            else:
                current_nom_inc = np.zeros(n_simulations)

            flexible_age_mult = self._dwz_flexible_age_multiplier(age) if dwz_mode else 1.0
            flexible_market_mult = (
                self._drawdown_flexible_multiplier(market_drawdown)
                if use_flex_spending
                else np.ones(n_simulations)
            )
            flexible_multiplier = flexible_age_mult * flexible_market_mult

            base_expense_applied = base_essential_expense + (
                base_flexible_expense * flexible_multiplier
            )
            extra_lifestyle_expense = (
                override_extra_margin * 10000 * 12 * flexible_multiplier
            )
            target_lifestyle_annual_pv = base_expense_applied + extra_lifestyle_expense
            spending_pv_matrix[:, t] = target_lifestyle_annual_pv

            total_income_annual = current_nom_inc + extra_inc
            nominal_actual_spending = (target_lifestyle_annual_pv * df_factor) + extra_exp
            net_cashflow = total_income_annual - nominal_actual_spending + nom_lump

            positive_cashflow = net_cashflow > 0
            if positive_cashflow.any():
                account_assets[positive_cashflow, 0] += net_cashflow[positive_cashflow]

            withdrawal_amount = np.where(net_cashflow < 0, -net_cashflow, 0.0)
            if np.any(withdrawal_amount > 0):
                _, withdrawn = self._withdraw_from_accounts(account_assets, withdrawal_amount)
                withdrawal_matrix[:, t, :] = withdrawn

            account_assets = np.maximum(account_assets, 0.0)
            current_total_assets = account_assets.sum(axis=1)

            account_assets_nom[:, t, :] = account_assets
            account_assets_pv[:, t, :] = account_assets / df_factor.reshape(-1, 1)
            sim_assets_nom[:, t] = current_total_assets
            sim_assets_pv[:, t] = current_total_assets / df_factor

        return {
            "years": years,
            "pv": sim_assets_pv,
            "nom": sim_assets_nom,
            "returns": sim_returns,
            "account_pv": account_assets_pv,
            "account_nom": account_assets_nom,
            "initial_account_pv": initial_account_assets,
            "initial_account_nom": initial_account_assets,
            "account_returns": account_returns,
            "shock_mask": shock_mask,
            "inflation_matrix": inflation_matrix,
            "quant_penalty": quant_penalty_matrix,
            "transfers": transfer_matrix,
            "withdrawals": withdrawal_matrix,
            "return_floor_mask": return_floor_mask,
            "spending_pv": spending_pv_matrix,
            "market_index": market_index_matrix,
            "scenario_name": self.scenario_name,
            "scenario": self.scenario.copy(),
        }

    @staticmethod
    def ruin_probability(sim_assets_pv):
        return (np.sum(np.any(sim_assets_pv <= 0, axis=1)) / sim_assets_pv.shape[0]) * 100

    def run_hybrid_analysis(self, main_sims=5000, search_sims=1000):
        is_dwz = self.params.get("dwz_mode", False)
        target_ruin_prob = DWZ_TARGET_RUIN_PROB if is_dwz else STANDARD_TARGET_RUIN_PROB

        main_result = self.run_monte_carlo(
            n_simulations=main_sims,
            override_extra_margin=0,
            seed_offset=0,
        )

        base_ruin = self.ruin_probability(main_result["pv"])

        safe_extra = 0
        if base_ruin <= target_ruin_prob:
            low, high = 0, 5000
            best_extra = 0
            for _ in range(8):
                mid = (low + high) / 2
                pv = self.run_monte_carlo(
                    n_simulations=search_sims,
                    override_extra_margin=mid,
                    seed_offset=100,
                )["pv"]
                ruin = self.ruin_probability(pv)
                if ruin <= target_ruin_prob:
                    best_extra = mid
                    low = mid
                else:
                    high = mid
            safe_extra = int(best_extra)

        trimmed_avg_extra = 0
        final_asset_floor = TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON * 10000.0
        base_trimmed_avg = self._middle_trimmed_average_final_asset(main_result["pv"])

        if base_trimmed_avg >= final_asset_floor:
            low, high = 0, 5000
            best_extra = 0
            for _ in range(8):
                mid = (low + high) / 2
                pv = self.run_monte_carlo(
                    n_simulations=search_sims,
                    override_extra_margin=mid,
                    seed_offset=200,
                )["pv"]
                trimmed_avg = self._middle_trimmed_average_final_asset(pv)
                if trimmed_avg >= final_asset_floor:
                    best_extra = mid
                    low = mid
                else:
                    high = mid
            trimmed_avg_extra = int(best_extra)

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
        stress_rows = []
        for inc in incs:
            if inc == 0:
                ruin = base_ruin
            else:
                pv = self.run_monte_carlo(
                    n_simulations=search_sims,
                    override_extra_margin=inc,
                    seed_offset=300,
                )["pv"]
                ruin = self.ruin_probability(pv)
            label = (
                f"+{inc}만 (안전방어선 🚩)"
                if inc == safe_extra and safe_extra > 0
                else "현재 유지 (0만 원)"
                if inc == 0
                else f"+{inc}만 원"
            )
            stress_rows.append({"라벨": label, "추가액": inc, "파산 확률(%)": ruin})

        return {
            **main_result,
            "n_sims": main_sims,
            "safe_extra": safe_extra,
            "base_ruin": base_ruin,
            "stress_df": pd.DataFrame(stress_rows),
            "trimmed_avg_extra": trimmed_avg_extra,
            "target_ruin_prob": target_ruin_prob,
        }

    def run_sensitivity(self, base_ruin, sims=SENSITIVITY_SIMULATIONS):
        scenarios = []

        def add(label, mutator):
            temp_params = self.params.copy()
            mutator(temp_params)
            scenarios.append((label, temp_params))

        add("전 계좌 기대수익률 -2%p", lambda p: p.update({"return_shift": -2.0}))
        add("전 계좌 변동성 +5%p", lambda p: p.update({"vol_shift": 5.0}))
        add("물가상승률 +1%p", lambda p: p.update({"inflation": p["inflation"] + 1.0}))
        add(
            "인플레이션 쇼크 확률 2배",
            lambda p: p.update(
                {
                    "inflation_shock_probability": float(
                        p.get("inflation_shock_probability", INFLATION_SHOCK_ANNUAL_PROBABILITY)
                    )
                    * 2.0
                }
            ),
        )
        add("월 기본지출 +100만 원", lambda p: p.update({"monthly_expense": p["monthly_expense"] + 100}))
        add("기본생활비 +10%", lambda p: p.update({"monthly_expense": p["monthly_expense"] * 1.10}))
        add(
            "은퇴 3년 조기",
            lambda p: p.update(
                {"retire_age": max(int(p["current_age"]), int(p["retire_age"]) - 3)}
            ),
        )
        add("주택구입 자기자본 +1억", _increase_house_purchase_by_1eok)
        add("주택연금 5년 지연", _delay_home_pension_5y)

        sens_rows = []
        for idx, (label, temp_params) in enumerate(scenarios):
            temp_sim = FinancialSimulator(temp_params)
            pv = temp_sim.run_monte_carlo(
                n_simulations=sims,
                override_extra_margin=0,
                seed_offset=700 + idx * 17,
            )["pv"]
            ruin = temp_sim.ruin_probability(pv)
            sens_rows.append({
                "민감도 항목": label,
                "파산확률": ruin,
                "기준 대비 변화(%p)": ruin - base_ruin,
            })

        return pd.DataFrame(sens_rows)

    def run_scenario_comparison(
        self,
        sims=SCENARIO_COMPARISON_SIMULATIONS,
        search_sims=SCENARIO_COMPARISON_SEARCH_SIMULATIONS,
    ):
        rows = []
        current_name = self.scenario_name

        for idx, scenario_name in enumerate(ACCOUNT_SCENARIOS.keys()):
            temp_params = self.params.copy()
            temp_params["account_scenario"] = scenario_name
            temp_sim = FinancialSimulator(temp_params)
            result = temp_sim.run_hybrid_analysis(main_sims=sims, search_sims=search_sims)

            years = result["years"]
            retire_age = int(temp_params["retire_age"])
            retire_idx = years.index(retire_age) if retire_age in years else len(years) - 1
            post_assets = result["pv"][:, retire_idx:]
            retire_assets = np.maximum(result["pv"][:, retire_idx], 1.0)
            half_asset_rate = np.mean(np.min(post_assets, axis=1) <= retire_assets * 0.5) * 100

            rows.append({
                "시나리오": scenario_name + (" *" if scenario_name == current_name else ""),
                "파산확률": result["base_ruin"],
                "안전 여유자금(만원/월)": result["safe_extra"],
                "상하위30% 제외 평균 여유자금(만원/월)": result["trimmed_avg_extra"],
                "은퇴시점 중앙값(억)": np.median(result["pv"][:, retire_idx]) / 100000000.0,
                "은퇴시점 하위10%(억)": np.percentile(result["pv"][:, retire_idx], 10) / 100000000.0,
                "최종 중앙값(억)": np.median(result["pv"][:, -1]) / 100000000.0,
                "은퇴 후 반토막 경험률": half_asset_rate,
            })

        return pd.DataFrame(rows)


def _increase_house_purchase_by_1eok(params):
    df = params.get("lump_events", pd.DataFrame()).copy()
    if df.empty:
        params["lump_events"] = pd.DataFrame([
            {"나이": 45, "유형": "지출", "내용": "주택구입", "금액(만원)": 10000}
        ])
        return

    mask = df["내용"].astype(str).str.contains("주택", na=False) & (
        df["유형"].astype(str) == "지출"
    )
    if mask.any():
        df.loc[mask, "금액(만원)"] = (
            pd.to_numeric(df.loc[mask, "금액(만원)"], errors="coerce").fillna(0) + 10000
        )
    else:
        df.loc[len(df)] = {"나이": 45, "유형": "지출", "내용": "주택구입", "금액(만원)": 10000}
    params["lump_events"] = df


def _delay_home_pension_5y(params):
    df = params.get("recurring_events", pd.DataFrame()).copy()
    if df.empty:
        params["recurring_events"] = df
        return

    mask = df["내용"].astype(str).str.contains("주택연금", na=False)
    if mask.any():
        df.loc[mask, "시작나이"] = (
            pd.to_numeric(df.loc[mask, "시작나이"], errors="coerce").fillna(55).astype(int) + 5
        )
    params["recurring_events"] = df


def build_failure_diagnostics(result, retire_age):
    years = result["years"]
    pv = result["pv"]
    returns = result["returns"]
    shock_mask = result.get("shock_mask")
    account_pv = result.get("account_pv")
    quant_penalty = result.get("quant_penalty")
    withdrawals = result.get("withdrawals")
    return_floor_mask = result.get("return_floor_mask")

    ruin_mask = np.any(pv <= 0, axis=1)
    survive_mask = ~ruin_mask
    n_paths = pv.shape[0]
    fail_count = int(ruin_mask.sum())
    retire_idx = years.index(retire_age) if retire_age in years else 0
    seq_end = min(len(years), retire_idx + 10)

    if fail_count > 0:
        first_ruin_idx = np.argmax(pv[ruin_mask] <= 0, axis=1)
        ruin_ages = np.asarray(years)[first_ruin_idx]
        avg_ruin_age = float(np.mean(ruin_ages))
    else:
        avg_ruin_age = np.nan

    def median_or_nan(arr):
        arr = np.asarray(arr)
        if arr.size == 0:
            return np.nan
        return float(np.median(arr))

    failed_seq = (
        np.prod(1 + returns[ruin_mask, retire_idx:seq_end], axis=1) - 1
        if fail_count
        else np.asarray([])
    )
    survive_seq = (
        np.prod(1 + returns[survive_mask, retire_idx:seq_end], axis=1) - 1
        if survive_mask.any()
        else np.asarray([])
    )

    diag_rows = [
        {
            "항목": "전체 경로 수",
            "실패 경로": f"{fail_count:,}개",
            "생존 경로": f"{n_paths - fail_count:,}개",
            "해석": "총 시뮬레이션 경로 중 자산 0원 도달 여부",
        },
        {
            "항목": "평균 파산 나이",
            "실패 경로": "-" if pd.isna(avg_ruin_age) else f"{avg_ruin_age:.1f}세",
            "생존 경로": "-",
            "해석": "실패 경로가 대체로 언제 무너지는지",
        },
        {
            "항목": "은퇴시점 자산 중앙값",
            "실패 경로": format_won(median_or_nan(pv[ruin_mask, retire_idx])),
            "생존 경로": format_won(median_or_nan(pv[survive_mask, retire_idx])),
            "해석": "은퇴 전 누적 성과와 지출 이벤트의 종합 결과",
        },
        {
            "항목": "은퇴 직후 10년 누적수익률 중앙값",
            "실패 경로": format_pct(median_or_nan(failed_seq) * 100),
            "생존 경로": format_pct(median_or_nan(survive_seq) * 100),
            "해석": "시퀀스 리스크 확인용",
        },
    ]

    if shock_mask is not None:
        diag_rows.append({
            "항목": "인플레이션 쇼크 경험률",
            "실패 경로": format_pct(np.mean(np.any(shock_mask[ruin_mask], axis=1)) * 100 if fail_count else np.nan),
            "생존 경로": format_pct(np.mean(np.any(shock_mask[survive_mask], axis=1)) * 100 if survive_mask.any() else np.nan),
            "해석": "고물가·저수익률 충격 노출 차이",
        })

    if quant_penalty is not None:
        diag_rows.append({
            "항목": "국내퀀트 페널티 평균값 중앙값",
            "실패 경로": format_pct(median_or_nan(np.mean(quant_penalty[ruin_mask], axis=1)) * 100),
            "생존 경로": format_pct(median_or_nan(np.mean(quant_penalty[survive_mask], axis=1)) * 100),
            "해석": "국내퀀트 운용규모 증가에 따른 수익률 차감 효과",
        })

    if withdrawals is not None:
        pre_retire_withdrawals = withdrawals[:, : retire_idx + 1, :]
        pre_retire_withdrawal_total = np.sum(pre_retire_withdrawals, axis=(1, 2))
        diag_rows.append({
            "항목": "은퇴 전 누적 인출 중앙값",
            "실패 경로": format_won(median_or_nan(pre_retire_withdrawal_total[ruin_mask])),
            "생존 경로": format_won(median_or_nan(pre_retire_withdrawal_total[survive_mask])),
            "해석": "은퇴 전 지출·목돈 이벤트가 계좌를 얼마나 소진했는지",
        })

    if return_floor_mask is not None:
        pre_retire_floor = np.any(return_floor_mask[:, : retire_idx + 1, :], axis=(1, 2))
        diag_rows.append({
            "항목": "은퇴 전 수익률 하한선 경험률",
            "실패 경로": format_pct(np.mean(pre_retire_floor[ruin_mask]) * 100 if fail_count else np.nan),
            "생존 경로": format_pct(np.mean(pre_retire_floor[survive_mask]) * 100 if survive_mask.any() else np.nan),
            "해석": "수익률 분포가 -95% 하한에 걸린 극단 경로 비율입니다.",
        })

    account_rows = []
    if account_pv is not None:
        for idx, key in enumerate(ACCOUNT_NAMES):
            row = {
                "계좌": ACCOUNT_LABELS[key],
                "실패 경로 은퇴시점 중앙값": format_won(median_or_nan(account_pv[ruin_mask, retire_idx, idx])),
                "생존 경로 은퇴시점 중앙값": format_won(median_or_nan(account_pv[survive_mask, retire_idx, idx])),
            }
            if withdrawals is not None:
                account_pre_retire_withdrawal = np.sum(withdrawals[:, : retire_idx + 1, idx], axis=1)
                row["실패 경로 은퇴 전 누적인출"] = format_won(
                    median_or_nan(account_pre_retire_withdrawal[ruin_mask])
                )
                row["생존 경로 은퇴 전 누적인출"] = format_won(
                    median_or_nan(account_pre_retire_withdrawal[survive_mask])
                )
            if return_floor_mask is not None:
                account_pre_retire_floor = np.any(return_floor_mask[:, : retire_idx + 1, idx], axis=1)
                row["실패 경로 수익률하한 경험률"] = format_pct(
                    np.mean(account_pre_retire_floor[ruin_mask]) * 100 if fail_count else np.nan
                )
                row["생존 경로 수익률하한 경험률"] = format_pct(
                    np.mean(account_pre_retire_floor[survive_mask]) * 100 if survive_mask.any() else np.nan
                )
            account_rows.append(row)

    reasons = []
    if fail_count > 0 and survive_mask.any():
        failed_retire = median_or_nan(pv[ruin_mask, retire_idx])
        survive_retire = median_or_nan(pv[survive_mask, retire_idx])
        if np.isfinite(failed_retire) and np.isfinite(survive_retire) and failed_retire < survive_retire * 0.70:
            reasons.append("실패 경로는 은퇴시점 자산이 생존 경로보다 크게 낮습니다.")

        failed_seq_med = median_or_nan(failed_seq)
        survive_seq_med = median_or_nan(survive_seq)
        if np.isfinite(failed_seq_med) and np.isfinite(survive_seq_med) and failed_seq_med < survive_seq_med - 0.10:
            reasons.append("은퇴 직후 10년 수익률 격차가 커서 시퀀스 리스크 영향이 큽니다.")

        if shock_mask is not None:
            fail_shock = np.mean(np.any(shock_mask[ruin_mask], axis=1)) if fail_count else 0.0
            survive_shock = np.mean(np.any(shock_mask[survive_mask], axis=1)) if survive_mask.any() else 0.0
            if fail_shock > survive_shock + 0.10:
                reasons.append("실패 경로는 인플레이션 쇼크 노출률이 더 높습니다.")

        if withdrawals is not None:
            failed_pre_withdrawal = median_or_nan(np.sum(withdrawals[ruin_mask, : retire_idx + 1, :], axis=(1, 2)))
            survive_pre_withdrawal = median_or_nan(np.sum(withdrawals[survive_mask, : retire_idx + 1, :], axis=(1, 2)))
            if np.isfinite(failed_pre_withdrawal) and np.isfinite(survive_pre_withdrawal) and failed_pre_withdrawal > survive_pre_withdrawal * 1.25:
                reasons.append("실패 경로의 계좌 소진은 수익률만이 아니라 은퇴 전 목돈·생활비 인출 영향이 큽니다.")

        if return_floor_mask is not None:
            fail_floor = np.mean(np.any(return_floor_mask[ruin_mask, : retire_idx + 1, :], axis=(1, 2))) if fail_count else 0.0
            if fail_floor > 0.20:
                reasons.append("일부 실패 경로에는 -95% 수익률 하한에 걸린 극단 경로도 포함되어 있습니다.")

        if account_pv is not None and withdrawals is not None and fail_count > 0:
            depleted_accounts = []
            for idx, key in enumerate(ACCOUNT_NAMES):
                failed_account_retire = median_or_nan(account_pv[ruin_mask, retire_idx, idx])
                failed_account_withdrawal = median_or_nan(np.sum(withdrawals[ruin_mask, : retire_idx + 1, idx], axis=1))
                failed_account_floor_rate = (
                    np.mean(np.any(return_floor_mask[ruin_mask, : retire_idx + 1, idx], axis=1))
                    if return_floor_mask is not None
                    else 0.0
                )
                if (
                    np.isfinite(failed_account_retire)
                    and failed_account_retire <= 1.0
                    and np.isfinite(failed_account_withdrawal)
                    and failed_account_withdrawal > 0
                    and failed_account_floor_rate < 0.30
                ):
                    depleted_accounts.append(ACCOUNT_LABELS[key])
            if depleted_accounts:
                reasons.append(
                    f"실패 경로에서 {', '.join(depleted_accounts)} 0원은 주로 수익률 하락 자체보다 인출 순서와 지출 이벤트에 따른 계좌 소진으로 보는 것이 맞습니다."
                )

    if not reasons:
        reasons.append("특정 단일 원인보다 수익률 경로, 지출 이벤트, 인플레이션의 복합효과로 해석하는 편이 안전합니다.")

    return {
        "diagnostic_df": pd.DataFrame(diag_rows),
        "account_df": pd.DataFrame(account_rows),
        "reason_text": " ".join(reasons),
    }


def get_representative_path_index(result, anchor_age=None):
    """
    계좌별 추적표와 그래프에 사용할 단일 대표 경로를 선택합니다.

    V61-2에서는 각 나이마다 그 시점의 총자산 중앙값에 가장 가까운 경로를 새로 골랐습니다.
    그러면 55세, 60세, 70세 행이 서로 다른 시뮬레이션 경로가 되어 국내퀀트 금액이
    갑자기 줄었다가 다시 커지는 것처럼 보이는 문제가 생깁니다.

    V61-3에서는 은퇴시점 총자산 중앙값에 가장 가까운 단일 경로를 고정한 뒤,
    그 경로의 계좌별 잔고를 전 기간 추적합니다.
    """
    years = result["years"]
    total_pv = np.asarray(result.get("pv"), dtype=float)

    if total_pv.ndim != 2 or total_pv.shape[0] == 0:
        return 0

    if anchor_age is None:
        anchor_age = result.get("retire_age", years[-1])

    if anchor_age in years:
        anchor_idx = years.index(anchor_age)
    else:
        years_arr = np.asarray(years)
        anchor_idx = int(np.argmin(np.abs(years_arr - anchor_age)))

    anchor_assets = total_pv[:, anchor_idx]
    return int(np.argmin(np.abs(anchor_assets - np.median(anchor_assets))))


def build_account_allocation_table(result, ages):
    """
    계좌별 추적표는 대표 경로 1개가 아니라 각 계좌의 분포 통계로 표시합니다.

    V61-3의 대표경로 방식은 총자산 중앙값에 가까운 실제 경로 1개를 고정했기 때문에,
    해당 경로에서 국내퀀트만 부진하고 듀얼모멘텀만 강한 경우 국내퀀트가 비정상적으로
    빨리 사라지는 것처럼 보였습니다. V61-4에서는 계좌별 중앙값과 하위 10%를 직접 표시해
    전형적 계좌 흐름과 불리한 계좌 흐름을 분리합니다.
    """
    years = result["years"]
    account_pv = result.get("account_pv")
    total_pv = result.get("pv")
    if account_pv is None or total_pv is None:
        return pd.DataFrame()

    initial_account_pv = result.get("initial_account_pv")

    rows = []
    for age in ages:
        if age not in years:
            continue

        if age == years[0] and initial_account_pv is not None:
            account_median = np.asarray(initial_account_pv[0], dtype=float)
            account_p10 = account_median.copy()
            total_median = float(np.sum(account_median))
            row_label = f"{age}세 시작"
        else:
            idx = years.index(age)
            account_slice = np.asarray(account_pv[:, idx, :], dtype=float)
            account_median = np.median(account_slice, axis=0)
            account_p10 = np.percentile(account_slice, 10, axis=0)
            total_median = float(np.median(total_pv[:, idx]))
            row_label = f"{age}세 연말"

        account_median_sum = float(np.sum(account_median))
        row = {
            "나이": row_label,
            "총자산 중앙값": format_won(total_median),
            "계좌중앙값 합계": format_won(account_median_sum),
        }
        for account_idx, key in enumerate(ACCOUNT_NAMES):
            value = float(account_median[account_idx])
            p10_value = float(account_p10[account_idx])
            row[f"{ACCOUNT_LABELS[key]} 중앙값"] = format_won(value)
            row[f"{ACCOUNT_LABELS[key]} 하위10%"] = format_won(p10_value)
            row[f"{ACCOUNT_LABELS[key]} 비중"] = (
                f"{(value / account_median_sum * 100.0) if account_median_sum > 0 else 0:.1f}%"
            )
        rows.append(row)

    return pd.DataFrame(rows)


def build_account_cashflow_table(result, ages):
    """나이별 누적 이체액과 계좌별 누적 인출액 중앙값을 표시합니다."""
    years = result["years"]
    transfers = result.get("transfers")
    withdrawals = result.get("withdrawals")
    if transfers is None and withdrawals is None:
        return pd.DataFrame()

    rows = []
    for age in ages:
        if age not in years:
            continue
        idx = years.index(age)
        row = {"나이": f"{age}세까지 누적"}

        if transfers is not None:
            cumulative_transfer = np.sum(transfers[:, : idx + 1], axis=1)
            row["국내퀀트→연금저축+ISA 누적이체 중앙값"] = format_won(
                float(np.median(cumulative_transfer))
            )
            row["누적이체 하위10%"] = format_won(
                float(np.percentile(cumulative_transfer, 10))
            )

        if withdrawals is not None:
            cumulative_withdrawal = np.sum(withdrawals[:, : idx + 1, :], axis=1)
            total_withdrawal = np.sum(cumulative_withdrawal, axis=1)
            row["전체 누적인출 중앙값"] = format_won(float(np.median(total_withdrawal)))
            for account_idx, key in enumerate(ACCOUNT_NAMES):
                row[f"{ACCOUNT_LABELS[key]} 누적인출 중앙값"] = format_won(
                    float(np.median(cumulative_withdrawal[:, account_idx]))
                )

        rows.append(row)

    return pd.DataFrame(rows)
