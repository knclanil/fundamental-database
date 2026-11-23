import argparse
import json
import os
import sys
from datetime import date
from .storage import connect
from .sec import SecClient, SecNotFound
from .ingest import ingest_companies, ingest_facts
from .metrics import normalize, snapshot, derived
from .quality import audit

def main(argv=None):
    p = argparse.ArgumentParser(description='SEC historical fundamental database')
    p.add_argument('--db',default='data/fundamentals.sqlite')
    sub = p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('companies')
    collect = sub.add_parser('collect')
    collect.add_argument('--cik',type=int,action='append')
    collect.add_argument('--limit',type=int,default=25)
    collect.add_argument('--offset',type=int,default=0)
    collect.add_argument('--continue-on-error',action='store_true')
    sub.add_parser('normalize')
    sub.add_parser('audit')
    exp = sub.add_parser('export')
    exp.add_argument('--out',default='data/parquet')
    snap = sub.add_parser('snapshot')
    snap.add_argument('--cik',type=int,required=True)
    snap.add_argument('--as-of',default=date.today().isoformat())
    snap.add_argument('--period-end')
    args = p.parse_args(argv)
    db = connect(args.db)
    if args.cmd == 'companies':
        print(json.dumps({'companies':ingest_companies(db,SecClient().companies())}))
    elif args.cmd == 'collect':
        client = SecClient()
        ciks = args.cik if args.cik else [x[0] for x in db.execute('SELECT cik FROM companies ORDER BY cik LIMIT ? OFFSET ?', (args.limit,args.offset))]
        ok = 0
        failed = []
        missing = []
        for cik in ciks:
            try:
                n = ingest_facts(db,client.facts(cik))
                normalize(db,cik)
                ok += 1
                print(json.dumps({'cik':cik,'observations_processed':n}))
            except SecNotFound as exc:
                missing.append({'cik': cik, 'reason': str(exc)})
                print(json.dumps(missing[-1]), file=sys.stderr)
                continue
            except Exception as exc:
                failed.append({'cik':cik,'error':str(exc)})
                print(json.dumps(failed[-1]),file=sys.stderr)
                if not args.continue_on_error:
                    raise
        print(json.dumps({'succeeded':ok,'missing':missing,'failed':failed}))
        if failed and (not args.continue_on_error or ok == 0): sys.exit(1)
    elif args.cmd == 'normalize':
        print(json.dumps({'metrics_inserted':normalize(db)}))
    elif args.cmd == 'audit':
        print(json.dumps(audit(db),indent=2))
    elif args.cmd == 'export':
        from .export import export_parquet
        print(json.dumps({'files':[str(x) for x in export_parquet(db,args.out)]}))
    elif args.cmd == 'snapshot':
        rows = snapshot(db,args.cik,args.as_of,args.period_end)
        print(json.dumps({'facts':[dict(metric=k[0],start=k[1],end=k[2],**v) for k,v in rows.items()],
                          'derived':[dict(start=k[0],end=k[1],**v) for k,v in derived(rows).items()]},indent=2))
    db.close()

if __name__ == '__main__': main()
