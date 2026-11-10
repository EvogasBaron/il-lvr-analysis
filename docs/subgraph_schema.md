# Uniswap v3 Subgraph & Toolkit Sample Schema

Tài liệu tham chiếu chính thức:
- Schema GraphQL: https://github.com/Uniswap/v3-subgraph/blob/main/src/v3/schema.graphql
- Subgraph ID (Mainnet): `5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV`
- Repo dữ liệu mẫu xác thực: `https://github.com/ilyamk/uniswap-v3-lp-strategy-toolkit`

---

## 1. Thực thể trên Uniswap v3 Subgraph (`schema.graphql`)

### 1.1 `Pool`
| Tên trường (GraphQL) | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | `ID!` | Địa chỉ hợp đồng thông minh của Pool (chữ thường trên Subgraph) |
| `createdAtTimestamp` | `BigInt!` | Unix timestamp (giây) khi tạo Pool |
| `token0` | `Token!` | Thông tin token0 (`id`, `symbol`, `name`, `decimals`) |
| `token1` | `Token!` | Thông tin token1 (`id`, `symbol`, `name`, `decimals`) |
| `feeTier` | `BigInt!` | Mức phí tính theo phần triệu (ví dụ: `100` = 0.01%, `500` = 0.05%, `3000` = 0.3%) |
| `liquidity` | `BigInt!` | Thanh khoản in-range hiện tại $L$ |
| `sqrtPrice` | `BigInt!` | Giá căn bậc hai định dạng Q64.96 (`sqrtPriceX96`) |
| `token0Price` | `BigDecimal!` | Giá của token0 tính bằng token1 |
| `token1Price` | `BigDecimal!` | Giá của token1 tính bằng token0 |
| `tick` | `BigInt` | Tick hiện tại của Pool |
| `totalValueLockedUSD` | `BigDecimal!` | Tổng giá trị khóa (TVL) tính theo USD |
| `volumeUSD` | `BigDecimal!` | Tổng khối lượng giao dịch tích lũy (USD) |
| `feesUSD` | `BigDecimal!` | Tổng phí giao dịch tích lũy (USD) |
| `txCount` | `BigInt!` | Tổng số giao dịch trên Pool |

### 1.2 `PoolHourData`
| Tên trường (GraphQL) | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | `ID!` | Định dạng `<poolAddress>-<hourIndex>` |
| `periodStartUnix` | `Int!` | Unix timestamp (giây) tại đầu giờ (UTC) |
| `pool` | `Pool!` | Tham chiếu tới thực thể `Pool` |
| `liquidity` | `BigInt!` | Thanh khoản hoạt động cuối giờ $L$ |
| `sqrtPrice` | `BigInt!` | `sqrtPriceX96` cuối giờ |
| `token0Price` | `BigDecimal!` | Giá token0 theo token1 cuối giờ |
| `token1Price` | `BigDecimal!` | Giá token1 theo token0 cuối giờ |
| `tick` | `BigInt` | Tick cuối giờ |
| `tvlUSD` | `BigDecimal!` | TVL của Pool cuối giờ (USD) |
| `volumeToken0` | `BigDecimal!` | Khối lượng giao dịch token0 trong giờ |
| `volumeToken1` | `BigDecimal!` | Khối lượng giao dịch token1 trong giờ |
| `volumeUSD` | `BigDecimal!` | Khối lượng giao dịch trong giờ (USD) |
| `feesUSD` | `BigDecimal!` | Phí thu được của toàn Pool trong giờ (USD) |
| `txCount` | `BigInt!` | Số lượng giao dịch phát sinh trong giờ |
| `open` | `BigDecimal!` | Giá mở cửa đầu giờ (`token0Price`) |
| `high` | `BigDecimal!` | Giá cao nhất trong giờ (`token0Price`) |
| `low` | `BigDecimal!` | Giá thấp nhất trong giờ (`token0Price`) |
| `close` | `BigDecimal!` | Giá đóng cửa cuối giờ (`token0Price`) |

### 1.3 `Swap`
| Tên trường (GraphQL) | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | `ID!` | Transaction hash + `#` + log index |
| `timestamp` | `BigInt!` | Unix timestamp (giây) của block chứa lệnh Swap |
| `amount0` | `BigDecimal!` | Lượng thay đổi token0 ($\Delta x$, dương khi trader bán token0 vào pool) |
| `amount1` | `BigDecimal!` | Lượng thay đổi token1 ($\Delta y$) |
| `amountUSD` | `BigDecimal!` | Giá trị lệnh Swap tính bằng USD |
| `sqrtPriceX96` | `BigInt!` | Giá `sqrtPriceX96` sau khi thực hiện lệnh Swap |
| `tick` | `BigInt!` | Tick sau khi thực hiện lệnh Swap |

---

## 2. Cấu trúc Thật của Bộ Dữ liệu Mẫu (`ilyamk/uniswap-v3-lp-strategy-toolkit`)

Bộ dữ liệu mẫu của pool `wstETH/WETH 0.01%` (`0x109830a1AAaD605BbF02a9dFA7B0B92EC2FB7dAa`) trong `data/raw/uniswap/toolkit_sample/` là dữ liệu snapshot theo block (217 bản ghi, cách nhau khoảng 1,000 block $\approx 3.3$ giờ, từ `2025-01-27` đến `2025-02-26`).

### 2.1 `wsteth_eth_data_0.01_pool_data.csv` (23 cột thực tế)
| Tên cột thực tế | Kiểu | Ý nghĩa |
|---|---|---|
| `block` | `int64` | Số hiệu block Ethereum (ví dụ `21714243`) |
| `timestamp` | `int64` | Unix timestamp (giây) của block |
| `datetime` | `str` | Chuỗi thời gian UTC (`YYYY-MM-DD HH:MM:SS`) |
| `sqrtPriceX96` | `str` / `int` | Giá căn bậc hai định dạng Q64.96 |
| `tick` | `int64` | Tick tại block (ví dụ `1739`) |
| `price` | `float64` | Tỷ giá `WETH` trên `1 wstETH` ($\approx 1.1900$, tương ứng $1.0001^{\text{tick}}$) |
| `liquidity` | `str` / `float` | Thanh khoản hoạt động $L$ tại block |
| `observationIndex`, `observationCardinality`, `observationCardinalityNext` | `int64` | Trạng thái oracle slot0 của hợp đồng Pool |
| `feeProtocol`, `unlocked` | `int` / `bool` | Tham số phí giao thức và trạng thái reentrancy lock |
| `price_change`, `price_change_pct` | `float64` | Thay đổi giá tuyệt đối và phần trăm so với snapshot trước |
| `liquidity_change`, `liquidity_change_pct` | `float64` | Thay đổi thanh khoản so với snapshot trước |
| `time_diff_seconds` | `float64` | Số giây giữa hai snapshot liên tiếp ($\approx 12012\text{s}$) |
| `est_volatility_daily` | `float64` | Ước lượng biến động ngày từ chuỗi snapshot |
| `daily_volume_usd`, `daily_volume_token0`, `daily_volume_token1`, `tvl_usd`, `fees_usd` | `float64` | Các cột tổng hợp ngày (chỉ điền ở một số dòng có mốc ngày) |

> **Lưu ý sử dụng:** Theo mục 2.3 của `DATASET_PLAN.md`, bộ dữ liệu mẫu toolkit chỉ dùng để kiểm thử parser và đối chiếu chéo tỷ giá `price` ($\approx 1.19\text{ WETH/wstETH}$) và `tick` với dữ liệu tải từ The Graph Subgraph, không dùng làm chuỗi giờ chính cho báo cáo.
