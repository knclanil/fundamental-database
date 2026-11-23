"""Standard metric mapping. Alternate tags are NOT summed; source tag is retained."""
MAPPING = {
 'revenue': ['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','RevenueFromContractWithCustomerIncludingAssessedTax'],
 'net_income': ['NetIncomeLoss','ProfitLoss'],
 'operating_income': ['OperatingIncomeLoss'],
 'gross_profit': ['GrossProfit'],
 'assets': ['Assets'], 'liabilities': ['Liabilities'],
 'equity': ['StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
 'cash': ['CashAndCashEquivalentsAtCarryingValue'],
 'operating_cash_flow': ['NetCashProvidedByUsedInOperatingActivities'],
 'capital_expenditure': ['PaymentsToAcquirePropertyPlantAndEquipment'],
 'shares_outstanding': ['CommonStockSharesOutstanding'],
 'eps_diluted': ['EarningsPerShareDiluted'],
}
UNITS = {'shares_outstanding':'shares','eps_diluted':'USD/shares'}

def normalize(db, cik=None):
    """Map facts to metrics while preserving each distinct filing and source tag."""
    inserted = 0
    for metric, tags in MAPPING.items():
        unit = UNITS.get(metric,'USD')
        for tag in tags:
            sql = '''INSERT OR IGNORE INTO metrics
                (cik,metric,period_start,period_end,accession,filed,value,unit,taxonomy,source_tag)
                SELECT cik, ?, start, end, accession, filed, val, unit, taxonomy, tag
                FROM facts WHERE taxonomy='us-gaap' AND tag=? AND unit=?'''
            args = [metric,tag,unit]
            if cik is not None:
                sql += ' AND cik=?'
                args.append(int(cik))
            cur = db.execute(sql,args)
            inserted += max(cur.rowcount,0)
    db.commit()
    return inserted

def snapshot(db, cik, as_of, period_end=None):
    """Latest filed source for each metric/period available as of cutoff.

    Avoid conflating annual and quarterly durations: period_start is part of key.
    Prefer source-tag order, then most recently filed restatement.
    """
    where = 'cik=? AND filed<=?'
    args = [int(cik),as_of]
    if period_end:
        where += ' AND period_end=?'
        args.append(period_end)
    rows = db.execute(f'''SELECT metric,period_start,period_end,value,unit,source_tag,filed,accession
        FROM metrics WHERE {where} ORDER BY metric,period_end,period_start,filed DESC''',args).fetchall()
    output = {}
    for metric,start,end,value,unit,tag,filed,accession in rows:
        key = (metric,start,end)
        if key not in output or (MAPPING[metric].index(tag),-int(filed.replace('-',''))) < (
                MAPPING[metric].index(output[key]['source_tag']),-int(output[key]['filed'].replace('-',''))):
            output[key] = dict(value=value,unit=unit,source_tag=tag,filed=filed,accession=accession)
    return output

def derived(snapshot_rows):
    """Derive safe ratios from matching period keys only; no price history assumed."""
    grouped = {}
    for (metric,start,end), info in snapshot_rows.items():
        grouped.setdefault((start,end),{})[metric] = info['value']
    result = {}
    for period, v in grouped.items():
        out = {}
        if v.get('revenue') not in (None,0):
            for key,source in [('net_margin','net_income'),('operating_margin','operating_income'),('gross_margin','gross_profit')]:
                if source in v: out[key] = v[source]/v['revenue']
        if v.get('equity') not in (None,0) and 'net_income' in v and period[0]:
            # Simple period-end ROE, not average equity; labeled explicitly.
            out['roe_ending_equity'] = v['net_income']/v['equity']
        if 'operating_cash_flow' in v and 'capital_expenditure' in v:
            out['free_cash_flow'] = v['operating_cash_flow']-v['capital_expenditure']
        if v.get('assets') not in (None,0) and 'liabilities' in v:
            out['liabilities_to_assets'] = v['liabilities']/v['assets']
        result[period] = out
    return result
