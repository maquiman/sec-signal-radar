CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector TEXT,
    market_cap REAL,
    revenue_growth REAL,
    gross_margin REAL,
    operating_margin REAL,
    free_cash_flow REAL,
    debt_ratio REAL,
    shares_growth REAL,
    earnings_trend REAL,
    avg_volume REAL,
    liquidity_score REAL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS form4_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    filing_date TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    insider_name TEXT,
    role TEXT,
    transaction_code TEXT NOT NULL,
    shares REAL,
    price REAL,
    value REAL,
    holdings_after REAL,
    is_10b5_1 INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS political_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    politician TEXT NOT NULL,
    party TEXT,
    chamber TEXT,
    transaction_date TEXT NOT NULL,
    disclosure_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    amount_range TEXT,
    amount_midpoint REAL,
    committee_relevance REAL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS institutional_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    filer_name TEXT NOT NULL,
    filing_date TEXT NOT NULL,
    period_end TEXT,
    shares_change REAL,
    value_change REAL,
    percent_change REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS activist_filings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    filing_type TEXT NOT NULL,
    filer_name TEXT NOT NULL,
    filing_date TEXT NOT NULL,
    ownership_percent REAL,
    change_percent REAL,
    intent TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS price_history (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    spy_close REAL,
    qqq_close REAL,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    records_loaded INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    message TEXT,
    updated_at TEXT NOT NULL
);
