from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd


NOISE_CODES = {"A", "M", "F", "G", "J", "X"}


def _column(df: pd.DataFrame, name: str, default: Any = None) -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series(default, index=df.index)


def _to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=False)


def _quality_from_score(score: float, has_noise_only: bool) -> str:
    if has_noise_only:
        return "Noise"
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    if score >= 15:
        return "Low"
    return "Noise"


def calculate_insider_score(
    form4_transactions: pd.DataFrame,
    as_of: datetime | pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Score Form 4 activity with emphasis on explainable open-market buying."""
    if form4_transactions is None or form4_transactions.empty:
        return {
            "score": 0.0,
            "quality": "Noise",
            "explanation": "No Form 4 transactions available.",
            "metrics": {},
        }

    df = form4_transactions.copy()
    as_of_ts = pd.Timestamp(as_of or datetime.now(UTC)).tz_localize(None)
    df["transaction_code"] = _column(df, "transaction_code", "").astype(str).str.upper()
    df["transaction_date"] = _to_datetime(_column(df, "transaction_date"))
    df["value"] = pd.to_numeric(_column(df, "value", 0), errors="coerce")
    if df["value"].isna().all():
        shares = pd.to_numeric(_column(df, "shares", 0), errors="coerce")
        price = pd.to_numeric(_column(df, "price", 0), errors="coerce")
        df["value"] = shares * price
    df["value"] = df["value"].fillna(0).abs()
    df["is_10b5_1"] = pd.to_numeric(_column(df, "is_10b5_1", 0), errors="coerce").fillna(0)

    purchases = df[df["transaction_code"] == "P"].copy()
    sales = df[df["transaction_code"] == "S"].copy()
    noise = df[df["transaction_code"].isin(NOISE_CODES)]

    if purchases.empty:
        sale_value = float(sales["value"].sum()) if not sales.empty else 0.0
        noise_reason = "noise transactions only" if not noise.empty else "no open-market purchases"
        return {
            "score": 0.0,
            "quality": "Noise",
            "explanation": f"No insider open-market purchases detected; {noise_reason}.",
            "metrics": {
                "purchase_value": 0.0,
                "sale_value": sale_value,
                "distinct_buyers": 0,
                "cluster_buying": False,
                "noise_transactions": int(len(noise)),
            },
        }

    purchases["days_ago"] = (
        as_of_ts - purchases["transaction_date"].dt.tz_localize(None)
    ).dt.days
    purchases["days_ago"] = purchases["days_ago"].clip(lower=0).fillna(999)
    purchases["recency_weight"] = np.exp(-purchases["days_ago"] / 90)

    weighted_purchase_value = float(
        (purchases["value"] * purchases["recency_weight"]).sum()
    )
    purchase_value = float(purchases["value"].sum())
    sale_value = float(sales["value"].sum()) if not sales.empty else 0.0
    distinct_buyers = int(purchases.get("insider_name", pd.Series(dtype=str)).nunique())
    recent_purchases = purchases[purchases["days_ago"] <= 30]
    cluster_buying = recent_purchases.get("insider_name", pd.Series(dtype=str)).nunique() >= 2

    role_text = " ".join(purchases.get("role", pd.Series(dtype=str)).fillna("").str.lower())
    role_bonus = 0
    if any(role in role_text for role in ["ceo", "chief executive"]):
        role_bonus += 8
    if any(role in role_text for role in ["cfo", "chief financial"]):
        role_bonus += 6
    if "director" in role_text:
        role_bonus += 4

    value_score = min(35.0, np.log10(max(weighted_purchase_value, 1.0)) * 7.0)
    buyer_score = min(18.0, distinct_buyers * 6.0)
    cluster_score = 15.0 if cluster_buying else 0.0
    recency_score = min(17.0, float(purchases["recency_weight"].max()) * 17.0)
    sale_penalty = min(18.0, (sale_value / max(purchase_value, 1.0)) * 12.0)
    plan_penalty = min(8.0, float(purchases["is_10b5_1"].sum()) * 4.0)
    noise_penalty = min(8.0, len(noise) * 1.5)

    score = (
        value_score
        + buyer_score
        + cluster_score
        + recency_score
        + role_bonus
        - sale_penalty
        - plan_penalty
        - noise_penalty
    )
    score = float(np.clip(score, 0, 100))
    quality = _quality_from_score(score, False)

    explanation_parts = [
        f"${purchase_value:,.0f} open-market purchases",
        f"{distinct_buyers} distinct buyer(s)",
    ]
    if cluster_buying:
        explanation_parts.append("cluster buying within 30 days")
    if sale_value > 0:
        explanation_parts.append(f"${sale_value:,.0f} insider sales offset part of the signal")
    if not noise.empty:
        explanation_parts.append(f"{len(noise)} noise transaction(s) penalized")

    return {
        "score": round(score, 2),
        "quality": quality,
        "explanation": "; ".join(explanation_parts) + ".",
        "metrics": {
            "purchase_value": round(purchase_value, 2),
            "weighted_purchase_value": round(weighted_purchase_value, 2),
            "sale_value": round(sale_value, 2),
            "distinct_buyers": distinct_buyers,
            "cluster_buying": bool(cluster_buying),
            "noise_transactions": int(len(noise)),
            "most_recent_days_ago": int(purchases["days_ago"].min()),
        },
    }
