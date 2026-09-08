from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from src.dashboard.pages.diagnostics import render_diagnostics
from src.dashboard.pages.screener import render_screener
from src.dashboard.pages.ticker_detail import render_ticker_detail
from src.storage.db import initialize_database
from src.utils.config import load_config


st.set_page_config(
    page_title="SEC Signal Radar",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def boot_database() -> str:
    config = load_config()
    return str(initialize_database(config["database_path"]))


def main() -> None:
    db_path = boot_database()
    st.title("SEC Signal Radar")
    st.caption("Explainable investment research screener using local filing and market data.")

    page = st.sidebar.radio(
        "View",
        ["Main Screener", "Ticker Detail", "Data Health"],
        label_visibility="collapsed",
    )

    if page == "Main Screener":
        render_screener(db_path)
    elif page == "Ticker Detail":
        render_ticker_detail(db_path)
    else:
        render_diagnostics(db_path)


if __name__ == "__main__":
    main()
