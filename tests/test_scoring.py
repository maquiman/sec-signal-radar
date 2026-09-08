from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.scoring.insider_score import calculate_insider_score
from src.scoring.political_score import calculate_political_score, parse_amount_midpoint
from src.scoring.total_score import calculate_total_score
from src.storage.db import diagnostics


def test_insider_score_rewards_cluster_open_market_purchases() -> None:
    transactions = pd.DataFrame(
        [
            {
                "transaction_code": "P",
                "transaction_date": "2026-05-20",
                "insider_name": "CEO Example",
                "role": "CEO",
                "shares": 10_000,
                "price": 25,
                "value": 250_000,
                "is_10b5_1": 0,
            },
            {
                "transaction_code": "P",
                "transaction_date": "2026-05-22",
                "insider_name": "CFO Example",
                "role": "CFO",
                "shares": 8_000,
                "price": 24,
                "value": 192_000,
                "is_10b5_1": 0,
            },
        ]
    )

    result = calculate_insider_score(transactions, as_of=pd.Timestamp("2026-05-31"))

    assert result["score"] >= 60
    assert result["quality"] in {"Medium", "High"}
    assert result["metrics"]["cluster_buying"] is True
    assert result["metrics"]["distinct_buyers"] == 2


def test_insider_score_treats_awards_as_noise() -> None:
    transactions = pd.DataFrame(
        [
            {
                "transaction_code": "A",
                "transaction_date": "2026-05-20",
                "insider_name": "Officer Example",
                "role": "Officer",
                "shares": 10_000,
                "price": 0,
                "value": 0,
            }
        ]
    )

    result = calculate_insider_score(transactions, as_of=pd.Timestamp("2026-05-31"))

    assert result["score"] == 0
    assert result["quality"] == "Noise"


def test_political_score_uses_amount_midpoint_and_lag() -> None:
    trades = pd.DataFrame(
        [
            {
                "politician": "Rep. Example",
                "transaction_type": "Purchase",
                "transaction_date": "2026-05-01",
                "disclosure_date": "2026-05-20",
                "amount_range": "$1,001 - $15,000",
                "committee_relevance": 0.8,
            }
        ]
    )

    result = calculate_political_score(trades, as_of=pd.Timestamp("2026-05-31"))

    assert parse_amount_midpoint("$1,001 - $15,000") == 8000.5
    assert result["score"] > 0
    assert result["metrics"]["average_disclosure_lag"] == 19


def test_total_score_subtracts_risk_penalty() -> None:
    result = calculate_total_score(
        {
            "insider_score": 80,
            "technical_score": 60,
            "fundamental_score": 50,
            "activist_score": 40,
            "institutional_score": 20,
            "political_score": 10,
        },
        risk_penalty=12,
    )

    assert result["total_opportunity_score"] == 46.5


def test_seeded_diagnostics_include_update_times() -> None:
    db_path = Path("data/cache/test_diagnostics.sqlite3")
    result = diagnostics(db_path)

    assert len(result) == 6
    assert result["last updated"].notna().all()
    assert result["records loaded"].sum() > 0
