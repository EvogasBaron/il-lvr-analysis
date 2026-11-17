"""
Step 6 Mandatory Unit Tests for Data Pipeline (Binance timestamps, Checksums, Backward Merge, Toolkit Sample).
"""
import hashlib
import io
import pandas as pd
import numpy as np

from src.config_loader import PROJECT_ROOT
from src.data.binance import (
    aggregate_1m_to_1h,
    detect_timestamp_unit,
    normalize_binance_timestamp,
    prepare_1h_klines,
    read_binance_kline_csv,
    verify_sha256_checksum,
)
from src.data.merge import merge_pool_and_cex_data
from src.data.thegraph import (
    TOOLKIT_SAMPLE_POOL_COLUMNS,
    normalize_pool_hour_dataframe,
    parse_toolkit_sample_pool_csv,
)


def test_binance_timestamp_ms_and_us_equivalence():
    """
    Mandatory Test 1 (Step 6):
    A timestamp in milliseconds (pre-2025) and microseconds (post-2025) representing the exact
    same UTC instant must normalize to the exact same Timestamp.
    Also tests mixed ms/µs series crossing 2025-01-01 00:00:00 UTC.
    """
    ts_sec = 1735689600
    ts_ms = ts_sec * 1_000
    ts_us = ts_sec * 1_000_000
    ts_ns = ts_sec * 1_000_000_000

    assert detect_timestamp_unit(ts_sec) == "s"
    assert detect_timestamp_unit(ts_ms) == "ms"
    assert detect_timestamp_unit(ts_us) == "us"
    assert detect_timestamp_unit(ts_ns) == "ns"

    normed = normalize_binance_timestamp([ts_sec, ts_ms, ts_us, ts_ns])
    assert len(normed.unique()) == 1
    assert normed.iloc[0] == pd.Timestamp("2025-01-01 00:00:00", tz="UTC")

    dec31_23h_ms = 1735686000 * 1_000
    jan01_00h_us = 1735689600 * 1_000_000
    mixed = normalize_binance_timestamp([dec31_23h_ms, jan01_00h_us])
    assert (mixed.iloc[1] - mixed.iloc[0]) == pd.Timedelta(hours=1)


def test_sha256_checksum_verification():
    """Verify SHA256 checksum helper detects valid and corrupted payloads."""
    payload = b"binance-public-data-test-archive"
    digest = hashlib.sha256(payload).hexdigest()
    checksum_line = f"{digest}  ETHUSDT-1h-2025-01.zip\n"

    assert verify_sha256_checksum(payload, checksum_line) is True
    assert verify_sha256_checksum(payload + b"corrupt", checksum_line) is False


def test_1m_to_1h_aggregation_and_candle_close_alignment():
    """
    Verify that 60 1-minute candles opening between 10:00 and 10:59 UTC aggregate into a single
    1-hour bar whose effective `timestamp` is 11:00 UTC (preventing 1-hour look-ahead bias).
    """
    base_open = pd.Timestamp("2025-01-01 10:00:00", tz="UTC")
    open_times_us = [int((base_open + pd.Timedelta(minutes=m)).timestamp() * 1_000_000) for m in range(60)]
    close_times_us = [t + 59_999_999 for t in open_times_us]

    prices = np.linspace(3000.0, 3060.0, 60)
    rows = []
    for i in range(60):
        rows.append(
            f"{open_times_us[i]},{prices[i]:.2f},{prices[i]+2:.2f},{prices[i]-2:.2f},"
            f"{prices[i]+1:.2f},10.5,{close_times_us[i]},31500.0,100,5.25,15750.0,0"
        )
    csv_buf = io.StringIO("\n".join(rows))
    df_1m = read_binance_kline_csv(csv_buf)
    df_1h = aggregate_1m_to_1h(df_1m)

    assert len(df_1h) == 1
    assert df_1h["cex_open_time"].iloc[0] == pd.Timestamp("2025-01-01 10:00:00", tz="UTC")
    assert df_1h["timestamp"].iloc[0] == pd.Timestamp("2025-01-01 11:00:00", tz="UTC")
    assert np.isclose(df_1h["cex_open"].iloc[0], 3000.0)
    assert np.isclose(df_1h["cex_close"].iloc[0], 3061.0)
    assert df_1h["cex_realized_vol_1h"].iloc[0] > 0.0


def test_backward_merge_no_future_candle_leakage():
    """
    Mandatory Test 2 & 3 (Step 6):
    Verify `merge_pool_and_cex_data` aligns completed candles without duplicate timestamps
    or look-ahead leakage, and cross-checks AMM vs CEX prices.
    """
    hours = pd.date_range("2025-01-01 00:00:00", periods=10, freq="1h", tz="UTC").astype("datetime64[ns, UTC]")
    cex_raw = pd.DataFrame(
        {
            "open_time": hours,
            "open": np.linspace(3000.0, 3090.0, 10),
            "high": np.linspace(3010.0, 3100.0, 10),
            "low": np.linspace(2990.0, 3080.0, 10),
            "close": np.linspace(3005.0, 3095.0, 10),
            "volume": 1000.0,
            "close_time": hours + pd.Timedelta(hours=1) - pd.Timedelta(milliseconds=1),
            "quote_asset_volume": 3_000_000.0,
            "number_of_trades": 500,
            "taker_buy_base_asset_volume": 520.0,
            "taker_buy_quote_asset_volume": 1_560_000.0,
            "ignore": 0,
        }
    )
    cex_1h = prepare_1h_klines(cex_raw)

    pool_raw = pd.DataFrame(
        {
            "id": [f"0x88e6-{i}" for i in range(10)],
            "periodStartUnix": (hours.astype("int64") // 1_000_000_000).astype("int64"),
            "liquidity": 1e18,
            "sqrtPrice": 1e24,
            "token0Price": np.linspace(3005.5, 3095.5, 10),
            "token1Price": 1.0 / np.linspace(3005.5, 3095.5, 10),
            "tick": 200000,
            "tvlUSD": 100_000_000.0,
            "volumeToken0": 1_000_000.0,
            "volumeToken1": 330.0,
            "volumeUSD": 2_000_000.0,
            "feesUSD": 1_000.0,
            "txCount": 250,
            "open": np.linspace(3000.0, 3090.0, 10),
            "high": np.linspace(3010.0, 3100.0, 10),
            "low": np.linspace(2990.0, 3080.0, 10),
            "close": np.linspace(3005.5, 3095.5, 10),
        }
    )
    pool_1h = normalize_pool_hour_dataframe(pool_raw, pool_address="0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

    pool_cfg = {
        "name": "USDC/WETH 0.05%",
        "address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
        "category": "volatile",
        "fee_tier_bps": 500,
        "fee_rate": 0.0005,
        "tick_spacing": 10,
        "price_field": "token0Price",
    }
    merged = merge_pool_and_cex_data(pool_1h, cex_1h, pool_key="weth_usdc_005", pool_cfg=pool_cfg)

    assert len(merged) == 10
    assert merged["timestamp"].duplicated().sum() == 0
    assert ((merged["cex_open_time"] + pd.Timedelta(hours=1)) <= merged["timestamp"]).all()
    assert ((merged["period_start"] + pd.Timedelta(hours=1)) <= merged["timestamp"]).all()
    assert (merged["amm_cex_spread_rel"].abs() < 0.001).all()


def test_toolkit_sample_csv_parser_and_tick_price_consistency():
    """
    Mandatory Test 5 (Step 6 of DATASET_PLAN.md):
    Test parsing the real `wsteth_eth_data_0.01_pool_data.csv` from `ilyamk/uniswap-v3-lp-strategy-toolkit`.
    Verifies all 23 columns and checks that `1.0001 ** tick` matches the `price` column.
    """
    sample_path = PROJECT_ROOT / "data" / "raw" / "uniswap" / "toolkit_sample" / "wsteth_eth_data_0.01_pool_data.csv"
    assert sample_path.exists(), "Toolkit sample CSV should be downloaded in data/raw/uniswap/toolkit_sample/"
    df = parse_toolkit_sample_pool_csv(sample_path)
    assert len(df) == 217
    for col in TOOLKIT_SAMPLE_POOL_COLUMNS:
        assert col in df.columns
    implied_price = 1.0001 ** df["tick"].to_numpy(dtype="float64")
    rel_diff = np.abs(implied_price - df["price"].to_numpy(dtype="float64")) / df["price"].to_numpy(dtype="float64")
    assert np.max(rel_diff) < 0.001


def test_subgraph_ohlc_adaptive_mad_sanitization_and_audit_counts():
    """
    Verify that `normalize_pool_hour_dataframe` sanitizes corrupted Subgraph OHLC wicks
    (such as a 1.2% wick on a stable/correlated pool whose close-to-close MAD scale is ~0.005%)
    and records `ohlc_sanitized_hours` and `ffill_zero_tx_hours`.
    """
    hours = pd.date_range("2025-01-01 00:00:00", periods=40, freq="1h", tz="UTC").astype("datetime64[ns, UTC]")
    base_p = 1.0 + np.linspace(0.0, 0.0004, 40)
    highs = base_p.copy()
    lows = base_p.copy()
    # Inject a corrupted 1.2% Subgraph high/low glitch at index 20 (which the old 1.5% filter missed!)
    highs[20] = base_p[20] * 1.012
    lows[20] = base_p[20] * 0.988

    pool_raw = pd.DataFrame(
        {
            "id": [f"0x3416-{i}" for i in range(40)],
            "periodStartUnix": (hours.astype("int64") // 1_000_000_000).astype("int64"),
            "liquidity": 1e18,
            "sqrtPrice": 1e24,
            "token0Price": base_p,
            "token1Price": 1.0 / base_p,
            "tick": 0,
            "tvlUSD": 30_000_000.0,
            "volumeToken0": 100_000.0,
            "volumeToken1": 100_000.0,
            "volumeUSD": 200_000.0,
            "feesUSD": 20.0,
            "txCount": 50,
            "open": base_p,
            "high": highs,
            "low": lows,
            "close": base_p,
        }
    )
    norm_df = normalize_pool_hour_dataframe(pool_raw, pool_address="0x3416cf6c708da44db2624d63ea0aaef7113527c6")
    assert int(norm_df["ohlc_sanitized_hours"].iloc[0]) >= 1
    assert np.isclose(norm_df.loc[20, "high"], base_p[20], atol=1e-4)
    assert np.isclose(norm_df.loc[20, "low"], base_p[20], atol=1e-4)


def test_pooldaydata_volume_fee_reconstruction_and_unseeded_tvl_trimming():
    """
    Verify that `normalize_pool_hour_dataframe`:
    1) Trims leading unseeded pool hours where `tvlUSD < min_active_tvl_usd` (e.g. $300 test liquidity).
    2) Reconstructs pre-March-2024 hourly `volumeUSD` and `feesUSD` from `PoolDayData` strictly
       in proportion to hourly `txCount` whenever `PoolHourData.volumeUSD == 0` and `txCount > 0`.
    """
    hours = pd.date_range("2023-06-15 00:00:00", periods=6, freq="1h", tz="UTC").astype("datetime64[ns, UTC]")
    # First 2 hours are unseeded ($300 TVL), next 4 hours are seeded ($5,000,000 TVL) with txCount = [0, 10, 30, 60]
    pool_raw = pd.DataFrame(
        {
            "id": [f"0x1098-{i}" for i in range(6)],
            "periodStartUnix": (hours.astype("int64") // 1_000_000_000).astype("int64"),
            "liquidity": 1e24,
            "sqrtPrice": 1e24,
            "token0Price": 0.88,
            "token1Price": 1.136,
            "tick": 1200,
            "tvlUSD": [300.0, 350.0, 5_000_000.0, 5_000_000.0, 5_000_000.0, 5_000_000.0],
            "volumeToken0": 0.0,
            "volumeToken1": 0.0,
            "volumeUSD": 0.0,
            "feesUSD": 0.0,
            "txCount": [1, 1, 0, 10, 30, 60],
            "open": 0.88,
            "high": 0.88,
            "low": 0.88,
            "close": 0.88,
        }
    )
    day_df = pd.DataFrame(
        {
            "date": [int(pd.Timestamp("2023-06-15 00:00:00", tz="UTC").timestamp())],
            "volumeUSD": [1_000_000.0],
            "feesUSD": [500.0],
            "volumeToken0": [500.0],
            "volumeToken1": [568.0],
            "txCount": [100],
        }
    )
    norm_df = normalize_pool_hour_dataframe(
        pool_raw,
        pool_address="0x109830a1aaad605bbf02a9dfa7b0b92ec2fb7daa",
        pool_day_df=day_df,
        fee_rate=0.0005,
        min_active_tvl_usd=100_000.0,
    )
    assert len(norm_df) == 4
    assert int(norm_df["unseeded_low_tvl_hours_trimmed"].iloc[0]) == 2
    assert int(norm_df["reconstructed_volume_hours"].iloc[0]) == 3
    assert np.allclose(norm_df["volumeUSD"].to_numpy(), [0.0, 100_000.0, 300_000.0, 600_000.0], atol=1e-6)
    assert np.allclose(norm_df["feesUSD"].to_numpy(), [0.0, 50.0, 150.0, 300.0], atol=1e-6)
