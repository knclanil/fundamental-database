def audit(db):
    counts = {}
    for name in ('companies','company_tickers','filings','facts','metrics'):
        counts[name] = db.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
    counts['orphan_facts'] = db.execute('''SELECT COUNT(*) FROM facts f LEFT JOIN companies c ON f.cik=c.cik WHERE c.cik IS NULL''').fetchone()[0]
    counts['invalid_dates'] = db.execute("SELECT COUNT(*) FROM facts WHERE filed<end OR length(end)!=10 OR length(filed)!=10").fetchone()[0]
    counts['missing_metrics_companies'] = db.execute('''SELECT COUNT(*) FROM companies c WHERE NOT EXISTS(SELECT 1 FROM metrics m WHERE m.cik=c.cik)''').fetchone()[0]
    return counts
