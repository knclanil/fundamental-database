"""GitHub Actions orchestrator for resumable SEC company-facts sweeps.

Requires gh CLI, GH_TOKEN, GH_REPO, SEC_USER_AGENT. One writer at a time.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

RELEASE = 'historical-sec-data'
STATE_ASSET = 'us-autopilot-state.json'


def gh(*args, check=True):
    return subprocess.run(['gh', *args], check=check, text=True, capture_output=True)


def download(asset, directory):
    result = gh('release', 'download', RELEASE, '--pattern', asset, '--dir', str(directory), check=False)
    if result.returncode != 0:
        if 'not found' in (result.stderr + result.stdout).lower() or 'no assets match' in (result.stderr + result.stdout).lower():
            return False
        raise RuntimeError(f'Unable to restore {asset}: {result.stderr}')
    return (directory / asset).exists()


def upload(path):
    gh('release', 'upload', RELEASE, str(path), '--clobber')


def execute(*args):
    proc = subprocess.run([sys.executable, '-m', 'fundamental_database.cli', *args], text=True)
    if proc.returncode:
        raise RuntimeError(f'Command failed ({proc.returncode}): {args}')


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--batch-size', type=int, default=100)
    p.add_argument('--db', default='data/fundamentals.sqlite')
    p.add_argument('--refresh-only', action='store_true')
    args = p.parse_args(argv)
    if not 1 <= args.batch_size <= 100:
        p.error('batch-size must be 1..100')
    if not os.environ.get('SEC_USER_AGENT') or not os.environ.get('GH_TOKEN'):
        p.error('SEC_USER_AGENT and GH_TOKEN must be configured')
    directory = Path('data')
    directory.mkdir(exist_ok=True)
    gh('release', 'view', RELEASE, check=False) if False else None
    if gh('release', 'view', RELEASE, check=False).returncode:
        gh('release', 'create', RELEASE, '--title', 'Historical SEC Data Shards', '--notes', 'Persistent SEC facts shards and autopilot checkpoints')
    state = {'offset': 0, 'sweeps': 0, 'batch_size': args.batch_size}
    if download(STATE_ASSET, directory):
        state.update(json.loads((directory / STATE_ASSET).read_text()))
    # Every run refreshes company list; company master ordering is stable for the current run.
    # Historical ticker membership can change: offset-based sweeps are repeated indefinitely.
    dbpath = Path(args.db)
    if dbpath.exists():
        dbpath.unlink()
    execute('companies')
    import sqlite3
    db = sqlite3.connect(dbpath)
    total = db.execute('select count(*) from companies').fetchone()[0]
    db.close()
    if total == 0:
        raise RuntimeError('Empty SEC company universe; refusing to advance checkpoint')
    offset = int(state.get('offset', 0))
    if offset >= total:
        offset = 0
        state['sweeps'] = int(state.get('sweeps', 0)) + 1
    if args.refresh_only:
        print(json.dumps({'companies': total, 'next_offset': offset}))
        return
    asset = f'sec-shard-{offset}-{args.batch_size}.sqlite.gz'
    if download(asset, directory):
        with gzip.open(directory / asset, 'rb') as src, dbpath.open('wb') as dst:
            import shutil
            shutil.copyfileobj(src, dst)
    # Re-ingest company master after shard restoration to include updated tickers.
    execute('companies')
    # --continue-on-error logs missing and temporary failures without losing successful companies.
    # A completely failed batch is not persisted and the checkpoint does not advance.
    execute('collect', '--offset', str(offset), '--limit', str(args.batch_size), '--continue-on-error')
    execute('audit')
    execute('rank')
    execute('export')
    # Checkpoint is uploaded only AFTER the durable shard was published successfully.
    db = sqlite3.connect(dbpath)
    facts = db.execute('select count(*) from facts').fetchone()[0]
    companies_with_facts = db.execute('select count(distinct cik) from facts').fetchone()[0]
    db.close()
    with gzip.open(directory / asset, 'wb', compresslevel=6) as dst, dbpath.open('rb') as src:
        import shutil
        shutil.copyfileobj(src, dst)
    upload(directory / asset)
    state.update(offset=offset + args.batch_size, batch_size=args.batch_size,
                 last_success_utc=datetime.now(timezone.utc).isoformat(),
                 last_asset=asset, last_batch_facts=facts, last_batch_companies=companies_with_facts,
                 company_universe=total)
    (directory / STATE_ASSET).write_text(json.dumps(state, indent=2) + '\n')
    upload(directory / STATE_ASSET)
    print(json.dumps({'status': 'persisted', **state}))

if __name__ == '__main__':
    main()
