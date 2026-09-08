from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def calculate_fundamental_score(company_row: pd.Series | dict[str, Any] | None) -> dict[str, Any]:
    if company_row is None or len(company_row) == 0:
        return {
            "score": 0.0,
            "quality": "Low",
            "explanation": "No fundamental data available.",
            "metrics": {},
        }

    row = pd.Series(company_row)
    revenue_growth = _num(row.get("revenue_growth"))
    gross_margin = _num(row.get("gross_margin"))
    operating_margin = _num(row.get("operating_margin"))
    free_cash_flow = _num(row.get("free_cash_flow"))
    debt_ratio = _num(row.get("debt_ratio"))
    shares_growth = _num(row.get("shares_growth"))
    earnings_trend = _num(row.get("earnings_trend"))
    market_cap = _num(row.get("market_cap"))

    score = 45.0
    score += np.clip(revenue_growth * 100, -15, 20)
    score += np.clip(gross_margin * 30, 0, 18)
    score += np.clip(operating_margin * 40, -12, 16)
    score += 10 if free_cash_flow > 0 else -8
    score -= np.clip(debt_ratio * 20, 0, 18)
    score -= np.clip(shares_growth * 120, 0, 16)
    score += np.clip(earnings_trend * 12, -8, 8)
    if market_cap < 300_000_000:
        score -= 8
    elif market_cap > 2_000_000_000:
        score += 4
    score = float(np.clip(score, 0, 100))

    positives = []
    risks = []
    if revenue_growth > 0.15:
        positives.append("revenue growth")
    if free_cash_flow > 0:
        positives.append("positive free cash flow")
    if debt_ratio > 0.7:
        risks.append("high debt")
    if shares_growth > 0.08:
        risks.append("dilution")

    parts = positives or ["basic fundamentals present"]
    if risks:
        parts.append("risks: " + ", ".join(risks))

    return {
        "score": round(score, 2),
        "quality": "High" if score >= 70 else "Medium" if score >= 40 else "Low",
        "explanation": "; ".join(parts) + ".",
        "metrics": {
            "revenue_growth": revenue_growth,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "free_cash_flow": free_cash_flow,
            "debt_ratio": debt_ratio,
            "shares_growth": shares_growth,
            "earnings_trend": earnings_trend,
            "market_cap": market_cap,
        },
    }


def _num(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0
