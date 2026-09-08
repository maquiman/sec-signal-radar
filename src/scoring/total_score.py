from __future__ import annotations

from typing import Any


WEIGHTS = {
    "insider_score": 0.35,
    "technical_score": 0.25,
    "fundamental_score": 0.20,
    "activist_score": 0.10,
    "institutional_score": 0.05,
    "political_score": 0.05,
}


def calculate_total_score(scores: dict[str, float], risk_penalty: float) -> dict[str, Any]:
    weighted = sum(float(scores.get(name, 0.0)) * weight for name, weight in WEIGHTS.items())
    total = max(0.0, min(100.0, weighted - float(risk_penalty or 0.0)))
    return {
        "total_opportunity_score": round(total, 2),
        "weighted_components": {
            name: round(float(scores.get(name, 0.0)) * weight, 2)
            for name, weight in WEIGHTS.items()
        },
    }


def signal_quality(total_score: float, component_qualities: list[str], risk_penalty: float) -> str:
    if "Noise" in component_qualities and total_score < 35:
        return "Noise"
    if total_score >= 70 and risk_penalty < 15:
        return "High"
    if total_score >= 45:
        return "Medium"
    if total_score >= 25:
        return "Low"
    return "Noise"
