# Danh sách câu hỏi mở & Các quyết định đã xác nhận (`open_questions.md`)

Tài liệu này ghi nhận toàn bộ các điểm cần làm rõ từ `DATASET_PLAN.md` (Mục 5) và `PROJECT_CONTEXT.md` (Mục 7), cùng phương án đã chốt với người dùng.

## 1. Các quyết định đã chốt với người dùng

| Hạng mục | Câu hỏi ban đầu | Phương án đã chốt |
|---|---|---|
| **Nguồn The Graph & API Key** | Đã có `THEGRAPH_API_KEY` chưa? | Hỗ trợ kép: đọc `THEGRAPH_API_KEY` từ `.env` để truy vấn trực tiếp Subgraph; nếu chưa điền key thì tự động sử dụng dữ liệu mẫu thực tế (`wstETH/ETH 0.01%`) kết hợp dữ liệu thật tải từ **Binance Vision** và chuỗi mô phỏng thực nghiệm chuẩn cho `WETH/USDC 0.05%` khớp sát với đường giá thực tế `ETHUSDT` của Binance. |
| **Danh sách Pool & Fee Tier** | Nghiên cứu những pool nào? | Chạy trọn pipeline với 2 pool đại diện cho 2 thái cực: **Correlated Pool (`wstETH/ETH 0.01%`)** và **Volatile Pool (`WETH/USDC 0.05%`)**. Cấu hình sẵn `WETH/USDC 0.30%` và `USDC/USDT 0.01%` trong `configs/pools.yaml` để bật lên bất cứ lúc nào. |
| **Khoảng thời gian & Độ phân giải** | Bao nhiêu tháng, nhịp bao lâu? | Nhịp chung **1 giờ (`1h`)** (UTC), bao phủ giai đoạn **2024–2025** để có nhiều chế độ thị trường (Low/Normal/High Volatility) và kiểm thử trực tiếp việc chuyển đổi đơn vị timestamp `ms` $\to$ `µs` từ ngày `2025-01-01` của Binance Vision. |
| **Vị thế LP & Chi phí Gas** | Dùng vị thế on-chain thật hay mô phỏng? Nguồn gas? | Mô phỏng vị thế LP theo đúng công thức toán học Concentrated Liquidity của Uniswap v3 Whitepaper trên nhiều độ rộng khoảng giá ($\pm 1\%, \pm 2\%, \pm 5\%, \pm 10\%, \pm 20\%, \pm 50\%$) và dùng tham số `gas_price_gwei` trong `configs/config.yaml` (kèm ước lượng biến động base fee theo xung lượng khối lượng giao dịch). |

---

## 2. Các giả định kỹ thuật & Hạn chế cần lưu ý trong Báo cáo

1. **Dữ liệu Gas On-chain Lịch sử:**
   - Hiện tại giai đoạn lõi sử dụng `gas_price_gwei: 20.0` (và có hỗ trợ chế độ dynamic gas nhạy theo congestion/volume spike trong backtest). Nếu mở rộng sang giai đoạn sau, có thể bổ sung bảng `bigquery-public-data.crypto_ethereum.blocks` (`base_fee_per_gas`).
2. **Độ phân giải LVR (Loss-Versus-Rebalancing):**
   - Theo Milionis et al. (2022), LVR lý thuyết được định nghĩa trong thời gian liên tục (continuous-time). Trong thực nghiệm rời rạc nhịp 1 giờ, chúng ta tính đồng thời 2 đại lượng:
     - **Analytical Continuous-Time LVR Proxy:** $\text{LVR}_{\text{cont}} = \frac{1}{2} \sigma_t^2 P_t^2 \left|\frac{\partial^2 V_{\text{LP}}}{\partial P^2}\right| \Delta t$ (với $\sigma_t$ được ước lượng từ nến 1 phút/1 giờ của Binance CEX).
     - **Discrete Arbitrage Flow LVR Proxy:** dựa trên chênh lệch giá thực thi giữa AMM (`pool_close_price`) và CEX (`cex_close_price`) khi giá nằm trong vùng thanh khoản.
3. **Ước lượng Phí giao dịch cho vị thế mô phỏng:**
   - Khi không tải toàn bộ lịch sử `Tick` ở mọi block, phí thu được của một vị thế mô phỏng có thanh khoản $\Delta L$ trong khoảng $[P_a, P_b]$ khi giá in-range được tính theo tỷ lệ đóng góp thanh khoản hoạt động ($\frac{\Delta L}{L_{\text{pool}, t} + \Delta L} \times \text{feesUSD}_t$) hoặc theo mật độ thanh khoản tương đối chuẩn hóa theo độ rộng khoảng giá.
