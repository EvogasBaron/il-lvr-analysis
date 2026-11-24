"""
Entry point to execute the full Uniswap v3 Impermanent Loss & LVR Analysis Pipeline.
Run:
    python main.py
"""
import sys
from src.pipeline import run_full_pipeline


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    results = run_full_pipeline()
    print("\n=====================================================================")
    print("HOÀN TẤT TOÀN BỘ 7 QUY TRÌNH ĐỒ ÁN PHÂN TÍCH & DỰ BÁO IL / LVR UNISWAP V3")
    print(f"Báo cáo tổng hợp: {results['final_report']}")
    print("=====================================================================")
