"""
Backward Time-Series Merger for Uniswap v3 PoolHourData and Binance CEX Klines.
Strictly enforces `merge_asof(..., direction='backward')` on completed candle timestamps.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from src.config_loader import PROJECT_ROOT

logger = logging.getLogger("merge")


def merge_pool_and_cex_data(
    pool_df: pd.DataFrame,
    cex_df: pd.DataFrame,
    pool_key: str,
    pool_cfg: Dict[str, Any],
    usdc_cex_df: pd.DataFrame | None = None,
    eth_cex_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Merge normalized PoolHourData and CEX 1h data using `pd.merge_asof(..., direction='backward')`.
    Both inputs must have `timestamp` in UTC representing the END of the 1-hour interval
    so that at time T, only candles completed at or before T are matched.
    """
    if pool_df.empty or cex_df.empty:
        raise ValueError(f"Cannot merge empty DataFrames for pool {pool_key}")

    left = pool_df.copy()
    right = cex_df.copy()

    left["timestamp"] = pd.to_datetime(left["timestamp"], utc=True).astype("datetime64[ns, UTC]")
    right["timestamp"] = pd.to_datetime(right["timestamp"], utc=True).astype("datetime64[ns, UTC]")

    left = left.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    right = right.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    # Backward merge_asof: takes the latest CEX candle whose completion timestamp <= pool timestamp
    merged = pd.merge_asof(
        left,
        right,
        on="timestamp",
        direction="backward",
        tolerance=pd.Timedelta(hours=1),
    )

    # Optional stablecoin reference (USDCUSDT) for depeg / stablecoin deviation tracking
    if usdc_cex_df is not None and not usdc_cex_df.empty:
        usdc = usdc_cex_df[["timestamp", "cex_close"]].rename(columns={"cex_close": "usdc_usdt_close"}).copy()
        usdc["timestamp"] = pd.to_datetime(usdc["timestamp"], utc=True).astype("datetime64[ns, UTC]")
        usdc = usdc.sort_values("timestamp").drop_duplicates(subset=["timestamp"])
        merged = pd.merge_asof(
            merged,
            usdc,
            on="timestamp",
            direction="backward",
            tolerance=pd.Timedelta(hours=2),
        )
        merged["stablecoin_deviation"] = (merged["usdc_usdt_close"] - 1.0).abs().fillna(0.0)
    else:
        merged["usdc_usdt_close"] = 1.0
        merged["stablecoin_deviation"] = 0.0

    # Always attach ETH USD reference price (`eth_usd_price`) for gas & liquidity USD conversion
    if eth_cex_df is not None and not eth_cex_df.empty:
        eth_ref = eth_cex_df[["timestamp", "cex_close"]].rename(columns={"cex_close": "eth_usd_price"}).copy()
        eth_ref["timestamp"] = pd.to_datetime(eth_ref["timestamp"], utc=True).astype("datetime64[ns, UTC]")
        eth_ref = eth_ref.sort_values("timestamp").drop_duplicates(subset=["timestamp"])
        merged = pd.merge_asof(
            merged,
            eth_ref,
            on="timestamp",
            direction="backward",
            tolerance=pd.Timedelta(hours=2),
        )
    else:
        merged["eth_usd_price"] = np.where(merged["cex_close"] > 100.0, merged["cex_close"], 2800.0)

    # Drop any initial rows before CEX coverage starts
    merged = merged.dropna(subset=["cex_close", "close"]).reset_index(drop=True)

    # Add static pool metadata columns from configs/pools.yaml
    merged["pool_key"] = pool_key
    merged["pool_category"] = pool_cfg["category"]
    merged["fee_tier_bps"] = int(pool_cfg["fee_tier_bps"])
    merged["fee_rate"] = float(pool_cfg["fee_rate"])
    merged["tick_spacing"] = int(pool_cfg["tick_spacing"])
    merged["token0_decimals"] = int(pool_cfg.get("token0", {}).get("decimals", 18))
    merged["token1_decimals"] = int(pool_cfg.get("token1", {}).get("decimals", 18))
    merged["use_cex_for_volatility"] = bool(pool_cfg.get("use_cex_for_volatility", True))

    price_field = pool_cfg.get("price_field", "token0Price")
    if price_field == "token1Price":
        # e.g. wstETH/WETH where token0 = wstETH, token1 = WETH, and we track WETH per 1 wstETH (~1.18)
        merged["amm_price"] = merged["token1Price"]
        merged["amm_open"] = 1.0 / merged["open"].clip(lower=1e-12)
        merged["amm_close"] = 1.0 / merged["close"].clip(lower=1e-12)
        merged["amm_high"] = 1.0 / merged["low"].clip(lower=1e-12)
        merged["amm_low"] = 1.0 / merged["high"].clip(lower=1e-12)
        # For correlated LST/ETH pair without a direct Binance spot pair, measure basis relative to
        # strictly causal trailing 24h median exchange rate
        trailing_ref = merged["amm_price"].rolling(24, min_periods=1).median()
        merged["amm_cex_spread_rel"] = (merged["amm_price"] - trailing_ref) / trailing_ref
    else:
        # e.g. USDC/WETH (token0Price = USDC per WETH) or USDC/USDT (token0Price = USDC per USDT)
        merged["amm_price"] = merged["token0Price"]
        merged["amm_open"] = merged["open"]
        merged["amm_close"] = merged["close"]
        merged["amm_high"] = merged["high"]
        merged["amm_low"] = merged["low"]
        merged["amm_cex_spread_rel"] = (merged["amm_price"] - merged["cex_close"]) / merged["cex_close"]

    return merged.sort_values("timestamp").reset_index(drop=True)


def save_merged_dataset(
    merged_df: pd.DataFrame,
    pool_key: str,
    pool_cfg: Dict[str, Any],
    data_sources_info: Dict[str, Any],
    processed_dir: Path | None = None,
) -> Tuple[Path, Path]:
    """
    Export `data/processed/merged_<pool_key>.parquet` and accompanying metadata JSON.
    """
    out_dir = processed_dir or (PROJECT_ROOT / "data" / "processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = out_dir / f"merged_{pool_key}.parquet"
    meta_path = out_dir / f"merged_{pool_key}_metadata.json"

    try:
        merged_df.to_parquet(parquet_path, index=False, engine="pyarrow")
    except Exception as exc:
        logger.warning(
            f"Could not save {parquet_path.name} with pyarrow ({exc}). "
            "Attempting fallback to default parquet engine or continuing with CSV."
        )
        try:
            merged_df.to_parquet(parquet_path, index=False)
        except Exception as fallback_exc:
            logger.warning(f"Parquet export skipped ({fallback_exc}). Proceeding with CSV export.")

    csv_path = out_dir / f"merged_{pool_key}.csv"
    merged_df.to_csv(csv_path, index=False)

    metadata = {
        "pool_key": pool_key,
        "pool_name": pool_cfg["name"],
        "pool_address": pool_cfg["address"],
        "category": pool_cfg["category"],
        "fee_tier_bps": pool_cfg["fee_tier_bps"],
        "fee_rate": pool_cfg["fee_rate"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_timestamp_utc": str(merged_df["timestamp"].min()),
        "end_timestamp_utc": str(merged_df["timestamp"].max()),
        "n_rows": int(len(merged_df)),
        "raw_subgraph_hours": int(merged_df["raw_subgraph_hours"].iloc[0]) if "raw_subgraph_hours" in merged_df.columns else int(len(merged_df)),
        "unseeded_low_tvl_hours_trimmed": int(merged_df["unseeded_low_tvl_hours_trimmed"].iloc[0]) if "unseeded_low_tvl_hours_trimmed" in merged_df.columns else 0,
        "ffill_zero_tx_hours": int(merged_df["ffill_zero_tx_hours"].iloc[0]) if "ffill_zero_tx_hours" in merged_df.columns else 0,
        "ohlc_sanitized_hours": int(merged_df["ohlc_sanitized_hours"].iloc[0]) if "ohlc_sanitized_hours" in merged_df.columns else 0,
        "reconstructed_volume_hours": int(merged_df["reconstructed_volume_hours"].iloc[0]) if "reconstructed_volume_hours" in merged_df.columns else 0,
        "frequency": "1h",
        "columns": list(merged_df.columns),
        "sources": data_sources_info,
    }
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return parquet_path, meta_path
