# Báo cáo Kiểm tra Chất lượng Dữ liệu (`data_quality.md`)

## 1. Kiểm tra từng nguồn dữ liệu (Pre-Merge & Post-Merge Integrity)

| Nguồn dữ liệu | Trạng thái | Bắt đầu (UTC) | Kết thúc (UTC) | Số dòng | Kỳ vọng | Độ phủ | Trùng lặp | Thiếu giờ | Giá <= 0 | Volume < 0 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `Binance_ETHUSDT_1h` | **PASS** | 2021-05-05 01:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 33504 | 33504 | 100.00% | 0 | 0 | 0 | 0 |
| `Binance_USDCUSDT_1h` | **PASS** | 2021-05-05 01:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 33504 | 33504 | 100.00% | 0 | 0 | 0 | 0 |
| `Uniswap_wsteth_eth_001_1h` | **PASS** | 2023-06-12 13:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 15060 | 15060 | 100.00% | 0 | 0 | 0 | 0 |
| `Uniswap_weth_usdc_005_1h` | **PASS** | 2021-05-06 09:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 33472 | 33472 | 100.00% | 0 | 0 | 0 | 0 |
| `Uniswap_weth_usdc_030_1h` | **PASS** | 2021-05-05 19:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 33486 | 33486 | 100.00% | 0 | 0 | 0 | 0 |
| `Uniswap_usdc_usdt_001_1h` | **PASS** | 2021-11-14 13:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 28860 | 28860 | 100.00% | 0 | 0 | 0 | 0 |
| `Merged_wsteth_eth_001_1h` | **PASS** | 2023-06-12 13:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 15060 | 15060 | 100.00% | 0 | 0 | 0 | 0 |
| `Merged_weth_usdc_005_1h` | **PASS** | 2021-05-06 09:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 33472 | 33472 | 100.00% | 0 | 0 | 0 | 0 |
| `Merged_weth_usdc_030_1h` | **PASS** | 2021-05-05 19:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 33486 | 33486 | 100.00% | 0 | 0 | 0 | 0 |
| `Merged_usdc_usdt_001_1h` | **PASS** | 2021-11-14 13:00:00+00:00 | 2025-03-01 00:00:00+00:00 | 28860 | 28860 | 100.00% | 0 | 0 | 0 | 0 |

## 2. Kiểm tra chéo sau khi ghép, Audit Lọc OHLC, Khôi phục Volume/Phí & Chống rò rỉ tương lai

| Pool | Phân loại | Giờ Subgraph gốc | Cắt khởi tạo TVL<100k | Giờ 0-tx (ffill) | Nến OHLC lọc nhiễu | Giờ khôi phục Volume/Fee từ PoolDayData | Vi phạm Look-ahead (CEX/Pool) | Median Chênh lệch AMM-CEX | P99 Chênh lệch AMM-CEX |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `wsteth_eth_001` | correlated | 15073 | 116 | 103 | 1022 | 6662 | 0/0 | 0.0012% | 0.0521% |
| `weth_usdc_005` | volatile | 33483 | 10 | 0 | 937 | 25160 | 0/0 | 0.0489% | 0.5337% |
| `weth_usdc_030` | volatile | 33056 | 7 | 437 | 313 | 24871 | 0/0 | 0.1433% | 0.4696% |
| `usdc_usdt_001` | stable | 28856 | 0 | 4 | 1535 | 20543 | 0/0 | 0.0529% | 0.5488% |

## 3. Nhận xét & Xác nhận Quy tắc Ghép
- **Chuẩn hóa Timestamp:** Đã kiểm tra và chuẩn hóa toàn bộ dấu thời gian (`s`, `ms`, `µs`) về `datetime64[ns, UTC]`.
- **Căn chỉnh Nến Mở/Đóng:** Nến Binance mở lúc `t` có thời điểm đóng hiệu lực là `t + 1h`, khớp chính xác với trạng thái cuối giờ của `PoolHourData` (`periodStartUnix + 3600s`).
- **Khôi phục Volume & Phí lịch sử trước 03/2024:** Đối với các giờ trước ngày `2024-03-19` mà Subgraph đặt `PoolHourData.volumeUSD = 0` và `feesUSD = 0`, hệ thống tự động phân bổ chính xác 100% tổng `volumeUSD` và `feesUSD` on-chain từ `PoolDayData` theo tỷ trọng `txCount` của từng giờ.
- **Cắt giai đoạn khởi tạo Pool chưa bơm thanh khoản (`tvlUSD < $100,000`):** Loại bỏ các giờ khởi tạo ban đầu khi pool chưa được cấp thanh khoản thực tế (đặc biệt `wsteth_eth_001` giai đoạn 08/2022–05/2023 chỉ có `~$321` TVL trước khi Lido bơm thanh khoản ngày `2023-06-12`).
- **Không rò rỉ tương lai:** Số vi phạm look-ahead trên cả nguồn CEX và nguồn Pool đều bằng `0`.
