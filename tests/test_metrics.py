"""
Hand-Verifiable Mathematical Unit Tests for Uniswap v3 Financial Metrics (`src/metrics.py`).
Per Section 5 of PROJECT_CONTEXT.md:
"Công thức: mỗi chỉ số có unit test bằng ví dụ số kiểm chứng được bằng tay."
"""
import numpy as np

from src.metrics import (
    compute_capital_efficiency,
    compute_hourly_fee_return,
    compute_impermanent_loss,
    compute_instantaneous_lvr,
    compute_liquidity_for_capital,
    compute_lp_and_hodl_values,
    compute_max_drawdown,
    compute_position_raw_liquidity,
    compute_uniswap_v2_il,
    compute_var_cvar,
)


def test_hand_calculated_concentrated_il_exact():
    """
    Hand-verified numerical example:
      Entry price P_0 = 100, Lower bound P_a = 64, Upper bound P_b = 144, Initial capital V_0 = 1100.
      Then:
        sqrt(P_0) = 10, sqrt(P_a) = 8, sqrt(P_b) = 12.
        denom = 2*10 - 8 - 100/12 = 12 - 25/3 = 11/3.
        Liquidity L = V_0 / (11/3) = 1100 * 3 / 11 = 300.0 (exact!).
      At P_1 = 121 (sqrt(P_1) = 11):
        V_LP(121)   = 1175.0 (exact!).
        V_HODL(121) = 1205.0 (exact!).
        IL_signed(121) = (1175 - 1205) / 1205 = -6 / 241.
    """
    p0, pa, pb, v0 = 100.0, 64.0, 144.0, 1100.0
    L = compute_liquidity_for_capital(v0=v0, p0=p0, pa=pa, pb=pb)
    assert np.isclose(L, 300.0, atol=1e-12)

    v_lp, v_hodl = compute_lp_and_hodl_values(price=121.0, p0=p0, pa=pa, pb=pb, v0=v0)
    assert np.isclose(v_lp, 1175.0, atol=1e-10)
    assert np.isclose(v_hodl, 1205.0, atol=1e-10)

    il_signed = compute_impermanent_loss(price=121.0, p0=p0, pa=pa, pb=pb, signed=True)
    il_abs = compute_impermanent_loss(price=121.0, p0=p0, pa=pa, pb=pb, signed=False)
    assert np.isclose(il_signed, -6.0 / 241.0, atol=1e-12)
    assert np.isclose(il_abs, 6.0 / 241.0, atol=1e-12)
    assert compute_impermanent_loss(price=100.0, p0=p0, pa=pa, pb=pb, signed=False) == 0.0


def test_concentrated_il_converges_to_uniswap_v2_on_wide_range():
    """
    When range [Pa, Pb] -> (0, inf), concentrated IL must converge to Uniswap v2 IL:
      For k = P_1 / P_0 = 4.0:
      IL_v2_signed(4.0) = 2 * sqrt(4) / (1 + 4) - 1 = -0.20 (20% loss).
    """
    il_v2 = compute_uniswap_v2_il(4.0, signed=False)
    assert np.isclose(il_v2, 0.20, atol=1e-12)

    il_v3_wide = compute_impermanent_loss(price=400.0, p0=100.0, pa=1e-12, pb=1e16, signed=False)
    assert np.isclose(il_v3_wide, 0.20, atol=1e-6)


def test_capital_efficiency_and_il_monotonicity_in_range_width():
    """
    Narrower range around P0 must yield strictly higher Capital Efficiency eta
    and strictly larger Impermanent Loss for any P != P0.
    For P_0 = 100, P_a = 64, P_b = 144:
      eta = (2 * 10) / (11 / 3) = 60 / 11 = 5.454545...
    """
    eta_std = compute_capital_efficiency(p0=100.0, pa=64.0, pb=144.0)
    assert np.isclose(eta_std, 60.0 / 11.0, atol=1e-12)

    eta_narrow = compute_capital_efficiency(p0=100.0, pa=81.0, pb=121.0)
    assert eta_narrow > eta_std

    il_std = compute_impermanent_loss(price=115.0, p0=100.0, pa=64.0, pb=144.0, signed=False)
    il_narrow = compute_impermanent_loss(price=115.0, p0=100.0, pa=81.0, pb=121.0, signed=False)
    assert il_narrow > il_std > 0.0


def test_hand_calculated_onchain_liquidity_share_fee_return():
    """
    Hand-verified numerical check for `compute_position_raw_liquidity` & `compute_hourly_fee_return`:
      Suppose P_0 = 100, P_a = 64, P_b = 144 => eta = 60 / 11.
      Let V_0 = $1,100, u0_usd = $1, u1_usd = $100, decimals0 = 6, decimals1 = 6:
        sqrt(u0 * u1) = 10, scale = 10^6.
        L_pos_raw = (1100 * (60 / 11)) / (2 * 10) * 10^6 = 6000 / 20 * 10^6 = 300 * 10^6 = 3e8 (exact!).
      If pool active liquidity L_pool_raw = 2.7e9 (so L_pos_raw / (L_pool_raw + L_pos_raw) = 3e8 / 3e9 = 0.10 = 10%),
      and pool fees in that hour are `feesUSD = $55.0`:
        Position fee earned = $55.0 * 0.10 = $5.50.
        Fee return fraction = $5.50 / $1,100 = 0.005 (0.5% exact!).
      When price = 150 > Pb (out-of-range), fee return must be 0.0.
    """
    l_pos_raw = compute_position_raw_liquidity(
        v0_usd=1100.0,
        p0=100.0,
        pa=64.0,
        pb=144.0,
        u0_usd=1.0,
        u1_usd=100.0,
        decimals0=6,
        decimals1=6,
    )
    assert np.isclose(l_pos_raw, 3.0e8, atol=1e-4)

    fee_in = compute_hourly_fee_return(
        price=105.0,
        pool_fees_usd=55.0,
        pool_tvl_usd=1_000_000.0,
        p0=100.0,
        pa=64.0,
        pb=144.0,
        pool_liquidity_raw=2.7e9,
        v0_usd=1100.0,
        u0_usd=1.0,
        u1_usd=100.0,
        decimals0=6,
        decimals1=6,
    )
    assert np.isclose(float(fee_in), 0.005, atol=1e-12)

    fee_out = compute_hourly_fee_return(
        price=150.0,
        pool_fees_usd=55.0,
        pool_tvl_usd=1_000_000.0,
        p0=100.0,
        pa=64.0,
        pb=144.0,
        pool_liquidity_raw=2.7e9,
        v0_usd=1100.0,
        u0_usd=1.0,
        u1_usd=100.0,
        decimals0=6,
        decimals1=6,
    )
    assert float(fee_out) == 0.0


def test_lvr_hand_calculation_and_out_of_range_zero():
    """
    Hand-verified LVR check:
      For P_0 = 100, P_a = 64, P_b = 144, V_0 = 1100 => L = 300.
      At P_t = 100 (sqrt(P_t) = 10) and sigma = 0.02 (2% hourly vol):
        LVR_dollar = 0.25 * L * sqrt(P_t) * sigma^2 = 0.25 * 300 * 10 * 0.0004 = 0.30.
        Normalized LVR = 0.30 / 1100 = 3 / 11000.
      When P_t = 150 > P_b (out-of-range), instantaneous LVR must be 0.0.
    """
    lvr_in = compute_instantaneous_lvr(price=100.0, sigma_hourly=0.02, p0=100.0, pa=64.0, pb=144.0, v0=1100.0)
    assert np.isclose(lvr_in, 0.30 / 1100.0, atol=1e-12)

    lvr_out = compute_instantaneous_lvr(price=150.0, sigma_hourly=0.02, p0=100.0, pa=64.0, pb=144.0, v0=1100.0)
    assert lvr_out == 0.0


def test_max_drawdown_and_var_cvar_hand_calculation():
    """
    Hand-calculated Max Drawdown:
      Wealth trajectory: [100, 120, 90, 110, 84, 130] => Max Drawdown = (120-84)/120 = 0.30.
    """
    wealth = [100.0, 120.0, 90.0, 110.0, 84.0, 130.0]
    assert np.isclose(compute_max_drawdown(wealth), 0.30, atol=1e-12)

    losses = np.arange(1.0, 101.0)
    var95, cvar95 = compute_var_cvar(losses, alpha=0.95)
    assert np.isclose(var95, np.quantile(losses, 0.95), atol=1e-12)
    assert cvar95 >= var95


def test_diebold_mariano_returns_nan_when_n_eff_below_10():
    """
    Verify that `diebold_mariano_test` returns `NaN` for `dm_stat` and `p_value`
    whenever the number of non-overlapping effective observations `n_eff < 10`.
    """
    from src.evaluation import diebold_mariano_test

    y_true = np.linspace(0.01, 0.05, 500)
    pred_m = y_true + 0.001
    pred_b = y_true + 0.005

    # For 500 hours and horizon_lags = 720 (30d), n_eff = 1 < 10 -> must return NaN
    res_underpowered = diebold_mariano_test(y_true, pred_m, pred_b, horizon_lags=720)
    assert res_underpowered["n_eff"] == 1
    assert np.isnan(res_underpowered["dm_stat"])
    assert np.isnan(res_underpowered["p_value"])

    # For 500 hours and horizon_lags = 24 (1d), n_eff = 20 >= 10 -> must return valid finite DM stat
    res_valid = diebold_mariano_test(y_true, pred_m, pred_b, horizon_lags=24)
    assert res_valid["n_eff"] == 20
    assert np.isfinite(res_valid["dm_stat"])
    assert np.isfinite(res_valid["p_value"])
