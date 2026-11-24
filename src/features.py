"""
Feature Engineering and Target Construction for Uniswap v3 IL & LVR Analysis.
Strictly adheres to the zero look-ahead rule:
- All features `feat_*` at timestamp `t` depend ONLY on historical observations `tau <= t` (no `.bfill()`).
- All forward targets `target_*` measure outcomes over `(t, t + H]` for H in {24h (1d), 168h (7d), 720h (30d)}.
"""
from typing import Any, Dict, List, Tuple

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import pandas as pd

from src.metrics import (
    compute_capital_efficiency,
    compute_hourly_fee_return,
    compute_impermanent_loss,
    compute_instantaneous_lvr,
    compute_liquidity_for_capital,
)


FEATURE_COLUMNS_TIME_SERIES: List[str] = [
    "feat_ret_1h",
    "feat_ret_6h",
    "feat_ret_24h",
    "feat_ret_7d",
    "feat_rvol_1h",
    "feat_rvol_6h",
    "feat_rvol_24h",
    "feat_rvol_7d",
    "feat_downside_vol_24h",
    "feat_jump_intensity_24h",
    "feat_parkinson_vol_24h",
    "feat_volume_usd_log",
    "feat_volume_tvl_ratio_24h",
    "feat_tvl_usd_log",
    "feat_fee_apr_24h",
    "feat_swap_count_log",
    "feat_flow_imbalance_1h",
    "feat_flow_imbalance_24h",
    "feat_amm_cex_spread_abs",
    "feat_amm_cex_spread_std_24h",
    "feat_dist_to_lower_pct",
    "feat_dist_to_upper_pct",
    "feat_in_range_ratio_24h",
    "feat_gas_price_gwei",
    "feat_asset_corr_24h",
    "feat_stable_dev_24h",
]


def resolve_token_usd_prices(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Determine the USD price `(u0_usd, u1_usd)` of 1 human token0 and 1 human token1 at each row
    so that on-chain raw liquidity `L_pos_raw` can be computed in exact units.
    """
    cat = str(df["pool_category"].iloc[0])
    eth_usd = df["eth_usd_price"].to_numpy(dtype="float64")
    amm_p = df["amm_price"].to_numpy(dtype="float64")

    if cat == "volatile":
        # USDC/WETH: token0 = USDC (~$1), token1 = WETH (~$eth_usd)
        u0_usd = np.ones(len(df), dtype="float64")
        u1_usd = eth_usd
    elif cat == "correlated":
        # wstETH/WETH: token0 = wstETH (~amm_p * eth_usd), token1 = WETH (~eth_usd)
        u0_usd = amm_p * eth_usd
        u1_usd = eth_usd
    else:
        # USDC/USDT: token0 = USDC (~$1), token1 = USDT (~$1)
        u0_usd = np.ones(len(df), dtype="float64")
        u1_usd = np.ones(len(df), dtype="float64")
    return u0_usd, u1_usd


def engineer_pool_features(
    merged_df: pd.DataFrame,
    default_range_width: float,
    gas_price_gwei: float = 20.0,
) -> pd.DataFrame:
    """
    Create strictly causal (backward-looking) features at each hourly timestamp `t`.
    No future information beyond `t` (and no `.bfill()`) is ever accessed in any `feat_*` column.
    """
    df = merged_df.sort_values("timestamp").copy().reset_index(drop=True)

    p_amm = df["amm_price"].astype("float64")
    p_cex = df["cex_close"].astype("float64")
    use_cex_vol = bool(df["use_cex_for_volatility"].iloc[0]) if "use_cex_for_volatility" in df.columns else True

    # 1. Historical log returns (strictly backward: log(P_t / P_{t-k}))
    df["feat_ret_1h"] = np.log(p_amm / p_amm.shift(1)).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["feat_ret_6h"] = np.log(p_amm / p_amm.shift(6)).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["feat_ret_24h"] = np.log(p_amm / p_amm.shift(24)).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["feat_ret_7d"] = np.log(p_amm / p_amm.shift(168)).replace([np.inf, -np.inf], 0.0).fillna(0.0)

    # Pool intrahour Parkinson high-low volatility
    amm_h = df["amm_high"].astype("float64") if "amm_high" in df.columns else df["high"].astype("float64")
    amm_l = df["amm_low"].astype("float64") if "amm_low" in df.columns else df["low"].astype("float64")
    log_hl_amm = np.log((amm_h / amm_l.clip(lower=1e-18)).clip(lower=1.0))
    parkinson_amm_1h = np.sqrt((1.0 / (4.0 * np.log(2.0))) * (log_hl_amm ** 2))
    amm_rvol_1h = np.maximum(parkinson_amm_1h, df["feat_ret_1h"].abs())

    # 2. Realized Volatility over trailing windows (1h, 6h, 24h, 7d)
    # Use CEX volatility only when CEX reference pair prices the exact same volatile asset ratio (e.g. WETH/USDC).
    # For correlated pair wstETH/WETH and stable pair USDC/USDT (use_cex_for_volatility=False):
    #   - Separate deterministic staking drift (Lido daily staking yield ~3-4% APR on wstETH/ETH)
    #   - Use robust MAD-filtered close-to-close + Bipower Variation estimator (never Subgraph high/low Parkinson!)
    cat = str(df["pool_category"].iloc[0]) if "pool_category" in df.columns else "volatile"
    if use_cex_vol:
        rvol_1h_base = df["cex_realized_vol_1h"].astype("float64").fillna(amm_rvol_1h)
        down_1h = df["cex_downside_vol_1h"].astype("float64").fillna(0.0)
        jump_1h = df["cex_jump_count_1h"].astype("float64").fillna(0.0)
    else:
        raw_ret = df["feat_ret_1h"].astype("float64")
        # Remove deterministic staking yield drift on correlated LST/ETH pairs (strictly causal 168h rolling median)
        staking_drift_1h = raw_ret.rolling(168, min_periods=1).median() if cat == "correlated" else 0.0
        ret_detrended = raw_ret - staking_drift_1h

        # Causal rolling MAD scale to filter isolated oracle rebase steps / single-block tick outliers
        rolling_med = ret_detrended.rolling(168, min_periods=1).median()
        rolling_mad = (ret_detrended - rolling_med).abs().rolling(168, min_periods=1).median() * 1.4826
        init_mad = float(ret_detrended.iloc[: min(len(ret_detrended), 168)].abs().median() * 1.4826) if len(ret_detrended) > 0 else 2e-5
        mad_scale = rolling_mad.clip(lower=max(init_mad, 1.5e-5))

        ret_clean = ret_detrended.clip(lower=-3.5 * mad_scale, upper=3.5 * mad_scale)
        bv_1h = np.sqrt((np.pi / 2.0) * ret_clean.abs() * ret_clean.abs().shift(1).fillna(ret_clean.abs()))
        rvol_1h_base = 0.5 * (ret_clean.abs() + bv_1h)
        down_1h = np.where(ret_clean < 0.0, rvol_1h_base, 0.0)
        jump_1h = (ret_detrended.abs() > 3.5 * mad_scale).astype("float64")

    df["feat_rvol_1h"] = rvol_1h_base
    df["feat_rvol_6h"] = np.sqrt((rvol_1h_base ** 2).rolling(6, min_periods=1).mean()) * np.sqrt(6.0)
    df["feat_rvol_24h"] = np.sqrt((rvol_1h_base ** 2).rolling(24, min_periods=1).mean()) * np.sqrt(24.0)
    df["feat_rvol_7d"] = np.sqrt((rvol_1h_base ** 2).rolling(168, min_periods=1).mean()) * np.sqrt(168.0)

    # 3. Downside Volatility & Jump Intensity (trailing 24h)
    df["feat_downside_vol_24h"] = np.sqrt(pd.Series(down_1h ** 2).rolling(24, min_periods=1).mean()) * np.sqrt(24.0)
    df["feat_jump_intensity_24h"] = pd.Series(jump_1h).rolling(24, min_periods=1).sum()
    df["feat_parkinson_vol_24h"] = parkinson_amm_1h.rolling(24, min_periods=1).mean() * np.sqrt(24.0)

    # 4. Volume, TVL, Fee APR, Swap Count, Flow Imbalance
    vol_usd = df["volumeUSD"].astype("float64").clip(lower=0.0)
    tvl_usd = df["tvlUSD"].astype("float64").clip(lower=1.0)
    fees_usd = df["feesUSD"].astype("float64").clip(lower=0.0)

    df["feat_volume_usd_log"] = np.log1p(vol_usd)
    df["feat_tvl_usd_log"] = np.log1p(tvl_usd)
    df["feat_volume_tvl_ratio_24h"] = (vol_usd / tvl_usd).rolling(24, min_periods=1).mean()
    df["feat_fee_apr_24h"] = (fees_usd / tvl_usd).rolling(24, min_periods=1).sum() * 365.0
    df["feat_swap_count_log"] = np.log1p(df["txCount"].astype("float64").clip(lower=0.0))

    imbalance = df["swap_flow_imbalance"].astype("float64").fillna(0.0)
    df["feat_flow_imbalance_1h"] = imbalance
    df["feat_flow_imbalance_24h"] = imbalance.rolling(24, min_periods=1).mean()

    # 5. AMM-CEX Arbitrage Spread
    spread_rel = df["amm_cex_spread_rel"].astype("float64").fillna(0.0)
    df["feat_amm_cex_spread_abs"] = spread_rel.abs()
    df["feat_amm_cex_spread_std_24h"] = spread_rel.rolling(24, min_periods=1).std().fillna(0.0)

    # 6. Rolling Position Reference State (strictly causal: uses P_{t-24} or P_0 for first 24 rows, never bfill!)
    anchor_p = p_amm.shift(24).fillna(p_amm.iloc[0])
    pa_ref = anchor_p * (1.0 - default_range_width)
    pb_ref = anchor_p * (1.0 + default_range_width)
    df["feat_dist_to_lower_pct"] = (p_amm - pa_ref) / p_amm
    df["feat_dist_to_upper_pct"] = (pb_ref - p_amm) / p_amm
    in_range_now = ((p_amm >= pa_ref) & (p_amm <= pb_ref)).astype("float64")
    df["feat_in_range_ratio_24h"] = in_range_now.rolling(24, min_periods=1).mean()

    # 7. Gas Price (base config + congestion sensitivity to volume spikes, strictly <= t)
    vol_mean_48 = df["feat_volume_usd_log"].rolling(48, min_periods=1).mean()
    vol_std_48 = df["feat_volume_usd_log"].rolling(48, min_periods=1).std().replace(0.0, 1.0).fillna(1.0)
    vol_zscore = ((df["feat_volume_usd_log"] - vol_mean_48) / vol_std_48).clip(-1.5, 4.0)
    df["feat_gas_price_gwei"] = gas_price_gwei * (1.0 + 0.20 * np.maximum(vol_zscore, 0.0))

    # 8. Cross-Asset Correlation & Stablecoin / Peg Deviation (trailing 24h)
    cex_ret_1h = np.log(p_cex / p_cex.shift(1)).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["feat_asset_corr_24h"] = (
        df["feat_ret_1h"].rolling(24, min_periods=4).corr(cex_ret_1h).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    )
    df["feat_stable_dev_24h"] = df["stablecoin_deviation"].astype("float64").rolling(24, min_periods=1).max().fillna(0.0)

    return df


def attach_forward_targets(
    df: pd.DataFrame,
    range_width: float,
    horizons_hours: Dict[str, int],
    exceedance_threshold: float,
    v0_usd: float = 10000.0,
) -> pd.DataFrame:
    """
    Attach forward-looking targets for each horizon H in `horizons_hours` (e.g. 1d=24h, 7d=168h, 30d=720h)
    for a fresh LP position opened at time `t` with entry price `P_t` and symmetric range
    `[P_t * (1 - w), P_t * (1 + w)]`.
    Uses exact on-chain liquidity share for fee calculation.
    """
    out = df.copy()
    p = out["amm_price"].to_numpy(dtype="float64")
    sigma_1h = out["feat_rvol_1h"].to_numpy(dtype="float64")
    fees_usd = out["feesUSD"].to_numpy(dtype="float64")
    tvl_usd = out["tvlUSD"].to_numpy(dtype="float64")
    liq_raw = out["liquidity"].to_numpy(dtype="float64")
    u0_arr, u1_arr = resolve_token_usd_prices(out)
    dec0 = int(out["token0_decimals"].iloc[0]) if "token0_decimals" in out.columns else 18
    dec1 = int(out["token1_decimals"].iloc[0]) if "token1_decimals" in out.columns else 18
    n = len(out)

    l_unit = compute_liquidity_for_capital(v0=1.0, p0=1.0, pa=1.0 - range_width, pb=1.0 + range_width)
    eta = compute_capital_efficiency(p0=1.0, pa=1.0 - range_width, pb=1.0 + range_width)
    scale_dec = 10.0 ** (0.5 * (dec0 + dec1))
    l_pos_all = (v0_usd * eta) / (2.0 * np.sqrt(np.maximum(u0_arr * u1_arr, 1e-18))) * scale_dec
    sigma_sq = sigma_1h ** 2

    for label, h_steps in horizons_hours.items():
        il_horizon = np.full(n, np.nan, dtype="float64")
        lvr_horizon = np.full(n, np.nan, dtype="float64")
        fee_horizon = np.full(n, np.nan, dtype="float64")
        net_ret_horizon = np.full(n, np.nan, dtype="float64")
        out_of_range_prob = np.full(n, np.nan, dtype="float64")
        il_exceed_flag = np.full(n, np.nan, dtype="float64")

        m = n - h_steps
        if m > 0:
            p0_arr = p[:m]
            p_end_arr = p[h_steps:]
            il_vals = np.asarray(
                compute_impermanent_loss(
                    price=p_end_arr / p0_arr,
                    p0=1.0,
                    pa=1.0 - range_width,
                    pb=1.0 + range_width,
                    signed=False,
                ),
                dtype="float64",
            )
            il_horizon[:m] = il_vals
            il_exceed_flag[:m] = (il_vals >= exceedance_threshold).astype("float64")

            win_p = sliding_window_view(p[1:], window_shape=h_steps)
            win_sig2 = sliding_window_view(sigma_sq[1:], window_shape=h_steps)
            win_fees = sliding_window_view(fees_usd[1:], window_shape=h_steps)
            win_liq = sliding_window_view(liq_raw[1:], window_shape=h_steps)

            chunk_size = 4096
            for start_i in range(0, m, chunk_size):
                end_i = min(start_i + chunk_size, m)
                p0_col = p0_arr[start_i:end_i, None]
                pa_col = p0_col * (1.0 - range_width)
                pb_col = p0_col * (1.0 + range_width)

                sub_p = win_p[start_i:end_i]
                sub_sig2 = win_sig2[start_i:end_i]
                sub_fees = win_fees[start_i:end_i]
                sub_liq = win_liq[start_i:end_i]

                in_range = (sub_p >= pa_col) & (sub_p <= pb_col)
                out_of_range_prob[start_i:end_i] = np.mean(~in_range, axis=1)

                lvr_chunk = 0.25 * l_unit * np.sum(
                    np.where(in_range, np.sqrt(sub_p / p0_col) * sub_sig2, 0.0),
                    axis=1,
                )
                lvr_horizon[start_i:end_i] = lvr_chunk

                l_pos_col = l_pos_all[start_i:end_i, None]
                share_mat = np.where(sub_liq > 0.0, l_pos_col / (sub_liq + l_pos_col), 0.0)
                fee_chunk = np.sum(np.where(in_range, sub_fees * share_mat, 0.0), axis=1) / v0_usd
                fee_horizon[start_i:end_i] = fee_chunk
                net_ret_horizon[start_i:end_i] = fee_chunk - il_vals[start_i:end_i]

        out[f"target_il_{label}"] = il_horizon
        out[f"target_lvr_{label}"] = lvr_horizon
        out[f"target_fee_{label}"] = fee_horizon
        out[f"target_net_return_{label}"] = net_ret_horizon
        out[f"target_oor_ratio_{label}"] = out_of_range_prob
        out[f"target_il_exceed_{label}"] = il_exceed_flag

    return out


def assign_market_regimes(
    df: pd.DataFrame,
    train_end_idx: int,
    low_q: float = 0.33,
    high_q: float = 0.67,
) -> pd.DataFrame:
    """
    Classify each timestamp into 'Low-Vol', 'Normal-Vol', or 'High-Vol' market regime.
    Thresholds are fit STRICTLY on the training slice `df.iloc[24:train_end_idx]` to prevent data leakage.
    """
    out = df.copy()
    train_vol = out["feat_rvol_24h"].iloc[24 : max(train_end_idx, 48)].dropna()
    q_low = float(train_vol.quantile(low_q))
    q_high = float(train_vol.quantile(high_q))

    vol = out["feat_rvol_24h"]
    out["market_regime"] = np.where(
        vol < q_low,
        "Low-Vol",
        np.where(vol >= q_high, "High-Vol", "Normal-Vol"),
    )
    out["regime_q_low_threshold"] = q_low
    out["regime_q_high_threshold"] = q_high
    return out


def build_position_panel_dataset(
    featured_dfs: Dict[str, pd.DataFrame],
    range_widths_pct: List[float],
    horizon_hours: int = 24,
    stride_hours: int = 24,
    v0_usd: float = 10000.0,
) -> pd.DataFrame:
    """
    Build a cross-sectional & time-series Panel Dataset of LP positions across all pools
    and liquidity range widths `w in range_widths_pct` for RQ1 econometric regressions.
    Default `stride_hours = 24 == horizon_hours` guarantees non-overlapping 24h windows!
    """
    records: List[Dict[str, Any]] = []

    for pool_key, df in featured_dfs.items():
        p = df["amm_price"].to_numpy(dtype="float64")
        sigma_1h = df["feat_rvol_1h"].to_numpy(dtype="float64")
        fees_usd = df["feesUSD"].to_numpy(dtype="float64")
        tvl_usd = df["tvlUSD"].to_numpy(dtype="float64")
        liq_raw = df["liquidity"].to_numpy(dtype="float64")
        u0_arr, u1_arr = resolve_token_usd_prices(df)
        dec0 = int(df["token0_decimals"].iloc[0]) if "token0_decimals" in df.columns else 18
        dec1 = int(df["token1_decimals"].iloc[0]) if "token1_decimals" in df.columns else 18
        n = len(df)

        # Start after 168h warm-up so all 7d trailing features are fully populated
        for idx in range(168, n - horizon_hours, stride_hours):
            row = df.iloc[idx]
            p0 = float(p[idx])
            p_end = float(p[idx + horizon_hours])
            path_prices = p[idx + 1 : idx + horizon_hours + 1]
            path_sigmas = sigma_1h[idx + 1 : idx + horizon_hours + 1]
            path_fees = fees_usd[idx + 1 : idx + horizon_hours + 1]
            path_tvl = tvl_usd[idx + 1 : idx + horizon_hours + 1]
            path_liq = liq_raw[idx + 1 : idx + horizon_hours + 1]

            for w in range_widths_pct:
                pa = p0 * (1.0 - w)
                pb = p0 * (1.0 + w)
                il_abs = float(compute_impermanent_loss(p_end, p0=p0, pa=pa, pb=pb, signed=False))
                lvr_sum = float(np.sum(compute_instantaneous_lvr(path_prices, path_sigmas, p0=p0, pa=pa, pb=pb, v0=1.0)))
                fee_sum = float(
                    np.sum(
                        compute_hourly_fee_return(
                            price=path_prices,
                            pool_fees_usd=path_fees,
                            pool_tvl_usd=path_tvl,
                            p0=p0,
                            pa=pa,
                            pb=pb,
                            pool_liquidity_raw=path_liq,
                            v0_usd=v0_usd,
                            u0_usd=float(u0_arr[idx]),
                            u1_usd=float(u1_arr[idx]),
                            decimals0=dec0,
                            decimals1=dec1,
                        )
                    )
                )
                cap_eff = float(compute_capital_efficiency(p0=p0, pa=pa, pb=pb))
                oor_frac = float(np.mean((path_prices < pa) | (path_prices > pb)))

                path_il = compute_impermanent_loss(path_prices, p0=p0, pa=pa, pb=pb, signed=False)
                cvar_95 = float(np.quantile(path_il, 0.95))

                records.append(
                    {
                        "pool_key": pool_key,
                        "pool_category": row["pool_category"],
                        "fee_tier_bps": int(row["fee_tier_bps"]),
                        "timestamp": row["timestamp"],
                        "market_regime": row.get("market_regime", "Normal-Vol"),
                        "range_width_pct": float(w),
                        "capital_efficiency": cap_eff,
                        "feat_rvol_24h": float(row["feat_rvol_24h"]),
                        "feat_downside_vol_24h": float(row["feat_downside_vol_24h"]),
                        "feat_jump_intensity_24h": float(row["feat_jump_intensity_24h"]),
                        "feat_volume_tvl_ratio_24h": float(row["feat_volume_tvl_ratio_24h"]),
                        "feat_fee_apr_24h": float(row["feat_fee_apr_24h"]),
                        "feat_flow_imbalance_24h": float(row["feat_flow_imbalance_24h"]),
                        "feat_amm_cex_spread_abs": float(row["feat_amm_cex_spread_abs"]),
                        "feat_gas_price_gwei": float(row["feat_gas_price_gwei"]),
                        "il_abs": il_abs,
                        "lvr_cum": lvr_sum,
                        "fee_cum": fee_sum,
                        "net_return_vs_hodl": fee_sum - il_abs,
                        "out_of_range_fraction": oor_frac,
                        "position_cvar_95": cvar_95,
                    }
                )

    return pd.DataFrame(records)
