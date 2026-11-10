"""
Configuration and Environment Loader.
Ensures zero hard-coding of parameters, pool addresses, or API keys.
"""
import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_environment() -> Dict[str, str]:
    """Load environment variables from .env if present."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    return {
        "THEGRAPH_API_KEY": os.getenv("THEGRAPH_API_KEY", "").strip(),
        "UNISWAP_V3_SUBGRAPH_ID": os.getenv(
            "UNISWAP_V3_SUBGRAPH_ID",
            "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
        ).strip(),
    }


def load_config(config_path: Path | None = None) -> Dict[str, Any]:
    """Load main project configuration from configs/config.yaml."""
    path = config_path or (PROJECT_ROOT / "configs" / "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_pools_config(pools_path: Path | None = None) -> Dict[str, Any]:
    """Load verified Uniswap v3 pool configurations from configs/pools.yaml."""
    path = pools_path or (PROJECT_ROOT / "configs" / "pools.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
