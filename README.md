# Phân tích và Dự báo Impermanent Loss (IL) & LVR của Liquidity Provider trên Uniswap v3

Đồ án nghiên cứu định lượng giải quyết 3 câu hỏi nghiên cứu cốt lõi trên Uniswap v3:
- **RQ1 (Giải thích):** Các yếu tố biến động giá, độ rộng vùng thanh khoản ($[P_a, P_b]$), fee tier, khối lượng giao dịch và chế độ thị trường ảnh hưởng thế nào đến Impermanent Loss (IL), Loss-Versus-Rebalancing (LVR) và lợi nhuận ròng của LP?
- **RQ2 (Dự báo):** Mô hình học máy (Gradient Boosting Point, Quantile $\tau \in \{0.50, 0.90, 0.95\}$ và Exceedance Probability) dự báo phân phối IL ở các chân trời 1, 7, 30 ngày tốt hơn mô hình giải tích truyền thống đến mức nào?
- **RQ3 (Quyết định chiến lược):** Sử dụng tín hiệu dự báo phân phối IL kết hợp ngưỡng chi phí giao dịch ($\text{Gas} + \text{Slippage}$) có giúp cải thiện lợi nhuận ròng điều chỉnh theo rủi ro so với chiến lược LP tĩnh và tái cân bằng định kỳ hay không?

---

## 1. Cấu trúc Thư mục Dự án

```text
il-lvr-analysis/
├── configs/
│   ├── config.yaml                 # Tham số cấu hình trung tâm (seed, horizon, gas, split ratios)
│   └── pools.yaml                  # Địa chỉ xác thực & thông số các pool Uniswap v3 Mainnet
├── data/
│   ├── raw/                        # Dữ liệu gốc tải từ Binance Vision & Uniswap v3 / Toolkit sample
│   └── processed/                  # Dữ liệu ghép chuẩn 1h (.parquet, .csv) & metadata JSON
├── docs/
│   ├── binance_schema.md           # Schema 12 cột Binance Klines & quy tắc xử lý ms/µs
│   ├── subgraph_schema.md          # Schema GraphQL của Uniswap v3 Subgraph (Pool, PoolHourData, Swap)
│   └── open_questions.md           # Nhật ký các quyết định thiết kế & giả định kỹ thuật
├── notebooks/
│   └── eda_and_results_walkthrough.py # Notebook dạng # %% để khám phá dữ liệu & bảng biểu
├── src/
│   ├── config_loader.py            # Trình đọc YAML config và biến môi trường .env
│   ├── data/
│   │   ├── binance.py              # Tải klines, kiểm tra SHA256 .CHECKSUM, chuẩn hóa ms/µs, gộp 1m->1h
│   │   ├── thegraph.py             # Client GraphQL phân trang + trình đọc dữ liệu mẫu xác thực
│   │   ├── quality.py              # Kiểm tra chất lượng dữ liệu & chống look-ahead bias
│   │   └── merge.py                # Ghép dữ liệu backward merge_asof theo thời điểm đóng nến UTC
│   ├── metrics.py                  # Công thức chuẩn: Concentrated IL, LVR, Capital Efficiency, MDD, VaR/CVaR
│   ├── features.py                 # 26 đặc trưng chuỗi thời gian nhân quả (<= t) & nhãn tương lai (1d, 7d, 30d)
│   ├── evaluation.py               # RMSE, MAE, Pinball Loss, Coverage, Brier Score, Diebold-Mariano Test
│   ├── models/
│   │   ├── rq1_econometrics.py     # Panel Fixed-Effects (HC3), Quantile Regression, TreeSHAP
│   │   └── rq2_forecasting.py      # Purged Walk-Forward Split, Baseline Vol, ML Point/Quantile/Prob
│   ├── backtest/
│   │   └── engine.py               # Mô phỏng Static LP, Periodic Rebalance, IL-Min, Signal Net-Utility
│   └── pipeline.py                 # Orchestrator chạy trọn vẹn 7 quy trình
├── tests/
│   ├── test_data_pipeline.py       # Test đơn vị ms/µs, SHA256 checksum, backward merge_asof
│   ├── test_metrics.py             # Unit test toán học kiểm chứng bằng tay cho IL, LVR, Capital Efficiency
│   ├── test_leakage.py             # Test gây nhiễu tương lai (perturbation test) & Purged split
│   └── test_backtest.py            # Test logic chiến lược LP và ngưỡng chi phí gas
├── reports/
│   ├── data_quality.md             # Báo cáo chất lượng dữ liệu trước và sau khi ghép
│   ├── rq1_econometric_analysis.md # Kết quả & phân tích RQ1
│   ├── rq2_forecasting_models.md   # Kết quả & phân tích RQ2
│   ├── rq3_strategy_backtest.md    # Kết quả & phân tích RQ3
│   ├── final_thesis_report.md      # Báo cáo tổng hợp toàn đồ án
│   ├── tables/                     # Các bảng kết quả định dạng CSV
│   └── figures/                    # Các biểu đồ trực quan hóa PNG
├── DATASET_PLAN.md
├── PROJECT_CONTEXT.md
├── requirements.txt
└── main.py
```

---

## 2. Hướng dẫn Cài đặt & Chạy lại từ đầu (Reproducibility)

### Bước 1: Cài đặt thư viện
```powershell
pip install -r requirements.txt
```

### Bước 2: Cấu hình API Key (Tùy chọn)
Sao chép `.env.example` thành `.env`:
```powershell
Copy-Item .env.example .env
```
- Nếu bạn có khóa `THEGRAPH_API_KEY`, điền vào `.env` để truy vấn trực tiếp từ Uniswap v3 Mainnet Subgraph (`5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV`).
- Nếu để trống, pipeline tự động tải dữ liệu thực từ **Binance Vision** và dữ liệu mẫu xác thực từ `ilyamk/uniswap-v3-lp-strategy-toolkit` để chạy trọn vẹn 7 quy trình.

### Bước 3: Chạy toàn bộ 7 quy trình bằng một lệnh duy nhất
```powershell
python main.py
```
*(Thời gian chạy ước tính: 15 – 45 giây).*

### Bước 4: Chạy bộ Kiểm thử Tự động (Unit Tests & Anti-Leakage Tests)
```powershell
pytest tests/ -v
```

---

## 3. Các Giả định & Quy tắc Kỹ thuật Quan trọng

1. **Chống rò rỉ tương lai (Zero Look-Ahead Bias):**
   - Nến 1 giờ của Binance mở lúc `t` và bản ghi `PoolHourData` có `periodStartUnix = t` đều chỉ kết thúc và xác định giá đóng cửa (`close`), khối lượng (`volumeUSD`) tại thời điểm `t + 1h`. Do đó, khóa thời gian chuẩn hóa `timestamp` luôn là thời điểm **đóng khung giờ** (`t + 1h`).
   - Toàn bộ phép ghép dùng `pd.merge_asof(..., direction="backward")`.
   - Khi chia tập `Train / Valid / Test` cho dự báo chân trời $H \in \{24\text{h}, 168\text{h}, 720\text{h}\}$, hệ thống áp dụng khoảng đệm cách ly (`purge_hours = H`) để nhãn tương lai của tập Train không bao giờ chồng lấn sang tập Validation/Test.
2. **Tự động phát hiện đơn vị Timestamp Binance (`ms` vs `µs`):**
   - Kể từ `2025-01-01 00:00:00 UTC`, Binance Vision đổi đơn vị timestamp từ mili giây (`13 chữ số`) sang micro giây (`16 chữ số`). Hàm `normalize_binance_timestamp()` tự động nhận diện theo từng phần tử và chuẩn hóa về `datetime64[ns, UTC]`.
