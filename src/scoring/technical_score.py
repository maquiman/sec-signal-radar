from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def calculate_technical_score(price_history: pd.DataFrame) -> dict[str, Any]:
    if price_history is None or price_history.empty or len(price_history) < 60:
        return {
            "score": 0.0,
            "quality": "Low",
            "explanation": "Insufficient price history for technical scoring.",
            "metrics": {},
        }

    df = price_history.copy().sort_values("date")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["close", "volume"])
    if len(df) < 60:
        return {
            "score": 0.0,
            "quality": "Low",
            "explanation": "Insufficient clean price data for technical scoring.",
            "metrics": {},
        }

    close = df["close"]
    latest = float(close.iloc[-1])
    dma50 = float(close.rolling(50).mean().iloc[-1])
    dma200 = float(close.rolling(200, min_periods=60).mean().iloc[-1])
    high_52w = float(close.tail(252).max())
    low_52w = float(close.tail(252).min())
    dist_high = (latest / high_52w - 1.0) if high_52w else 0.0

    dma50_slope = _slope(close.rolling(50).mean().dropna().tail(30))
    dma200_slope = _slope(close.rolling(200, min_periods=60).mean().dropna().tail(30))
    volume_trend = _volume_trend(df["volume"])
    relative_strength = _relative_strength(df)
    atr_pct = _atr_proxy(close)
    vcp_score = _vcp_score(df)

    score = 0.0
    score += 18 if latest > dma50 else 4
    score += 16 if latest > dma200 else 2
    score += np.clip(dma50_slope * 500, -8, 12) + 8
    score += np.clip(dma200_slope * 500, -6, 10) + 6
    score += np.clip(relative_strength * 80, -10, 14) + 8
    score += max(0, 12 - abs(dist_high) * 80)
    score += np.clip(volume_trend * 20, -4, 8) + 4
    score += vcp_score * 0.16
    score -= max(0, atr_pct - 0.08) * 100
    score = float(np.clip(score, 0, 100))

    positives = []
    if latest > dma50:
        positives.append("above 50 DMA")
    if latest > dma200:
        positives.append("above 200 DMA")
    if relative_strength > 0:
        positives.append("outperforming benchmark proxy")
    if vcp_score >= 55:
        positives.append("constructive volatility contraction")
    explanation = ", ".join(positives) if positives else "Weak or incomplete technical setup"

    return {
        "score": round(score, 2),
        "quality": "High" if score >= 70 else "Medium" if score >= 40 else "Low",
        "explanation": explanation + ".",
        "metrics": {
            "latest_close": round(latest, 2),
            "dma50": round(dma50, 2),
            "dma200": round(dma200, 2),
            "dma50_slope": round(float(dma50_slope), 4),
            "dma200_slope": round(float(dma200_slope), 4),
            "relative_strength": round(float(relative_strength), 4),
            "distance_from_52w_high": round(float(dist_high), 4),
            "volume_trend": round(float(volume_trend), 4),
            "atr_pct": round(float(atr_pct), 4),
            "vcp_score": round(float(vcp_score), 2),
        },
    }


def _slope(series: pd.Series) -> float:
    if len(series) < 2:
        return 0.0
    start = float(series.iloc[0])
    end = float(series.iloc[-1])
    return (end / start - 1.0) / max(len(series), 1) if start else 0.0


def _volume_trend(volume: pd.Series) -> float:
    recent = float(volume.tail(20).mean())
    prior = float(volume.tail(60).head(40).mean())
    return (recent / prior - 1.0) if prior else 0.0


def _relative_strength(df: pd.DataFrame) -> float:
    benchmark_col = "spy_close" if "spy_close" in df and df["spy_close"].notna().any() else None
    if not benchmark_col:
        return 0.0
    stock_return = df["close"].tail(63).iloc[-1] / df["close"].tail(63).iloc[0] - 1.0
    bench = pd.to_numeric(df[benchmark_col], errors="coerce").dropna().tail(63)
    if len(bench) < 2:
        return 0.0
    bench_return = bench.iloc[-1] / bench.iloc[0] - 1.0
    return float(stock_return - bench_return)


def _atr_proxy(close: pd.Series) -> float:
    returns = close.pct_change().dropna()
    return float(returns.tail(20).std() * np.sqrt(1)) if not returns.empty else 0.0


def _vcp_score(df: pd.DataFrame) -> float:
    close = df["close"]
    windows = [80, 40, 20]
    ranges = []
    for window in windows:
        chunk = close.tail(window)
        if len(chunk) < max(10, window // 2):
            return 0.0
        ranges.append(float(chunk.max() / chunk.min() - 1.0))
    contracting = ranges[0] > ranges[1] > ranges[2]
    tightness = max(0.0, 1.0 - ranges[-1] / 0.25)
    base = 70.0 if contracting else 35.0
    return float(np.clip(base + tightness * 30.0, 0, 100))
