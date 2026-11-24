"""
Unit Tests for the RQ3 Strategy Backtester (`src/backtest/engine.py`),
including look-ahead perturbation test on backtest trajectories.
"""
import numpy as np
import pandas as pd

from src.backtest.engine import run_single_strategy_backtest


def _make_synthetic_test_predictions(n_hours: int = 400) -> pd.DataFrame:
    ts = pd.date_range("2025-01-01 00:00:00", periods=n_hours, freq="1h", tz="UTC")
    t_grid = np.linspace(0.0, 4.0 * np.pi, n_hours)
    prices = 3000.0 * (1.0 + 0.14 * np.sin(t_grid) + 0.05 * (t_grid / (4.0 * np.pi)))

    return pd.DataFrame(
        {
            "timestamp": ts,
            "pool_category": "volatile",
            "amm_price": prices,
            "cex_close": prices,
            "eth_usd_price": prices,
            "liquidity": np.full(n_hours, 1.8e19),
            "feesUSD": np.full(n_hours, 12_000.0),
            "tvlUSD": np.full(n_hours, 350_000_000.0),
            "token0_decimals": 6,
            "token1_decimals": 18,
            "feat_rvol_1h": np.full(n_hours, 0.006),
            "feat_rvol_24h": np.full(n_hours, 0.028),
            "feat_gas_price_gwei": np.full(n_hours, 20.0),
            "market_regime": "Normal-Vol",
            "y_true_il": np.full(n_hours, 0.008),
            "baseline_pred_il": np.full(n_hours, 0.007),
            "ml_pred_il": np.full(n_hours, 0.0075),
            "ml_q_50_il": np.full(n_hours, 0.006),
            "ml_q_90_il": np.where(np.cos(t_grid) < -0.5, 0.025, 0.009),
            "ml_q_95_il": np.where(np.cos(t_grid) < -0.5, 0.032, 0.012),
            "ml_prob_exceed": np.where(np.cos(t_grid) < -0.5, 0.65, 0.15),
        }
    )


def test_static_lp_zero_rebalance_and_gas():
    """Static LP must never rebalance and must incur zero rebalance gas/slippage."""
    df_test = _make_synthetic_test_predictions()
    summary, traj = run_single_strategy_backtest(
        df_test,
        strategy_name="Static_LP",
        base_width=0.10,
        initial_capital_usd=10000.0,
    )
    assert summary["rebalance_count"] == 0
    assert summary["tx_cost_gas_slippage_pct"] == 0.0
    assert np.isclose(
        summary["hedged_net_return_pct"],
        summary["cum_fees_pct"] - summary["cum_lvr_bench_pct"],
        atol=1e-9,
    )
    assert len(traj) == len(df_test)


def test_signal_strategy_respects_gas_cost_threshold():
    """
    When gas price is astronomically high (e.g. 50,000 Gwei), `Signal_Net_Utility`
    must refuse to rebalance because expected benefit < safety_margin * tx_cost.
    """
    df_test = _make_synthetic_test_predictions()
    df_high_gas = df_test.copy()
    df_high_gas["feat_gas_price_gwei"] = 50_000.0

    val_thresh = {"q90_p25": 0.008, "q90_median": 0.010, "q90_p75": 0.020, "prob_exceed_p75": 0.50}

    summary_normal, _ = run_single_strategy_backtest(
        df_test,
        strategy_name="Signal_Net_Utility",
        base_width=0.08,
        val_thresholds=val_thresh,
        initial_capital_usd=10000.0,
    )
    summary_extreme_gas, _ = run_single_strategy_backtest(
        df_high_gas,
        strategy_name="Signal_Net_Utility",
        base_width=0.08,
        val_thresholds=val_thresh,
        initial_capital_usd=10000.0,
    )

    assert summary_extreme_gas["rebalance_count"] == 0
    assert summary_normal["rebalance_count"] >= summary_extreme_gas["rebalance_count"]


def test_backtest_trajectory_zero_future_leakage():
    """
    Anti-leakage test for RQ3 backtest:
    Perturbing future prices and predictions after `t_cut = 200` must NEVER alter
    any decision or portfolio wealth at `t <= t_cut`.
    """
    df_orig = _make_synthetic_test_predictions(400)
    val_thresh = {"q90_p25": 0.008, "q90_median": 0.010, "q90_p75": 0.020, "prob_exceed_p75": 0.50}

    _, traj_orig = run_single_strategy_backtest(
        df_orig,
        strategy_name="Signal_Net_Utility",
        base_width=0.10,
        val_thresholds=val_thresh,
    )

    t_cut = 200
    df_shock = df_orig.copy()
    df_shock.loc[t_cut + 1 :, "amm_price"] *= 5.0
    df_shock.loc[t_cut + 1 :, "ml_q_90_il"] *= 20.0

    _, traj_shock = run_single_strategy_backtest(
        df_shock,
        strategy_name="Signal_Net_Utility",
        base_width=0.10,
        val_thresholds=val_thresh,
    )

    assert np.allclose(
        traj_orig.loc[:t_cut, "net_wealth_usd"].to_numpy(),
        traj_shock.loc[:t_cut, "net_wealth_usd"].to_numpy(),
        atol=1e-12,
    )
    assert (traj_orig.loc[:t_cut, "rebalanced"] == traj_shock.loc[:t_cut, "rebalanced"]).all()
