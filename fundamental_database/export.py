from pathlib import Path

def export_parquet(sqlite_db, output):
    """Optional Parquet export, requires duckdb and pyarrow."""
    import pandas as pd
    import pyarrow  # noqa: F401
    import duckdb
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    for table in ('companies','company_tickers','filings','facts','metrics'):
        df = pd.read_sql_query(f'SELECT * FROM {table}',sqlite_db)
        if df.empty:
            continue
        dest = output / f'{table}.parquet'
        duckdb.from_df(df).write_parquet(str(dest),compression='zstd')
    return sorted(output.glob('*.parquet'))
