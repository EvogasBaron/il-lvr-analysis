"""
Automation script to incrementally push the next scheduled step (Step 3 or Step 4) to GitHub.
State is maintained in `.git_push_state.json`.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PROJECT_ROOT / ".git_push_state.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def run_git(args: list[str]) -> str:
    """Run a git command and return its stdout, or raise RuntimeError."""
    res = subprocess.run(
        ["git"] + args,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if res.returncode != 0:
        raise RuntimeError(f"Git command failed: git {' '.join(args)}\nError: {res.stderr}")
    return res.stdout.strip()


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"current_step": 3, "history": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def push_step_3() -> None:
    print(">>> Đang thực hiện Bước 3: Toán học cốt lõi & Unit Test...")
    files = ["src/metrics.py", "src/evaluation.py", "tests/test_metrics.py"]
    run_git(["add"] + files)
    run_git(["commit", "-m", "feat(metrics): cong thuc tinh IL, LVR va kiem dinh tai chinh dinh luong"])
    run_git(["push", "origin", "main"])
    print(">>> Đã push thành công Bước 3 lên GitHub!")


def push_step_4() -> None:
    print(">>> Đang thực hiện Bước 4: Pipeline Dữ liệu ETL & Kiểm soát Chất lượng...")
    files = [
        "src/data/__init__.py",
        "src/data/binance.py",
        "src/data/thegraph.py",
        "src/data/quality.py",
        "src/data/merge.py",
        "tests/test_data_pipeline.py",
        "data/processed/merged_usdc_usdt_001_metadata.json",
        "data/processed/merged_weth_usdc_005_metadata.json",
        "data/processed/merged_weth_usdc_030_metadata.json",
        "data/processed/merged_wsteth_eth_001_metadata.json",
    ]
    run_git(["add"] + files)
    run_git(["commit", "-m", "feat(data): quy trinh ETL du lieu Subgraph va Binance CEX"])
    run_git(["push", "origin", "main"])
    print(">>> Đã push thành công Bước 4 lên GitHub!")


def main() -> None:
    state = load_state()
    step = state.get("current_step", 3)

    if step == 3:
        push_step_3()
        state["current_step"] = 4
        state["history"].append({
            "step": 3,
            "name": "Toán học cốt lõi & Unit Test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        save_state(state)
        print(">>> Bước tiếp theo sẽ là Bước 4 vào ngày kế tiếp.")
    elif step == 4:
        push_step_4()
        state["current_step"] = 5
        state["history"].append({
            "step": 4,
            "name": "Pipeline Dữ liệu ETL & Kiểm soát Chất lượng",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        save_state(state)
        print(">>> Hoàn tất 2 bước tiếp theo theo lịch hẹn!")
    else:
        print(f">>> Trạng thái hiện tại: Bước {step} (đã hoàn thành cả 2 bước theo lịch).")


if __name__ == "__main__":
    main()
