# SEC Signal Radar

MVP Streamlit dashboard for ranking stocks that may deserve deeper investment research based on public filing signals and market data. It is a research screener, not a buy/sell recommendation engine.

## What Is Included

- Main screener with total opportunity score, component scores, risk penalty, signal quality, and explanation.
- Ticker detail page with score breakdown, positive signals, risks, event timeline, Form 4 table, political trades, 13F changes, 13D/13G filings, and a price chart with event markers.
- Data health page with source timestamps, record counts, estimated API calls, ingestion errors, and sparse-data tickers.
- Local SQLite storage seeded with sample data, so the dashboard runs without API keys.
- Modular scoring for insider activity, political trades, technical setup, fundamentals, risk, and total score.
- Placeholder adapters for SEC EDGAR, Financial Modeling Prep, and Yahoo-style price ingestion.

## Run The Dashboard

On Windows, double click `Abrir SEC Signal Radar.bat` from the project folder.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run src/dashboard/app.py
```

The first run creates:

```text
data/cache/sec_signal_radar.sqlite3
data/cache/screener.log
```

The dashboard reads from SQLite/cache on refresh and does not call external APIs in the MVP.

> **Current status:** This repository is a working demo seeded with synthetic sample data.
> The SEC, political-trade, and market-data ingestion adapters are placeholders and must
> be implemented before using the dashboard with live investment data.

## Deploy On Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. In Streamlit Community Cloud, create an app from that repository.
3. Select your branch and use `src/dashboard/app.py` as the entrypoint.
4. Add API keys in Streamlit's Secrets settings; never commit `.env` or `secrets.toml`.

The local SQLite database is recreated with sample data when needed. Use an external
database before adding persistent watchlists or scheduled live-data ingestion.

## Optional FMP API Key

Copy `.env.example` to `.env` and set:

```text
FMP_API_KEY=your_key_here
ENABLE_FMP=true
```

FMP ingestion is intentionally a placeholder in this MVP. The app is already structured so a future ingestion job can fetch political trades, write them to SQLite, and let the dashboard continue reading local cached data.

## Scoring Model

Total Opportunity Score:

```text
35% insider_score
25% technical_score
20% fundamental_score
10% activist_score
5% institutional_score
5% political_score
- risk_penalty
```

All sub-scores are 0-100. `risk_penalty` subtracts points.

Insider scoring emphasizes open-market Form 4 purchase code `P`, purchase value, distinct buyers, officer/director role, cluster buying within 30 days, and recency decay. It penalizes sales, 10b5-1 context, and noise codes such as awards, option exercises, and tax withholding.

Political scoring is deliberately conservative because disclosures can arrive late. It considers unique buyers, buy/sell mix, midpoint trade amount, disclosure lag, recency, and committee relevance when available.

## Project Structure

```text
data/
  raw/
  processed/
  cache/
src/
  data_sources/
    sec_edgar.py
    fmp_political.py
    yahoo_prices.py
  scoring/
    insider_score.py
    political_score.py
    technical_score.py
    fundamental_score.py
    risk_score.py
    total_score.py
  storage/
    db.py
    schema.sql
  dashboard/
    app.py
    pages/
      screener.py
      ticker_detail.py
      diagnostics.py
  utils/
    config.py
    logging.py
tests/
```

## Tests

```powershell
pytest
```

## Next Phase TODOs

- Add SEC EDGAR Form 4 ingestion with issuer CIK/ticker mapping and transaction-code normalization.
- Add cached FMP political trades ingestion guarded by `ENABLE_FMP` and API-call logging.
- Add 13F and 13D/13G ingestion with quarterly refresh cadence.
- Replace sample fundamentals with SEC company facts or a cached fundamentals provider.
- Add watchlist persistence and exportable research notes.
