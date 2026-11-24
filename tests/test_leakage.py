"""
Strict Anti-Leakage Unit Tests (`tests/test_leakage.py`).
Verifies:
1. Perturbing future prices/volumes after t0 NEVER alters any feature `feat_*` at or before t0.
2. Purged Walk-Forward time-series split strictly enforces an embargo gap >= horizon_hours
   so training targets never overlap with validation or test periods.
"""
import numpy as np
import pandas as pd

from src.features import FEATURE_COLUMNS_TIME_SERIES, engineer_pool_features
from src.models.rq2_forecasting import purged_time_series_split, walk_forward_purged_splits


def _make_deterministic_merged_df(n_hours: int = 1500) -> pd.DataFrame:
    ts = pd.date_range("2024-12-01 01:00:00", periods=n_hours, freq="1h", tz="UTC").astype("datetime64[ns, UTC]")
    rng = np.random.default_rng(123)
    ret = rng.normal(0.0, 0.006, size=n_hours)
    prices = 3000.0 * np.exp(np.cumsum(ret))

    return pd.DataFrame(
        {
            "timestamp": ts,
            "period_start": ts - pd.Timedelta(hours=1),
            "cex_open_time": ts - pd.Timedelta(hours=1),
            "amm_price": prices,
            "amm_open": np.roll(prices, 1),
            "amm_close": prices,
            "amm_high": prices * 1.004,
            "amm_low": prices * 0.996,
            "token0Price": prices,
            "token1Price": 1.0 / prices,
            "open": np.roll(prices, 1),
            "high": prices * 1.004,
            "low": prices * 0.996,
            "close": prices,
            "cex_close": prices * 0.9998,
            "eth_usd_price": prices,
            "liquidity": np.full(n_hours, 1.5e19),
            "volumeUSD": np.full(n_hours, 12_000_000.0),
            "tvlUSD": np.full(n_hours, 250_000_000.0),
            "feesUSD": np.full(n_hours, 6_000.0),
            "txCount": np.full(n_hours, 300),
            "swap_flow_imbalance": rng.uniform(-0.5, 0.5, size=n_hours),
            "amm_cex_spread_rel": rng.normal(0.0, 0.0003, size=n_hours),
            "cex_realized_vol_1h": np.abs(ret) + 0.002,
            "cex_downside_vol_1h": np.where(ret < 0, np.abs(ret), 0.0),
            "cex_jump_count_1h": (np.abs(ret) > 0.015).astype("int64"),
            "stablecoin_deviation": np.full(n_hours, 0.0001),
            "pool_category": "volatile",
            "fee_tier_bps": 500,
            "token0_decimals": 6,
            "token1_decimals": 18,
            "use_cex_for_volatility": True,
        }
    )


def test_feature_causality_under_future_shock():
    """
    Perturbation Causality Test:
    Modify all observations strictly after index `t_cut = 300` by multiplying prices and volumes by 10x.
    Every single feature column in `FEATURE_COLUMNS_TIME_SERIES` at indices `0 .. t_cut` must remain
    100% bitwise identical to the unperturbed features!
    """
    merged_orig = _make_deterministic_merged_df(600)
    feat_orig = engineer_pool_features(merged_orig, default_range_width=0.10, gas_price_gwei=20.0)

    t_cut = 300
    merged_shocked = merged_orig.copy()
    shock_cols = [
        "amm_price",
        "amm_open",
        "amm_close",
        "amm_high",
        "amm_low",
        "token0Price",
        "close",
        "high",
        "low",
        "cex_close",
        "volumeUSD",
        "tvlUSD",
        "feesUSD",
    ]
    for col in shock_cols:
        merged_shocked.loc[t_cut + 1 :, col] = merged_shocked.loc[t_cut + 1 :, col] * 10.0

    feat_shocked = engineer_pool_features(merged_shocked, default_range_width=0.10, gas_price_gwei=20.0)

    for col in FEATURE_COLUMNS_TIME_SERIES:
        orig_slice = feat_orig.loc[:t_cut, col].to_numpy(dtype="float64")
        shock_slice = feat_shocked.loc[:t_cut, col].to_numpy(dtype="float64")
        assert np.allclose(orig_slice, shock_slice, atol=1e-12, equal_nan=True), (
            f"Look-ahead leakage detected in feature '{col}' at or before t_cut={t_cut}!"
        )


def test_purged_time_series_split_no_overlapping_labels():
    """
    Verify that for horizon H (e.g., 24h and 168h), the last training observation's forward label
    window `train_last_ts + H` finishes at or before `valid_first_ts`.
    """
    merged = _make_deterministic_merged_df(1500)
    for h_hours in [24, 168]:
        splits = purged_time_series_split(merged, horizon_hours=h_hours, train_ratio=0.60, valid_ratio=0.20)
        train_max_ts = splits["train"]["timestamp"].max()
        valid_min_ts = splits["valid"]["timestamp"].min()
        valid_max_ts = splits["valid"]["timestamp"].max()
        test_min_ts = splits["test"]["timestamp"].min()

        assert train_max_ts + pd.Timedelta(hours=h_hours) <= valid_min_ts
        assert valid_max_ts + pd.Timedelta(hours=h_hours) <= test_min_ts


def test_walk_forward_8_folds_strict_purging_and_contiguous_oos():
    """
    Verify that `walk_forward_purged_splits` generates 8 expanding walk-forward folds on a
    multi-year-sized dataset, enforces `purge >= horizon_hours` in EVERY fold, and produces
    contiguous out-of-sample test blocks without gaps or overlaps.
    """
    merged = _make_deterministic_merged_df(6000)
    folds = walk_forward_purged_splits(merged, horizon_hours=24, n_folds=8, min_train_ratio=0.45)
    assert len(folds) == 8

    prev_test_end = None
    prev_train_len = 0
    for f in folds:
        tr_max = f["train"]["timestamp"].max()
        val_min = f["valid"]["timestamp"].min()
        val_max = f["valid"]["timestamp"].max()
        te_min = f["test"]["timestamp"].min()
        te_max = f["test"]["timestamp"].max()

        assert tr_max + pd.Timedelta(hours=24) <= val_min
        assert val_max + pd.Timedelta(hours=24) <= te_min
        assert len(f["train"]) > prev_train_len
        prev_train_len = len(f["train"])

        if prev_test_end is not None:
            assert te_min == prev_test_end + pd.Timedelta(hours=1)
        prev_test_end = te_max


def test_correlated_pool_drift_removal_and_robust_volatility():
    """
    Verify that when `use_cex_for_volatility = False` and `pool_category = 'correlated'`,
    `engineer_pool_features` removes the deterministic staking drift and ignores corrupted
    `amm_high` / `amm_low` Parkinson spikes.
    """
    df = _make_deterministic_merged_df(400)
    # Pure deterministic staking yield drift of +0.01% per hour with tiny 0.001% noise
    rng = np.random.default_rng(7)
    log_p = np.cumsum(0.0001 + rng.normal(0.0, 0.00001, size=400))
    p = 1.15 * np.exp(log_p)
    df["amm_price"] = p
    df["pool_category"] = "correlated"
    df["use_cex_for_volatility"] = False
    # Corrupt amm_high / amm_low by +5% / -5% to verify rvol_1h_base ignores Parkinson high/low
    df["amm_high"] = p * 1.05
    df["amm_low"] = p * 0.95

    feat = engineer_pool_features(df, default_range_width=0.02, gas_price_gwei=20.0)
    # True detrended hourly vol is ~1e-5 (bounded below by mad floor 1.5e-5), NOT 0.0001 (drift) and NOT 0.05 (corrupted high/low)!
    assert feat["feat_rvol_1h"].iloc[200:].mean() < 5e-5
