# Fundamental Database

Independent, open-source historical financial fundamentals ingestion pipeline. **Current production-capable scope: US SEC EDGAR XBRL Company Facts.** India, global markets, pricing, ownership, and cross-sector rankings are **not implemented**. Data is not bundled and must be collected under applicable SEC access rules.

## Quick start

```bash
python -m pip install -e '.[analytics,dev]'
export SEC_USER_AGENT='Research Team research@example.org'  # REPLACE with your real contact
python -m fundamental_database.cli companies
python -m fundamental_database.cli collect --limit 25 --offset 0
python -m fundamental_database.cli audit
python -m fundamental_database.cli export
python -m fundamental_database.cli snapshot --cik 320193 --as-of 2025-01-01
python -m pytest -q
```

Windows PowerShell: `$env:SEC_USER_AGENT = 'Your Organization contact@yourdomain.com'`.

## Architecture

- `companies` and `company_tickers`: current SEC company ticker list (not a complete historical identifier timeline).
- `facts`: unmodified numeric XBRL values and their form, accession, filed date, reporting period, units, taxonomy, and frame. Annual/quarterly observations and amended facts are retained without arbitrary history cutoff.
- `metrics`: a deliberately conservative set of US GAAP tags mapped to common financial metrics; alternate tags are retained individually.
- `snapshot`: a point-in-time view as of a filing cutoff; key includes start/end dates to avoid mixing annual with quarterly durations. Derived ratios require matching periods; no historical valuation without price data.
- `data/fundamentals.sqlite`: transactional local database generated during a run; `data/parquet/*.parquet`: optional DuckDB/Arrow exports.

## GitHub Actions

Set repository secret `SEC_USER_AGENT` to a real identifying name and email. Run **SEC Incremental Collection** manually with `offset` and `limit`, or allow weekly schedule. Workflow uploads its SQLite and Parquet outputs as a 30-day Actions artifact. **Artifacts are not a persistent global database**: each run starts fresh, and weekly schedule collects the first 100 companies unless configured differently. To build full coverage, orchestrate all batches and durable artifact consolidation/storage separately. No unbounded automated scraping is configured.

## Data integrity / limitations

- SEC Company Facts availability differs across issuers, tags, years, and accounting regimes. Some companies have no XBRL facts; SEC coverage is not universal.
- The collector stores 10-K, 10-Q, 20-F and 40-F including amendments; excludes other forms and nonnumeric values. SEC may repeat observations across filings; distinct accession provenance is retained.
- Normalization currently covers selected `us-gaap` tags and USD amounts; IFRS and currency conversion are not yet normalized.
- Values are source-native and may include cumulative year-to-date cash flows; **do not treat every duration as a standalone quarter**. TTM, sector ranking, price valuation, and cross-company comparability require additional rules.
- Source tag precedence is deterministic; restatements are selected within the same metric, duration, and source tag. Point-in-time view filters by `filed` (not exact public timestamp).
- SQLite is used for robust ingestion without a server. DuckDB is used for optional Parquet export; Parquet requires installed analytics extras.
- Audit reports coverage and suspicious dates, not an external financial-statement reconciliation or guarantee of accuracy.
- Respect SEC fair access, reasonable request pacing, and data licensing. Requests use an identifying User-Agent and timeout. Failures are reported rather than silently marked complete.

## Next milestones

Full market universe batching/checkpointing, durable GitHub-compatible storage, IFRS/India filings access, richer taxonomy mapping, per-company quality coverage, accounting-period normalization, price history and valuation, sector classifications, rankings, dashboard and integration tests against live sources.

## Collection reliability (November 2026 update)

- SEC Company Facts HTTP 404 responses are reported under `missing` and do not abort the batch.
- Transient HTTP 429/5xx and network errors are retried with bounded backoff.
- `--continue-on-error` continues after per-company errors; a batch with no successful requests and actual failures still exits nonzero.
- Parquet export uses `pyarrow` directly; no pandas installation is required. Install `pip install -e '.[analytics]'` for export.
- GitHub Actions artifacts are **temporary** (30-day retention), not a persistent historical database. Download and persist them before expiry; each run starts from a fresh checkout unless separate persistence is configured.

## Extended research pipeline (November 2026)

The `rank` command produces `data/rankings.json` with transparent within-reporting-date percentile scores. It uses annual flow periods only, does not impute missing metrics, and compares companies with identical fiscal period-end dates. **These are preliminary financial-strength scores, not investment recommendations or globally comparable rankings.** The score currently uses net/operating/gross margins, simple ending-equity ROE, FCF and liabilities/assets when calculable; companies require at least two metrics. Market-price-based valuation and industry-relative comparisons are not implemented.

Run `python -m fundamental_database.cli rank`, or launch the optional local dashboard with `pip install -e '.[dashboard]'` and `streamlit run dashboard_app.py`.

### Persistent GitHub storage

The collection workflow now saves a gzip-compressed SQLite snapshot **per offset/limit batch** as an asset in the `historical-sec-data` GitHub Release. Each run restores the matching shard before updating it. These are *independent shards*, not one automatically merged global database. Download shards and merge/deduplicate them before cross-universe rankings; rankings produced by a single workflow run only cover that shard. Scheduled runs rotate through 150 shards of 100 CIKs; this rotation is a starting configuration, **not a guarantee of complete SEC coverage**. SEC listings may grow or change, and offsets can shift. Release asset size and GitHub quotas still apply. Never put private data or secrets in public release assets. A full-universe manifest and stable-CIK partitioning are recommended before production-scale backfills.

### Limitations and next work

* U.S. SEC Company Facts collection works where facts are available; coverage and completeness must be audited against the entire company master. Filings not represented in Company Facts are not ingested.
* The India exchange filing collectors and IFRS/Ind AS normalization are **not implemented**; no India financial coverage is claimed.
* Global historical market prices, FX rates, industry mappings, ownership, valuation ratios, consolidated multi-market rankings, and hosted dashboard deployment are **not implemented**.
* This project has unit tests and a GitHub workflow, but a passing CI job alone does not verify the full history or every issuer. Download the workflow artifact and inspect `audit.json` and the underlying data.
