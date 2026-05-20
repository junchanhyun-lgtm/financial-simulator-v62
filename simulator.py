import numpy as np
import pandas as pd

from config import (
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
    MIN_TOTAL_ANNUAL_RETURN,
    QUANT_SIZE_PENALTY_TIERS,
    RANDOM_SEED,
    SCENARIO_COMPARISON_SEARCH_SIMULATIONS,
    SCENARIO_COMPARISON_SIMULATIONS,
    SCENARIO_OPTIONS,
    SENSITIVITY_SIMULATIONS,
    STANDARD_TARGET_RUIN_PROB,
    TRIMMED_AVERAGE_FINAL_ASSET_FLOOR_MANWON,
    TRIMMED_AVERAGE_LOWER_EXCLUSION_RATIO,
    TRIMMED_AVERAGE_UPPER_EXCLUSION_RATIO,
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
    def _quant_size_penalty(estimated_quant_assets_manwon):
        """국내퀀트 추정 운용금액 기준 구간형 수익률 차감률을 반환합니다."""
        estimated_quant_assets_manwon = np.asarray(estimated_quant_assets_manwon, dtype=float)
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
    def _initial_quant_share():
        initial_total = (
            INITIAL_QUANT_ASSET_MANWON
            + INITIAL_DUAL_MOMENTUM_ASSET_MANWON
            + INITIAL_VOO_ASSET_MANWON
        )
        if initial_total <= 0:
            return 0.0
        return INITIAL_QUANT_ASSET_MANWON / initial_total

    @staticmethod
    def _portfolio_transition_ratio_and_quant_share(
        current_asset_manwon,
        current_age,
        retire_age,
        age,
        use_portfolio_transition,
    ):
        """
        V62-1 호환용 함수입니다.

        과거 V60-7에서는 연 3,800만 원 계좌이동을 은퇴 전 포트폴리오 전환으로 환산했습니다.
        V62-1에서는 해당 가정을 제거하고, 통합자산 모델 안에서는 국내퀀트 시작비중만
        운용규모 페널티 추정에 사용합니다.
        """
        quant_share = FinancialSimulator._initial_quant_share()
        transition_ratio = 1.0 if age >= retire_age else 0.0
        return transition_ratio, quant_share

    def _build_return_assumption_paths(self, years):
        retire_age = self.params["retire_age"]
        ret_pre = self.params["expected_return_pre"] / 100.0
        ret_post = self.params["expected_return_post"] / 100.0
        v_pre = self.params["vol_pre"] / 100.0
        v_post = self.params["vol_post"] / 100.0

        mu_base = np.zeros(len(years))
        vol_base = np.zeros(len(years))
        quant_share_base = np.full(len(years), self._initial_quant_share(), dtype=float)

        for t, age in enumerate(years):
            if age < retire_age:
                mu_base[t] = ret_pre
                vol_base[t] = v_pre
            else:
                mu_base[t] = ret_post
                vol_base[t] = v_post

        return mu_base, vol_base, quant_share_base

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

    def run_monte_carlo(self, n_simulations=5000, override_extra_margin=0, seed_offset=0):
        current_age = self.params["current_age"]
        death_age = self.params["death_age"]
        retire_age = self.params["retire_age"]
        current_asset_manwon = self.params["current_asset"]
        current_asset = current_asset_manwon * 10000.0
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
        friction_cost = self.params["tax_fee_rate"] / 100.0

        use_fat_tail = self.params.get("use_fat_tail", False)
        use_inflation_shock = self.params.get("use_inflation_shock", False)
        use_flex_spending = self.params.get("use_flex_spending", False)
        dwz_mode = self.params.get("dwz_mode", False)

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

        event_arrays = self._build_event_arrays(years)

        mu_base, vol_base, quant_share_base = self._build_return_assumption_paths(years=years)
        mu_matrix = np.tile(mu_base, (n_simulations, 1))
        vol_matrix = np.tile(vol_base, (n_simulations, 1))

        if use_inflation_shock:
            mu_matrix[shock_mask] -= INFLATION_SHOCK_RETURN_PENALTY
            vol_matrix[shock_mask] *= INFLATION_SHOCK_VOL_MULTIPLIER

        if use_fat_tail:
            fat_tail_scale = np.sqrt(FAT_TAIL_DF / (FAT_TAIL_DF - 2))
            z_matrix = rng.standard_t(df=FAT_TAIL_DF, size=(n_simulations, simulation_years)) / fat_tail_scale
        else:
            z_matrix = rng.normal(loc=0.0, scale=1.0, size=(n_simulations, simulation_years))

        temp_returns = z_matrix * vol_matrix + mu_matrix - friction_cost

        sim_returns = np.zeros_like(temp_returns)
        sim_returns[:, 0] = temp_returns[:, 0]
        for t in range(1, simulation_years):
            excess_prev = sim_returns[:, t - 1] - mu_matrix[:, t - 1]
            sim_returns[:, t] = temp_returns[:, t] - (MEAN_REVERSION_STRENGTH * excess_prev)

        return_floor_mask = sim_returns < MIN_TOTAL_ANNUAL_RETURN
        sim_returns = np.maximum(sim_returns, MIN_TOTAL_ANNUAL_RETURN)

        market_index_matrix = np.cumprod(1 + sim_returns, axis=1) * 100.0
        high_water_mark_matrix = np.maximum.accumulate(market_index_matrix, axis=1)
        market_drawdown_matrix = (high_water_mark_matrix - market_index_matrix) / high_water_mark_matrix

        sim_assets_pv = np.zeros((n_simulations, simulation_years))
        sim_assets_nom = np.zeros((n_simulations, simulation_years))
        quant_penalty_matrix = np.zeros((n_simulations, simulation_years))
        spending_pv_matrix = np.zeros((n_simulations, simulation_years))
        net_cashflow_pv_matrix = np.zeros((n_simulations, simulation_years))
        withdrawal_pv_matrix = np.zeros((n_simulations, simulation_years))

        current_assets = np.full(n_simulations, current_asset)

        for t, age in enumerate(years):
            df_factor = discount_factors[:, t]

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
            spending_pv_matrix[:, t] = target_lifestyle_annual_pv

            total_income_annual = current_nom_inc + extra_inc
            nominal_actual_spending = (target_lifestyle_annual_pv * df_factor) + extra_exp
            net_cashflow = total_income_annual - nominal_actual_spending + nom_lump
            net_cashflow_pv_matrix[:, t] = net_cashflow / df_factor
            withdrawal_pv_matrix[:, t] = np.maximum(-net_cashflow, 0.0) / df_factor

            estimated_quant_assets_manwon = (current_assets / 10000.0) * quant_share_base[t]
            scale_penalty = self._quant_size_penalty(estimated_quant_assets_manwon)
            quant_penalty_matrix[:, t] = scale_penalty
            adj_return = sim_returns[:, t] - scale_penalty
            adj_return = np.maximum(adj_return, MIN_TOTAL_ANNUAL_RETURN)

            gain_on_base = current_assets * adj_return
            gain_on_cashflow = net_cashflow * (adj_return / 2.0)

            current_assets = current_assets + gain_on_base + net_cashflow + gain_on_cashflow
            current_assets = np.maximum(current_assets, 0.0)

            sim_assets_nom[:, t] = current_assets
            sim_assets_pv[:, t] = current_assets / df_factor

        return {
            "years": years,
            "pv": sim_assets_pv,
            "nom": sim_assets_nom,
            "returns": sim_returns,
            "shock_mask": shock_mask,
            "inflation_matrix": inflation_matrix,
            "quant_penalty": quant_penalty_matrix,
            "spending_pv": spending_pv_matrix,
            "net_cashflow_pv": net_cashflow_pv_matrix,
            "withdrawal_pv": withdrawal_pv_matrix,
            "return_floor_mask": return_floor_mask,
            "market_index": market_index_matrix,
        }

    @staticmethod
    def ruin_probability(sim_assets_pv):
        sim_assets_pv = np.asarray(sim_assets_pv, dtype=float)
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
            incs_set.update([
                int(safe_extra * 0.5),
                safe_extra,
                safe_extra + 50,
                safe_extra + 150,
                safe_extra + 300,
            ])
        else:
            incs_set.update([50, 100, 200, 300])

        stress_rows = []
        for inc in sorted(list(incs_set)):
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

        add("전구간 기대수익률 -2%p", lambda p: p.update({
            "expected_return_pre": p["expected_return_pre"] - 2.0,
            "expected_return_post": p["expected_return_post"] - 2.0,
        }))
        add("전구간 변동성 +5%p", lambda p: p.update({
            "vol_pre": p["vol_pre"] + 5.0,
            "vol_post": p["vol_post"] + 5.0,
        }))
        add("물가상승률 +1%p", lambda p: p.update({"inflation": p["inflation"] + 1.0}))
        add(
            "인플레이션 쇼크 확률 2배",
            lambda p: p.update({
                "inflation_shock_probability": float(
                    p.get("inflation_shock_probability", INFLATION_SHOCK_ANNUAL_PROBABILITY)
                ) * 2.0
            }),
        )
        add("월 기본지출 +100만 원", lambda p: p.update({"monthly_expense": p["monthly_expense"] + 100}))
        add("기본생활비 +10%", lambda p: p.update({"monthly_expense": p["monthly_expense"] * 1.10}))
        add("은퇴 3년 조기", lambda p: p.update({
            "retire_age": max(int(p["current_age"]), int(p["retire_age"]) - 3)
        }))
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
        current_values = (
            float(self.params.get("expected_return_pre", 0.0)),
            float(self.params.get("vol_pre", 0.0)),
            float(self.params.get("expected_return_post", 0.0)),
            float(self.params.get("vol_post", 0.0)),
        )

        for scenario_name, scenario_values in SCENARIO_OPTIONS.items():
            temp_params = self.params.copy()
            (
                temp_params["expected_return_pre"],
                temp_params["vol_pre"],
                temp_params["expected_return_post"],
                temp_params["vol_post"],
            ) = scenario_values
            temp_sim = FinancialSimulator(temp_params)
            result = temp_sim.run_hybrid_analysis(main_sims=sims, search_sims=search_sims)

            years = result["years"]
            retire_age = int(temp_params["retire_age"])
            retire_idx = years.index(retire_age) if retire_age in years else len(years) - 1
            post_assets = result["pv"][:, retire_idx:]
            retire_assets = np.maximum(result["pv"][:, retire_idx], 1.0)
            half_asset_rate = np.mean(np.min(post_assets, axis=1) <= retire_assets * 0.5) * 100
            is_current = tuple(float(x) for x in scenario_values) == current_values

            rows.append({
                "시나리오": scenario_name + (" *" if is_current else ""),
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
    pv = np.asarray(result["pv"], dtype=float)
    returns = np.asarray(result["returns"], dtype=float)
    shock_mask = result.get("shock_mask")
    quant_penalty = result.get("quant_penalty")
    withdrawal_pv = result.get("withdrawal_pv")
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
            "해석": "통합자산 중 국내퀀트 추정비중에 따른 수익률 차감 효과",
        })

    if withdrawal_pv is not None:
        pre_retire_withdrawal_total = np.sum(withdrawal_pv[:, : retire_idx + 1], axis=1)
        diag_rows.append({
            "항목": "은퇴 전 누적 순인출 중앙값",
            "실패 경로": format_won(median_or_nan(pre_retire_withdrawal_total[ruin_mask])),
            "생존 경로": format_won(median_or_nan(pre_retire_withdrawal_total[survive_mask])),
            "해석": "은퇴 전 지출·목돈 이벤트가 총자산을 얼마나 소진했는지",
        })

    if return_floor_mask is not None:
        pre_retire_floor = np.any(return_floor_mask[:, : retire_idx + 1], axis=1)
        diag_rows.append({
            "항목": "은퇴 전 수익률 하한선 경험률",
            "실패 경로": format_pct(np.mean(pre_retire_floor[ruin_mask]) * 100 if fail_count else np.nan),
            "생존 경로": format_pct(np.mean(pre_retire_floor[survive_mask]) * 100 if survive_mask.any() else np.nan),
            "해석": f"연간수익률 {MIN_TOTAL_ANNUAL_RETURN * 100:.0f}% 하한에 걸린 극단 경로 비율",
        })

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

        if withdrawal_pv is not None:
            failed_pre_withdrawal = median_or_nan(np.sum(withdrawal_pv[ruin_mask, : retire_idx + 1], axis=1))
            survive_pre_withdrawal = median_or_nan(np.sum(withdrawal_pv[survive_mask, : retire_idx + 1], axis=1))
            if np.isfinite(failed_pre_withdrawal) and np.isfinite(survive_pre_withdrawal) and failed_pre_withdrawal > survive_pre_withdrawal * 1.25:
                reasons.append("실패 경로는 수익률만이 아니라 은퇴 전 목돈·생활비 순인출 영향도 큽니다.")

        if return_floor_mask is not None:
            fail_floor = np.mean(np.any(return_floor_mask[ruin_mask, : retire_idx + 1], axis=1)) if fail_count else 0.0
            if fail_floor > 0.20:
                reasons.append("일부 실패 경로에는 극단적 연간손실 하한에 걸린 경로도 포함되어 있습니다.")

    if not reasons:
        reasons.append("특정 단일 원인보다 수익률 경로, 지출 이벤트, 인플레이션의 복합효과로 해석하는 편이 안전합니다.")

    return {
        "diagnostic_df": pd.DataFrame(diag_rows),
        "reason_text": " ".join(reasons),
    }
