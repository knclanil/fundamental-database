"""Idempotent ingestion; never discard amended historical filing facts."""
from datetime import date

ALLOWED_FORMS = {'10-K', '10-K/A', '10-Q', '10-Q/A', '20-F', '20-F/A', '40-F', '40-F/A'}

def ingest_companies(db, rows):
    count = 0
    for row in rows:
        cik = int(row['cik'])
        name = row.get('name') or row.get('title') or f'CIK {cik}'
        ticker = row.get('ticker') or ''
        exchange = row.get('exchange') or ''
        db.execute('''INSERT INTO companies(cik,name,ticker,exchange) VALUES(?,?,?,?)
            ON CONFLICT(cik) DO UPDATE SET name=excluded.name,ticker=excluded.ticker,
            exchange=excluded.exchange,updated_at=CURRENT_TIMESTAMP''', (cik,name,ticker,exchange))
        if ticker:
            db.execute('INSERT OR IGNORE INTO company_tickers VALUES(?,?,?)', (cik,ticker,exchange))
        count += 1
    db.commit()
    return count

def ingest_facts(db, payload, forms=ALLOWED_FORMS):
    cik = int(payload['cik'])
    db.execute('INSERT OR IGNORE INTO companies(cik,name) VALUES(?,?)', (cik,payload.get('entityName') or str(cik)))
    records = 0
    for taxonomy, tags in payload.get('facts', {}).items():
        for tag, definition in tags.items():
            for unit, items in definition.get('units', {}).items():
                for item in items:
                    if item.get('form') not in forms:
                        continue
                    if not all(k in item for k in ('end','val','accn','filed')):
                        continue
                    if not isinstance(item['val'], (int,float)) or isinstance(item['val'],bool):
                        continue
                    if item['filed'] > date.today().isoformat():
                        continue
                    accession = item['accn']
                    db.execute('INSERT OR IGNORE INTO filings(cik,accession,form,filed) VALUES(?,?,?,?)',
                               (cik,accession,item['form'],item['filed']))
                    db.execute('''INSERT OR IGNORE INTO facts
                        (cik,taxonomy,tag,unit,start,end,val,accession,filed,form,fiscal_year,fiscal_period,frame)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (cik,taxonomy,tag,unit,item.get('start',''),item['end'],item['val'],
                         accession,item['filed'],item['form'],item.get('fy'),item.get('fp'),item.get('frame','')))
                    records += 1
    db.commit()
    return records
