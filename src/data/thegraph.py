"""
Uniswap v3 Subgraph GraphQL Client (The Graph) and Toolkit Sample Dataset Parser.
Strictly uses the official schema fields from:
https://github.com/Uniswap/v3-subgraph/blob/main/src/v3/schema.graphql
"""
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests

from src.config_loader import PROJECT_ROOT, load_environment

logger = logging.getLogger(__name__)

# Official GraphQL queries adhering to Uniswap v3 subgraph schema
POOL_METADATA_QUERY = """
query GetPool($poolId: ID!) {
  pool(id: $poolId) {
    id
    createdAtTimestamp
    feeTier
    liquidity
    sqrtPrice
    token0Price
    token1Price
    tick
    totalValueLockedUSD
    volumeUSD
    feesUSD
    txCount
    token0 {
      id
      symbol
      name
      decimals
    }
    token1 {
      id
      symbol
      name
      decimals
    }
  }
}
"""

POOL_HOUR_DATA_QUERY = """
query GetPoolHourDatas($poolId: String!, $startTime: Int!, $endTime: Int!, $first: Int!) {
  poolHourDatas(
    first: $first
    orderBy: periodStartUnix
    orderDirection: asc
    where: {
      pool: $poolId
      periodStartUnix_gte: $startTime
      periodStartUnix_lt: $endTime
    }
  ) {
    id
    periodStartUnix
    liquidity
    sqrtPrice
    token0Price
    token1Price
    tick
    tvlUSD
    volumeToken0
    volumeToken1
    volumeUSD
    feesUSD
    txCount
    open
    high
    low
    close
  }
}
"""

POOL_DAY_DATA_QUERY = """
query GetPoolDayDatas($poolId: String!, $startTime: Int!, $endTime: Int!, $first: Int!) {
  poolDayDatas(
    first: $first
    orderBy: date
    orderDirection: asc
    where: {
      pool: $poolId
      date_gte: $startTime
      date_lt: $endTime
    }
  ) {
    id
    date
    liquidity
    sqrtPrice
    token0Price
    token1Price
    tick
    tvlUSD
    volumeToken0
    volumeToken1
    volumeUSD
    feesUSD
    txCount
  }
}
"""

SWAPS_QUERY = """
query GetSwaps($poolId: String!, $startTime: BigInt!, $endTime: BigInt!, $first: Int!) {
  swaps(
    first: $first
    orderBy: timestamp
    orderDirection: asc
    where: {
      pool: $poolId
      timestamp_gte: $startTime
      timestamp_lt: $endTime
    }
  ) {
    id
    timestamp
    amount0
    amount1
    amountUSD
    sqrtPriceX96
    tick
  }
}
"""

# Exact 23 columns of `wsteth_eth_data_0.01_pool_data.csv` from ilyamk/uniswap-v3-lp-strategy-toolkit
TOOLKIT_SAMPLE_POOL_COLUMNS: List[str] = [
    "block",
    "timestamp",
    "datetime",
    "sqrtPriceX96",
    "tick",
    "price",
    "liquidity",
    "observationIndex",
    "observationCardinality",
    "observationCardinalityNext",
    "feeProtocol",
    "unlocked",
    "price_change",
    "price_change_pct",
    "liquidity_change",
    "liquidity_change_pct",
    "time_diff_seconds",
    "est_volatility_daily",
    "daily_volume_usd",
    "daily_volume_token0",
    "daily_volume_token1",
    "tvl_usd",
    "fees_usd",
]


class UniswapV3SubgraphClient:
    """GraphQL client with cursor pagination and retry backoff for Uniswap v3 Subgraph."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        subgraph_id: Optional[str] = None,
        gateway_base_url: str = "https://gateway.thegraph.com/api",
        max_retries: int = 4,
        retry_backoff_sec: float = 2.0,
    ) -> None:
        env = load_environment()
        self.api_key = (api_key if api_key is not None else env["THEGRAPH_API_KEY"]).strip()
        self.subgraph_id = subgraph_id or env["UNISWAP_V3_SUBGRAPH_ID"]
        self.gateway_base_url = gateway_base_url.rstrip("/")
        self.max_retries = max_retries
        self.retry_backoff_sec = retry_backoff_sec

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    @property
    def endpoint(self) -> str:
        if not self.has_api_key:
            raise RuntimeError("THEGRAPH_API_KEY is not set in environment or .env")
        return f"{self.gateway_base_url}/{self.api_key}/subgraphs/id/{self.subgraph_id}"

    def execute_query(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GraphQL POST query with exponential backoff retry."""
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(
                    self.endpoint,
                    json={"query": query, "variables": variables},
                    timeout=30,
                )
                resp.raise_for_status()
                payload = resp.json()
                if "errors" in payload:
                    raise RuntimeError(f"GraphQL error: {payload['errors']}")
                return payload.get("data", {})
            except Exception as exc:
                if attempt == self.max_retries:
                    raise
                sleep_time = self.retry_backoff_sec * (2 ** (attempt - 1))
                logger.warning(
                    "Subgraph query failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt,
                    self.max_retries,
                    exc,
                    sleep_time,
                )
                time.sleep(sleep_time)
        return {}

    def fetch_pool_metadata(self, pool_address: str) -> Dict[str, Any]:
        """Fetch Pool entity metadata from The Graph."""
        data = self.execute_query(POOL_METADATA_QUERY, {"poolId": pool_address.lower()})
        pool_obj = data.get("pool")
        if not pool_obj:
            raise ValueError(f"Pool {pool_address} not found on Uniswap v3 Subgraph")
        return pool_obj

    def fetch_pool_day_data(
        self,
        pool_address: str,
        start_date: str,
        end_date: str,
        page_size: int = 1000,
        raw_json_path: Optional[Path] = None,
    ) -> pd.DataFrame:
        """
        Fetch real PoolDayData (`poolDayDatas`) using timestamp-cursor pagination (`date_gte`).
        In the Uniswap v3 Subgraph, `PoolDayData` preserves complete historical `volumeUSD`, `feesUSD`,
        `volumeToken0`, and `volumeToken1` across 2021–2025 (including pre-March-2024 dates where
        `PoolHourData` volume accumulators were reset to 0).
        """
        pool_id = pool_address.lower()
        start_unix = int(pd.Timestamp(start_date, tz="UTC").floor("1D").timestamp())
        end_unix = int((pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)).timestamp())
        cursor = start_unix

        records: List[Dict[str, Any]] = []
        while cursor < end_unix:
            data = self.execute_query(
                POOL_DAY_DATA_QUERY,
                {
                    "poolId": pool_id,
                    "startTime": cursor,
                    "endTime": end_unix,
                    "first": page_size,
                },
            )
            batch = data.get("poolDayDatas", [])
            if not batch:
                break
            records.extend(batch)
            last_ts = int(batch[-1]["date"])
            if last_ts <= cursor or len(batch) < page_size:
                break
            cursor = last_ts + 1

        if raw_json_path is not None and records:
            raw_json_path.parent.mkdir(parents=True, exist_ok=True)
            raw_json_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
            logger.info("Saved %d unmodified raw Subgraph PoolDayData JSON records to %s", len(records), raw_json_path)

        return pd.DataFrame(records)

    def fetch_pool_hour_data(
        self,
        pool_address: str,
        start_date: str,
        end_date: str,
        page_size: int = 1000,
        raw_json_path: Optional[Path] = None,
        pool_day_df: Optional[pd.DataFrame] = None,
        fee_rate: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Fetch real PoolHourData using timestamp-cursor pagination (`periodStartUnix_gte`).
        Saves unmodified raw GraphQL JSON records to `raw_json_path` (if provided) for auditability,
        and returns normalized DataFrame where `timestamp` = `periodStartUnix + 1h` (UTC).
        """
        pool_id = pool_address.lower()
        start_unix = int(pd.Timestamp(start_date, tz="UTC").timestamp())
        end_unix = int((pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)).timestamp())
        cursor = start_unix

        records: List[Dict[str, Any]] = []
        while cursor < end_unix:
            data = self.execute_query(
                POOL_HOUR_DATA_QUERY,
                {
                    "poolId": pool_id,
                    "startTime": cursor,
                    "endTime": end_unix,
                    "first": page_size,
                },
            )
            batch = data.get("poolHourDatas", [])
            if not batch:
                break
            records.extend(batch)
            last_ts = int(batch[-1]["periodStartUnix"])
            if last_ts <= cursor or len(batch) < page_size:
                break
            cursor = last_ts + 1

        if not records:
            raise RuntimeError(f"No PoolHourData returned from Subgraph for pool {pool_id} in [{start_date}, {end_date}]")

        if raw_json_path is not None:
            raw_json_path.parent.mkdir(parents=True, exist_ok=True)
            raw_json_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
            logger.info("Saved %d unmodified raw Subgraph PoolHourData JSON records to %s", len(records), raw_json_path)

        raw_df = pd.DataFrame(records)
        return normalize_pool_hour_dataframe(
            raw_df,
            pool_address=pool_id,
            start_date=start_date,
            end_date=end_date,
            pool_day_df=pool_day_df,
            fee_rate=fee_rate,
        )


def normalize_pool_hour_dataframe(
    df: pd.DataFrame,
    pool_address: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    pool_day_df: Optional[pd.DataFrame] = None,
    fee_rate: Optional[float] = None,
    min_active_tvl_usd: float = 100000.0,
) -> pd.DataFrame:
    """
    Normalize raw PoolHourData records into typed columns with UTC timestamps.
    `period_start` is the start of the hour; `timestamp` is the end of the hour (`period_start + 1h`)
    when the closing state and hourly volume/fees become known.
    - If `pool_day_df` (`PoolDayData`) is provided, reconstructs historical pre-March-2024 hourly
      `volumeUSD`, `feesUSD`, `volumeToken0`, and `volumeToken1` (which the Subgraph reset to 0 in
      `PoolHourData` prior to 2024-03-19) by disaggregating exact on-chain daily totals across the
      24 hours of each UTC day strictly in proportion to hourly on-chain `txCount`.
    - Trims leading unseeded warm-up hours (`tvlUSD < min_active_tvl_usd`) prior to initial pool seeding.
    """
    if df.empty:
        return pd.DataFrame()

    out = df.copy()
    if "periodStartUnix" in out.columns:
        out["periodStartUnix"] = pd.to_numeric(out["periodStartUnix"], errors="coerce").astype("int64")
        out["period_start"] = pd.to_datetime(out["periodStartUnix"], unit="s", utc=True).astype("datetime64[ns, UTC]")
    else:
        raise ValueError("PoolHourData must contain 'periodStartUnix' column from Subgraph schema")

    float_cols = [
        "liquidity",
        "sqrtPrice",
        "token0Price",
        "token1Price",
        "tvlUSD",
        "volumeToken0",
        "volumeToken1",
        "volumeUSD",
        "feesUSD",
        "open",
        "high",
        "low",
        "close",
    ]
    for col in float_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")
        else:
            out[col] = np.nan

    out["tick"] = pd.to_numeric(out.get("tick", 0), errors="coerce").fillna(0).astype("int64")
    out["txCount"] = pd.to_numeric(out.get("txCount", 0), errors="coerce").fillna(0).astype("int64")

    out = out.sort_values("period_start").drop_duplicates(subset=["period_start"]).reset_index(drop=True)
    raw_hour_count = len(out)

    # Replace uninitialized or glitchy zero token0Price/token1Price in Subgraph PoolHourData with NaN,
    # strictly forward-fill from previous valid hour, and drop leading uninitialized hours prior to first pool swap
    zero_price_hours = int(((out["token0Price"] <= 0) | (out["token1Price"] <= 0) | out["token0Price"].isna() | out["token1Price"].isna()).sum())
    out["token0Price"] = np.where(out["token0Price"] > 0, out["token0Price"], np.nan)
    out["token1Price"] = np.where(out["token1Price"] > 0, out["token1Price"], np.nan)
    out["token0Price"] = out["token0Price"].ffill()
    out["token1Price"] = out["token1Price"].ffill()
    out = out.dropna(subset=["token0Price", "token1Price"]).reset_index(drop=True)

    # Trim leading unseeded pool deployment warm-up hours (e.g. wstETH/ETH Aug 2022 - May 2023 when TVL was ~$321)
    unseeded_trimmed_count = 0
    if min_active_tvl_usd > 0 and out["tvlUSD"].max() >= min_active_tvl_usd:
        seeded_mask = out["tvlUSD"] >= min_active_tvl_usd
        if seeded_mask.any():
            first_seeded_pos = int(np.argmax(seeded_mask.to_numpy()))
            if first_seeded_pos > 0:
                unseeded_trimmed_count = first_seeded_pos
                out = out.iloc[first_seeded_pos:].reset_index(drop=True)

    # Fix known Uniswap v3 Subgraph PoolHourData quirks where:
    # 1) 0-volume hours have open=high=low=close=0 while token0Price/token1Price remain populated
    # 2) Isolated subgraph indexing ticks produce corrupted open/high/low far outside [prev_close, token0Price]
    # Scale the allowable wick dynamically using the pool's empirical MAD close-to-close return scale!
    cc_ret = np.log(out["token0Price"] / out["token0Price"].shift(1)).replace([np.inf, -np.inf], np.nan).dropna()
    if len(cc_ret) > 10:
        med_r = float(np.median(cc_ret))
        mad_scale = float(1.4826 * np.median(np.abs(cc_ret - med_r)))
    else:
        mad_scale = 1e-4
    mad_scale = max(mad_scale, 2e-5)
    close_tol = max(6.0 * mad_scale, 5e-4)

    orig_open = out["open"].copy()
    orig_high = out["high"].copy()
    orig_low = out["low"].copy()
    orig_close = out["close"].copy()

    out["close"] = np.where(
        (out["close"] > 0) & ((out["close"] - out["token0Price"]).abs() / out["token0Price"].clip(lower=1e-18) <= close_tol),
        out["close"],
        out["token0Price"],
    )
    prev_close = out["close"].shift(1).fillna(out["close"])
    out["open"] = np.where(
        (out["open"] > 0) & ((out["open"] - prev_close).abs() / prev_close.clip(lower=1e-18) <= close_tol),
        out["open"],
        prev_close,
    )
    bar_top = np.maximum(out["open"], out["close"])
    bar_bot = np.minimum(out["open"], out["close"])
    max_wick = np.maximum(2.0 * (bar_top - bar_bot), 3.5 * mad_scale * out["close"])
    out["high"] = np.where(
        (out["high"] >= bar_top) & (out["high"] <= bar_top + max_wick),
        out["high"],
        bar_top,
    )
    out["low"] = np.where(
        (out["low"] > 0) & (out["low"] <= bar_bot) & (out["low"] >= np.maximum(bar_bot - max_wick, 1e-18)),
        out["low"],
        bar_bot,
    )
    sanitized_mask = (
        (out["open"] != orig_open)
        | (out["high"] != orig_high)
        | (out["low"] != orig_low)
        | (out["close"] != orig_close)
    )
    ohlc_sanitized_count = int(sanitized_mask.sum()) + zero_price_hours

    # Reindex onto complete hourly grid if start_date and end_date are specified
    if start_date is not None and end_date is not None:
        first_valid_start = out["period_start"].min().floor("1h")
        grid_start = max(pd.Timestamp(start_date, tz="UTC").floor("1h"), first_valid_start)
        grid_end = pd.Timestamp(end_date, tz="UTC").floor("1h") + pd.Timedelta(hours=23)
        full_starts = pd.date_range(start=grid_start, end=grid_end, freq="1h", tz="UTC").astype("datetime64[ns, UTC]")

        out = out.set_index("period_start").reindex(full_starts).rename_axis("period_start").reset_index()
        out["periodStartUnix"] = (out["period_start"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000_000).astype("int64")
        out["id"] = out["id"].fillna(
            pd.Series([f"{pool_address.lower()}-{ts // 3600}" for ts in out["periodStartUnix"]], index=out.index)
        )

        # Strictly causal forward-fill of unchanged pool state during zero-transaction hours
        state_cols = ["liquidity", "sqrtPrice", "token0Price", "token1Price", "tick", "tvlUSD", "close"]
        for col in state_cols:
            out[col] = out[col].ffill()
        # Drop any leading hours prior to the first subgraph observation
        out = out.dropna(subset=["close", "token0Price", "token1Price"]).reset_index(drop=True)
        out["tick"] = out["tick"].astype("int64")

        # For zero-tx hours, open = high = low = previous close, and flows = 0
        for ohlc_col in ["open", "high", "low"]:
            out[ohlc_col] = out[ohlc_col].fillna(out["close"])
        for flow_col in ["volumeToken0", "volumeToken1", "volumeUSD", "feesUSD"]:
            out[flow_col] = out[flow_col].fillna(0.0)
        out["txCount"] = out["txCount"].fillna(0).astype("int64")

    # Reconstruct pre-March-2024 hourly volumeUSD, feesUSD, volumeToken0, volumeToken1 from PoolDayData
    # whenever PoolHourData has volumeUSD <= 0 while txCount > 0
    reconstructed_vol_hours = 0
    if pool_day_df is not None and not pool_day_df.empty and "date" in pool_day_df.columns:
        day_df = pool_day_df.copy()
        day_df["date_unix"] = pd.to_numeric(day_df["date"], errors="coerce").astype("int64")
        day_df["utc_day"] = pd.to_datetime(day_df["date_unix"], unit="s", utc=True).dt.floor("1D")
        for d_col in ["volumeUSD", "feesUSD", "volumeToken0", "volumeToken1", "txCount"]:
            if d_col in day_df.columns:
                day_df[d_col] = pd.to_numeric(day_df[d_col], errors="coerce").fillna(0.0).astype("float64")
            else:
                day_df[d_col] = 0.0
        day_map = day_df.drop_duplicates(subset=["utc_day"]).set_index("utc_day")

        out_days = out["period_start"].dt.floor("1D")
        untracked_mask = (out["volumeUSD"] <= 0.0) & (out["txCount"] > 0)
        if untracked_mask.any():
            day_tracked_vol = out.groupby(out_days)["volumeUSD"].transform("sum")
            day_tracked_fee = out.groupby(out_days)["feesUSD"].transform("sum")
            day_tracked_v0 = out.groupby(out_days)["volumeToken0"].transform("sum")
            day_tracked_v1 = out.groupby(out_days)["volumeToken1"].transform("sum")

            untracked_tx = np.where(untracked_mask, out["txCount"].to_numpy(dtype="float64"), 0.0)
            day_untracked_tx_sum = pd.Series(untracked_tx, index=out.index).groupby(out_days).transform("sum").to_numpy()
            tx_share = np.divide(
                untracked_tx,
                day_untracked_tx_sum,
                out=np.zeros_like(untracked_tx, dtype="float64"),
                where=day_untracked_tx_sum > 0.0,
            )

            d_tot_vol = out_days.map(day_map["volumeUSD"]).fillna(0.0).to_numpy(dtype="float64")
            d_tot_fee = out_days.map(day_map["feesUSD"]).fillna(0.0).to_numpy(dtype="float64")
            d_tot_v0 = out_days.map(day_map["volumeToken0"]).fillna(0.0).to_numpy(dtype="float64")
            d_tot_v1 = out_days.map(day_map["volumeToken1"]).fillna(0.0).to_numpy(dtype="float64")

            rem_vol = np.maximum(d_tot_vol - day_tracked_vol.to_numpy(), 0.0)
            rem_fee = np.maximum(d_tot_fee - day_tracked_fee.to_numpy(), 0.0)
            rem_v0 = np.maximum(d_tot_v0 - day_tracked_v0.to_numpy(), 0.0)
            rem_v1 = np.maximum(d_tot_v1 - day_tracked_v1.to_numpy(), 0.0)

            apply_mask = untracked_mask.to_numpy() & (rem_vol > 0.0) & (tx_share > 0.0)
            reconstructed_vol_hours = int(apply_mask.sum())
            out["volumeUSD"] = np.where(apply_mask, rem_vol * tx_share, out["volumeUSD"])
            out["feesUSD"] = np.where(apply_mask, rem_fee * tx_share, out["feesUSD"])
            out["volumeToken0"] = np.where(apply_mask, rem_v0 * tx_share, out["volumeToken0"])
            out["volumeToken1"] = np.where(apply_mask, rem_v1 * tx_share, out["volumeToken1"])

    if fee_rate is not None and fee_rate > 0:
        missing_fee_mask = (out["feesUSD"] <= 0.0) & (out["volumeUSD"] > 0.0)
        out["feesUSD"] = np.where(missing_fee_mask, out["volumeUSD"] * float(fee_rate), out["feesUSD"])

    out["raw_subgraph_hours"] = raw_hour_count
    out["ffill_zero_tx_hours"] = max(0, int(len(out) - (raw_hour_count - unseeded_trimmed_count)))
    out["ohlc_sanitized_hours"] = ohlc_sanitized_count
    out["reconstructed_volume_hours"] = reconstructed_vol_hours
    out["unseeded_low_tvl_hours_trimmed"] = unseeded_trimmed_count
    out["timestamp"] = (out["period_start"] + pd.Timedelta(hours=1)).astype("datetime64[ns, UTC]")
    out["pool_address"] = pool_address.lower()

    # Signed intrahour price pressure / flow imbalance proxy from PoolHourData OHLC
    price_change = out["close"] - out["open"]
    hl_range = (out["high"] - out["low"]).replace(0.0, np.nan)
    out["swap_flow_imbalance"] = (price_change / hl_range).clip(-1.0, 1.0).fillna(0.0)

    return out.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)


def download_toolkit_sample_files(sample_urls: Dict[str, str], raw_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    Download sample dataset files from `ilyamk/uniswap-v3-lp-strategy-toolkit` (Section 2.3 of DATASET_PLAN.md).
    """
    target_dir = raw_dir or (PROJECT_ROOT / "data" / "raw" / "uniswap" / "toolkit_sample")
    target_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: Dict[str, Path] = {}

    for key, url in sample_urls.items():
        filename = url.split("/")[-1]
        dest = target_dir / filename
        if dest.exists() and dest.stat().st_size > 0:
            saved_paths[key] = dest
            continue
        try:
            logger.info("Downloading toolkit sample %s from %s ...", key, url)
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                dest.write_bytes(resp.content)
                saved_paths[key] = dest
        except Exception as exc:
            logger.warning("Could not download toolkit sample %s: %s", key, exc)
    return saved_paths


def parse_toolkit_sample_pool_csv(csv_path: Path) -> pd.DataFrame:
    """
    Parse and validate the block-level snapshot CSV (`wsteth_eth_data_0.01_pool_data.csv`)
    from `ilyamk/uniswap-v3-lp-strategy-toolkit` using its exact 23-column schema.
    """
    df = pd.read_csv(csv_path)
    missing_cols = [c for c in TOOLKIT_SAMPLE_POOL_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Toolkit sample CSV missing expected columns: {missing_cols}")

    df["block"] = pd.to_numeric(df["block"], errors="coerce").astype("int64")
    df["timestamp_unix"] = pd.to_numeric(df["timestamp"], errors="coerce").astype("int64")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_unix"], unit="s", utc=True).astype("datetime64[ns, UTC]")
    df["tick"] = pd.to_numeric(df["tick"], errors="coerce").astype("int64")
    df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("float64")
    df["liquidity_float"] = pd.to_numeric(df["liquidity"], errors="coerce").astype("float64")
    return df.sort_values("timestamp_utc").reset_index(drop=True)
