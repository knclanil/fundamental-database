import tempfile
import unittest
from pathlib import Path
from fundamental_database.storage import connect
from fundamental_database.rankings import rank_companies

class RankingTests(unittest.TestCase):
    def test_annual_period_and_missing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = connect(Path(tmp) / 'test.sqlite')
            for cik, income in [(1, 20), (2, 10)]:
                db.execute('INSERT INTO companies(cik,name,ticker) VALUES(?,?,?)', (cik, str(cik), str(cik)))
                for metric, value in [('revenue',100),('net_income',income),('operating_income',income)]:
                    db.execute('''INSERT INTO metrics(cik,metric,period_start,period_end,accession,filed,value,unit,taxonomy,source_tag)
                        VALUES(?,?,?,?,?,?,?,?,?,?)''', (cik,metric,'2024-01-01','2024-12-31',str(cik),'2025-02-01',value,'USD','us-gaap',
                        {'revenue':'Revenues','net_income':'NetIncomeLoss','operating_income':'OperatingIncomeLoss'}[metric]))
            db.commit()
            ranks = rank_companies(db, '2025-12-31')
            self.assertEqual(len(ranks), 2)
            self.assertEqual(ranks[0]['cik'], 1)
            self.assertEqual([r['rank'] for r in ranks], [1,2])
            self.assertEqual(rank_companies(db,'2025-01-01'), [])
            db.close()

if __name__ == '__main__': unittest.main()
