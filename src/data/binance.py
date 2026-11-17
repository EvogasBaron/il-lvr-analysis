"""
Binance Vision Public Data Downloader, Checksum Verifier, and Timestamp Normalizer.
Handles the known Binance timestamp unit change (ms before 2025-01-01, µs from 2025-01-01 onwards).
"""
import hashlib
import io
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd
import requests

from src.config_loader import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Official 12-column schema from https://github.com/binance/binance-public-data/
BINANCE_KLINE_COLUMNS: List[str] = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
]


def detect_timestamp_unit(value: int | float) -> str:
    """
    Detect the unit of a Unix epoch timestamp based on magnitude.
    - < 1e11: seconds ('s')
    - 1e11 <= val < 1e14: milliseconds ('ms')
    - 1e14 <= val < 1e17: microseconds ('us')
    - >= 1e17: nanoseconds ('ns')
    """
    val = abs(float(value))
    if val < 1e11:
        return "s"
    elif val < 1e14:
        return "ms"
    elif val < 1e17:
        return "us"
    else:
        return "ns"


def normalize_binance_timestamp(ts_series: pd.Series | Iterable) -> pd.Series:
    """
    Normalize a series of integer/float epoch timestamps into UTC datetime64[ns, UTC].
    Works seamlessly even if a single DataFrame mixes milliseconds (pre-2025)
    and microseconds (post-2025-01-01).
    """
    s = pd.Series(ts_series).astype("int64")
    if s.empty:
        return pd.to_datetime(s, utc=True)

    # Convert element-wise / mask-wise to nanoseconds since epoch
    ns_values = np.empty(len(s), dtype="int64")
    vals = s.to_numpy(dtype="int64")

    mask_s = vals < 100_000_000_000
    mask_ms = (vals >= 100_000_000_000) & (vals < 100_000_000_000_000)
    mask_us = (vals >= 100_000_000_000_000) & (vals < 100_000_000_000_000_000)
    mask_ns = vals >= 100_000_000_000_000_000

    ns_values[mask_s] = vals[mask_s] * 1_000_000_000
    ns_values[mask_ms] = vals[mask_ms] * 1_000_000
    ns_values[mask_us] = vals[mask_us] * 1_000
    ns_values[mask_ns] = vals[mask_ns]

    return pd.to_datetime(pd.Series(ns_values, index=s.index), unit="ns", utc=True).astype("datetime64[ns, UTC]")


def verify_sha256_checksum(zip_bytes: bytes, checksum_text: str) -> bool:
    """Verify SHA256 digest of downloaded zip bytes against .CHECKSUM file content."""
    expected_hash = checksum_text.strip().split()[0].lower()
    actual_hash = hashlib.sha256(zip_bytes).hexdigest().lower()
    return actual_hash == expected_hash


def generate_year_months(start_date: str, end_date: str) -> List[tuple[int, int]]:
    """Return list of (year, month) tuples covering [start_date, end_date]."""
    start_dt = pd.Timestamp(start_date, tz="UTC")
    end_dt = pd.Timestamp(end_date, tz="UTC")
    months = []
    cur = pd.Timestamp(year=start_dt.year, month=start_dt.month, day=1, tz="UTC")
    while cur <= end_dt:
        months.append((cur.year, cur.month))
        if cur.month == 12:
            cur = pd.Timestamp(year=cur.year + 1, month=1, day=1, tz="UTC")
        else:
            cur = pd.Timestamp(year=cur.year, month=cur.month + 1, day=1, tz="UTC")
    return months


def read_binance_kline_csv(csv_source: Path | io.BytesIO | io.StringIO) -> pd.DataFrame:
    """
    Read a Binance kline CSV file (with or without header row) and normalize columns & timestamps.
    """
    if isinstance(csv_source, Path):
        with open(csv_source, "rb") as f:
            raw_bytes = f.read()
    elif isinstance(csv_source, io.BytesIO):
        raw_bytes = csv_source.getvalue()
    else:
        raw_bytes = csv_source.getvalue().encode("utf-8")

    first_line = raw_bytes.splitlines()[0].decode("utf-8", errors="ignore") if raw_bytes else ""
    has_header = any(ch.isalpha() for ch in first_line.split(",")[0])

    df = pd.read_csv(
        io.BytesIO(raw_bytes),
        header=0 if has_header else None,
        names=BINANCE_KLINE_COLUMNS,
    )

    numeric_float_cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
    ]
    for col in numeric_float_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    df["number_of_trades"] = pd.to_numeric(df["number_of_trades"], errors="coerce").fillna(0).astype("int64")

    df["open_time_raw"] = pd.to_numeric(df["open_time"], errors="coerce").astype("int64")
    df["close_time_raw"] = pd.to_numeric(df["close_time"], errors="coerce").astype("int64")
    df["open_time"] = normalize_binance_timestamp(df["open_time_raw"])
    df["close_time"] = normalize_binance_timestamp(df["close_time_raw"])

    return df.sort_values("open_time").drop_duplicates(subset=["open_time"]).reset_index(drop=True)


def download_binance_monthly_klines(
    symbol: str,
    interval: str,
    start_date: str,
    end_date: str,
    raw_dir: Optional[Path] = None,
    base_url: str = "https://data.binance.vision/data/spot/monthly/klines",
    verify_checksum: bool = True,
    timeout: int = 30,
) -> pd.DataFrame:
    """
    Download monthly kline zip archives from Binance Vision, verify .CHECKSUM,
    extract CSVs into data/raw/binance/, and concatenate into a normalized DataFrame.
    """
    target_dir = raw_dir or (PROJECT_ROOT / "data" / "raw" / "binance" / symbol / interval)
    target_dir.mkdir(parents=True, exist_ok=True)

    months = generate_year_months(start_date, end_date)
    frames: List[pd.DataFrame] = []

    for year, month in months:
        stem = f"{symbol}-{interval}-{year:04d}-{month:02d}"
        csv_path = target_dir / f"{stem}.csv"
        not_found_marker = target_dir / f"{stem}.404"

        if csv_path.exists():
            logger.info("Loading cached Binance CSV: %s", csv_path)
            frames.append(read_binance_kline_csv(csv_path))
            continue
        if not_found_marker.exists():
            logger.info("Skipping known unavailable Binance archive (404 cached): %s", stem)
            continue

        zip_url = f"{base_url}/{symbol}/{interval}/{stem}.zip"
        checksum_url = f"{zip_url}.CHECKSUM"
        try:
            logger.info("Downloading %s ...", zip_url)
            resp = requests.get(zip_url, timeout=timeout)
            if resp.status_code == 404:
                logger.info("Archive %s not available on Binance Vision (HTTP 404); caching marker.", stem)
                not_found_marker.write_text("404", encoding="utf-8")
                continue
            if resp.status_code != 200:
                logger.warning("URL %s returned status %d", zip_url, resp.status_code)
                continue
            zip_bytes = resp.content

            if verify_checksum:
                chk_resp = requests.get(checksum_url, timeout=timeout)
                if chk_resp.status_code == 200:
                    if not verify_sha256_checksum(zip_bytes, chk_resp.text):
                        raise ValueError(f"SHA256 checksum mismatch for {stem}.zip")
                    logger.info("Verified SHA256 checksum for %s.zip", stem)

            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
                if not csv_names:
                    raise ValueError(f"No CSV found inside {stem}.zip")
                extracted_bytes = zf.read(csv_names[0])
                with open(csv_path, "wb") as out_f:
                    out_f.write(extracted_bytes)

            frames.append(read_binance_kline_csv(csv_path))
        except Exception as exc:
            logger.warning("Could not download %s: %s", zip_url, exc)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("open_time").drop_duplicates(subset=["open_time"]).reset_index(drop=True)

    start_ts = pd.Timestamp(start_date, tz="UTC")
    end_ts = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
    combined = combined[(combined["open_time"] >= start_ts) & (combined["open_time"] < end_ts)].reset_index(drop=True)
    return combined


def aggregate_1m_to_1h(df_1m: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate 1-minute Binance klines into 1-hour records indexed by candle completion time
    (`timestamp = hour_open + 1h`) so that any backward merge at time T only uses data known at T.
    Computes intrahour realized volatility, downside volatility, and jump count.
    """
    if df_1m.empty:
        return pd.DataFrame()

    df = df_1m.sort_values("open_time").copy()
    df["log_ret_1m"] = np.log(df["close"] / df["open"]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    df["neg_ret_sq_1m"] = np.where(df["log_ret_1m"] < 0, df["log_ret_1m"] ** 2, 0.0)

    # Group by the start of the hour
    df["hour_open"] = df["open_time"].dt.floor("1h")
    rolling_std = df["log_ret_1m"].rolling(60, min_periods=1).std().fillna(0.001)
    df["is_jump_1m"] = (df["log_ret_1m"].abs() > 3.0 * rolling_std).astype("int64")

    grouped = df.groupby("hour_open", as_index=False).agg(
        cex_open=("open", "first"),
        cex_high=("high", "max"),
        cex_low=("low", "min"),
        cex_close=("close", "last"),
        cex_volume=("volume", "sum"),
        cex_quote_volume=("quote_asset_volume", "sum"),
        cex_trades=("number_of_trades", "sum"),
        cex_taker_buy_base_vol=("taker_buy_base_asset_volume", "sum"),
        cex_realized_var_1h=("log_ret_1m", lambda x: float(np.sum(np.square(x)))),
        cex_downside_var_1h=("neg_ret_sq_1m", "sum"),
        cex_jump_count_1h=("is_jump_1m", "sum"),
        n_1m_bars=("close", "count"),
    )

    grouped["cex_realized_vol_1h"] = np.sqrt(grouped["cex_realized_var_1h"])
    grouped["cex_downside_vol_1h"] = np.sqrt(grouped["cex_downside_var_1h"])
    grouped["cex_taker_buy_ratio"] = np.where(
        grouped["cex_volume"] > 0,
        grouped["cex_taker_buy_base_vol"] / grouped["cex_volume"],
        0.5,
    )
    # CRITICAL: Candle opening at hour_open finishes at hour_open + 1h
    grouped["timestamp"] = (grouped["hour_open"] + pd.Timedelta(hours=1)).astype("datetime64[ns, UTC]")
    grouped["cex_open_time"] = grouped["hour_open"].astype("datetime64[ns, UTC]")
    return grouped.drop(columns=["hour_open", "cex_realized_var_1h", "cex_downside_var_1h"]).sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)


def prepare_1h_klines(df_1h: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize 1-hour Binance klines so that `timestamp` represents the end of the 1h candle
    (`open_time + 1h`), preventing 1-hour look-ahead bias during backward merge_asof.
    Also computes Parkinson/Garman-Klass intrahour volatility estimator if 1m bars are absent.
    """
    if df_1h.empty:
        return pd.DataFrame()

    df = df_1h.sort_values("open_time").copy()
    df["cex_open_time"] = df["open_time"].dt.floor("1h").astype("datetime64[ns, UTC]")
    df["timestamp"] = (df["cex_open_time"] + pd.Timedelta(hours=1)).astype("datetime64[ns, UTC]")

    df = df.rename(
        columns={
            "open": "cex_open",
            "high": "cex_high",
            "low": "cex_low",
            "close": "cex_close",
            "volume": "cex_volume",
            "quote_asset_volume": "cex_quote_volume",
            "number_of_trades": "cex_trades",
            "taker_buy_base_asset_volume": "cex_taker_buy_base_vol",
        }
    )

    df = df.sort_values("cex_open_time").drop_duplicates(subset=["cex_open_time"]).reset_index(drop=True)
    # Reindex onto complete hourly grid between min and max cex_open_time (strictly causal ffill for exchange maintenance/pause hours)
    full_open_grid = pd.date_range(
        start=df["cex_open_time"].min(),
        end=df["cex_open_time"].max(),
        freq="1h",
        tz="UTC",
    ).astype("datetime64[ns, UTC]")
    df = df.set_index("cex_open_time").reindex(full_open_grid).rename_axis("cex_open_time").reset_index()
    df["timestamp"] = (df["cex_open_time"] + pd.Timedelta(hours=1)).astype("datetime64[ns, UTC]")
    df["cex_close"] = df["cex_close"].ffill()
    for ohl_col in ["cex_open", "cex_high", "cex_low"]:
        df[ohl_col] = df[ohl_col].fillna(df["cex_close"])
    for vol_col in ["cex_volume", "cex_quote_volume", "cex_taker_buy_base_vol"]:
        df[vol_col] = df[vol_col].fillna(0.0)
    df["cex_trades"] = df["cex_trades"].fillna(0).astype("int64")

    # Parkinson high-low volatility estimator within the hour + log return
    log_hl = np.log((df["cex_high"] / df["cex_low"]).clip(lower=1.0))
    parkinson_vol = np.sqrt((1.0 / (4.0 * np.log(2.0))) * (log_hl ** 2))
    log_co = np.log(df["cex_close"] / df["cex_open"]).replace([np.inf, -np.inf], 0.0).fillna(0.0)

    df["cex_realized_vol_1h"] = np.maximum(parkinson_vol, log_co.abs())
    df["cex_downside_vol_1h"] = np.where(log_co < 0, df["cex_realized_vol_1h"], 0.0)
    rolling_vol = df["cex_realized_vol_1h"].rolling(24, min_periods=1).mean().replace(0.0, 0.005).fillna(0.005)
    df["cex_jump_count_1h"] = (log_co.abs() > 2.5 * rolling_vol).astype("int64")
    df["cex_taker_buy_ratio"] = np.where(
        df["cex_volume"] > 0,
        df["cex_taker_buy_base_vol"] / df["cex_volume"],
        0.5,
    )
    df["n_1m_bars"] = 60

    keep_cols = [
        "timestamp",
        "cex_open_time",
        "cex_open",
        "cex_high",
        "cex_low",
        "cex_close",
        "cex_volume",
        "cex_quote_volume",
        "cex_trades",
        "cex_taker_buy_base_vol",
        "cex_realized_vol_1h",
        "cex_downside_vol_1h",
        "cex_jump_count_1h",
        "cex_taker_buy_ratio",
        "n_1m_bars",
    ]
    return df[keep_cols].sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
