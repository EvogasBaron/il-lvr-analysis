# DATASET_PLAN.md: Thu thập và ghép dữ liệu cho đồ án phân tích IL trên Uniswap v3

> File này giao việc cho AI coding agent. Đọc kèm `PROJECT_CONTEXT.md`.
> Quy tắc chung: **không tự bịa tên cột, địa chỉ pool hay URL.** Mọi tên cột phải lấy từ schema thật hoặc dữ liệu đã tải về. Chỗ nào chưa chắc, hỏi lại hoặc ghi vào `docs/open_questions.md`.

---

## 1. Mục tiêu

Xây pipeline thu thập và ghép dữ liệu để phục vụ đồ án nghiên cứu: *phân tích và dự báo impermanent loss (IL) của liquidity provider trên Uniswap v3*.

**Hướng dữ liệu:** không có dataset đơn lẻ nào có đủ mọi thứ, nên ghép từ nhiều nguồn công khai, miễn phí:

| Nguồn | Cung cấp | Trạng thái |
|---|---|---|
| The Graph (Uniswap v3 subgraph) / Dữ liệu mẫu xác thực | Giá, thanh khoản, volume, TVL, fee tier, swap, mint/burn, tick | Bắt buộc |
| Binance Vision | Giá CEX (klines) cho LVR, chênh lệch AMM-CEX, volatility | Bắt buộc |
| Gas lịch sử | Chi phí giao dịch thực tế | Giai đoạn đầu dùng tham số cố định `gas_price_gwei` trong config |

**Phạm vi bắt đầu nhỏ:** chạy trọn pipeline với `wstETH/ETH 0.01%` và `WETH/USDC 0.05%`, cấu hình sẵn `WETH/USDC 0.3%` và `USDC/USDT 0.01%` để mở rộng.

---

## 2. Nguồn dữ liệu và link

### 2.1 Binance Vision (tải file zip, không cần key)
- Tài liệu: https://github.com/binance/binance-public-data/
- Kho dữ liệu: https://data.binance.vision
- Mẫu đường dẫn (spot, monthly klines):
  ```
  https://data.binance.vision/data/spot/monthly/klines/<SYMBOL>/<interval>/<SYMBOL>-<interval>-<năm>-<tháng>.zip
  ```
  Mỗi zip có file `.CHECKSUM` đi kèm để kiểm tra toàn vẹn. Tháng chưa kết thúc lấy từ thư mục `daily`.
- Cần tải:

  | Symbol | Interval | Mục đích |
  |---|---|---|
  | `ETHUSDT` | `1m` và `1h` | Giá CEX, realized volatility, LVR |
  | `WSTETHETH` / `WBETHETH` *(hoặc tính tỷ giá qua ETHUSDT)* | `1h` | Đối chiếu cặp LST/ETH |
  | `USDCUSDT` *(kiểm tra có tồn tại, đủ lịch sử)* | `1h` | Stablecoin deviation (nếu làm stable pool) |

- **Bẫy đã biết:** timestamp của spot từ **1/1/2025 trở đi tính bằng micro giây**, trước đó là mili giây. Phải tự phát hiện đơn vị và chuẩn hóa.

### 2.2 The Graph: Uniswap v3 subgraph (truy vấn GraphQL, cần API key)
- Tổng quan subgraph: https://developers.uniswap.org/docs/ecosystem/subgraphs/overview.md
- Trang subgraph v3 Mainnet: https://thegraph.com/explorer/subgraphs/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV
- Schema: https://github.com/Uniswap/v3-subgraph/blob/main/src/v3/schema.graphql
- Mẫu truy vấn: https://developers.uniswap.org/docs/ecosystem/subgraphs/concepts/v3/queries.md
- Endpoint dạng: `https://gateway.thegraph.com/api/<API_KEY>/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV`
- **Giới hạn:** tối đa 1000 mục mỗi truy vấn, phải phân trang (theo timestamp/id để tránh giới hạn skip).
- Thực thể cần lấy (**xác minh tên trường bằng schema trước khi viết truy vấn**):

  | Thực thể | Dùng cho |
  |---|---|
  | `Pool` | Token0/token1, fee tier, tick spacing |
  | `PoolHourData` (và `PoolDayData`) | Chuỗi giờ/ngày: giá, thanh khoản, tick, TVL, volume, phí |
  | `Swap` | Buy/sell flow imbalance, swap count |
  | `Mint`, `Burn`, `Position` | Chỉ nếu dùng vị thế thật |
  | `Tick` | Chỉ nếu cần mô phỏng phí theo phân bố thanh khoản |

- **Pool:** địa chỉ có nguồn xác thực từ repo toolkit là wstETH/ETH 0.01%: `0x109830a1AAaD605BbF02a9dFA7B0B92EC2FB7dAa`. Các pool khác truy vấn qua subgraph `pools` theo cặp token và `feeTier`. Ghi kết quả vào `configs/pools.yaml`.

### 2.3 Dữ liệu mẫu để thử pipeline (không cần key)
Repo `ilyamk/uniswap-v3-lp-strategy-toolkit`, pool wstETH/ETH 0.01%:
- https://github.com/ilyamk/uniswap-v3-lp-strategy-toolkit/blob/main/wsteth_eth_data_0.01_pool_data.csv
- https://github.com/ilyamk/uniswap-v3-lp-strategy-toolkit/blob/main/wsteth_eth_data_0.01_impermanent_loss.csv
- https://github.com/ilyamk/uniswap-v3-lp-strategy-toolkit/blob/main/wsteth_eth_data_0.01_ticks_data.csv
- https://github.com/ilyamk/uniswap-v3-lp-strategy-toolkit/blob/main/wsteth_eth_data_0.01_metadata.json

**Lưu ý:** chỉ dùng dữ liệu thô (`pool_data.csv`, `ticks_data.csv`, `metadata.json`) để chạy thử và đối chiếu cấu trúc dữ liệu; toàn bộ công thức IL, LVR, phí và backtest được xây dựng độc lập trong `src/` kèm unit test.

---

## 3. Công việc cần làm (theo thứ tự)

### Bước 1: Thiết lập
- [x] Tạo cấu trúc: `configs/`, `data/raw/`, `data/processed/`, `src/data/`, `tests/`, `docs/`
- [x] API key đặt trong `.env` (có `.env.example`), thêm `.env` vào `.gitignore`. **Không hard-code key.**
- [x] `configs/` chứa: danh sách pool, khoảng thời gian, nhịp chung (mặc định 1 giờ), symbol Binance, `gas_price_gwei`

### Bước 2: Tải giá CEX (Binance)
- [x] Script tải theo tháng, kiểm tra `.CHECKSUM`, giải nén vào `data/raw/binance/`
- [x] Đọc klines, tự phát hiện đơn vị timestamp (ms hay µs), chuẩn hóa về datetime UTC
- [x] Ghi `docs/binance_schema.md`: tên cột, kiểu, ý nghĩa, đơn vị

### Bước 3: Tải dữ liệu pool (The Graph & Sample Fallback)
- [x] Đọc schema, ghi `docs/subgraph_schema.md` với các trường thực sự dùng
- [x] Truy vấn `Pool` để lấy địa chỉ và thông số pool, ghi `configs/pools.yaml`
- [x] Tải `PoolHourData` có phân trang, có retry và nghỉ khi bị giới hạn, lưu `data/raw/uniswap/` (hỗ trợ fallback sang dữ liệu mẫu khi chưa điền `.env`)
- [x] Tải `Swap` (sau khi bước trên chạy ổn)

### Bước 4: Kiểm tra chất lượng từng nguồn (trước khi ghép)
- [x] Số dòng so với kỳ vọng (ví dụ 24 x số ngày cho dữ liệu giờ)
- [x] Giờ bị thiếu hoặc trùng, giá trị âm hoặc bằng 0, ngoại lệ bất thường
- [x] Báo cáo ngắn `reports/data_quality.md`

### Bước 5: Ghép dữ liệu
- [x] Đưa mọi timestamp về **UTC**, cùng đơn vị, cùng nhịp (mặc định 1 giờ)
- [x] Gộp nến 1 phút của Binance về nhịp chung (giá cuối giờ, realized vol trong giờ)
- [x] Ghép bằng `merge_asof` hướng `backward` (lấy giá trị gần nhất **trước hoặc bằng** mốc thời gian), tuyệt đối không dùng dữ liệu của nến chưa kết thúc
- [x] Nhớ rằng nến Binance gắn với thời điểm **mở** nến, còn giá pool cuối giờ là trạng thái **cuối** giờ; xử lý để không lệch một giờ
- [x] Xuất `data/processed/merged_<pool>.parquet` + metadata (nguồn, khoảng thời gian, ngày tải)

### Bước 6: Kiểm thử bắt buộc
- [x] Test đơn vị timestamp (ms và µs cho cùng một mốc thời gian phải ra cùng kết quả)
- [x] Test không rò rỉ tương lai: không dòng nào ở thời điểm *t* chứa thông tin từ sau *t*
- [x] Test số dòng sau ghép bằng số giờ kỳ vọng, không trùng khóa thời gian
- [x] Kiểm tra chéo: giá pool và giá CEX của cùng cặp phải sát nhau. Lệch lớn kéo dài là dấu hiệu ghép sai thời gian
- [x] Test bằng dữ liệu mẫu từ repo toolkit (mục 2.3)

### Bước 7: Bàn giao
- [x] `README.md` ngắn: cách chạy từng bước, thời gian chạy ước tính, các giả định
- [x] Danh sách cột của file ghép cuối cùng và nguồn gốc từng cột
- [x] Báo cáo những gì còn thiếu so với danh sách đặc trưng của đề tài (gas, tick, v.v.)
