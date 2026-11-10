# PROJECT_CONTEXT.md: Phân tích và dự báo impermanent loss của LP trên Uniswap v3

> File quản lý ngữ cảnh, công thức, quyết định thiết kế và tiến độ đồ án.

---

## 1. Mục tiêu và câu hỏi nghiên cứu

**Mục tiêu chung:** Giải thích các yếu tố tác động đến impermanent loss (IL) và lợi nhuận ròng của liquidity provider (LP) trên Uniswap v3, đánh giá khả năng dự báo phân phối IL, và kiểm tra xem dự báo đó có giúp LP ra quyết định tốt hơn các chiến lược tĩnh hay không.

### RQ1: Các yếu tố nào giải thích IL và lợi nhuận ròng của LP?

Mức độ biến động giá, độ rộng vùng thanh khoản, vị trí giá trong vùng, fee tier, khối lượng giao dịch và tần suất tái cân bằng ảnh hưởng thế nào đến IL và lợi nhuận ròng của LP?

- **Giả thuyết**
  - H1.1: Biến động giá lớn làm IL và LVR tăng.
  - H1.2: Vùng thanh khoản càng hẹp thì hiệu quả sử dụng vốn và phí thu được có thể tăng, nhưng rủi ro out-of-range và tail loss cũng tăng.
  - H1.3: Stablecoin / correlated pool có IL thấp hơn volatile-asset pool, trừ các giai đoạn depeg.
  - H1.4: Khối lượng giao dịch cao chỉ có lợi nếu phí thu được lớn hơn IL, LVR và gas.
  - H1.5: Tái cân bằng quá thường xuyên có thể giảm IL nhưng làm lợi nhuận ròng giảm vì gas và chi phí giao dịch.
- **Biến phụ thuộc:** IL sau 1/7/30 ngày; LVR; phí giao dịch tích lũy; lợi nhuận ròng so với HODL; xác suất vị thế out-of-range; maximum drawdown và CVaR của vị thế LP.
- **Phương pháp:** phân tích mô tả theo pool, fee tier, market regime; panel regression / fixed-effects; quantile regression (phần đuôi của IL); XGBoost + SHAP (yếu tố phi tuyến).

### RQ2: Dự báo phân phối IL trong tương lai tốt đến mức nào?

Mô hình ML/DL có dự báo IL trong 1/7/30 ngày tốt hơn mô hình phân tích truyền thống dựa trên giá và volatility hay không?

- **Giả thuyết**
  - H2.1: ML cải thiện dự báo cho concentrated liquidity vì quan hệ giữa volatility, range width, volume và IL mang tính phi tuyến.
  - H2.2: Mô hình chuỗi thời gian tốt trong cùng một pool nhưng suy giảm khi chuyển sang pool hoặc market regime khác.
  - H2.3: Dự báo quantile hoặc xác suất vượt ngưỡng hữu ích hơn chỉ tối ưu RMSE.
- **Đặc trưng dự báo:** realized volatility (1h, 6h, 24h, 7d); return, downside volatility, jump intensity; khoảng cách từ giá hiện tại đến tick dưới/trên; độ rộng vùng thanh khoản; tỷ lệ thời gian in-range; trading volume, TVL, swap count; fee tier, fee APR; buy/sell flow imbalance; chênh lệch giá AMM–CEX; gas price, base fee; correlation giữa hai tài sản; stablecoin/LST deviation.
- **Mục tiêu dự báo:** giá trị IL, phân vị (quantile 0.50, 0.90, 0.95), xác suất vượt ngưỡng. Horizon: 1, 7, 30 ngày.

### RQ3: Dự báo IL có giúp LP quyết định tốt hơn không?

Dùng dự báo IL để chọn khoảng giá và thời điểm tái cân bằng có cải thiện lợi nhuận ròng điều chỉnh theo rủi ro so với chiến lược LP tĩnh hay không?

- **Giả thuyết**
  - H3.1: Dự báo IL có thể giảm tail loss, nhưng không nhất thiết tăng gross return.
  - H3.2: Tái cân bằng theo tín hiệu chỉ nên thực hiện khi lợi ích dự kiến vượt gas và slippage.
  - H3.3: Chính sách tối ưu theo lợi nhuận ròng tốt hơn chính sách chỉ cố giảm IL.
  - H3.4: Chiến lược tốt trên WETH/USDC có thể không tổng quát sang stable/correlated pool hoặc pool thanh khoản thấp.
- **Chỉ số đánh giá:** net return so với HODL; phí giao dịch; IL và LVR; gas và số lần tái cân bằng; Sharpe/Sortino; maximum drawdown; VaR và CVaR; tỷ lệ thời gian in-range; capital efficiency.

---

## 2. Thuật ngữ & Công thức Toán học Chính thức

| Thuật ngữ | Ý nghĩa | Công thức chuẩn (Uniswap v3 Concentrated Liquidity) |
|---|---|---|
| **IL** (Impermanent Loss) | Tỷ lệ suy giảm giá trị vị thế LP trên vùng $[P_a, P_b]$ so với giữ nguyên lượng tài sản ban đầu (HODL) | $\text{IL}(P_t; P_0, P_a, P_b) = \frac{V_{\text{LP}}(P_t) - V_{\text{HODL}}(P_t)}{V_{\text{HODL}}(P_t)} \le 0$ (hoặc lấy độ lớn $\|\text{IL}\|$ khi mô hình hóa mức lỗ) |
| **LVR** (Loss-versus-Rebalancing) | Thiệt hại tức thời tích lũy do giao dịch với arbitrageur ở giá AMM so với giá CEX (Milionis et al.) | Xấp xỉ rời rạc theo nhịp $\Delta t$: $\text{LVR}_t = \sum_{\tau} \frac{1}{2} L_{\text{eff}}(\tau) \cdot \left.\frac{\partial^2 V}{\partial P^2}\right\| \cdot \sigma_\tau^2 P_\tau^2 \Delta t$ hoặc $\frac{1}{2} \|\Delta x_{\tau}\| \cdot \|P_{\tau}^{\text{CEX}} - P_{\tau}^{\text{exec}}\|$ |
| **Net Return vs HODL** | Lợi nhuận ròng của vị thế LP so với danh mục HODL sau phí và gas | $R_{\text{net}} = \frac{V_{\text{LP}}(P_T) + \text{Fees}_{[0,T]} - \text{Gas}_{[0,T]} - V_{\text{HODL}}(P_T)}{V_{\text{HODL}}(P_0)}$ |
| **In-range / Out-of-range** | Trạng thái giá hiện tại $P_t$ nằm trong $[P_a, P_b]$ | $\mathbb{I}(P_a \le P_t \le P_b)$ |
| **Capital Efficiency** | Hệ số khuếch đại vốn của thanh khoản tập trung so với Uniswap v2 $[0, \infty)$ | $\eta = \frac{1}{1 - \frac{\sqrt{P_a / P_0} + \sqrt{P_0 / P_b}}{2}}$ (khi $P_0 = \sqrt{P_a P_b}$: $\eta = \frac{1}{1 - (P_a/P_b)^{1/4}}$) |
| **Max Drawdown, VaR, CVaR** | Thước đo rủi ro đuôi của vị thế LP | $\text{MDD} = \max_{t} \frac{\text{Peak}_t - W_t}{\text{Peak}_t}$, $\text{VaR}_\alpha(L) = \inf \{l : P(L > l) \le 1-\alpha\}$, $\text{CVaR}_\alpha = \mathbb{E}[L \mid L \ge \text{VaR}_\alpha]$ |
| **Market Regime** | Phân loại chế độ thị trường theo phân vị biến động thực tế (Realized Volatility) | Low-Vol ($\sigma_{24h} < Q_{33}$), Normal-Vol ($Q_{33} \le \sigma_{24h} < Q_{67}$), High-Vol ($\sigma_{24h} \ge Q_{67}$) |

---

## 3. Cấu hình Dữ liệu đã chốt

- **Nguồn dữ liệu:**
  1. **The Graph (Uniswap v3 Subgraph)** + **Fallback dữ liệu mẫu thực tế** (`wstETH/ETH 0.01%` từ `ilyamk/uniswap-v3-lp-strategy-toolkit` khi chưa cung cấp `THEGRAPH_API_KEY` trong `.env`).
  2. **Binance Vision Public Data**: klines `1m` và `1h` của `ETHUSDT`, `USDCUSDT`, `WBETHETH`.
- **Danh sách Pool:**
  - `wstETH/ETH 0.01%` (`0x109830a1AAaD605BbF02a9dFA7B0B92EC2FB7dAa`) — Correlated / LST Pool.
  - `WETH/USDC 0.05%` (`0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640`) — High-Volume Volatile Pool.
  - `WETH/USDC 0.30%` (`0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8`) — Standard Volatile Pool (mở rộng).
  - `USDC/USDT 0.01%` (`0x3416cF6C708Da44DB2624D63ea0AAef7113527C6`) — Stablecoin Pool (mở rộng).
- **Độ phân giải thời gian:** Nhịp chung `1h` (UTC), bao phủ giai đoạn đa chu kỳ `2021-05-05` đến `2025-02-28` (`15,060` đến `33,486` giờ thực tế mỗi pool) để kiểm thử đầy đủ các chế độ thị trường và bẫy đổi đơn vị timestamp ms/µs của Binance từ `2025-01-01`.
- **Vị thế LP & Gas:** Mô phỏng vị thế Concentrated Liquidity chuẩn với các độ rộng range ($\pm 1\%, \pm 2\%, \pm 5\%, \pm 10\%, \pm 20\%, \text{Full-Range}$) và tham số `gas_price_gwei` trong `configs/config.yaml`.

---

## 4. Cấu trúc Thư mục

```
il-lvr-analysis/
  configs/
    config.yaml       # Tham số chung, horizon, seed, gas, regime thresholds
    pools.yaml        # Danh sách pool, địa chỉ xác thực, fee tier, cặp CEX ánh xạ
  data/
    raw/              # Dữ liệu gốc tải về (Binance zip/csv, Uniswap raw/sample)
    processed/        # Dữ liệu sau khi ghép (parquet) + metadata json + features
  docs/
    binance_schema.md
    subgraph_schema.md
    open_questions.md
  notebooks/          # Script/Notebook khám phá dữ liệu & trực quan hóa
  src/
    __init__.py
    data/
      binance.py      # Tải, kiểm tra CHECKSUM, chuẩn hóa ms/µs, gộp nến 1m -> 1h
      thegraph.py     # Truy vấn GraphQL có phân trang + tải/đọc sample dataset
      quality.py      # Kiểm tra chất lượng dữ liệu trước & sau khi ghép
      merge.py        # Ghép dữ liệu backward merge_asof chống rò rỉ tương lai
    metrics.py        # Công thức toán học Uniswap v3: IL, LVR, Fees, Capital Efficiency, VaR/CVaR, MDD
    features.py       # Tạo đặc trưng tại thời điểm t (chỉ dùng lịch sử <= t) + nhãn tương lai (1d, 7d, 30d)
    models/
      rq1_econometrics.py # Panel FE regression, Quantile regression, XGBoost + SHAP
      rq2_forecasting.py  # Walk-forward split (purging/embargo), Baseline Vol, XGBoost Point/Quantile/Prob
    backtest/
      engine.py       # Mô phỏng chiến lược Static LP, Periodic Rebalance, Signal-Driven Rebalance
    evaluation.py     # RMSE, MAE, Pinball Loss, Brier Score, Coverage, Diebold-Mariano test
    pipeline.py       # CLI chạy trọn vẹn từ Quy trình 2 đến Quy trình 7
  tests/
    test_data_pipeline.py
    test_metrics.py
    test_leakage.py
    test_backtest.py
  reports/            # Toàn bộ báo cáo markdown, bảng số liệu CSV và biểu đồ PNG
```

---

## 5. Tiến độ Thực hiện

| Bước | Trạng thái | Ghi chú |
|---|---|---|
| Làm rõ phạm vi và dữ liệu (Quy trình 1) | ✅ | Đã chốt cấu hình với người dùng tại `configs/` |
| Pipeline thu thập & ghép dữ liệu (Quy trình 2) | ✅ | Đa chu kỳ 2021–2025 (`15,060`–`33,486` giờ/pool), khôi phục `PoolDayData` pre-03/2024, SHA256, xử lý ms/µs (`reports/data_quality.md`) |
| Định nghĩa biến, công thức, đặc trưng + unit test (Quy trình 3) | ✅ | `src/metrics.py`, `src/features.py`, `tests/test_metrics.py` |
| RQ1: Kiểm định yếu tố ảnh hưởng (Quy trình 4) | ✅ | Panel FE (Clustered SE), Fixed-Width Market Reg, Quantile Reg, TreeSHAP (`reports/rq1_econometric_analysis.md`) |
| RQ2: Dự báo phân phối IL (Quy trình 5) | ✅ | 8-Fold Multi-Origin Purged Walk-Forward (1d, 7d, 30d), Pure ML vs Analytical vs Hybrid, Split Conformal (`reports/rq2_forecasting_models.md`) |
| RQ3: Backtest chiến lược LP (Quy trình 6) | ✅ | 8-Fold OOS Backtest, Dynamic Slippage, Gas Sensitivity (5/20/60 Gwei) (`reports/rq3_strategy_backtest.md`) |
| Kiểm thử rò rỉ, tổng hợp báo cáo & README (Quy trình 7) | ✅ | 21/21 unit tests passed (`reports/final_thesis_report.md`, `README.md`) |
