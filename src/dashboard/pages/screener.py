from __future__ import annotations

import pandas as pd
import streamlit as st

from src.storage.db import build_screener


@st.cache_data(ttl=300, show_spinner=False)
def _load_screener(db_path: str) -> pd.DataFrame:
    return build_screener(db_path)


def render_screener(db_path: str) -> None:
    df = _load_screener(db_path)
    st.subheader("Main Screener")

    left, middle, right = st.columns([1.1, 1, 1])
    sectors = sorted(df["sector"].dropna().unique().tolist())
    with left:
        selected_sectors = st.multiselect("Sector", sectors, default=sectors)
        watchlist_text = st.text_input("Watchlist tickers", placeholder="CRWD, RXRX, BROS")
    with middle:
        min_market_cap = st.number_input(
            "Minimum market cap ($M)",
            min_value=0,
            max_value=5_000_000,
            value=0,
            step=100,
        )
        min_score = st.slider("Minimum score", 0, 100, 25)
    with right:
        max_days = st.slider("Max days since filing", 1, 365, 180)
        only_open_market = st.checkbox("Only insider open-market purchases")
        exclude_low_quality = st.checkbox("Exclude Low / Noise signals", value=True)

    filtered = df.copy()
    if selected_sectors:
        filtered = filtered[filtered["sector"].isin(selected_sectors)]
    filtered = filtered[filtered["market cap"] >= min_market_cap * 1_000_000]
    filtered = filtered[filtered["total opportunity score"] >= min_score]
    filtered = filtered[
        filtered["days since latest filing"].fillna(9999).astype(int) <= max_days
    ]
    if only_open_market:
        filtered = filtered[filtered["has open-market purchase"]]
    if exclude_low_quality:
        filtered = filtered[~filtered["signal quality"].isin(["Low", "Noise"])]
    watchlist = [item.strip().upper() for item in watchlist_text.split(",") if item.strip()]
    if watchlist:
        filtered = filtered[filtered["ticker"].isin(watchlist)]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Candidates", len(filtered))
    metric_cols[1].metric(
        "Median score",
        f"{filtered['total opportunity score'].median():.1f}" if not filtered.empty else "0.0",
    )
    metric_cols[2].metric("High quality", int((filtered["signal quality"] == "High").sum()))
    metric_cols[3].metric("Open-market buys", int(filtered["has open-market purchase"].sum()))

    display_cols = [
        "ticker",
        "company name",
        "sector",
        "market cap",
        "total opportunity score",
        "filing score",
        "insider score",
        "political trades score",
        "institutional score",
        "activist score",
        "technical score",
        "fundamental score",
        "risk penalty",
        "latest relevant event",
        "days since latest filing",
        "signal quality",
        "short explanation",
    ]
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "market cap": st.column_config.NumberColumn(format="$%0.0f"),
            "total opportunity score": st.column_config.ProgressColumn(
                min_value=0,
                max_value=100,
                format="%0.1f",
            ),
            "insider score": st.column_config.NumberColumn(format="%0.1f"),
            "technical score": st.column_config.NumberColumn(format="%0.1f"),
            "fundamental score": st.column_config.NumberColumn(format="%0.1f"),
            "risk penalty": st.column_config.NumberColumn(format="%0.1f"),
        },
    )
