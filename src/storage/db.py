from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.scoring.fundamental_score import calculate_fundamental_score
from src.scoring.insider_score import calculate_insider_score
from src.scoring.political_score import calculate_political_score
from src.scoring.risk_score import calculate_risk_penalty
from src.scoring.technical_score import calculate_technical_score
from src.scoring.total_score import calculate_total_score, signal_quality
from src.utils.config import DB_PATH, ROOT_DIR
from src.utils.logging import get_logger


LOGGER = get_logger(__name__)


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def initialize_database(db_path: Path | str = DB_PATH) -> Path:
    db_path = Path(db_path)
    with get_connection(db_path) as conn:
        schema = (ROOT_DIR / "src" / "storage" / "schema.sql").read_text()
        conn.executescript(schema)
        company_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        if company_count == 0:
            LOGGER.info("Seeding sample data into %s", db_path)
            seed_sample_data(conn)
    return db_path


def seed_sample_data(conn: sqlite3.Connection) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    companies = [
        (
            "NVDA",
            "NVIDIA Corp.",
            "Technology",
            2_900_000_000_000,
            0.78,
            0.76,
            0.58,
            29_000_000_000,
            0.18,
            0.01,
            1.0,
            44_000_000,
            0.95,
        ),
        (
            "CRWD",
            "CrowdStrike Holdings",
            "Technology",
            86_000_000_000,
            0.31,
            0.75,
            0.09,
            1_100_000_000,
            0.32,
            0.025,
            0.7,
            3_800_000,
            0.88,
        ),
        (
            "ENPH",
            "Enphase Energy",
            "Energy",
            15_000_000_000,
            -0.08,
            0.43,
            0.03,
            520_000_000,
            0.58,
            0.018,
            -0.3,
            4_100_000,
            0.75,
        ),
        (
            "RXRX",
            "Recursion Pharmaceuticals",
            "Healthcare",
            2_700_000_000,
            0.21,
            0.69,
            -0.95,
            -390_000_000,
            0.22,
            0.12,
            -0.2,
            2_500_000,
            0.7,
        ),
        (
            "SMCI",
            "Super Micro Computer",
            "Technology",
            45_000_000_000,
            0.43,
            0.16,
            0.09,
            420_000_000,
            0.41,
            0.06,
            0.3,
            6_200_000,
            0.86,
        ),
        (
            "BROS",
            "Dutch Bros",
            "Consumer Cyclical",
            7_200_000_000,
            0.28,
            0.31,
            0.06,
            70_000_000,
            0.64,
            0.04,
            0.5,
            1_800_000,
            0.73,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO companies (
            ticker, company_name, sector, market_cap, revenue_growth, gross_margin,
            operating_margin, free_cash_flow, debt_ratio, shares_growth,
            earnings_trend, avg_volume, liquidity_score, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [row + (now.isoformat(),) for row in companies],
    )

    form4_rows = [
        ("CRWD", 9, 10, "George Kurtz", "CEO", "P", 12_000, 345.5, 4_146_000, 870_000, 0, "Open-market purchase"),
        ("CRWD", 12, 12, "Burt Podbere", "CFO", "P", 4_000, 338.0, 1_352_000, 150_000, 0, "Open-market purchase"),
        ("CRWD", 24, 24, "Director A", "Director", "P", 2_500, 318.0, 795_000, 62_000, 0, "Director buy"),
        ("ENPH", 17, 18, "Badri Kothandaraman", "CEO", "P", 20_000, 91.25, 1_825_000, 260_000, 0, "Open-market purchase"),
        ("ENPH", 85, 85, "Executive B", "Officer", "S", 8_000, 108.0, 864_000, 100_000, 1, "10b5-1 sale"),
        ("RXRX", 14, 15, "Director C", "Director", "P", 75_000, 8.1, 607_500, 440_000, 0, "Director buy"),
        ("RXRX", 16, 16, "Director D", "Director", "P", 50_000, 8.0, 400_000, 320_000, 0, "Director buy"),
        ("RXRX", 30, 31, "Executive E", "Officer", "A", 100_000, 0.0, 0, 100_000, 0, "RSU award"),
        ("SMCI", 23, 24, "Officer F", "Officer", "S", 5_000, 880.0, 4_400_000, 88_000, 1, "10b5-1 sale"),
        ("NVDA", 120, 120, "Officer G", "Officer", "M", 20_000, 0.0, 0, 200_000, 0, "Option exercise"),
        ("BROS", 6, 7, "Director H", "Director", "P", 30_000, 39.2, 1_176_000, 210_000, 0, "Open-market purchase"),
    ]
    conn.executemany(
        """
        INSERT INTO form4_transactions (
            ticker, filing_date, transaction_date, insider_name, role,
            transaction_code, shares, price, value, holdings_after, is_10b5_1, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                ticker,
                (now - timedelta(days=filing_days)).date().isoformat(),
                (now - timedelta(days=tx_days)).date().isoformat(),
                insider,
                role,
                code,
                shares,
                price,
                value,
                holdings,
                plan,
                notes,
            )
            for (
                ticker,
                filing_days,
                tx_days,
                insider,
                role,
                code,
                shares,
                price,
                value,
                holdings,
                plan,
                notes,
            ) in form4_rows
        ],
    )

    political_rows = [
        ("CRWD", "Representative Sample", "I", "House", 42, 25, "Purchase", "$15,001 - $50,000", 32_500.5, 0.7, "Cybersecurity committee relevance"),
        ("ENPH", "Senator Sample", "I", "Senate", 76, 16, "Purchase", "$1,001 - $15,000", 8_000.5, 0.4, "Energy policy relevance"),
        ("SMCI", "Representative Sample 2", "I", "House", 58, 39, "Sale", "$50,001 - $100,000", 75_000.5, 0.3, "Sale disclosure"),
        ("BROS", "Representative Sample 3", "I", "House", 25, 8, "Purchase", "$1,001 - $15,000", 8_000.5, 0.1, "Consumer sector trade"),
    ]
    conn.executemany(
        """
        INSERT INTO political_trades (
            ticker, politician, party, chamber, transaction_date, disclosure_date,
            transaction_type, amount_range, amount_midpoint, committee_relevance, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                ticker,
                politician,
                party,
                chamber,
                (now - timedelta(days=tx_days)).date().isoformat(),
                (now - timedelta(days=max(tx_days - lag_days, 0))).date().isoformat(),
                tx_type,
                amount_range,
                midpoint,
                relevance,
                notes,
            )
            for (
                ticker,
                politician,
                party,
                chamber,
                tx_days,
                lag_days,
                tx_type,
                amount_range,
                midpoint,
                relevance,
                notes,
            ) in political_rows
        ],
    )

    inst_rows = [
        ("CRWD", "Sample Growth Fund", 38, 75, 420_000, 145_000_000, 0.12, "Added shares in latest 13F"),
        ("ENPH", "Sample Green Fund", 41, 75, -110_000, -10_000_000, -0.04, "Reduced position"),
        ("RXRX", "Sample Innovation Fund", 39, 75, 900_000, 7_200_000, 0.22, "Added speculative growth exposure"),
        ("BROS", "Sample Consumer Fund", 35, 75, 150_000, 5_800_000, 0.09, "Added shares"),
    ]
    conn.executemany(
        """
        INSERT INTO institutional_changes (
            ticker, filer_name, filing_date, period_end, shares_change,
            value_change, percent_change, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                ticker,
                filer,
                (now - timedelta(days=filing_days)).date().isoformat(),
                (now - timedelta(days=period_days)).date().isoformat(),
                shares,
                value,
                pct,
                notes,
            )
            for ticker, filer, filing_days, period_days, shares, value, pct, notes in inst_rows
        ],
    )

    activist_rows = [
        ("ENPH", "13G", "Sample Capital", 52, 5.4, 1.2, "Passive stake", "New beneficial owner filing"),
        ("RXRX", "13D", "Sample Activist LP", 22, 7.8, 3.1, "Strategic alternatives", "Activist intent language"),
    ]
    conn.executemany(
        """
        INSERT INTO activist_filings (
            ticker, filing_type, filer_name, filing_date, ownership_percent,
            change_percent, intent, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                ticker,
                filing_type,
                filer,
                (now - timedelta(days=filing_days)).date().isoformat(),
                ownership,
                change,
                intent,
                notes,
            )
            for ticker, filing_type, filer, filing_days, ownership, change, intent, notes in activist_rows
        ],
    )

    price_rows: list[tuple[Any, ...]] = []
    for ticker, _, _, _, *_ in companies:
        price_rows.extend(_generate_price_rows(ticker, now))
    conn.executemany(
        """
        INSERT INTO price_history (ticker, date, close, volume, spy_close, qqq_close)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        price_rows,
    )

    logs = [
        ("sample_companies", "ok", len(companies), 0, "Seeded local sample company data"),
        ("sample_form4", "ok", len(form4_rows), 0, "Seeded local sample Form 4 data"),
        ("sample_political", "ok", len(political_rows), 0, "Seeded local sample political trades"),
        ("sample_13f", "ok", len(inst_rows), 0, "Seeded local sample 13F changes"),
        ("sample_13d_13g", "ok", len(activist_rows), 0, "Seeded local sample activist filings"),
        ("sample_prices", "ok", len(price_rows), 0, "Seeded deterministic sample prices"),
    ]
    conn.executemany(
        """
        INSERT INTO ingestion_log (source, status, records_loaded, api_calls, message, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [row + (now.isoformat(),) for row in logs],
    )
    conn.commit()


def load_table(table_name: str, db_path: Path | str = DB_PATH) -> pd.DataFrame:
    allowed = {
        "companies",
        "form4_transactions",
        "political_trades",
        "institutional_changes",
        "activist_filings",
        "price_history",
        "ingestion_log",
    }
    if table_name not in allowed:
        raise ValueError(f"Unsupported table: {table_name}")
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)


def load_ticker_bundle(ticker: str, db_path: Path | str = DB_PATH) -> dict[str, pd.DataFrame]:
    initialize_database(db_path)
    ticker = ticker.upper()
    with get_connection(db_path) as conn:
        return {
            "company": pd.read_sql_query(
                "SELECT * FROM companies WHERE ticker = ?", conn, params=(ticker,)
            ),
            "form4": pd.read_sql_query(
                "SELECT * FROM form4_transactions WHERE ticker = ? ORDER BY transaction_date DESC",
                conn,
                params=(ticker,),
            ),
            "political": pd.read_sql_query(
                "SELECT * FROM political_trades WHERE ticker = ? ORDER BY transaction_date DESC",
                conn,
                params=(ticker,),
            ),
            "institutional": pd.read_sql_query(
                "SELECT * FROM institutional_changes WHERE ticker = ? ORDER BY filing_date DESC",
                conn,
                params=(ticker,),
            ),
            "activist": pd.read_sql_query(
                "SELECT * FROM activist_filings WHERE ticker = ? ORDER BY filing_date DESC",
                conn,
                params=(ticker,),
            ),
            "prices": pd.read_sql_query(
                "SELECT * FROM price_history WHERE ticker = ? ORDER BY date ASC",
                conn,
                params=(ticker,),
            ),
        }


def build_screener(db_path: Path | str = DB_PATH) -> pd.DataFrame:
    initialize_database(db_path)
    companies = load_table("companies", db_path)
    rows: list[dict[str, Any]] = []

    for _, company in companies.iterrows():
        ticker = company["ticker"]
        bundle = load_ticker_bundle(ticker, db_path)
        form4 = bundle["form4"]
        political = bundle["political"]
        institutional = bundle["institutional"]
        activist = bundle["activist"]
        prices = bundle["prices"]

        insider = calculate_insider_score(form4)
        political_score = calculate_political_score(political)
        technical = calculate_technical_score(prices)
        fundamental = calculate_fundamental_score(company)
        institutional_score = _institutional_score(institutional)
        activist_score = _activist_score(activist)
        latest_event, days_since_latest = _latest_event(form4, political, institutional, activist)
        risk = calculate_risk_penalty(company, technical, insider, days_since_latest)
        filing_score = _filing_score(days_since_latest, insider, activist_score)

        scores = {
            "insider_score": insider["score"],
            "technical_score": technical["score"],
            "fundamental_score": fundamental["score"],
            "activist_score": activist_score,
            "institutional_score": institutional_score,
            "political_score": political_score["score"],
        }
        total = calculate_total_score(scores, risk["penalty"])
        quality = signal_quality(
            total["total_opportunity_score"],
            [insider["quality"], political_score["quality"], technical["quality"], fundamental["quality"]],
            risk["penalty"],
        )
        explanation = _short_explanation(
            insider,
            political_score,
            technical,
            fundamental,
            activist_score,
            institutional_score,
            risk,
        )

        rows.append(
            {
                "ticker": ticker,
                "company name": company["company_name"],
                "sector": company["sector"],
                "market cap": company["market_cap"],
                "total opportunity score": total["total_opportunity_score"],
                "filing score": filing_score,
                "insider score": insider["score"],
                "political trades score": political_score["score"],
                "institutional score": institutional_score,
                "activist score": activist_score,
                "technical score": technical["score"],
                "fundamental score": fundamental["score"],
                "risk penalty": risk["penalty"],
                "latest relevant event": latest_event,
                "days since latest filing": days_since_latest,
                "signal quality": quality,
                "short explanation": explanation,
                "has open-market purchase": bool(insider["metrics"].get("purchase_value", 0) > 0),
            }
        )

    return pd.DataFrame(rows).sort_values("total opportunity score", ascending=False)


def diagnostics(db_path: Path | str = DB_PATH) -> pd.DataFrame:
    initialize_database(db_path)
    log = load_table("ingestion_log", db_path)
    tables = [
        "companies",
        "form4_transactions",
        "political_trades",
        "institutional_changes",
        "activist_filings",
        "price_history",
    ]
    counts = {}
    with get_connection(db_path) as conn:
        for table in tables:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    rows = []
    source_aliases = {
        "companies": {"sample_companies", "sec_companies"},
        "form4_transactions": {"sample_form4", "sec_form4"},
        "political_trades": {"sample_political", "fmp_political"},
        "institutional_changes": {"sample_13f", "sec_13f"},
        "activist_filings": {"sample_13d_13g", "sec_13d_13g"},
        "price_history": {"sample_prices", "yahoo_prices"},
    }
    for source, count in counts.items():
        source_log = log[log["source"].isin(source_aliases[source])]
        latest = source_log["updated_at"].max() if not source_log.empty else None
        rows.append(
            {
                "source": source,
                "last updated": latest,
                "records loaded": count,
                "estimated api calls": int(source_log["api_calls"].sum()) if not source_log.empty else 0,
                "recent errors": "; ".join(source_log[source_log["status"] != "ok"]["message"].fillna("").tail(3)),
            }
        )
    return pd.DataFrame(rows)


def _generate_price_rows(ticker: str, now: datetime) -> list[tuple[Any, ...]]:
    seed = sum(ord(char) for char in ticker)
    rng = np.random.default_rng(seed)
    rows = []
    start_prices = {
        "NVDA": 820,
        "CRWD": 250,
        "ENPH": 132,
        "RXRX": 6.5,
        "SMCI": 420,
        "BROS": 28,
    }
    drift = {
        "NVDA": 0.0022,
        "CRWD": 0.0028,
        "ENPH": -0.0011,
        "RXRX": 0.0017,
        "SMCI": 0.0021,
        "BROS": 0.0015,
    }
    vol = {
        "NVDA": 0.022,
        "CRWD": 0.026,
        "ENPH": 0.033,
        "RXRX": 0.045,
        "SMCI": 0.04,
        "BROS": 0.024,
    }
    price = start_prices.get(ticker, 50.0)
    spy = 500.0
    qqq = 430.0
    for idx in range(260):
        date = (now - timedelta(days=259 - idx)).date().isoformat()
        price *= 1 + drift.get(ticker, 0.001) + rng.normal(0, vol.get(ticker, 0.025))
        spy *= 1 + 0.0007 + rng.normal(0, 0.008)
        qqq *= 1 + 0.0009 + rng.normal(0, 0.01)
        volume = max(80_000, abs(rng.normal(1_000_000 + seed * 3000, 180_000)))
        rows.append((ticker, date, round(price, 2), round(volume), round(spy, 2), round(qqq, 2)))
    return rows


def _institutional_score(rows: pd.DataFrame) -> float:
    if rows.empty:
        return 0.0
    pct = pd.to_numeric(rows.get("percent_change", 0), errors="coerce").fillna(0)
    value = pd.to_numeric(rows.get("value_change", 0), errors="coerce").fillna(0)
    score = 45 + pct.sum() * 120 + np.sign(value.sum()) * min(abs(value.sum()) / 20_000_000, 20)
    return round(float(np.clip(score, 0, 100)), 2)


def _activist_score(rows: pd.DataFrame) -> float:
    if rows.empty:
        return 0.0
    score = 0.0
    for _, row in rows.iterrows():
        filing_type = str(row.get("filing_type", "")).upper()
        ownership = float(row.get("ownership_percent") or 0)
        change = float(row.get("change_percent") or 0)
        intent = str(row.get("intent", "")).lower()
        score += 35 if filing_type == "13D" else 20
        score += min(ownership * 4, 25)
        score += min(max(change, 0) * 6, 20)
        if "strategic" in intent or "activist" in intent:
            score += 15
    return round(float(np.clip(score, 0, 100)), 2)


def _latest_event(*tables: pd.DataFrame) -> tuple[str, int | None]:
    candidates: list[tuple[pd.Timestamp, str]] = []
    for table in tables:
        if table.empty:
            continue
        date_col = "filing_date" if "filing_date" in table.columns else "disclosure_date"
        for _, row in table.iterrows():
            date = pd.to_datetime(row.get(date_col), errors="coerce")
            if pd.notna(date):
                label = row.get("notes") or row.get("filing_type") or row.get("transaction_type") or "Event"
                candidates.append((date, str(label)))
    if not candidates:
        return "No local filing event", None
    latest_date, label = max(candidates, key=lambda item: item[0])
    days = int((pd.Timestamp.utcnow().tz_localize(None) - latest_date.tz_localize(None)).days)
    return f"{latest_date.date().isoformat()} - {label}", max(days, 0)


def _filing_score(
    days_since_latest: int | None,
    insider_result: dict[str, Any],
    activist_score: float,
) -> float:
    if days_since_latest is None:
        return 0.0
    recency = max(0.0, 100.0 - days_since_latest * 1.2)
    event_strength = max(float(insider_result.get("score", 0)), activist_score)
    return round(float(np.clip(recency * 0.45 + event_strength * 0.55, 0, 100)), 2)


def _short_explanation(
    insider: dict[str, Any],
    political: dict[str, Any],
    technical: dict[str, Any],
    fundamental: dict[str, Any],
    activist_score: float,
    institutional_score: float,
    risk: dict[str, Any],
) -> str:
    parts = [
        f"Insider: {insider['explanation']}",
        f"Technical: {technical['explanation']}",
        f"Fundamental: {fundamental['explanation']}",
    ]
    if political.get("score", 0) > 0:
        parts.append(f"Political: {political['explanation']}")
    if activist_score > 0:
        parts.append(f"Activist score {activist_score:.0f}")
    if institutional_score > 0:
        parts.append(f"Institutional score {institutional_score:.0f}")
    if risk.get("penalty", 0) > 0:
        parts.append(f"Risk penalty: {risk['explanation']}")
    return " ".join(parts)
