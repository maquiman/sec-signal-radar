from __future__ import annotations

from typing import Any

import pandas as pd


def calculate_risk_penalty(
    company_row: pd.Series | dict[str, Any] | None,
    technical_result: dict[str, Any] | None = None,
    insider_result: dict[str, Any] | None = None,
    days_since_latest_filing: int | None = None,
) -> dict[str, Any]:
    if company_row is None:
        row = pd.Series(dtype=object)
    else:
        row = pd.Series(company_row)
    technical_metrics = (technical_result or {}).get("metrics", {})
    insider_metrics = (insider_result or {}).get("metrics", {})

    penalty = 0.0
    reasons: list[str] = []

    market_cap = _num(row.get("market_cap"))
    avg_volume = _num(row.get("avg_volume"))
    debt_ratio = _num(row.get("debt_ratio"))
    shares_growth = _num(row.get("shares_growth"))

    if market_cap and market_cap < 300_000_000:
        penalty += 8
        reasons.append("small market cap")
    if avg_volume and avg_volume < 200_000:
        penalty += 8
        reasons.append("low liquidity")
    if debt_ratio > 0.7:
        penalty += 8
        reasons.append("high debt")
    if shares_growth > 0.08:
        penalty += 8
        reasons.append("dilution")
    if technical_metrics:
        latest = technical_metrics.get("latest_close", 0)
        dma200 = technical_metrics.get("dma200", 0)
        if dma200 and latest and latest < dma200 * 0.85:
            penalty += 10
            reasons.append("price materially below 200 DMA")
    if days_since_latest_filing is None:
        penalty += 6
        reasons.append("insufficient filing data")
    elif days_since_latest_filing > 120:
        penalty += 6
        reasons.append("stale filing signal")
    sale_value = insider_metrics.get("sale_value", 0)
    purchase_value = insider_metrics.get("purchase_value", 0)
    if sale_value > purchase_value * 1.5 and sale_value > 100_000:
        penalty += 8
        reasons.append("insider selling cluster")

    return {
        "penalty": round(min(penalty, 40.0), 2),
        "explanation": "; ".join(reasons) if reasons else "No major MVP risk penalty.",
        "metrics": {
            "market_cap": market_cap,
            "avg_volume": avg_volume,
            "debt_ratio": debt_ratio,
            "shares_growth": shares_growth,
        },
    }


def _num(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0
