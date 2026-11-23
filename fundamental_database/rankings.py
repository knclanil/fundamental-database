"""Transparent, coverage-aware, cross-sectional fundamental rankings.

Only same-period annual results are compared. No missing values are imputed.
"""
from collections import defaultdict
from datetime import date
from .metrics import snapshot, derived

DIRECTION = {'net_margin': 1, 'operating_margin': 1, 'gross_margin': 1,
             'roe_ending_equity': 1, 'free_cash_flow': 1,
             'liabilities_to_assets': -1}

def rank_companies(db, as_of=None, period_end=None, minimum_metrics=2):
    as_of = as_of or date.today().isoformat()
    candidates = []
    companies = db.execute('SELECT cik,name,ticker,exchange FROM companies ORDER BY cik').fetchall()
    for cik, name, ticker, exchange in companies:
        rows = snapshot(db, cik, as_of, period_end)
        periods = derived(rows)
        # Annual flows: start/end duration between 330 and 380 days; balance-sheet
        # metrics have empty start and are joined by their matching period end.
        annual = []
        for (start, end), vals in periods.items():
            if not start:
                continue
            try:
                duration = (date.fromisoformat(end) - date.fromisoformat(start)).days
            except ValueError:
                continue
            if 330 <= duration <= 380:
                annual.append((end, start, vals))
        if not annual:
            continue
        end, start, values = max(annual)
        balance = periods.get(('', end), {})
        values = {**balance, **values}
        if len([k for k in DIRECTION if k in values]) < minimum_metrics:
            continue
        candidates.append(dict(cik=cik, name=name, ticker=ticker, exchange=exchange,
                               period_start=start, period_end=end, metrics=values))
    # Compare each company to peers from the SAME period end, not different years.
    groups = defaultdict(list)
    for item in candidates:
        groups[item['period_end']].append(item)
    result = []
    for end, peers in groups.items():
        for metric, direction in DIRECTION.items():
            eligible = sorted([p for p in peers if metric in p['metrics']],
                              key=lambda p: (direction * p['metrics'][metric], p['cik']))
            n = len(eligible)
            for i, p in enumerate(eligible):
                p.setdefault('_scores', []).append((i / (n - 1) if n > 1 else 0.5) * 100)
        for p in peers:
            scores = p.pop('_scores', [])
            p['score'] = round(sum(scores) / len(scores), 3) if scores else None
            p['metric_count'] = len(scores)
            p['peer_count'] = len(peers)
            result.append(p)
    result.sort(key=lambda p: (p['period_end'], p['score'] if p['score'] is not None else -1, -p['cik']), reverse=True)
    for end in groups:
        ranked = [p for p in result if p['period_end'] == end]
        for i, p in enumerate(ranked, 1):
            p['rank'] = i
    return result
