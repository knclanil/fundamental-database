import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS companies (
 cik INTEGER PRIMARY KEY, name TEXT NOT NULL, ticker TEXT, exchange TEXT,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS company_tickers (
 cik INTEGER NOT NULL, ticker TEXT NOT NULL, exchange TEXT,
 PRIMARY KEY(cik,ticker,exchange), FOREIGN KEY(cik) REFERENCES companies(cik)
);
CREATE TABLE IF NOT EXISTS filings (
 cik INTEGER NOT NULL, accession TEXT NOT NULL, form TEXT, filed TEXT,
 PRIMARY KEY(cik,accession), FOREIGN KEY(cik) REFERENCES companies(cik)
);
CREATE TABLE IF NOT EXISTS facts (
 cik INTEGER NOT NULL, taxonomy TEXT NOT NULL, tag TEXT NOT NULL,
 unit TEXT NOT NULL, start TEXT NOT NULL DEFAULT '', end TEXT NOT NULL,
 val REAL NOT NULL, accession TEXT NOT NULL, filed TEXT NOT NULL,
 form TEXT NOT NULL, fiscal_year INTEGER, fiscal_period TEXT, frame TEXT NOT NULL DEFAULT '',
 PRIMARY KEY(cik,taxonomy,tag,unit,start,end,accession,frame),
 FOREIGN KEY(cik) REFERENCES companies(cik)
);
CREATE INDEX IF NOT EXISTS ix_facts_period ON facts(cik,tag,end,filed);
CREATE INDEX IF NOT EXISTS ix_facts_filed ON facts(filed);
CREATE TABLE IF NOT EXISTS metrics (
 cik INTEGER NOT NULL, metric TEXT NOT NULL, period_start TEXT NOT NULL DEFAULT '',
 period_end TEXT NOT NULL, accession TEXT NOT NULL, filed TEXT NOT NULL,
 value REAL NOT NULL, unit TEXT NOT NULL, taxonomy TEXT NOT NULL, source_tag TEXT NOT NULL,
 PRIMARY KEY(cik,metric,period_start,period_end,accession,source_tag)
);
CREATE INDEX IF NOT EXISTS ix_metrics ON metrics(cik,metric,period_end,filed);
CREATE TABLE IF NOT EXISTS runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT DEFAULT CURRENT_TIMESTAMP,
 ended_at TEXT, operation TEXT NOT NULL, status TEXT NOT NULL, detail TEXT
);
"""

def connect(path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(p))
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript(SCHEMA)
    return db
