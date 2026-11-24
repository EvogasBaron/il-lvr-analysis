# %% [markdown]
# # EDA & Trình bày Kết quả Thực nghiệm: Phân tích và Dự báo IL/LVR trên Uniswap v3
# File định dạng `# %%` (Jupyter Percent Script) hỗ trợ chạy từng cell trực tiếp trong PyCharm / VS Code.

# %%
from pathlib import Path
import pandas as pd
from src.config_loader import PROJECT_ROOT, load_config, load_pools_config

config = load_config()
pools_cfg = load_pools_config()
print("Project:", config["project"])
print("Enabled Pools:", [k for k, v in pools_cfg["pools"].items() if v.get("enabled")])

# %% [markdown]
# ## 1. Kiểm tra Dữ liệu Ghép (`data/processed/merged_*.csv`)

# %%
processed_dir = PROJECT_ROOT / "data" / "processed"
for csv_file in sorted(processed_dir.glob("merged_*.csv")):
    df = pd.read_csv(csv_file)
    print(f"\n=== {csv_file.name}: {len(df)} rows, {len(df.columns)} columns ===")
    print(df[["timestamp", "amm_price", "cex_close", "amm_cex_spread_rel", "volumeUSD", "feesUSD"]].head(5))

# %% [markdown]
# ## 2. Xem Bảng Kết quả RQ1, RQ2, RQ3 tại `reports/tables/`

# %%
tables_dir = PROJECT_ROOT / "reports" / "tables"
for tbl_file in sorted(tables_dir.glob("*.csv")):
    print(f"\n--- {tbl_file.name} ---")
    print(pd.read_csv(tbl_file).head(10).to_string(index=False))
