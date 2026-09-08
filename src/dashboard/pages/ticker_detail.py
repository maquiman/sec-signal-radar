from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.scoring.fundamental_score import calculate_fundamental_score
from src.scoring.insider_score import calculate_insider_score
from src.scoring.political_score import calculate_political_score
from src.scoring.risk_score import calculate_risk_penalty
from src.scoring.technical_score import calculate_technical_score
from src.scoring.total_score import calculate_total_score
from src.storage.db import build_screener, load_ticker_bundle


@st.cache_data(ttl=300, show_spinner=False)
def _load_screener(db_path: str) -> pd.DataFrame:
    return build_screener(db_path)


@st.cache_data(ttl=300, show_spinner=False)
def _load_bundle(ticker: str, db_path: str) -> dict[str, pd.DataFrame]:
    return load_ticker_bundle(ticker, db_path)


def render_ticker_detail(db_path: str) -> None:
    screener = _load_screener(db_path)
    tickers = screener["ticker"].tolist()
    ticker = st.selectbox("Ticker", tickers)
    bundle = _load_bundle(ticker, db_path)
    company = bundle["company"].iloc[0] if not bundle["company"].empty else pd.Series()

    insider = calculate_insider_score(bundle["form4"])
    political = calculate_political_score(bundle["political"])
    technical = calculate_technical_score(bundle["prices"])
    fundamental = calculate_fundamental_score(company)
    days_since_latest = _lookup_nullable_int(screener, ticker, "days since latest filing")
    risk = calculate_risk_penalty(company, technical, insider, days_since_latest)
    total = calculate_total_score(
        {
            "insider_score": insider["score"],
            "technical_score": technical["score"],
            "fundamental_score": fundamental["score"],
            "activist_score": _lookup_score(screener, ticker, "activist score"),
            "institutional_score": _lookup_score(screener, ticker, "institutional score"),
            "political_score": political["score"],
        },
        risk["penalty"],
    )

    st.subheader(f"{ticker} - {company.get('company_name', '')}")
    cols = st.columns(7)
    cols[0].metric("Total", f"{total['total_opportunity_score']:.1f}")
    cols[1].metric("Insider", f"{insider['score']:.1f}")
    cols[2].metric("Technical", f"{technical['score']:.1f}")
    cols[3].metric("Fundamental", f"{fundamental['score']:.1f}")
    cols[4].metric("Political", f"{political['score']:.1f}")
    cols[5].metric("Risk", f"-{risk['penalty']:.1f}")
    cols[6].metric("Quality", _lookup_text(screener, ticker, "signal quality"))

    st.write(_lookup_text(screener, ticker, "short explanation"))

    pos_col, risk_col = st.columns(2)
    with pos_col:
        st.markdown("**Positive Signals**")
        positives = [
            insider["explanation"],
            technical["explanation"],
            fundamental["explanation"],
            political["explanation"] if political["score"] > 0 else "",
        ]
        for item in [p for p in positives if p]:
            st.write(f"- {item}")
    with risk_col:
        st.markdown("**Risks**")
        st.write(f"- {risk['explanation']}")
        if insider["quality"] == "Noise":
            st.write("- Insider data does not currently show open-market buying.")
        if fundamental["metrics"].get("shares_growth", 0) > 0.08:
            st.write("- Shares outstanding growth suggests dilution risk.")

    st.plotly_chart(_price_chart(ticker, bundle), use_container_width=True)

    tab_names = [
        "Timeline",
        "Form 4",
        "Political Trades",
        "Institutional / 13F",
        "13D / 13G",
    ]
    tabs = st.tabs(tab_names)
    with tabs[0]:
        st.dataframe(_timeline(bundle), use_container_width=True, hide_index=True)
    with tabs[1]:
        st.dataframe(bundle["form4"], use_container_width=True, hide_index=True)
    with tabs[2]:
        st.dataframe(bundle["political"], use_container_width=True, hide_index=True)
    with tabs[3]:
        st.dataframe(bundle["institutional"], use_container_width=True, hide_index=True)
    with tabs[4]:
        st.dataframe(bundle["activist"], use_container_width=True, hide_index=True)


def _price_chart(ticker: str, bundle: dict[str, pd.DataFrame]) -> go.Figure:
    prices = bundle["prices"].copy()
    prices["date"] = pd.to_datetime(prices["date"])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=prices["date"],
            y=prices["close"],
            mode="lines",
            name="Close",
            line={"color": "#2563eb", "width": 2},
        )
    )
    events = _timeline(bundle)
    if not events.empty:
        events["date"] = pd.to_datetime(events["date"])
        event_points = pd.merge_asof(
            events.sort_values("date"),
            prices[["date", "close"]].sort_values("date"),
            on="date",
            direction="nearest",
        )
        fig.add_trace(
            go.Scatter(
                x=event_points["date"],
                y=event_points["close"],
                mode="markers",
                name="Events",
                text=event_points["event"],
                marker={"size": 9, "color": "#dc2626"},
            )
        )
    fig.update_layout(
        height=420,
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        title=f"{ticker} Price With Filing/Event Markers",
        xaxis_title="Date",
        yaxis_title="Close",
    )
    return fig


def _timeline(bundle: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for _, row in bundle["form4"].iterrows():
        rows.append(
            {
                "date": row.get("filing_date"),
                "source": "Form 4",
                "event": f"{row.get('transaction_code')} - {row.get('insider_name')}",
                "notes": row.get("notes"),
            }
        )
    for _, row in bundle["political"].iterrows():
        rows.append(
            {
                "date": row.get("disclosure_date"),
                "source": "Political",
                "event": f"{row.get('transaction_type')} - {row.get('politician')}",
                "notes": row.get("amount_range"),
            }
        )
    for _, row in bundle["institutional"].iterrows():
        rows.append(
            {
                "date": row.get("filing_date"),
                "source": "13F",
                "event": row.get("filer_name"),
                "notes": row.get("notes"),
            }
        )
    for _, row in bundle["activist"].iterrows():
        rows.append(
            {
                "date": row.get("filing_date"),
                "source": row.get("filing_type"),
                "event": row.get("filer_name"),
                "notes": row.get("intent"),
            }
        )
    timeline = pd.DataFrame(rows)
    if timeline.empty:
        return timeline
    return timeline.sort_values("date", ascending=False)


def _lookup_score(df: pd.DataFrame, ticker: str, column: str) -> float:
    match = df[df["ticker"] == ticker]
    if match.empty:
        return 0.0
    return float(match.iloc[0][column])


def _lookup_text(df: pd.DataFrame, ticker: str, column: str) -> str:
    match = df[df["ticker"] == ticker]
    if match.empty:
        return ""
    return str(match.iloc[0][column])


def _lookup_nullable_int(df: pd.DataFrame, ticker: str, column: str) -> int | None:
    match = df[df["ticker"] == ticker]
    if match.empty or pd.isna(match.iloc[0][column]):
        return None
    return int(match.iloc[0][column])
