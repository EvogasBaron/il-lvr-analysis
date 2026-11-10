# Binance Vision Public Data Schema (Spot Klines)

Tài liệu chính thức: https://github.com/binance/binance-public-data/

## 1. Cấu trúc cột của file CSV trong gói `.zip` (Spot Klines)

File CSV tải từ `https://data.binance.vision/data/spot/monthly/klines/<SYMBOL>/<interval>/` **không có dòng header** (hoặc ở một số file mới có thể có header; parser phải tự động kiểm tra dòng đầu tiên). Thứ tự chuẩn 12 cột của Binance Spot Klines:

| Thứ tự | Tên cột chuẩn hóa | Kiểu dữ liệu | Đơn vị | Ý nghĩa |
|---|---|---|---|---|
| 0 | `open_time` | `int64` -> `datetime64[ns, UTC]` | `ms` (trước 2025-01-01) hoặc `µs` (từ 2025-01-01) | Thời điểm **mở** nến (Open time) |
| 1 | `open` | `float64` | Quote asset (`USDT`) | Giá mở cửa |
| 2 | `high` | `float64` | Quote asset (`USDT`) | Giá cao nhất trong nến |
| 3 | `low` | `float64` | Quote asset (`USDT`) | Giá thấp nhất trong nến |
| 4 | `close` | `float64` | Quote asset (`USDT`) | Giá đóng cửa (cuối nến) |
| 5 | `volume` | `float64` | Base asset (`ETH`, `USDC`) | Khối lượng giao dịch tính theo Base Asset |
| 6 | `close_time` | `int64` -> `datetime64[ns, UTC]` | `ms` hoặc `µs` | Thời điểm **đóng** nến (ví dụ: `open_time + 3599999 ms` cho nến `1h`) |
| 7 | `quote_asset_volume` | `float64` | Quote asset (`USDT`) | Khối lượng giao dịch tính theo Quote Asset |
| 8 | `number_of_trades` | `int64` | Số nguyên | Tổng số lệnh khớp trong nến |
| 9 | `taker_buy_base_asset_volume` | `float64` | Base asset | Khối lượng chủ động mua (Taker buy) tính theo Base Asset |
| 10 | `taker_buy_quote_asset_volume` | `float64` | Quote asset | Khối lượng chủ động mua (Taker buy) tính theo Quote Asset |
| 11 | `ignore` | `str` / `float64` | N/A | Trường dự phòng của Binance (bỏ qua khi xử lý) |

---

## 2. Quy tắc chuẩn hóa Timestamp & Chống lệch thời gian (Look-ahead Bias Prevention)

1. **Tự động phát hiện đơn vị (`ms` vs `µs`):**
   - Với các mốc thời gian từ năm 2020–2030:
     - Tính bằng giây (`s`): $\approx 1.7 \times 10^9$ (10 chữ số)
     - Tính bằng mili giây (`ms`): $\approx 1.7 \times 10^{12}$ (13 chữ số)
     - Tính bằng micro giây (`µs`): $\approx 1.7 \times 10^{15}$ (16 chữ số)
     - Tính bằng nano giây (`ns`): $\approx 1.7 \times 10^{18}$ (19 chữ số)
   - Hàm `normalize_binance_timestamp(ts_series)` kiểm tra từng giá trị để quy đổi chính xác về `datetime64[ns, UTC]`, xử lý được cả trường hợp ghép nối chuỗi dữ liệu跨 qua mốc `2025-01-01 00:00:00 UTC`.

2. **Căn chỉnh thời điểm mở/đóng nến khi ghép (`merge_asof`):**
   - Trong Binance Klines, `open_time` là đầu giờ (ví dụ `10:00:00 UTC`), còn giá `close`, `high`, `low`, `volume` của nến đó chỉ được biết đầy đủ vào cuối giờ (`10:59:59.999 UTC`, tức mốc đánh dấu giờ kế tiếp `11:00:00 UTC`).
   - Do đó, mốc thời gian hiệu lực (`effective_close_timestamp`) của một cây nến 1 giờ bắt đầu lúc `t` là `t + 1 hour` (hoặc `floor/ceil` của `close_time` lên đầu giờ kế tiếp).
   - Khi ghép với dữ liệu cuối giờ của Pool ở mốc `T`, chỉ được phép dùng nến Binance đã đóng tại hoặc trước `T` (`direction="backward"` trên `effective_close_timestamp`). Tuyệt đối không ghép giá `close` của nến mở lúc `T` (vì nến đó kết thúc lúc `T + 1h`).
