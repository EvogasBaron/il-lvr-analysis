# Báo cáo Thực nghiệm RQ1: Các yếu tố giải thích Impermanent Loss (IL), LVR và Lợi nhuận ròng LP

> **Phương pháp lấy mẫu & suy luận:** Sử dụng các cửa sổ 24 giờ **không chồng lấn** (`stride_hours = 24`) trên 4 pool thật từ Uniswap v3 Subgraph, sai số chuẩn phân cụm theo thời gian (`cluster-robust SE by timestamp` / Driscoll-Kraay cross-sectional clustering) để kiểm soát tương quan chéo giữa các độ rộng vùng thanh khoản và các pool tại cùng thời điểm.

## 1. Thống kê mô tả theo Pool và Chế độ Thị trường (Market Regime — Kèm Median/IQR & Hedged Return)

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

## 2. Ảnh hưởng của Độ rộng Vùng Thanh khoản (Range Width $\pm w$)

| pool_key       |   range_width_pct |   capital_efficiency |   median_il_pct |   mean_il_pct |   p95_il_pct |   mean_lvr_pct |   mean_fee_pct |   mean_net_return_pct |   mean_hedged_return_pct |   mean_oor_pct |   mean_cvar95_pct |
|:---------------|------------------:|---------------------:|----------------:|--------------:|-------------:|---------------:|---------------:|----------------------:|-------------------------:|---------------:|------------------:|
| usdc_usdt_001  |              0.01 |            200.494   |     2.66044e-05 |   0.00798333  |  0.000927203 |    0.000167647 |    0.0352517   |            0.0272683  |              0.035084    |      0.264993  |       0.0101814   |
| usdc_usdt_001  |              0.02 |            100.488   |     1.33341e-05 |   0.00685045  |  0.000464715 |    8.42822e-05 |    0.0228703   |            0.0160198  |              0.022786    |      0.163877  |       0.0089701   |
| usdc_usdt_001  |              0.05 |             40.469   |     5.37002e-06 |   0.00467651  |  0.000187154 |    3.40717e-05 |    0.0162481   |            0.0115716  |              0.0162141   |      0.0592748 |       0.00674446  |
| usdc_usdt_001  |              0.1  |             20.4386  |     2.71209e-06 |   0.00280997  |  9.45215e-05 |    1.72348e-05 |    0.0222261   |            0.0194161  |              0.0222089   |      0.0174338 |       0.0045033   |
| usdc_usdt_001  |              0.2  |             10.3787  |     1.3772e-06  |   0.00142866  |  4.79988e-05 |    8.75797e-06 |    0.0181874   |            0.0167588  |              0.0181787   |      0         |       0.00239684  |
| usdc_usdt_001  |              0.5  |              4.19818 |     5.57082e-07 |   0.00057994  |  1.94162e-05 |    3.54259e-06 |    0.0108081   |            0.0102282  |              0.0108046   |      0         |       0.000974613 |
| weth_usdc_005  |              0.01 |            200.494   |     0.664968    |   1.12779     |  3.77373     |    1.12205     |    0.918514    |           -0.209273   |             -0.203534    |     52.3552    |       1.47336     |
| weth_usdc_005  |              0.02 |            100.488   |     0.421037    |   0.957723    |  3.54097     |    1.01784     |    0.75616     |           -0.201563   |             -0.261678    |     31.1884    |       1.25943     |
| weth_usdc_005  |              0.05 |             40.469   |     0.169586    |   0.625738    |  2.81289     |    0.74535     |    0.502275    |           -0.123463   |             -0.243075    |      8.06597   |       0.825888    |
| weth_usdc_005  |              0.1  |             20.4386  |     0.085667    |   0.371918    |  1.65292     |    0.485356    |    0.313116    |           -0.058802   |             -0.17224     |      1.08748   |       0.490283    |
| weth_usdc_005  |              0.2  |             10.3787  |     0.0435204   |   0.196003    |  0.840008    |    0.272929    |    0.171445    |           -0.0245577  |             -0.101483    |      0.0480654 |       0.261909    |
| weth_usdc_005  |              0.5  |              4.19818 |     0.0175916   |   0.0791661   |  0.340781    |    0.113596    |    0.070449    |           -0.00871713 |             -0.0431467   |      0         |       0.106046    |
| weth_usdc_030  |              0.01 |            200.494   |     0.61252     |   1.10679     |  3.67255     |    1.14173     |    0.982767    |           -0.12402    |             -0.158963    |     49.961     |       1.42755     |
| weth_usdc_030  |              0.02 |            100.488   |     0.372481    |   0.938929    |  3.44013     |    1.02483     |    0.823329    |           -0.1156     |             -0.201498    |     28.9055    |       1.2146      |
| weth_usdc_030  |              0.05 |             40.469   |     0.150008    |   0.612346    |  2.70986     |    0.763919    |    0.555857    |           -0.056489   |             -0.208062    |      6.88641   |       0.786828    |
| weth_usdc_030  |              0.1  |             20.4386  |     0.0757605   |   0.361818    |  1.55497     |    0.488458    |    0.348817    |           -0.0130017  |             -0.139641    |      0.957613  |       0.465146    |
| weth_usdc_030  |              0.2  |             10.3787  |     0.0384713   |   0.192532    |  0.789567    |    0.273012    |    0.197712    |            0.00518025 |             -0.0753004   |      0.0690442 |       0.2483      |
| weth_usdc_030  |              0.5  |              4.19818 |     0.0155617   |   0.078314    |  0.31988     |    0.114178    |    0.0813108   |            0.00299683 |             -0.0328675   |      0         |       0.101183    |
| wsteth_eth_001 |              0.01 |            200.494   |     3.08262e-05 |   0.000251806 |  0.000766486 |    0.000250778 |    0.0160907   |            0.0158389  |              0.0158399   |      0.0134409 |       0.000883413 |
| wsteth_eth_001 |              0.02 |            100.488   |     1.54501e-05 |   0.000126205 |  0.000384163 |    0.00012578  |    0.0091943   |            0.00906809 |              0.00906852  |      0         |       0.000442762 |
| wsteth_eth_001 |              0.05 |             40.469   |     6.22218e-06 |   5.08263e-05 |  0.000154714 |    5.06549e-05 |    0.00393061  |            0.00387978 |              0.00387995  |      0         |       0.000178306 |
| wsteth_eth_001 |              0.1  |             20.4386  |     3.14247e-06 |   2.56694e-05 |  7.81374e-05 |    2.55829e-05 |    0.00203081  |            0.00200514 |              0.00200522  |      0         |       9.00476e-05 |
| wsteth_eth_001 |              0.2  |             10.3787  |     1.59575e-06 |   1.3035e-05  |  3.96787e-05 |    1.2991e-05  |    0.00104375  |            0.00103072 |              0.00103076  |      0         |       4.57215e-05 |
| wsteth_eth_001 |              0.5  |              4.19818 |     6.45477e-07 |   5.27264e-06 |  1.60505e-05 |    5.25484e-06 |    0.000425433 |            0.00042016 |              0.000420178 |      0         |       1.84889e-05 |

## 3. Hồi quy Bảng Tác động Cố định Toàn phần (Full Panel Fixed-Effects với Timestamp-Clustered SE)

| dependent_var      | term                          |         coef |     std_err |     t_stat |     p_value |        r2 |    adj_r2 |   n_obs |
|:-------------------|:------------------------------|-------------:|------------:|-----------:|------------:|----------:|----------:|--------:|
| IL_Magnitude       | Intercept                     |  0.00127755  | 0.000140918 |   9.06591  | 1.23564e-19 | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | C(pool_key)[T.weth_usdc_005]  |  0.00116715  | 0.000619123 |   1.88516  | 0.0594081   | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | C(pool_key)[T.weth_usdc_030]  |  0.00167297  | 0.000682269 |   2.45206  | 0.0142041   | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | C(pool_key)[T.wsteth_eth_001] | -0.000142616 | 7.28744e-05 |  -1.95701  | 0.0503461   | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | feat_rvol_24h                 |  0.103653    | 0.0165431   |   6.26564  | 3.71286e-10 | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | range_width_pct               | -0.010865    | 0.000269523 | -40.3119   | 0           | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | vol_x_narrow                  |  0.00194089  | 0.000102251 |  18.9816   | 2.41947e-80 | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | feat_volume_tvl_ratio_24h     |  0.0104135   | 0.00343008  |   3.03592  | 0.002398    | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | feat_jump_intensity_24h       | -0.00016443  | 4.98829e-05 |  -3.29631  | 0.000979636 | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | feat_flow_imbalance_24h       | -0.000960605 | 0.000405795 |  -2.36722  | 0.0179223   | 0.253382  | 0.253111  |   27540 |
| IL_Magnitude       | feat_amm_cex_spread_abs       |  0.0426137   | 0.0356694   |   1.19469  | 0.23221     | 0.253382  | 0.253111  |   27540 |
| LVR_Cumulative     | Intercept                     |  0.00159553  | 8.0774e-05  |  19.753    | 7.56325e-87 | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | C(pool_key)[T.weth_usdc_005]  | -0.000421019 | 0.000306838 |  -1.37212  | 0.170026    | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | C(pool_key)[T.weth_usdc_030]  | -3.47775e-05 | 0.000342707 |  -0.101479 | 0.91917     | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | C(pool_key)[T.wsteth_eth_001] | -6.46349e-05 | 4.3691e-05  |  -1.47936  | 0.139043    | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | feat_rvol_24h                 |  0.163749    | 0.00867601  |  18.8737   | 1.87535e-79 | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | range_width_pct               | -0.0112953   | 0.000213029 | -53.0223   | 0           | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | vol_x_narrow                  |  0.00185863  | 0.000148315 |  12.5316   | 5.01352e-36 | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | feat_volume_tvl_ratio_24h     |  0.00492242  | 0.00179313  |   2.74515  | 0.00604832  | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | feat_jump_intensity_24h       | -0.000169274 | 2.61724e-05 |  -6.46764  | 9.95448e-11 | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | feat_flow_imbalance_24h       | -0.000576373 | 0.000242544 |  -2.37637  | 0.0174841   | 0.474673  | 0.474482  |   27540 |
| LVR_Cumulative     | feat_amm_cex_spread_abs       |  0.0199373   | 0.029421    |   0.677654 | 0.497991    | 0.474673  | 0.474482  |   27540 |
| Net_Return_vs_HODL | Intercept                     | -0.0002306   | 0.000156989 |  -1.46889  | 0.141863    | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | C(pool_key)[T.weth_usdc_005]  | -0.00111408  | 0.000665337 |  -1.67446  | 0.0940406   | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | C(pool_key)[T.weth_usdc_030]  | -0.0012903   | 0.000669026 |  -1.92862  | 0.0537777   | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | C(pool_key)[T.wsteth_eth_001] |  0.000269917 | 0.000109969 |   2.45449  | 0.0141084   | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | feat_rvol_24h                 |  0.00472113  | 0.0174753   |   0.270161 | 0.787037    | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | range_width_pct               |  0.00172037  | 0.000338824 |   5.07748  | 3.82465e-07 | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | vol_x_narrow                  | -0.000313818 | 0.00011907  |  -2.63557  | 0.0083995   | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | feat_volume_tvl_ratio_24h     | -0.00723542  | 0.003393    |  -2.13245  | 0.0329696   | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | feat_jump_intensity_24h       |  0.000134655 | 5.93621e-05 |   2.26837  | 0.0233066   | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | feat_flow_imbalance_24h       |  0.000516756 | 0.000478266 |   1.08048  | 0.27993     | 0.0174481 | 0.0170912 |   27540 |
| Net_Return_vs_HODL | feat_amm_cex_spread_abs       |  0.316686    | 0.100403    |   3.15415  | 0.00160965  | 0.0174481 | 0.0170912 |   27540 |

## 4. Hồi quy Tác nhân Thị trường Thuần túy tại Độ rộng Cố định (Fixed-Width Pure Market Drivers — Tách Hiệu ứng Cơ học của $W$)

| sample_group                   | dependent_var      | term                          |         coef |     std_err |      t_stat |     p_value |         r2 |     adj_r2 |   n_obs |
|:-------------------------------|:-------------------|:------------------------------|-------------:|------------:|------------:|------------:|-----------:|-----------:|--------:|
| All_Pools_Fixed_Width          | IL_Magnitude       | Intercept                     | -0.00026323  | 0.000136031 | -1.93507    | 0.0529816   | 0.162855   | 0.161393   |    4590 |
| All_Pools_Fixed_Width          | IL_Magnitude       | C(pool_key)[T.weth_usdc_005]  | -0.000312496 | 0.00062918  | -0.496671   | 0.619421    | 0.162855   | 0.161393   |    4590 |
| All_Pools_Fixed_Width          | IL_Magnitude       | C(pool_key)[T.weth_usdc_030]  |  4.3899e-05  | 0.00066159  |  0.0663538  | 0.947096    | 0.162855   | 0.161393   |    4590 |
| All_Pools_Fixed_Width          | IL_Magnitude       | C(pool_key)[T.wsteth_eth_001] | -0.000108551 | 7.97898e-05 | -1.36046    | 0.173685    | 0.162855   | 0.161393   |    4590 |
| All_Pools_Fixed_Width          | IL_Magnitude       | feat_rvol_24h                 |  0.0946076   | 0.0168038   |  5.63013    | 1.80076e-08 | 0.162855   | 0.161393   |    4590 |
| All_Pools_Fixed_Width          | IL_Magnitude       | feat_volume_tvl_ratio_24h     |  0.00827772  | 0.00339469  |  2.43843    | 0.0147512   | 0.162855   | 0.161393   |    4590 |
| All_Pools_Fixed_Width          | IL_Magnitude       | feat_jump_intensity_24h       | -0.000128169 | 5.06789e-05 | -2.52903    | 0.0114377   | 0.162855   | 0.161393   |    4590 |
| All_Pools_Fixed_Width          | IL_Magnitude       | feat_flow_imbalance_24h       | -0.000885689 | 0.000382523 | -2.31538    | 0.0205919   | 0.162855   | 0.161393   |    4590 |
| All_Pools_Fixed_Width          | IL_Magnitude       | feat_amm_cex_spread_abs       |  0.0776151   | 0.0447215   |  1.73552    | 0.0826484   | 0.162855   | 0.161393   |    4590 |
| All_Pools_Fixed_Width          | LVR_Cumulative     | Intercept                     | -0.000159439 | 7.32378e-05 | -2.17701    | 0.0294802   | 0.573686   | 0.572941   |    4590 |
| All_Pools_Fixed_Width          | LVR_Cumulative     | C(pool_key)[T.weth_usdc_005]  | -0.00181875  | 0.000316432 | -5.74766    | 9.04846e-09 | 0.573686   | 0.572941   |    4590 |
| All_Pools_Fixed_Width          | LVR_Cumulative     | C(pool_key)[T.weth_usdc_030]  | -0.00133993  | 0.000335583 | -3.99284    | 6.52871e-05 | 0.573686   | 0.572941   |    4590 |
| All_Pools_Fixed_Width          | LVR_Cumulative     | C(pool_key)[T.wsteth_eth_001] | -9.24758e-05 | 4.24846e-05 | -2.17669    | 0.0295036   | 0.573686   | 0.572941   |    4590 |
| All_Pools_Fixed_Width          | LVR_Cumulative     | feat_rvol_24h                 |  0.162289    | 0.00866548  | 18.7282     | 2.91804e-78 | 0.573686   | 0.572941   |    4590 |
| All_Pools_Fixed_Width          | LVR_Cumulative     | feat_volume_tvl_ratio_24h     |  0.0071897   | 0.00174091  |  4.12984    | 3.63012e-05 | 0.573686   | 0.572941   |    4590 |
| All_Pools_Fixed_Width          | LVR_Cumulative     | feat_jump_intensity_24h       | -0.000177343 | 2.64868e-05 | -6.69553    | 2.14896e-11 | 0.573686   | 0.572941   |    4590 |
| All_Pools_Fixed_Width          | LVR_Cumulative     | feat_flow_imbalance_24h       | -0.000821315 | 0.00022397  | -3.66709    | 0.000245331 | 0.573686   | 0.572941   |    4590 |
| All_Pools_Fixed_Width          | LVR_Cumulative     | feat_amm_cex_spread_abs       |  0.017745    | 0.0259618   |  0.683503   | 0.494289    | 0.573686   | 0.572941   |    4590 |
| All_Pools_Fixed_Width          | Net_Return_vs_HODL | Intercept                     | -0.000206114 | 0.000213114 | -0.967153   | 0.333468    | 0.036702   | 0.0350198  |    4590 |
| All_Pools_Fixed_Width          | Net_Return_vs_HODL | C(pool_key)[T.weth_usdc_005]  | -0.000613584 | 0.000691388 | -0.887467   | 0.374828    | 0.036702   | 0.0350198  |    4590 |
| All_Pools_Fixed_Width          | Net_Return_vs_HODL | C(pool_key)[T.weth_usdc_030]  | -0.000758263 | 0.000681547 | -1.11256    | 0.265897    | 0.036702   | 0.0350198  |    4590 |
| All_Pools_Fixed_Width          | Net_Return_vs_HODL | C(pool_key)[T.wsteth_eth_001] |  0.000347749 | 0.000155259 |  2.23979    | 0.0251043   | 0.036702   | 0.0350198  |    4590 |
| All_Pools_Fixed_Width          | Net_Return_vs_HODL | feat_rvol_24h                 |  0.00314829  | 0.0181979   |  0.173003   | 0.862649    | 0.036702   | 0.0350198  |    4590 |
| All_Pools_Fixed_Width          | Net_Return_vs_HODL | feat_volume_tvl_ratio_24h     | -0.00453123  | 0.00333396  | -1.35912    | 0.17411     | 0.036702   | 0.0350198  |    4590 |
| All_Pools_Fixed_Width          | Net_Return_vs_HODL | feat_jump_intensity_24h       |  0.000150913 | 7.46868e-05 |  2.02061    | 0.0433201   | 0.036702   | 0.0350198  |    4590 |
| All_Pools_Fixed_Width          | Net_Return_vs_HODL | feat_flow_imbalance_24h       |  6.03823e-05 | 0.000402149 |  0.150149   | 0.880647    | 0.036702   | 0.0350198  |    4590 |
| All_Pools_Fixed_Width          | Net_Return_vs_HODL | feat_amm_cex_spread_abs       |  0.381571    | 0.202988    |  1.87977    | 0.0601388   | 0.036702   | 0.0350198  |    4590 |
| Volatile_Pools_w10pct          | IL_Magnitude       | Intercept                     | -0.000518333 | 0.000561695 | -0.922802   | 0.35611     | 0.105011   | 0.103071   |    2775 |
| Volatile_Pools_w10pct          | IL_Magnitude       | C(pool_key)[T.weth_usdc_030]  |  0.000758222 | 0.000436294 |  1.73787    | 0.082234    | 0.105011   | 0.103071   |    2775 |
| Volatile_Pools_w10pct          | IL_Magnitude       | feat_rvol_24h                 |  0.0905868   | 0.0184741   |  4.90346    | 9.41624e-07 | 0.105011   | 0.103071   |    2775 |
| Volatile_Pools_w10pct          | IL_Magnitude       | feat_volume_tvl_ratio_24h     |  0.0132517   | 0.00619172  |  2.14024    | 0.0323357   | 0.105011   | 0.103071   |    2775 |
| Volatile_Pools_w10pct          | IL_Magnitude       | feat_jump_intensity_24h       | -0.000346964 | 0.0002141   | -1.62057    | 0.105111    | 0.105011   | 0.103071   |    2775 |
| Volatile_Pools_w10pct          | IL_Magnitude       | feat_flow_imbalance_24h       | -0.00267529  | 0.00102031  | -2.62203    | 0.00874079  | 0.105011   | 0.103071   |    2775 |
| Volatile_Pools_w10pct          | IL_Magnitude       | feat_amm_cex_spread_abs       | -0.000572263 | 0.0492602   | -0.0116171  | 0.990731    | 0.105011   | 0.103071   |    2775 |
| Volatile_Pools_w10pct          | LVR_Cumulative     | Intercept                     | -0.00183125  | 0.00028461  | -6.43426    | 1.24073e-10 | 0.478933   | 0.477803   |    2775 |
| Volatile_Pools_w10pct          | LVR_Cumulative     | C(pool_key)[T.weth_usdc_030]  |  0.000706087 | 0.000244611 |  2.88657    | 0.00389469  | 0.478933   | 0.477803   |    2775 |
| Volatile_Pools_w10pct          | LVR_Cumulative     | feat_rvol_24h                 |  0.160223    | 0.00978415  | 16.3758     | 2.84705e-60 | 0.478933   | 0.477803   |    2775 |
| Volatile_Pools_w10pct          | LVR_Cumulative     | feat_volume_tvl_ratio_24h     |  0.0106134   | 0.00328116  |  3.23465    | 0.00121792  | 0.478933   | 0.477803   |    2775 |
| Volatile_Pools_w10pct          | LVR_Cumulative     | feat_jump_intensity_24h       | -0.000574142 | 0.00011297  | -5.08223    | 3.73021e-07 | 0.478933   | 0.477803   |    2775 |
| Volatile_Pools_w10pct          | LVR_Cumulative     | feat_flow_imbalance_24h       | -0.00230641  | 0.000598908 | -3.85103    | 0.000117624 | 0.478933   | 0.477803   |    2775 |
| Volatile_Pools_w10pct          | LVR_Cumulative     | feat_amm_cex_spread_abs       |  0.026855    | 0.0549078   |  0.489093   | 0.624776    | 0.478933   | 0.477803   |    2775 |
| Volatile_Pools_w10pct          | Net_Return_vs_HODL | Intercept                     | -0.000712757 | 0.000636319 | -1.12012    | 0.262661    | 0.00342701 | 0.00126681 |    2775 |
| Volatile_Pools_w10pct          | Net_Return_vs_HODL | C(pool_key)[T.weth_usdc_030]  |  1.66594e-06 | 0.000417271 |  0.00399247 | 0.996814    | 0.00342701 | 0.00126681 |    2775 |
| Volatile_Pools_w10pct          | Net_Return_vs_HODL | feat_rvol_24h                 |  0.00820719  | 0.0194182   |  0.422655   | 0.672547    | 0.00342701 | 0.00126681 |    2775 |
| Volatile_Pools_w10pct          | Net_Return_vs_HODL | feat_volume_tvl_ratio_24h     | -0.00599776  | 0.00599539  | -1.0004     | 0.317119    | 0.00342701 | 0.00126681 |    2775 |
| Volatile_Pools_w10pct          | Net_Return_vs_HODL | feat_jump_intensity_24h       |  0.000172395 | 0.000209146 |  0.824285   | 0.409778    | 0.00342701 | 0.00126681 |    2775 |
| Volatile_Pools_w10pct          | Net_Return_vs_HODL | feat_flow_imbalance_24h       |  0.000724389 | 0.00103716  |  0.698435   | 0.484905    | 0.00342701 | 0.00126681 |    2775 |
| Volatile_Pools_w10pct          | Net_Return_vs_HODL | feat_amm_cex_spread_abs       |  0.0944581   | 0.0572978   |  1.64855    | 0.0992406   | 0.00342701 | 0.00126681 |    2775 |
| Correlated_Stable_Pools_w02pct | IL_Magnitude       | Intercept                     | -3.42038e-05 | 2.81872e-05 | -1.21345    | 0.224957    | 0.225442   | 0.222872   |    1815 |
| Correlated_Stable_Pools_w02pct | IL_Magnitude       | C(pool_key)[T.wsteth_eth_001] |  9.14965e-05 | 4.42287e-05 |  2.06871    | 0.0385729   | 0.225442   | 0.222872   |    1815 |
| Correlated_Stable_Pools_w02pct | IL_Magnitude       | feat_rvol_24h                 | -0.41855     | 0.193878    | -2.15884    | 0.0308627   | 0.225442   | 0.222872   |    1815 |
| Correlated_Stable_Pools_w02pct | IL_Magnitude       | feat_volume_tvl_ratio_24h     |  0.000656805 | 0.00126043  |  0.521096   | 0.6023      | 0.225442   | 0.222872   |    1815 |
| Correlated_Stable_Pools_w02pct | IL_Magnitude       | feat_jump_intensity_24h       | -1.29761e-05 | 1.03771e-05 | -1.25045    | 0.211134    | 0.225442   | 0.222872   |    1815 |
| Correlated_Stable_Pools_w02pct | IL_Magnitude       | feat_flow_imbalance_24h       |  9.6174e-05  | 8.72047e-05 |  1.10285    | 0.270091    | 0.225442   | 0.222872   |    1815 |
| Correlated_Stable_Pools_w02pct | IL_Magnitude       | feat_amm_cex_spread_abs       |  0.15296     | 0.0087326   | 17.5159     | 1.08299e-68 | 0.225442   | 0.222872   |    1815 |
| Correlated_Stable_Pools_w02pct | LVR_Cumulative     | Intercept                     | -1.07905e-06 | 2.02389e-07 | -5.33154    | 9.73822e-08 | 0.512802   | 0.511185   |    1815 |
| Correlated_Stable_Pools_w02pct | LVR_Cumulative     | C(pool_key)[T.wsteth_eth_001] | -4.42164e-07 | 1.62882e-07 | -2.71463    | 0.00663498  | 0.512802   | 0.511185   |    1815 |
| Correlated_Stable_Pools_w02pct | LVR_Cumulative     | feat_rvol_24h                 |  0.0106315   | 0.0013824   |  7.6906     | 1.46443e-14 | 0.512802   | 0.511185   |    1815 |
| Correlated_Stable_Pools_w02pct | LVR_Cumulative     | feat_volume_tvl_ratio_24h     |  7.6558e-06  | 5.76929e-06 |  1.32699    | 0.184512    | 0.512802   | 0.511185   |    1815 |
| Correlated_Stable_Pools_w02pct | LVR_Cumulative     | feat_jump_intensity_24h       | -2.55921e-07 | 6.21378e-08 | -4.1186     | 3.81177e-05 | 0.512802   | 0.511185   |    1815 |
| Correlated_Stable_Pools_w02pct | LVR_Cumulative     | feat_flow_imbalance_24h       |  2.61787e-07 | 1.73056e-07 |  1.51273    | 0.130349    | 0.512802   | 0.511185   |    1815 |
| Correlated_Stable_Pools_w02pct | LVR_Cumulative     | feat_amm_cex_spread_abs       |  2.24446e-05 | 3.01249e-05 |  0.745051   | 0.456241    | 0.512802   | 0.511185   |    1815 |
| Correlated_Stable_Pools_w02pct | Net_Return_vs_HODL | Intercept                     | -0.000226338 | 0.000120416 | -1.87963    | 0.0601586   | 0.593304   | 0.591954   |    1815 |
| Correlated_Stable_Pools_w02pct | Net_Return_vs_HODL | C(pool_key)[T.wsteth_eth_001] |  0.000637704 | 0.000282575 |  2.25676    | 0.024023    | 0.593304   | 0.591954   |    1815 |
| Correlated_Stable_Pools_w02pct | Net_Return_vs_HODL | feat_rvol_24h                 | -0.973555    | 0.557737    | -1.74554    | 0.0808902   | 0.593304   | 0.591954   |    1815 |
| Correlated_Stable_Pools_w02pct | Net_Return_vs_HODL | feat_volume_tvl_ratio_24h     | -0.00258173  | 0.0018817   | -1.37202    | 0.170058    | 0.593304   | 0.591954   |    1815 |
| Correlated_Stable_Pools_w02pct | Net_Return_vs_HODL | feat_jump_intensity_24h       |  1.07364e-05 | 3.30033e-05 |  0.325314   | 0.744944    | 0.593304   | 0.591954   |    1815 |
| Correlated_Stable_Pools_w02pct | Net_Return_vs_HODL | feat_flow_imbalance_24h       | -0.000344346 | 0.000221661 | -1.55348    | 0.120309    | 0.593304   | 0.591954   |    1815 |
| Correlated_Stable_Pools_w02pct | Net_Return_vs_HODL | feat_amm_cex_spread_abs       |  0.660874    | 0.315374    |  2.09553    | 0.0361243   | 0.593304   | 0.591954   |    1815 |

## 5. Hồi quy Phân vị (Quantile Regression tại $\tau \in \{0.50, 0.90, 0.95\}$)

|   quantile | term                          |         coef |     std_err |       t_stat |      p_value |   pseudo_r2 |
|-----------:|:------------------------------|-------------:|------------:|-------------:|-------------:|------------:|
|       0.5  | Intercept                     |  0.000148325 | 7.15582e-06 |   20.7278    | 1.02887e-94  |   0.0715389 |
|       0.5  | C(pool_key)[T.weth_usdc_005]  | -0.000168453 | 1.00727e-05 |  -16.7238    | 1.79e-62     |   0.0715389 |
|       0.5  | C(pool_key)[T.weth_usdc_030]  | -0.000197716 | 1.11391e-05 |  -17.7497    | 4.2626e-70   |   0.0715389 |
|       0.5  | C(pool_key)[T.wsteth_eth_001] | -3.69471e-06 | 9.86956e-06 |   -0.374354  | 0.708144     |   0.0715389 |
|       0.5  | feat_rvol_24h                 |  0.0458091   | 0.000165379 |  276.995     | 0            |   0.0715389 |
|       0.5  | range_width_pct               | -0.00159402  | 1.72268e-05 |  -92.5317    | 0            |   0.0715389 |
|       0.5  | vol_x_narrow                  |  0.000265034 | 3.09406e-06 |   85.6591    | 0            |   0.0715389 |
|       0.5  | feat_volume_tvl_ratio_24h     |  1.95409e-05 | 6.17616e-05 |    0.316393  | 0.751707     |   0.0715389 |
|       0.5  | feat_jump_intensity_24h       | -2.29389e-06 | 1.83246e-06 |   -1.25181   | 0.21065      |   0.0715389 |
|       0.9  | Intercept                     |  0.00591918  | 2.95382e-05 |  200.391     | 0            |   0.335208  |
|       0.9  | C(pool_key)[T.weth_usdc_005]  | -0.000711154 | 4.04792e-05 |  -17.5684    | 1.02126e-68  |   0.335208  |
|       0.9  | C(pool_key)[T.weth_usdc_030]  | -0.000607077 | 4.6332e-05  |  -13.1028    | 4.15781e-39  |   0.335208  |
|       0.9  | C(pool_key)[T.wsteth_eth_001] | -1.61179e-05 | 3.96184e-05 |   -0.40683   | 0.684136     |   0.335208  |
|       0.9  | feat_rvol_24h                 |  0.283101    | 0.000660982 |  428.303     | 0            |   0.335208  |
|       0.9  | range_width_pct               | -0.016752    | 8.14266e-05 | -205.731     | 0            |   0.335208  |
|       0.9  | vol_x_narrow                  |  0.00348212  | 1.39521e-05 |  249.576     | 0            |   0.335208  |
|       0.9  | feat_volume_tvl_ratio_24h     | -3.10464e-06 | 0.000267209 |   -0.0116188 | 0.99073      |   0.335208  |
|       0.9  | feat_jump_intensity_24h       | -1.12222e-05 | 8.9639e-06  |   -1.25193   | 0.210607     |   0.335208  |
|       0.95 | Intercept                     |  0.00813067  | 4.13388e-05 |  196.684     | 0            |   0.376253  |
|       0.95 | C(pool_key)[T.weth_usdc_005]  |  0.00178445  | 5.5657e-05  |   32.0615    | 1.80151e-221 |   0.376253  |
|       0.95 | C(pool_key)[T.weth_usdc_030]  |  0.00234899  | 6.35257e-05 |   36.977     | 3.7664e-292  |   0.376253  |
|       0.95 | C(pool_key)[T.wsteth_eth_001] | -1.88955e-05 | 5.3686e-05  |   -0.351964  | 0.724868     |   0.376253  |
|       0.95 | feat_rvol_24h                 |  0.373822    | 0.000898813 |  415.906     | 0            |   0.376253  |
|       0.95 | range_width_pct               | -0.0229912   | 0.000112469 | -204.423     | 0            |   0.376253  |
|       0.95 | vol_x_narrow                  |  0.00477159  | 1.80996e-05 |  263.63      | 0            |   0.376253  |
|       0.95 | feat_volume_tvl_ratio_24h     |  1.49627e-05 | 0.000375936 |    0.0398011 | 0.968252     |   0.376253  |
|       0.95 | feat_jump_intensity_24h       | -1.04515e-05 | 1.41479e-05 |   -0.738731  | 0.460077     |   0.376253  |

## 6. Phân tích Phi tuyến Tác nhân Thị trường (Gradient Boosted Trees + SHAP Attribution tại Độ rộng Chuẩn)

| feature                   |   mean_abs_shap |   relative_share_pct |
|:--------------------------|----------------:|---------------------:|
| feat_downside_vol_24h     |     0.000908092 |             29.126   |
| feat_fee_apr_24h          |     0.000777364 |             24.933   |
| feat_rvol_24h             |     0.000568394 |             18.2306  |
| feat_amm_cex_spread_abs   |     0.000273397 |              8.76888 |
| feat_flow_imbalance_24h   |     0.00022052  |              7.07292 |
| feat_volume_tvl_ratio_24h |     0.000190145 |              6.09868 |
| feat_jump_intensity_24h   |     0.000179897 |              5.76998 |

## 7. Kết luận Kiểm định Giả thuyết RQ1 (Sinh tự động từ Số liệu Thực nghiệm)
- **H1.1 (Biến động giá làm tăng IL & LVR):** **Ủng hộ (Supported)** — Biến `vol_x_narrow` trong phương trình `IL_Magnitude` có hệ số $\beta = 0.001941$ ($t = 18.98, p = 2.419e-80$, sai số chuẩn phân cụm theo thời gian). Trên mặt cắt độ rộng cố định chuẩn (không nhân bản $W$), `feat_rvol_24h` vẫn mang hệ số dương có ý nghĩa thống kê ($\beta = 0.094608, t = 5.63, p = 1.801e-08$).
- **H1.2 (Vùng thanh khoản hẹp khuếch đại rủi ro đuôi):** **Ủng hộ (Supported)** — Hệ số tương tác `vol_x_narrow` tăng từ $\beta_{0.50} = 0.000265$ ở trung vị lên $\beta_{0.95} = 0.004772$ ($p = 0$) ở phân vị 95%.
- **H1.3 (Stable/Correlated pool có IL thấp hơn Volatile pool):** **Ủng hộ (Supported)** — IL 24h trung vị (và trung bình) của nhóm Stable/Correlated là `0.00000%` (mean `0.0020%`), thấp hơn rõ rệt so với `0.1498%` (mean `0.5979%`) của nhóm Volatile pool.
- **H1.4 (Tác động của tỷ lệ Volume/TVL lên Net Return):** **Bác bỏ theo chiều ngược (dòng lệnh arbitrage độc hại / lựa chọn bất lợi làm tăng IL nhanh hơn phí)** — Hệ số của `feat_volume_tvl_ratio_24h` trong phương trình `Net_Return_vs_HODL` là $\beta = -0.007235$ ($p = 0.03297$).
