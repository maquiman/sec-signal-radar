from __future__ import annotations

import pandas as pd
import streamlit as st

from src.storage.db import build_screener, diagnostics


@st.cache_data(ttl=300, show_spinner=False)
def _load_diagnostics(db_path: str) -> pd.DataFrame:
    return diagnostics(db_path)


@st.cache_data(ttl=300, show_spinner=False)
def _load_screener(db_path: str) -> pd.DataFrame:
    return build_screener(db_path)


def render_diagnostics(db_path: str) -> None:
    st.subheader("Data Health / Diagnostics")
    diag = _load_diagnostics(db_path)
    screener = _load_screener(db_path)

    cols = st.columns(4)
    cols[0].metric("Sources", len(diag))
    cols[1].metric("Records", int(diag["records loaded"].sum()))
    cols[2].metric("API calls", int(diag["estimated api calls"].sum()))
    cols[3].metric("Tickers", len(screener))

    st.dataframe(diag, use_container_width=True, hide_index=True)

    insufficient = screener[
        (screener["technical score"] == 0)
        | (screener["fundamental score"] == 0)
        | (screener["days since latest filing"].isna())
    ][["ticker", "company name", "technical score", "fundamental score", "days since latest filing"]]

    st.markdown("**Tickers With Sparse Data**")
    st.dataframe(insufficient, use_container_width=True, hide_index=True)

    st.markdown("**Recent Ingestion Errors**")
    errors = diag[diag["recent errors"].fillna("") != ""]
    if errors.empty:
        st.success("No ingestion errors recorded in local SQLite.")
    else:
        st.dataframe(errors, use_container_width=True, hide_index=True)
