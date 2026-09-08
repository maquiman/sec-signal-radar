from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = CACHE_DIR / "sec_signal_radar.sqlite3"


def load_config() -> dict[str, Any]:
    """Load local config without requiring Streamlit to be present."""
    load_dotenv(ROOT_DIR / ".env")

    fmp_api_key = os.getenv("FMP_API_KEY", "")
    try:
        import streamlit as st

        fmp_api_key = st.secrets.get("FMP_API_KEY", fmp_api_key)
    except Exception:
        pass

    return {
        "database_path": Path(os.getenv("SCREENER_DB_PATH", DB_PATH)),
        "fmp_api_key": fmp_api_key,
        "enable_fmp": os.getenv("ENABLE_FMP", "false").lower() == "true",
        "enable_yahoo": os.getenv("ENABLE_YAHOO", "false").lower() == "true",
        "enable_sec_edgar": os.getenv("ENABLE_SEC_EDGAR", "false").lower() == "true",
    }
