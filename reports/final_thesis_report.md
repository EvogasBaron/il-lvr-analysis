# Báo cáo Tổng hợp Đồ án: Phân tích & Dự báo Impermanent Loss (IL) / LVR của Liquidity Provider trên Uniswap v3

## 1. Nguồn Dữ liệu Thực tế & Phương pháp Kiểm soát Chất lượng

- **Uniswap v3 On-Chain Subgraph (`5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV`):** Truy vấn trực tiếp `Pool` và `PoolHourData` thật trên Ethereum Mainnet cho **4 pool** đại diện cho 3 cấu trúc thị trường:
  1. `wsteth_eth_001` (`0x109830a1aaad605bbf02a9dfa7b0b92ec2fb7daa` — Correlated LST/ETH, fee tier 0.01%)
  2. `weth_usdc_005` (`0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640` — High-Volume Volatile, fee tier 0.05%)
  3. `weth_usdc_030` (`0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8` — Standard Volatile, fee tier 0.30%)
  4. `usdc_usdt_001` (`0x3416cf6c708da44db2624d63ea0aaef7113527c6` — Stablecoin, fee tier 0.01%)
- **Binance Vision Public Data:** Dữ liệu thật `ETHUSDT` và `USDCUSDT` (`1h`, xác thực SHA256 `.CHECKSUM`, tự động chuẩn hóa đơn vị `ms` trước 2025 và `µs` từ `2025-01-01`).
- **Đối chiếu chéo với bộ dữ liệu mẫu (`ilyamk/uniswap-v3-lp-strategy-toolkit`):** Đã đối chiếu `217` snapshot block từ repo toolkit với dữ liệu thật từ The Graph Subgraph trên pool `wsteth_eth_001`: sai lệch tỷ giá trung vị chỉ bằng **`0.0003%`**.

---

## 2. Danh mục Cột của Bộ Dữ liệu Ghép (`merged_<pool>.parquet`) & Nguồn gốc

Tổng số cột trong file ghép chuẩn: **57 cột**.

| Nhóm cột | Tên cột cụ thể | Nguồn gốc | Ý nghĩa |
|---|---|---|---|
| Khóa thời gian | `timestamp`, `period_start`, `cex_open_time`, `periodStartUnix` | Chuẩn hóa UTC (`1h`) | Thời điểm đóng khung giờ `t` (chống look-ahead bias) |
| Trạng thái Pool | `liquidity`, `sqrtPrice`, `token0Price`, `token1Price`, `tick`, `tvlUSD` | The Graph Subgraph (`PoolHourData`) | Thanh khoản hoạt động on-chain, giá Q64.96, tỷ giá và TVL cuối giờ |
| Dòng chảy & Phí AMM | `volumeToken0`, `volumeToken1`, `volumeUSD`, `feesUSD`, `txCount`, `swap_flow_imbalance` | The Graph Subgraph (`PoolHourData`) | Khối lượng, phí thu được, số giao dịch và mất cân bằng nội giờ |
| OHLC Pool | `open`, `high`, `low`, `close`, `amm_price`, `amm_open`, `amm_high`, `amm_low`, `amm_close` | The Graph Subgraph (`PoolHourData`) | Giá mở/cao/thấp/đóng của Pool theo đơn vị đồng nhất |
| Giá & Khối lượng CEX | `cex_open`, `cex_high`, `cex_low`, `cex_close`, `cex_volume`, `cex_quote_volume`, `cex_trades`, `eth_usd_price` | Binance Vision (`ETHUSDT`, `USDCUSDT`) | Giá và khối lượng khớp lệnh trên sàn tập trung Binance |
| Biến động & Vi cấu trúc | `cex_realized_vol_1h`, `cex_downside_vol_1h`, `cex_jump_count_1h`, `cex_taker_buy_ratio` | Binance Vision & Pool OHLC | Biến động thực tế nội giờ, biến động âm, bước nhảy giá và tỷ lệ mua chủ động |
| Chênh lệch Liên thị trường | `amm_cex_spread_rel`, `usdc_usdt_close`, `stablecoin_deviation` | Ghép AMM + Binance (`ETHUSDT`, `USDCUSDT`) | Độ lệch giá tương đối AMM–CEX và độ lệch peg stablecoin |

---

## 3. Tóm tắt Kết quả Nghiên cứu Thực nghiệm (Trên Dữ liệu On-Chain Thật)

### 3.1 Kết quả RQ1 (Giải thích các yếu tố ảnh hưởng đến IL, LVR và Net Return)

| pool_key       | pool_category   | market_regime   |   n_obs |   median_il_pct |   iqr_il_pct |   mean_il_pct |   p95_il_pct |   mean_lvr_pct |   mean_fee_pct |   mean_net_return_pct |   mean_hedged_return_pct |   mean_oor_pct |
|:---------------|:----------------|:----------------|--------:|----------------:|-------------:|--------------:|-------------:|---------------:|---------------:|----------------------:|-------------------------:|---------------:|
| usdc_usdt_001  | stable          | High-Vol        |    3732 |     1.03515e-05 |  5.48391e-05 |   0.00346409  |  0.000532147 |    9.353e-05   |    0.0247763   |           0.0213123   |              0.0246828   |     0.118346   |
| usdc_usdt_001  | stable          | Low-Vol         |    1512 |     6.88447e-07 |  4.35718e-06 |   1.19836e-05 |  4.38304e-05 |    3.75978e-06 |    9.03604e-05 |           7.83769e-05 |              8.66007e-05 |     0          |
| usdc_usdt_001  | stable          | Normal-Vol      |    1926 |     2.30108e-06 |  1.17886e-05 |   0.00837325  |  0.000119493 |    1.15924e-05 |    0.0298443   |           0.0214711   |              0.0298328   |     0.0843718  |
| weth_usdc_005  | volatile        | High-Vol        |    2106 |     0.278499    |  1.09297     |   0.904086    |  3.88848     |    1.11587     |    0.779276    |          -0.12481     |             -0.336595    |    22.0264     |
| weth_usdc_005  | volatile        | Low-Vol         |    3384 |     0.0492422   |  0.293731    |   0.327979    |  1.72484     |    0.328795    |    0.261112    |          -0.0668675   |             -0.0676828   |    10.4265     |
| weth_usdc_005  | volatile        | Normal-Vol      |    2832 |     0.135716    |  0.653763    |   0.580552    |  2.68633     |    0.617393    |    0.446494    |          -0.134058    |             -0.170899    |    16.5843     |
| weth_usdc_030  | volatile        | High-Vol        |    2124 |     0.254946    |  1.0941      |   0.902534    |  3.81032     |    1.15197     |    0.912781    |           0.0102471   |             -0.239185    |    21.6376     |
| weth_usdc_030  | volatile        | Low-Vol         |    3426 |     0.052565    |  0.308404    |   0.35138     |  1.83269     |    0.338831    |    0.260058    |          -0.0913221   |             -0.0787731   |     9.94235    |
| weth_usdc_030  | volatile        | Normal-Vol      |    2778 |     0.128088    |  0.559152    |   0.520777    |  2.42044     |    0.603057    |    0.475208    |          -0.045569    |             -0.127849    |    14.5533     |
| wsteth_eth_001 | correlated      | High-Vol        |    1122 |     9.15402e-06 |  4.92956e-05 |   0.000158055 |  0.000534163 |    0.000182693 |    0.00459965  |           0.0044416   |              0.00441696  |     0          |
| wsteth_eth_001 | correlated      | Low-Vol         |    1398 |     3.12816e-06 |  1.28163e-05 |   1.7809e-05  |  7.79274e-05 |    2.6443e-05  |    0.00146548  |           0.00144767  |              0.00143904  |     0          |
| wsteth_eth_001 | correlated      | Normal-Vol      |    1200 |     3.66247e-06 |  1.77023e-05 |   7.57587e-05 |  0.000134835 |    4.17474e-05 |    0.0108951   |           0.0108193   |              0.0108533   |     0.00694444 |

**Hồi quy Tác nhân Thị trường tại Độ rộng Cố định Chuẩn (`All_Pools_Fixed_Width`):**

| sample_group          | dependent_var      | term                          |         coef |     std_err |     t_stat |     p_value |       r2 |    adj_r2 |   n_obs |
|:----------------------|:-------------------|:------------------------------|-------------:|------------:|-----------:|------------:|---------:|----------:|--------:|
| All_Pools_Fixed_Width | IL_Magnitude       | Intercept                     | -0.00026323  | 0.000136031 | -1.93507   | 0.0529816   | 0.162855 | 0.161393  |    4590 |
| All_Pools_Fixed_Width | IL_Magnitude       | C(pool_key)[T.weth_usdc_005]  | -0.000312496 | 0.00062918  | -0.496671  | 0.619421    | 0.162855 | 0.161393  |    4590 |
| All_Pools_Fixed_Width | IL_Magnitude       | C(pool_key)[T.weth_usdc_030]  |  4.3899e-05  | 0.00066159  |  0.0663538 | 0.947096    | 0.162855 | 0.161393  |    4590 |
| All_Pools_Fixed_Width | IL_Magnitude       | C(pool_key)[T.wsteth_eth_001] | -0.000108551 | 7.97898e-05 | -1.36046   | 0.173685    | 0.162855 | 0.161393  |    4590 |
| All_Pools_Fixed_Width | IL_Magnitude       | feat_rvol_24h                 |  0.0946076   | 0.0168038   |  5.63013   | 1.80076e-08 | 0.162855 | 0.161393  |    4590 |
| All_Pools_Fixed_Width | IL_Magnitude       | feat_volume_tvl_ratio_24h     |  0.00827772  | 0.00339469  |  2.43843   | 0.0147512   | 0.162855 | 0.161393  |    4590 |
| All_Pools_Fixed_Width | IL_Magnitude       | feat_jump_intensity_24h       | -0.000128169 | 5.06789e-05 | -2.52903   | 0.0114377   | 0.162855 | 0.161393  |    4590 |
| All_Pools_Fixed_Width | IL_Magnitude       | feat_flow_imbalance_24h       | -0.000885689 | 0.000382523 | -2.31538   | 0.0205919   | 0.162855 | 0.161393  |    4590 |
| All_Pools_Fixed_Width | IL_Magnitude       | feat_amm_cex_spread_abs       |  0.0776151   | 0.0447215   |  1.73552   | 0.0826484   | 0.162855 | 0.161393  |    4590 |
| All_Pools_Fixed_Width | LVR_Cumulative     | Intercept                     | -0.000159439 | 7.32378e-05 | -2.17701   | 0.0294802   | 0.573686 | 0.572941  |    4590 |
| All_Pools_Fixed_Width | LVR_Cumulative     | C(pool_key)[T.weth_usdc_005]  | -0.00181875  | 0.000316432 | -5.74766   | 9.04846e-09 | 0.573686 | 0.572941  |    4590 |
| All_Pools_Fixed_Width | LVR_Cumulative     | C(pool_key)[T.weth_usdc_030]  | -0.00133993  | 0.000335583 | -3.99284   | 6.52871e-05 | 0.573686 | 0.572941  |    4590 |
| All_Pools_Fixed_Width | LVR_Cumulative     | C(pool_key)[T.wsteth_eth_001] | -9.24758e-05 | 4.24846e-05 | -2.17669   | 0.0295036   | 0.573686 | 0.572941  |    4590 |
| All_Pools_Fixed_Width | LVR_Cumulative     | feat_rvol_24h                 |  0.162289    | 0.00866548  | 18.7282    | 2.91804e-78 | 0.573686 | 0.572941  |    4590 |
| All_Pools_Fixed_Width | LVR_Cumulative     | feat_volume_tvl_ratio_24h     |  0.0071897   | 0.00174091  |  4.12984   | 3.63012e-05 | 0.573686 | 0.572941  |    4590 |
| All_Pools_Fixed_Width | LVR_Cumulative     | feat_jump_intensity_24h       | -0.000177343 | 2.64868e-05 | -6.69553   | 2.14896e-11 | 0.573686 | 0.572941  |    4590 |
| All_Pools_Fixed_Width | LVR_Cumulative     | feat_flow_imbalance_24h       | -0.000821315 | 0.00022397  | -3.66709   | 0.000245331 | 0.573686 | 0.572941  |    4590 |
| All_Pools_Fixed_Width | LVR_Cumulative     | feat_amm_cex_spread_abs       |  0.017745    | 0.0259618   |  0.683503  | 0.494289    | 0.573686 | 0.572941  |    4590 |
| All_Pools_Fixed_Width | Net_Return_vs_HODL | Intercept                     | -0.000206114 | 0.000213114 | -0.967153  | 0.333468    | 0.036702 | 0.0350198 |    4590 |
| All_Pools_Fixed_Width | Net_Return_vs_HODL | C(pool_key)[T.weth_usdc_005]  | -0.000613584 | 0.000691388 | -0.887467  | 0.374828    | 0.036702 | 0.0350198 |    4590 |
| All_Pools_Fixed_Width | Net_Return_vs_HODL | C(pool_key)[T.weth_usdc_030]  | -0.000758263 | 0.000681547 | -1.11256   | 0.265897    | 0.036702 | 0.0350198 |    4590 |
| All_Pools_Fixed_Width | Net_Return_vs_HODL | C(pool_key)[T.wsteth_eth_001] |  0.000347749 | 0.000155259 |  2.23979   | 0.0251043   | 0.036702 | 0.0350198 |    4590 |
| All_Pools_Fixed_Width | Net_Return_vs_HODL | feat_rvol_24h                 |  0.00314829  | 0.0181979   |  0.173003  | 0.862649    | 0.036702 | 0.0350198 |    4590 |
| All_Pools_Fixed_Width | Net_Return_vs_HODL | feat_volume_tvl_ratio_24h     | -0.00453123  | 0.00333396  | -1.35912   | 0.17411     | 0.036702 | 0.0350198 |    4590 |
| All_Pools_Fixed_Width | Net_Return_vs_HODL | feat_jump_intensity_24h       |  0.000150913 | 7.46868e-05 |  2.02061   | 0.0433201   | 0.036702 | 0.0350198 |    4590 |
| All_Pools_Fixed_Width | Net_Return_vs_HODL | feat_flow_imbalance_24h       |  6.03823e-05 | 0.000402149 |  0.150149  | 0.880647    | 0.036702 | 0.0350198 |    4590 |
| All_Pools_Fixed_Width | Net_Return_vs_HODL | feat_amm_cex_spread_abs       |  0.381571    | 0.202988    |  1.87977   | 0.0601388   | 0.036702 | 0.0350198 |    4590 |

**Kết luận Kiểm định Giả thuyết RQ1:**
- **H1.1 (Biến động giá làm tăng IL & LVR):** **Ủng hộ (Supported)** — Biến `vol_x_narrow` trong phương trình `IL_Magnitude` có hệ số $\beta = 0.001941$ ($t = 18.98, p = 2.419e-80$, sai số chuẩn phân cụm theo thời gian). Trên mặt cắt độ rộng cố định chuẩn (không nhân bản $W$), `feat_rvol_24h` vẫn mang hệ số dương có ý nghĩa thống kê ($\beta = 0.094608, t = 5.63, p = 1.801e-08$).
- **H1.2 (Vùng thanh khoản hẹp khuếch đại rủi ro đuôi):** **Ủng hộ (Supported)** — Hệ số tương tác `vol_x_narrow` tăng từ $\beta_{0.50} = 0.000265$ ở trung vị lên $\beta_{0.95} = 0.004772$ ($p = 0$) ở phân vị 95%.
- **H1.3 (Stable/Correlated pool có IL thấp hơn Volatile pool):** **Ủng hộ (Supported)** — IL 24h trung vị (và trung bình) của nhóm Stable/Correlated là `0.00000%` (mean `0.0020%`), thấp hơn rõ rệt so với `0.1498%` (mean `0.5979%`) của nhóm Volatile pool.
- **H1.4 (Tác động của tỷ lệ Volume/TVL lên Net Return):** **Bác bỏ theo chiều ngược (dòng lệnh arbitrage độc hại / lựa chọn bất lợi làm tăng IL nhanh hơn phí)** — Hệ số của `feat_volume_tvl_ratio_24h` trong phương trình `Net_Return_vs_HODL` là $\beta = -0.007235$ ($p = 0.03297$).

### 3.2 Kết quả RQ2 (Dự báo Phân phối IL trên Tập Test Ngoại mẫu: Analytical Baseline vs Pure ML vs Hybrid Ensemble)

| pool_key       | horizon   |   n_folds |   purge_hours |   n_test |   n_eff_test |   baseline_rmse |   pure_ml_rmse |   pure_ml_improvement_pct |     ml_rmse |   rmse_improvement_pct |   hybrid_alpha_mean |    dm_stat |   dm_p_value |   baseline_pinball_q_90 |   ml_pinball_q_90 |   ml_raw_coverage_q_90 |   ml_coverage_q_90 |
|:---------------|:----------|----------:|--------------:|---------:|-------------:|----------------:|---------------:|--------------------------:|------------:|-----------------------:|--------------------:|-----------:|-------------:|------------------------:|------------------:|-----------------------:|-------------------:|
| wsteth_eth_001 | 1d        |         8 |            24 |     8921 |          371 |     4.35699e-05 |    4.33504e-05 |                0.503709   | 4.3415e-05  |               0.355519 |             0.8125  |  1.54957   |  0.121281    |             2.51496e-06 |       2.5552e-06  |               0.874229 |           0.867952 |
| wsteth_eth_001 | 7d        |         8 |           168 |     8835 |           52 |     5.17092e-05 |    5.05788e-05 |                2.18606    | 5.03466e-05 |               2.63525  |             0.90625 |  1.20487   |  0.228285    |             5.36936e-06 |       4.71378e-06 |               0.889643 |           0.861121 |
| wsteth_eth_001 | 30d       |         8 |           720 |     7772 |           10 |     9.9428e-05  |    7.18666e-05 |               27.7199     | 6.75532e-05 |              32.0582   |             0.78125 |  4.04831   |  5.20892e-05 |             4.11798e-05 |       1.34422e-05 |               0.918425 |           0.833505 |
| weth_usdc_005  | 1d        |         8 |            24 |    19968 |          832 |     0.0068493   |    0.00568933  |               16.9356     | 0.00569031  |              16.9212   |             1       |  2.85805   |  0.00426701  |             0.00128438  |       0.00118026  |               0.893379 |           0.894231 |
| weth_usdc_005  | 7d        |         8 |           168 |    19882 |          118 |     0.0289126   |    0.022647    |               21.6708     | 0.0235479   |              18.5548   |             0.85    |  2.76461   |  0.0057043   |             0.00631704  |       0.00672618  |               0.863092 |           0.866211 |
| weth_usdc_005  | 30d       |         8 |           720 |    19551 |           27 |     0.0694941   |    0.0594873   |               14.3995     | 0.0641572   |               7.67964  |             0.675   |  0.863025  |  0.388134    |             0.014751    |       0.0147113   |               0.776891 |           0.915503 |
| weth_usdc_030  | 1d        |         8 |            24 |    19977 |          832 |     0.00685809  |    0.00573834  |               16.3274     | 0.0058117   |              15.2577   |             0.75625 |  2.65747   |  0.00787933  |             0.00128696  |       0.00123296  |               0.917605 |           0.906593 |
| weth_usdc_030  | 7d        |         8 |           168 |    19890 |          118 |     0.0289047   |    0.023864    |               17.4392     | 0.0257605   |              10.8778   |             0.7125  |  1.5868    |  0.112575    |             0.00631053  |       0.00649307  |               0.95093  |           0.917044 |
| weth_usdc_030  | 30d       |         8 |           720 |    19559 |           27 |     0.0694703   |    0.0682365   |                1.77604    | 0.0696785   |              -0.299682 |             0.64375 | -0.0285229 |  0.977245    |             0.0147401   |       0.0166649   |               0.921929 |           0.934761 |
| usdc_usdt_001  | 1d        |         8 |            24 |    17201 |          716 |     6.0094e-06  |    5.41822e-06 |                9.83746    | 5.48085e-06 |               8.79539  |             0.775   |  1.61941   |  0.105378    |             8.68466e-07 |       1.09745e-05 |               0.825243 |           0.889541 |
| usdc_usdt_001  | 7d        |         8 |           168 |    17115 |          101 |     0.000669922 |    0.000669936 |               -0.00209947 | 0.000670007 |              -0.012706 |             0.8     | -0.193475  |  0.84659     |             2.63472e-05 |       3.7934e-05  |               0.806427 |           0.888285 |
| usdc_usdt_001  | 30d       |         8 |           720 |    16742 |           23 |     0.00146747  |    0.0014656   |                0.12733    | 0.00146527  |               0.149611 |             0.83125 |  1.45456   |  0.145809    |             7.15874e-05 |       6.87079e-05 |               0.819496 |           0.869251 |

**Kết luận Kiểm định Giả thuyết RQ2:**
- **H2.1 (Tách bạch `Pure_ML` và `Hybrid_Ensemble` vs `Analytical_Baseline` ở horizon 1d qua 8 fold Walk-Forward):** Trên chuỗi Test ngoại mẫu tổng hợp qua 8 fold Expanding-Window (cách ly `purge_hours = 24h`), mô hình **`Pure_ML`** độc lập (chỉ dùng đặc trưng chuỗi thời gian, không dùng đầu vào Baseline) đạt RMSE thấp hơn Baseline giải tích trên **4/4 pool**, trong khi mô hình kết hợp **`Hybrid_Ensemble`** (`ML + Baseline` với trọng số $\alpha$ chọn trên tập Validation) vượt Baseline giải tích trên **4/4 pool** (**2/4 pool** đạt ý nghĩa thống kê Diebold-Mariano HLN $p < 0.10$). Việc báo cáo song song cả 3 mô hình đảm bảo tính minh bạch học thuật tuyệt đối.
- **H2.2 (Suy giảm theo chân trời xa & Mở rộng mẫu Walk-Forward):** Nhờ mở rộng dữ liệu đa chu kỳ 2021–2025 và đánh giá qua 8 fold Walk-Forward, số mẫu độc lập không chồng lấn ở chân trời 30 ngày (`720h`) đạt $n_{\text{eff}} \in [10, 27]$ (vượt ngưỡng tối thiểu $n_{\text{eff}} \ge 10$ để kiểm định DM-HLN hợp lệ; mọi trường hợp $n_{\text{eff}} < 10$ đều tự động trả về `NaN`).
- **H2.3 (Hiệu chỉnh Conformal theo từng Fold cho Dự báo Phân vị):** Trước khi hiệu chỉnh, phân vị `q_90` có độ phủ trung bình trên tập Test là `87.1%`. Sau khi áp dụng **Split Conformal Quantile Calibration** tái ước lượng trên tập Validation của từng fold Walk-Forward (không chạm tập Test), độ phủ thực nghiệm đạt **`88.7%`** (mục tiêu lý thuyết `90.0%`).

### 3.3 Kết quả RQ3 (Backtest Chiến lược LP Động: Unhedged `Fee - IL` & Delta-Hedged `Fee - LVR`)

| pool_key       | strategy           |   n_folds |   net_return_vs_hodl_pct |   net_return_ci95_pct |   hedged_net_return_pct |   cum_fees_pct |   realized_il_pct |   cum_lvr_bench_pct |   tx_cost_gas_slippage_pct |   rebalance_count |   in_range_time_pct |   avg_active_cap_efficiency |   sharpe_vs_hodl |   sortino_vs_hodl |   max_drawdown_pct |   hourly_var95_pct |   hourly_cvar95_pct |
|:---------------|:-------------------|----------:|-------------------------:|----------------------:|------------------------:|---------------:|------------------:|--------------------:|---------------------------:|------------------:|--------------------:|----------------------------:|-----------------:|------------------:|-------------------:|-------------------:|--------------------:|
| wsteth_eth_001 | Static_LP          |         8 |                 0.724947 |              0.784227 |                0.736689 |       0.744506 |       -0.0195584  |          0.00781717 |                  0         |             0     |            100      |                   100.488   |         5.91946  |         57.933    |         0.0147361  |        0.000493037 |         0.00116415  |
| wsteth_eth_001 | Periodic_Rebalance |         8 |                -0.28272  |              0.7996   |               -0.284897 |       0.744371 |       -0.00563584 |          0.00781338 |                  1.02145   |             6     |            100      |                   100.488   |        -3.56887  |         -0.822571 |         0.797321   |        0.000102427 |         0.018638    |
| wsteth_eth_001 | IL_Min_Rule        |         8 |                 0.446585 |              0.653505 |                0.511819 |       0.664023 |       -0.0719527  |          0.0067193  |                  0.145485  |             0.875 |            100      |                    89.8949  |         4.0821   |         18.9085   |         0.0903631  |        0.00043549  |         0.00286078  |
| wsteth_eth_001 | Signal_Net_Utility |         8 |                 0.724947 |              0.784227 |                0.736689 |       0.744506 |       -0.0195584  |          0.00781717 |                  0         |             0     |            100      |                   100.488   |         5.91946  |         57.933    |         0.0147361  |        0.000493037 |         0.00116415  |
| weth_usdc_005  | Static_LP          |         8 |                 0.772672 |              7.41242  |               -3.2451   |       8.74111  |       -7.96844    |         11.9862     |                  0         |             0     |             41.0056 |                     8.38097 |         0.27383  |          0.257539 |        14.8661     |        0.408446    |         0.705467    |
| weth_usdc_005  | Periodic_Rebalance |         8 |                -5.57976  |              3.06393  |               -8.79961  |      17.0246   |      -20.6226     |         23.8425     |                  1.98174   |            14     |             93.2292 |                    19.0547  |        -1.16488  |         -0.968787 |        10.9482     |        0.208373    |         0.450101    |
| weth_usdc_005  | IL_Min_Rule        |         8 |                -4.09223  |              2.09146  |               -9.23831  |      13.7117   |      -13.7479     |         18.8939     |                  4.05608   |            24.25  |             99.995  |                    12.2392  |        -1.57401  |         -1.24986  |         8.03949    |        0.128368    |         0.27286     |
| weth_usdc_005  | Signal_Net_Utility |         8 |                 1.21129  |              4.48171  |               -6.79715  |      17.3294   |      -15.2862     |         23.2946     |                  0.831904  |             5     |             99.985  |                    15.7985  |         0.138448 |          0.170332 |         7.25878    |        0.161667    |         0.342177    |
| weth_usdc_030  | Static_LP          |         8 |                 0.691977 |              7.27871  |               -3.54191  |       8.81814  |       -8.12617    |         12.36       |                  0         |             0     |             46.108  |                     9.42383 |         0.297147 |          0.268056 |        14.304      |        0.378161    |         0.685434    |
| weth_usdc_030  | Periodic_Rebalance |         8 |                -1.27459  |              3.35467  |               -8.12713  |      18.5528   |      -17.9265     |         24.779      |                  1.90095   |            14     |             94.0433 |                    19.2211  |        -0.125563 |         -0.132263 |         8.43847    |        0.191715    |         0.425106    |
| weth_usdc_030  | IL_Min_Rule        |         8 |                -3.36298  |              2.48202  |               -7.68103  |      13.8735   |      -14.0142     |         18.3322     |                  3.22229   |            21.75  |             99.99   |                    12.1555  |        -1.13038  |         -0.841273 |         8.23393    |        0.119447    |         0.276133    |
| weth_usdc_030  | Signal_Net_Utility |         8 |                 1.17539  |              5.61896  |               -6.00462  |      18.5036   |      -16.5022     |         23.6822     |                  0.826002  |             5.5   |             99.98   |                    16.0335  |         0.229641 |          0.308979 |         8.54316    |        0.152247    |         0.342292    |
| usdc_usdt_001  | Static_LP          |         8 |                 0.491006 |              0.461117 |                0.485671 |       0.496984 |       -0.00597842 |          0.0113132  |                  0         |             0     |            100      |                   100.488   |        12.5114   |        136.904    |         0.00525634 |        0.000199739 |         0.000474504 |
| usdc_usdt_001  | Periodic_Rebalance |         8 |                -1.24481  |              0.58564  |               -1.24806  |       0.49698  |       -0.00807138 |          0.0113148  |                  1.73372   |            12     |            100      |                   100.488   |        -5.02548  |         -2.02748  |         1.61899    |        7.64485e-05 |         0.0163312   |
| usdc_usdt_001  | IL_Min_Rule        |         8 |                 0.370311 |              0.291582 |                0.367377 |       0.406385 |       -0.0073755  |          0.0103097  |                  0.0286986 |             0.25  |            100      |                    89.7255  |        11.8616   |         93.1151   |         0.0156414  |        0.000116289 |         0.000422445 |
| usdc_usdt_001  | Signal_Net_Utility |         8 |                 0.491006 |              0.461117 |                0.485671 |       0.496984 |       -0.00597842 |          0.0113132  |                  0         |             0     |            100      |                   100.488   |        12.5114   |        136.904    |         0.00525634 |        0.000199739 |         0.000474504 |

**Phân tích Độ nhạy Chi phí Gas (`5 Gwei` vs `20 Gwei` vs `60 Gwei`):**

| pool_key       | gas_scenario    | strategy           |   rebalance_count |   tx_cost_pct |   net_return_vs_hodl_pct |   hedged_net_return_pct |
|:---------------|:----------------|:-------------------|------------------:|--------------:|-------------------------:|------------------------:|
| wsteth_eth_001 | Low_Gas_5gwei   | Periodic_Rebalance |                 6 |      0.373464 |                1.07166   |                1.06812  |
| wsteth_eth_001 | Low_Gas_5gwei   | Signal_Net_Utility |                 0 |      0        |                1.43475   |                1.44179  |
| wsteth_eth_001 | Base_Gas_20gwei | Periodic_Rebalance |                 6 |      1.0435   |                0.401622  |                0.398088 |
| wsteth_eth_001 | Base_Gas_20gwei | Signal_Net_Utility |                 0 |      0        |                1.43475   |                1.44179  |
| wsteth_eth_001 | High_Gas_60gwei | Periodic_Rebalance |                 6 |      2.83026  |               -1.38514   |               -1.38868  |
| wsteth_eth_001 | High_Gas_60gwei | Signal_Net_Utility |                 0 |      0        |                1.43475   |                1.44179  |
| weth_usdc_005  | Low_Gas_5gwei   | Periodic_Rebalance |                14 |      0.842808 |                0.823613  |              -12.102    |
| weth_usdc_005  | Low_Gas_5gwei   | Signal_Net_Utility |                 5 |      0.329917 |               12.6311    |               -9.46581  |
| weth_usdc_005  | Base_Gas_20gwei | Periodic_Rebalance |                14 |      2.41114  |               -0.744719  |              -13.6703   |
| weth_usdc_005  | Base_Gas_20gwei | Signal_Net_Utility |                 5 |      0.96685  |               11.9941    |              -10.1027   |
| weth_usdc_005  | High_Gas_60gwei | Periodic_Rebalance |                14 |      6.59336  |               -4.92694   |              -17.8526   |
| weth_usdc_005  | High_Gas_60gwei | Signal_Net_Utility |                 5 |      2.59669  |               10.4132    |              -11.7524   |
| weth_usdc_030  | Low_Gas_5gwei   | Periodic_Rebalance |                14 |      0.832375 |                1.57      |              -11.2511   |
| weth_usdc_030  | Low_Gas_5gwei   | Signal_Net_Utility |                 5 |      0.316779 |               11.4479    |               -9.38423  |
| weth_usdc_030  | Base_Gas_20gwei | Periodic_Rebalance |                14 |      2.3746   |                0.0277803 |              -12.7933   |
| weth_usdc_030  | Base_Gas_20gwei | Signal_Net_Utility |                 5 |      0.916518 |               10.8482    |               -9.98397  |
| weth_usdc_030  | High_Gas_60gwei | Periodic_Rebalance |                14 |      6.48719  |               -4.08481   |              -16.9059   |
| weth_usdc_030  | High_Gas_60gwei | Signal_Net_Utility |                 5 |      2.65943  |               11.1797    |              -13.1034   |
| usdc_usdt_001  | Low_Gas_5gwei   | Periodic_Rebalance |                12 |      0.762205 |               -0.531818  |               -0.536142 |
| usdc_usdt_001  | Low_Gas_5gwei   | Signal_Net_Utility |                 0 |      0        |                0.236166  |                0.226073 |
| usdc_usdt_001  | Base_Gas_20gwei | Periodic_Rebalance |                12 |      2.14915  |               -1.91876   |               -1.92308  |
| usdc_usdt_001  | Base_Gas_20gwei | Signal_Net_Utility |                 0 |      0        |                0.236166  |                0.226073 |
| usdc_usdt_001  | High_Gas_60gwei | Periodic_Rebalance |                12 |      5.84766  |               -5.61728   |               -5.6216   |
| usdc_usdt_001  | High_Gas_60gwei | Signal_Net_Utility |                 0 |      0        |                0.236166  |                0.226073 |

**Kết luận Kiểm định Giả thuyết RQ3:**
- **H3.1 & H3.2 (Kiểm soát chi phí Gas/Slippage bằng ngưỡng lợi ích kỳ vọng):** Trên tập Test ngoại mẫu (sử dụng ngưỡng phân vị cố định từ tập Validation, không rò rỉ tương lai), `Signal_Net_Utility` đạt Unhedged Net Return cao hơn hoặc bằng `Periodic_Rebalance` trên **4/4 pool**, cao hơn hoặc bằng `Static_LP` trên **4/4 pool**, và đạt Delta-Hedged Net Return (`Fee - LVR - TxCost`) cao hơn hoặc bằng `Static_LP` trên **2/4 pool**.
- **H3.3 (Chính sách tối ưu Net Return vs Chính sách chỉ giảm IL):** **Ủng hộ (4/4 pool)** — Chiến lược `IL_Min_Rule` tái cân bằng trung bình `11.8` lần/fold (tiêu tốn `1.86%` vốn cho gas + slippage và hiện thực hóa lỗ IL), dẫn tới Net Return trung bình `-1.66%`, thấp hơn `Signal_Net_Utility` (`+0.90%`, Hedged Return `-2.89%`, trung bình `2.6` lần rebalance/fold).
- **H3.4 (Sự khác biệt giữa các cấu trúc Pool & So sánh Unhedged `Fee - IL` vs Delta-Hedged `Fee - LVR`):** Chiến lược dẫn đầu theo từng pool thực tế: `wsteth_eth_001`: **Static_LP** (Unhedged `+0.72%`, Hedged `+0.74%`), `weth_usdc_005`: **Signal_Net_Utility** (Unhedged `+1.21%`, Hedged `-6.80%`), `weth_usdc_030`: **Signal_Net_Utility** (Unhedged `+1.18%`, Hedged `-6.00%`), `usdc_usdt_001`: **Static_LP** (Unhedged `+0.49%`, Hedged `+0.49%`).

---

## 4. Các Giả định & Hạn chế Thực nghiệm
- **Phí giao dịch của vị thế mô phỏng:** Được tính bằng công thức tỷ phần thanh khoản hoạt động thực tế trên on-chain `feesUSD * (L_pos_raw / (L_pool_raw + L_pos_raw))` khi giá nằm trong vùng $[P_a, P_b]$.
- **Chi phí Gas:** Sử dụng tham số cơ sở `gas_price_gwei = 20.0` điều chỉnh theo xung lượng giao dịch (`feat_gas_price_gwei`); có thể kết nối bảng `blocks.base_fee_per_gas` từ Ethereum BigQuery nếu mở rộng sang giai đoạn tối ưu thời điểm gửi lệnh theo block.
