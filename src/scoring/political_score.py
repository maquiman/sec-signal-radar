from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd


def _column(df: pd.DataFrame, name: str, default: Any = None) -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series(default, index=df.index)


def parse_amount_midpoint(value: str | float | int | None) -> float:
    if value is None or pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    numbers = [float(n.replace(",", "")) for n in re.findall(r"\$?([0-9][0-9,]*)", value)]
    if not numbers:
        return 0.0
    if len(numbers) == 1:
        return numbers[0]
    return float(sum(numbers[:2]) / 2)


def calculate_political_score(
    political_trades: pd.DataFrame,
    as_of: datetime | pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Score political trades conservatively because disclosure timing can lag."""
    if political_trades is None or political_trades.empty:
        return {
            "score": 0.0,
            "quality": "Noise",
            "explanation": "No political trade data available.",
            "metrics": {},
        }

    df = political_trades.copy()
    as_of_ts = pd.Timestamp(as_of or datetime.now(UTC)).tz_localize(None)
    df["transaction_type"] = _column(df, "transaction_type", "").astype(str).str.lower()
    df["transaction_date"] = pd.to_datetime(_column(df, "transaction_date"), errors="coerce")
    df["disclosure_date"] = pd.to_datetime(_column(df, "disclosure_date"), errors="coerce")
    if "amount_midpoint" not in df:
        df["amount_midpoint"] = _column(df, "amount_range", "").apply(parse_amount_midpoint)
    df["amount_midpoint"] = pd.to_numeric(df["amount_midpoint"], errors="coerce").fillna(0)
    df["committee_relevance"] = pd.to_numeric(
        _column(df, "committee_relevance", 0), errors="coerce"
    ).fillna(0)
    df["days_ago"] = (as_of_ts - df["transaction_date"].dt.tz_localize(None)).dt.days
    df["days_ago"] = df["days_ago"].clip(lower=0).fillna(999)
    df["disclosure_lag"] = (
        df["disclosure_date"].dt.tz_localize(None)
        - df["transaction_date"].dt.tz_localize(None)
    ).dt.days.clip(lower=0)

    buys = df[df["transaction_type"].str.contains("purchase|buy", regex=True)]
    sells = df[df["transaction_type"].str.contains("sale|sell", regex=True)]

    if buys.empty:
        return {
            "score": 0.0,
            "quality": "Noise",
            "explanation": "No disclosed political purchases detected.",
            "metrics": {
                "unique_buyers": 0,
                "buy_value": 0.0,
                "sell_value": float(sells["amount_midpoint"].sum()) if not sells.empty else 0.0,
            },
        }

    buys["recency_weight"] = np.exp(-buys["days_ago"] / 120)
    unique_buyers = int(buys.get("politician", pd.Series(dtype=str)).nunique())
    weighted_buy_value = float((buys["amount_midpoint"] * buys["recency_weight"]).sum())
    buy_value = float(buys["amount_midpoint"].sum())
    sell_value = float(sells["amount_midpoint"].sum()) if not sells.empty else 0.0
    avg_lag = float(buys["disclosure_lag"].mean()) if not buys.empty else 999.0
    avg_relevance = float(buys["committee_relevance"].mean()) if not buys.empty else 0.0

    value_score = min(28.0, np.log10(max(weighted_buy_value, 1.0)) * 5.0)
    buyer_score = min(18.0, unique_buyers * 6.0)
    recency_score = min(18.0, float(buys["recency_weight"].max()) * 18.0)
    relevance_score = min(12.0, avg_relevance * 12.0)
    lag_penalty = min(18.0, avg_lag / 5.0)
    sale_penalty = min(15.0, (sell_value / max(buy_value, 1.0)) * 10.0)
    ambiguity_penalty = 6.0 if (buys["amount_midpoint"] <= 0).any() else 0.0

    score = (
        value_score
        + buyer_score
        + recency_score
        + relevance_score
        - lag_penalty
        - sale_penalty
        - ambiguity_penalty
    )
    score = float(np.clip(score, 0, 100))
    if score >= 60:
        quality = "Medium"
    elif score >= 25:
        quality = "Low"
    else:
        quality = "Noise"

    explanation = (
        f"{unique_buyers} politician(s) disclosed purchases near ${buy_value:,.0f}; "
        f"average disclosure lag {avg_lag:.0f} days."
    )

    return {
        "score": round(score, 2),
        "quality": quality,
        "explanation": explanation,
        "metrics": {
            "unique_buyers": unique_buyers,
            "buy_value": round(buy_value, 2),
            "weighted_buy_value": round(weighted_buy_value, 2),
            "sell_value": round(sell_value, 2),
            "average_disclosure_lag": round(avg_lag, 2),
            "average_committee_relevance": round(avg_relevance, 2),
        },
    }
