"""
Master End-to-End Orchestrator Pipeline for the Uniswap v3 IL & LVR Analysis Project.
Strictly uses real on-chain Uniswap v3 Subgraph data (via THEGRAPH_API_KEY in .env)
and real SHA256-verified Binance Vision klines. Zero synthetic data in production.
"""
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from src.backtest.engine import execute_rq3_workflow
from src.config_loader import PROJECT_ROOT, load_config, load_environment, load_pools_config
from src.data.binance import (
    download_binance_monthly_klines,
    prepare_1h_klines,
)
from src.data.merge import merge_pool_and_cex_data, save_merged_dataset
from src.data.quality import (
    check_merged_cross_consistency,
    check_timeseries_quality,
    write_data_quality_report,
)
from src.data.thegraph import (
    UniswapV3SubgraphClient,
    download_toolkit_sample_files,
    normalize_pool_hour_dataframe,
    parse_toolkit_sample_pool_csv,
)
from src.features import (
    assign_market_regimes,
    attach_forward_targets,
    build_position_panel_dataset,
    engineer_pool_features,
)
from src.models.rq1_econometrics import execute_rq1_workflow
from src.models.rq2_forecasting import execute_rq2_workflow

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("il_lvr_pipeline")


def acquire_cex_data(config: Dict[str, Any]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str]]:
    """
    Step 2 of DATASET_PLAN.md: Download and verify real Binance 1h klines for ETHUSDT and USDCUSDT.
    Raises RuntimeError if real data cannot be acquired (never silently falls back to synthetic data).
    """
    start_date = config["time_range"]["start_date"]
    end_date = config["time_range"]["end_date"]
    verify_chk = bool(config["binance"]["verify_checksum"])

    cex_1h_map: Dict[str, pd.DataFrame] = {}
    cex_source_map: Dict[str, str] = {}

    for sym_entry in config["binance"]["symbols"]:
        symbol = sym_entry["symbol"]
        raw_df = download_binance_monthly_klines(
            symbol=symbol,
            interval="1h",
            start_date=start_date,
            end_date=end_date,
            verify_checksum=verify_chk,
        )
        if raw_df.empty:
            raise RuntimeError(f"Failed to download real Binance Vision klines for {symbol} ({start_date} to {end_date}).")
        cex_source_map[symbol] = "data.binance.vision_verified_sha256"
        cex_1h_map[symbol] = prepare_1h_klines(raw_df)

    return cex_1h_map, cex_source_map


def acquire_pool_data(
    config: Dict[str, Any],
    pools_cfg: Dict[str, Any],
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str], Dict[str, Any]]:
    """
    Step 3 of DATASET_PLAN.md:
    1) Verify Pool metadata and fetch real `PoolHourData` from the Uniswap v3 Mainnet Subgraph
       for all enabled pools in `configs/pools.yaml`.
    2) Parse the toolkit sample CSV (`wsteth_eth_data_0.01_pool_data.csv`) using its real 23-column schema
       and cross-validate its prices against the live Subgraph series.
    """
    sample_urls = config["thegraph"]["toolkit_sample_urls"]
    sample_paths = download_toolkit_sample_files(sample_urls)

    toolkit_df = pd.DataFrame()
    if "pool_data" in sample_paths and sample_paths["pool_data"].exists():
        toolkit_df = parse_toolkit_sample_pool_csv(sample_paths["pool_data"])
        logger.info("Parsed toolkit sample pool CSV: %d block snapshots (%s to %s)", len(toolkit_df), toolkit_df["timestamp_utc"].min(), toolkit_df["timestamp_utc"].max())

    client = UniswapV3SubgraphClient(
        subgraph_id=config["thegraph"]["subgraph_id"],
        gateway_base_url=config["thegraph"]["gateway_base_url"],
        max_retries=int(config["thegraph"]["max_retries"]),
        retry_backoff_sec=float(config["thegraph"]["retry_backoff_sec"]),
    )
    if not client.has_api_key:
        raise RuntimeError("THEGRAPH_API_KEY is required in .env to fetch real Uniswap v3 Subgraph data.")

    start_date = config["time_range"]["start_date"]
    end_date = config["time_range"]["end_date"]

    pool_dfs: Dict[str, pd.DataFrame] = {}
    pool_sources: Dict[str, str] = {}
    verified_pool_meta: Dict[str, Any] = {}

    for pool_key, p_cfg in pools_cfg["pools"].items():
        if not p_cfg.get("enabled", False):
            continue

        raw_pool_dir = PROJECT_ROOT / "data" / "raw" / "uniswap" / pool_key
        raw_pool_dir.mkdir(parents=True, exist_ok=True)
        subgraph_raw_json = raw_pool_dir / "pool_hour_data_raw.json"
        subgraph_day_json = raw_pool_dir / "pool_day_data_raw.json"
        subgraph_cache_csv = raw_pool_dir / "pool_hour_data_subgraph.csv"
        meta_cache_json = raw_pool_dir / "pool_metadata_subgraph.json"

        if meta_cache_json.exists():
            verified_pool_meta[pool_key] = json.loads(meta_cache_json.read_text(encoding="utf-8"))
        else:
            meta_obj = client.fetch_pool_metadata(p_cfg["address"])
            verified_pool_meta[pool_key] = meta_obj
            meta_cache_json.write_text(json.dumps(meta_obj, indent=2), encoding="utf-8")
            logger.info(
                "Verified Subgraph Pool %s (%s): %s/%s feeTier=%s",
                pool_key,
                meta_obj["id"],
                meta_obj["token0"]["symbol"],
                meta_obj["token1"]["symbol"],
                meta_obj["feeTier"],
            )

        created_unix = int(verified_pool_meta[pool_key].get("createdAtTimestamp", 0))
        req_start_unix = int(pd.Timestamp(start_date, tz="UTC").timestamp())
        req_end_unix = int(pd.Timestamp(end_date, tz="UTC").timestamp())
        effective_start_unix = max(req_start_unix, created_unix)

        # Fetch or load PoolDayData (which preserves complete 2021-2025 daily volumeUSD and feesUSD)
        df_pool_day = pd.DataFrame()
        if subgraph_day_json.exists() and subgraph_day_json.stat().st_size > 200:
            try:
                day_records = json.loads(subgraph_day_json.read_text(encoding="utf-8"))
                if day_records:
                    df_pool_day = pd.DataFrame(day_records)
            except Exception as exc:
                logger.warning("Failed to read cached PoolDayData JSON for %s: %s", pool_key, exc)

        if df_pool_day.empty:
            logger.info("Fetching PoolDayData from Subgraph for %s (%s)...", pool_key, p_cfg["address"])
            df_pool_day = client.fetch_pool_day_data(
                pool_address=p_cfg["address"],
                start_date=start_date,
                end_date=end_date,
                page_size=int(config["thegraph"]["page_size"]),
                raw_json_path=subgraph_day_json,
            )

        pool_fee_rate = float(p_cfg.get("fee_rate", 0.0))
        use_cached_raw = False
        if subgraph_raw_json.exists() and subgraph_raw_json.stat().st_size > 1000:
            try:
                raw_records = json.loads(subgraph_raw_json.read_text(encoding="utf-8"))
                if raw_records:
                    min_cached_unix = int(raw_records[0]["periodStartUnix"])
                    max_cached_unix = int(raw_records[-1]["periodStartUnix"])
                    # Verify cache covers from effective pool start (within 7 days) up to end_date (within 7 days)
                    if min_cached_unix <= effective_start_unix + 7 * 86400 and max_cached_unix >= req_end_unix - 7 * 86400:
                        use_cached_raw = True
                        logger.info(
                            "Loading cached unmodified Subgraph JSON (%d records) for %s from %s",
                            len(raw_records),
                            pool_key,
                            subgraph_raw_json,
                        )
                        df_pool = normalize_pool_hour_dataframe(
                            pd.DataFrame(raw_records),
                            pool_address=p_cfg["address"],
                            start_date=start_date,
                            end_date=end_date,
                            pool_day_df=df_pool_day,
                            fee_rate=pool_fee_rate,
                        )
                        df_pool.to_csv(subgraph_cache_csv, index=False)
            except Exception as exc:
                logger.warning("Failed to read cached raw JSON for %s: %s", pool_key, exc)

        if not use_cached_raw:
            logger.info(
                "Querying real PoolHourData from The Graph Subgraph for %s (%s) [%s -> %s]...",
                pool_key,
                p_cfg["address"],
                start_date,
                end_date,
            )
            df_pool = client.fetch_pool_hour_data(
                pool_address=p_cfg["address"],
                start_date=start_date,
                end_date=end_date,
                page_size=int(config["thegraph"]["page_size"]),
                raw_json_path=subgraph_raw_json,
                pool_day_df=df_pool_day,
                fee_rate=pool_fee_rate,
            )
            df_pool.to_csv(subgraph_cache_csv, index=False)
            logger.info(
                "Normalized %d hourly records for %s (raw=%d, ffill_zero_tx=%d, ohlc_sanitized=%d, recon_vol=%d)",
                len(df_pool),
                pool_key,
                int(df_pool["raw_subgraph_hours"].iloc[0]),
                int(df_pool["ffill_zero_tx_hours"].iloc[0]),
                int(df_pool["ohlc_sanitized_hours"].iloc[0]),
                int(df_pool["reconstructed_volume_hours"].iloc[0]),
            )

        pool_dfs[pool_key] = df_pool
        pool_sources[pool_key] = f"thegraph_subgraph_{config['thegraph']['subgraph_id']}_real_onchain"

    # Cross-check toolkit sample vs real Subgraph data on wsteth_eth_001
    toolkit_validation_info: Dict[str, Any] = {}
    if not toolkit_df.empty and "wsteth_eth_001" in pool_dfs:
        sub_wst = pool_dfs["wsteth_eth_001"][["timestamp", "token1Price", "tick"]].copy()
        tk = toolkit_df[["timestamp_utc", "price", "tick"]].rename(
            columns={"timestamp_utc": "timestamp", "price": "toolkit_price", "tick": "toolkit_tick"}
        )
        matched = pd.merge_asof(
            tk.sort_values("timestamp"),
            sub_wst.sort_values("timestamp"),
            on="timestamp",
            direction="backward",
            tolerance=pd.Timedelta(hours=2),
        ).dropna()
        rel_err = ((matched["toolkit_price"] - matched["token1Price"]).abs() / matched["token1Price"])
        toolkit_validation_info = {
            "n_matched_snapshots": int(len(matched)),
            "median_rel_price_diff": float(rel_err.median()),
            "max_rel_price_diff": float(rel_err.max()),
        }
        logger.info(
            "Cross-validated toolkit sample vs real Subgraph on wsteth_eth_001: %d snapshots, median price diff = %.6f%%",
            len(matched),
            float(rel_err.median()) * 100.0,
        )

    return pool_dfs, pool_sources, toolkit_validation_info


def write_final_thesis_report(
    merged_dfs: Dict[str, pd.DataFrame],
    toolkit_validation_info: Dict[str, Any],
    rq1_res: Dict[str, Any],
    rq2_res: Dict[str, Any],
    rq3_res: Dict[str, Any],
    report_path: Path | None = None,
) -> Path:
    """
    Generate the comprehensive final report `reports/final_thesis_report.md`
    synthesizing all 7 workflows, real on-chain dataset provenance, and data-driven findings for RQ1, RQ2, and RQ3.
    """
    out_path = report_path or (PROJECT_ROOT / "reports" / "final_thesis_report.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sample_pool_key = next(iter(merged_dfs.keys()))
    sample_cols = list(merged_dfs[sample_pool_key].columns)

    tk_line = (
        f"Đã đối chiếu `{toolkit_validation_info.get('n_matched_snapshots', 0)}` snapshot block từ repo toolkit với dữ liệu thật từ The Graph Subgraph trên pool `wsteth_eth_001`: sai lệch tỷ giá trung vị chỉ bằng **`{toolkit_validation_info.get('median_rel_price_diff', 0.0)*100:.4f}%`**."
        if toolkit_validation_info
        else "Đã kiểm tra bộ dữ liệu mẫu từ repo toolkit."
    )

    lines = [
        "# Báo cáo Tổng hợp Đồ án: Phân tích & Dự báo Impermanent Loss (IL) / LVR của Liquidity Provider trên Uniswap v3",
        "",
        "## 1. Nguồn Dữ liệu Thực tế & Phương pháp Kiểm soát Chất lượng",
        "",
        "- **Uniswap v3 On-Chain Subgraph (`5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV`):** Truy vấn trực tiếp `Pool` và `PoolHourData` thật trên Ethereum Mainnet cho **4 pool** đại diện cho 3 cấu trúc thị trường:",
        "  1. `wsteth_eth_001` (`0x109830a1aaad605bbf02a9dfa7b0b92ec2fb7daa` — Correlated LST/ETH, fee tier 0.01%)",
        "  2. `weth_usdc_005` (`0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640` — High-Volume Volatile, fee tier 0.05%)",
        "  3. `weth_usdc_030` (`0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8` — Standard Volatile, fee tier 0.30%)",
        "  4. `usdc_usdt_001` (`0x3416cf6c708da44db2624d63ea0aaef7113527c6` — Stablecoin, fee tier 0.01%)",
        "- **Binance Vision Public Data:** Dữ liệu thật `ETHUSDT` và `USDCUSDT` (`1h`, xác thực SHA256 `.CHECKSUM`, tự động chuẩn hóa đơn vị `ms` trước 2025 và `µs` từ `2025-01-01`).",
        f"- **Đối chiếu chéo với bộ dữ liệu mẫu (`ilyamk/uniswap-v3-lp-strategy-toolkit`):** {tk_line}",
        "",
        "---",
        "",
        "## 2. Danh mục Cột của Bộ Dữ liệu Ghép (`merged_<pool>.parquet`) & Nguồn gốc",
        "",
        f"Tổng số cột trong file ghép chuẩn: **{len(sample_cols)} cột**.",
        "",
        "| Nhóm cột | Tên cột cụ thể | Nguồn gốc | Ý nghĩa |",
        "|---|---|---|---|",
        "| Khóa thời gian | `timestamp`, `period_start`, `cex_open_time`, `periodStartUnix` | Chuẩn hóa UTC (`1h`) | Thời điểm đóng khung giờ `t` (chống look-ahead bias) |",
        "| Trạng thái Pool | `liquidity`, `sqrtPrice`, `token0Price`, `token1Price`, `tick`, `tvlUSD` | The Graph Subgraph (`PoolHourData`) | Thanh khoản hoạt động on-chain, giá Q64.96, tỷ giá và TVL cuối giờ |",
        "| Dòng chảy & Phí AMM | `volumeToken0`, `volumeToken1`, `volumeUSD`, `feesUSD`, `txCount`, `swap_flow_imbalance` | The Graph Subgraph (`PoolHourData`) | Khối lượng, phí thu được, số giao dịch và mất cân bằng nội giờ |",
        "| OHLC Pool | `open`, `high`, `low`, `close`, `amm_price`, `amm_open`, `amm_high`, `amm_low`, `amm_close` | The Graph Subgraph (`PoolHourData`) | Giá mở/cao/thấp/đóng của Pool theo đơn vị đồng nhất |",
        "| Giá & Khối lượng CEX | `cex_open`, `cex_high`, `cex_low`, `cex_close`, `cex_volume`, `cex_quote_volume`, `cex_trades`, `eth_usd_price` | Binance Vision (`ETHUSDT`, `USDCUSDT`) | Giá và khối lượng khớp lệnh trên sàn tập trung Binance |",
        "| Biến động & Vi cấu trúc | `cex_realized_vol_1h`, `cex_downside_vol_1h`, `cex_jump_count_1h`, `cex_taker_buy_ratio` | Binance Vision & Pool OHLC | Biến động thực tế nội giờ, biến động âm, bước nhảy giá và tỷ lệ mua chủ động |",
        "| Chênh lệch Liên thị trường | `amm_cex_spread_rel`, `usdc_usdt_close`, `stablecoin_deviation` | Ghép AMM + Binance (`ETHUSDT`, `USDCUSDT`) | Độ lệch giá tương đối AMM–CEX và độ lệch peg stablecoin |",
        "",
        "---",
        "",
        "## 3. Tóm tắt Kết quả Nghiên cứu Thực nghiệm (Trên Dữ liệu On-Chain Thật)",
        "",
        "### 3.1 Kết quả RQ1 (Giải thích các yếu tố ảnh hưởng đến IL, LVR và Net Return)",
        "",
        rq1_res["descriptive_by_regime"].to_markdown(index=False),
        "",
        "**Hồi quy Tác nhân Thị trường tại Độ rộng Cố định Chuẩn (`All_Pools_Fixed_Width`):**",
        "",
        rq1_res["fixed_width_reg"][rq1_res["fixed_width_reg"]["sample_group"] == "All_Pools_Fixed_Width"].to_markdown(index=False)
        if "fixed_width_reg" in rq1_res and not rq1_res["fixed_width_reg"].empty
        else "",
        "",
        "**Kết luận Kiểm định Giả thuyết RQ1:**",
        *rq1_res["conclusions"],
        "",
        "### 3.2 Kết quả RQ2 (Dự báo Phân phối IL trên Tập Test Ngoại mẫu: Analytical Baseline vs Pure ML vs Hybrid Ensemble)",
        "",
        rq2_res["summary_df"][
            [
                "pool_key",
                "horizon",
                "n_folds",
                "purge_hours",
                "n_test",
                "n_eff_test",
                "baseline_rmse",
                "pure_ml_rmse",
                "pure_ml_improvement_pct",
                "ml_rmse",
                "rmse_improvement_pct",
                "hybrid_alpha_mean",
                "dm_stat",
                "dm_p_value",
                "baseline_pinball_q_90",
                "ml_pinball_q_90",
                "ml_raw_coverage_q_90",
                "ml_coverage_q_90",
            ]
        ].to_markdown(index=False),
        "",
        "**Kết luận Kiểm định Giả thuyết RQ2:**",
        *rq2_res["conclusions"],
        "",
        "### 3.3 Kết quả RQ3 (Backtest Chiến lược LP Động: Unhedged `Fee - IL` & Delta-Hedged `Fee - LVR`)",
        "",
        rq3_res["summary_df"].to_markdown(index=False),
        "",
        "**Phân tích Độ nhạy Chi phí Gas (`5 Gwei` vs `20 Gwei` vs `60 Gwei`):**",
        "",
        rq3_res["gas_sensitivity_df"].to_markdown(index=False)
        if "gas_sensitivity_df" in rq3_res and not rq3_res["gas_sensitivity_df"].empty
        else "",
        "",
        "**Kết luận Kiểm định Giả thuyết RQ3:**",
        *rq3_res["conclusions"],
        "",
        "---",
        "",
        "## 4. Các Giả định & Hạn chế Thực nghiệm",
        "- **Phí giao dịch của vị thế mô phỏng:** Được tính bằng công thức tỷ phần thanh khoản hoạt động thực tế trên on-chain `feesUSD * (L_pos_raw / (L_pool_raw + L_pos_raw))` khi giá nằm trong vùng $[P_a, P_b]$.",
        "- **Chi phí Gas:** Sử dụng tham số cơ sở `gas_price_gwei = 20.0` điều chỉnh theo xung lượng giao dịch (`feat_gas_price_gwei`); có thể kết nối bảng `blocks.base_fee_per_gas` từ Ethereum BigQuery nếu mở rộng sang giai đoạn tối ưu thời điểm gửi lệnh theo block.",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def run_full_pipeline() -> Dict[str, Any]:
    """Run all 7 workflows of the thesis project end-to-end on real Subgraph + Binance data."""
    logger.info("=== [Quy trình 1] Loading project and pool configurations ===")
    load_environment()
    config = load_config()
    pools_cfg = load_pools_config()

    logger.info("=== [Quy trình 2] Acquiring real Binance CEX & real Uniswap v3 Subgraph data ===")
    cex_1h_map, cex_sources = acquire_cex_data(config)
    pool_dfs, pool_sources, toolkit_val_info = acquire_pool_data(config, pools_cfg)

    source_quality_checks: List[Dict[str, Any]] = []
    for sym, c_df in cex_1h_map.items():
        source_quality_checks.append(
            check_timeseries_quality(c_df, name=f"Binance_{sym}_1h", price_col="cex_close", volume_col="cex_volume")
        )
    for p_key, p_df in pool_dfs.items():
        source_quality_checks.append(
            check_timeseries_quality(p_df, name=f"Uniswap_{p_key}_1h", price_col="close", volume_col="volumeUSD")
        )

    merged_dfs: Dict[str, pd.DataFrame] = {}
    cross_checks: List[Dict[str, Any]] = []
    usdc_df = cex_1h_map.get("USDCUSDT")
    eth_df = cex_1h_map.get("ETHUSDT")

    for pool_key, p_df in pool_dfs.items():
        p_cfg = pools_cfg["pools"][pool_key]
        ref_sym = p_cfg.get("cex_reference_symbol", "ETHUSDT")
        merged = merge_pool_and_cex_data(
            pool_df=p_df,
            cex_df=cex_1h_map[ref_sym],
            pool_key=pool_key,
            pool_cfg=p_cfg,
            usdc_cex_df=usdc_df,
            eth_cex_df=eth_df,
        )
        save_merged_dataset(
            merged_df=merged,
            pool_key=pool_key,
            pool_cfg=p_cfg,
            data_sources_info={
                "pool_source": pool_sources[pool_key],
                "cex_source": cex_sources[ref_sym],
            },
        )
        merged_dfs[pool_key] = merged
        source_quality_checks.append(
            check_timeseries_quality(merged, name=f"Merged_{pool_key}_1h", price_col="amm_price", volume_col="volumeUSD")
        )
        cross_checks.append(check_merged_cross_consistency(merged, pool_key=pool_key, category=p_cfg["category"]))

    dq_report = write_data_quality_report(source_quality_checks, cross_checks)
    logger.info("Data quality report saved to %s", dq_report)

    logger.info("=== [Quy trình 3] Engineering strictly causal features & forward targets ===")
    featured_dfs: Dict[str, pd.DataFrame] = {}
    gas_gwei = float(config["lp_simulation"]["gas_price_gwei"])
    init_cap = float(config["lp_simulation"]["initial_capital_usd"])
    horizons_hours = config["modeling"]["horizons_hours"]
    train_ratio = float(config["modeling"]["split_ratios"]["train"])

    for pool_key, m_df in merged_dfs.items():
        cat = str(m_df["pool_category"].iloc[0])
        default_w = (
            float(config["backtest"]["default_range_width_volatile"])
            if cat == "volatile"
            else float(config["backtest"]["default_range_width_correlated"])
        )
        ex_thresh = (
            float(config["modeling"]["il_exceedance_thresholds"]["volatile_pool"])
            if cat == "volatile"
            else float(config["modeling"]["il_exceedance_thresholds"]["correlated_pool"])
        )
        feat_df = engineer_pool_features(m_df, default_range_width=default_w, gas_price_gwei=gas_gwei)
        feat_df = assign_market_regimes(
            feat_df,
            train_end_idx=int(len(feat_df) * train_ratio),
            low_q=float(config["modeling"]["regime_quantiles"]["low_vol_upper"]),
            high_q=float(config["modeling"]["regime_quantiles"]["high_vol_lower"]),
        )
        feat_df = attach_forward_targets(
            feat_df,
            range_width=default_w,
            horizons_hours=horizons_hours,
            exceedance_threshold=ex_thresh,
            v0_usd=init_cap,
        )
        featured_dfs[pool_key] = feat_df

    panel_df = build_position_panel_dataset(
        featured_dfs=featured_dfs,
        range_widths_pct=[float(w) for w in config["lp_simulation"]["range_widths_pct"]],
        horizon_hours=24,
        stride_hours=24,
        v0_usd=init_cap,
    )

    logger.info("=== [Quy trình 4] Running RQ1 Econometric, Quantile & TreeSHAP Analysis ===")
    rq1_res = execute_rq1_workflow(panel_df, random_seed=int(config["project"]["random_seed"]))

    logger.info("=== [Quy trình 5] Running RQ2 Distributional IL Forecasting (1d, 7d, 30d) ===")
    rq2_res = execute_rq2_workflow(featured_dfs, config=config)

    logger.info("=== [Quy trình 6] Running RQ3 Cost-Aware Dynamic LP Strategy Backtesting ===")
    rq3_res = execute_rq3_workflow(
        test_predictions_1d=rq2_res["test_predictions_1d"],
        val_thresholds_1d=rq2_res["val_thresholds_1d"],
        config=config,
    )

    logger.info("=== [Quy trình 7] Generating Final Synthesis Report ===")
    final_report = write_final_thesis_report(merged_dfs, toolkit_val_info, rq1_res, rq2_res, rq3_res)
    logger.info("Pipeline completed successfully! Final report: %s", final_report)

    return {
        "merged_dfs": merged_dfs,
        "featured_dfs": featured_dfs,
        "panel_df": panel_df,
        "rq1": rq1_res,
        "rq2": rq2_res,
        "rq3": rq3_res,
        "final_report": final_report,
    }


if __name__ == "__main__":
    run_full_pipeline()
