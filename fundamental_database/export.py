"""Export SQLite tables to compressed Parquet without a pandas dependency."""
from pathlib import Path


def export_parquet(sqlite_db, output):
    import pyarrow as pa
    import pyarrow.parquet as pq

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    exported = []
    for name in ('companies', 'company_tickers', 'filings', 'facts', 'metrics'):
        cursor = sqlite_db.execute(f'SELECT * FROM {name}')
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        if not rows:
            continue
        data = {col: [row[i] for row in rows] for i, col in enumerate(columns)}
        table = pa.table(data)
        target = output / f'{name}.parquet'
        pq.write_table(table, target, compression='zstd')
        exported.append(target)
    return exported
