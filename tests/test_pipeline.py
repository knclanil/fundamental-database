import tempfile
import unittest
from pathlib import Path
from fundamental_database.storage import connect
from fundamental_database.ingest import ingest_companies, ingest_facts
from fundamental_database.metrics import normalize, snapshot, derived
from fundamental_database.quality import audit

class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name)/'db.sqlite')
        ingest_companies(self.db,[{'cik':123,'name':'Example Inc','ticker':'EX','exchange':'NYSE'}])
    def tearDown(self):
        self.db.close()
        self.temp.cleanup()
    def payload(self):
        def item(val, accn, filed):
            return {'start':'2023-01-01','end':'2023-12-31','val':val,'accn':accn,'filed':filed,'form':'10-K','fy':2023,'fp':'FY'}
        return {'cik':123,'entityName':'Example Inc','facts':{'us-gaap':{
            'Revenues':{'units':{'USD':[item(100,'a','2024-02-01'),item(120,'b','2024-04-01')]}},
            'NetIncomeLoss':{'units':{'USD':[item(20,'a','2024-02-01'),item(25,'b','2024-04-01')]}},
            'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':[item(30,'a','2024-02-01')]}},
            'PaymentsToAcquirePropertyPlantAndEquipment':{'units':{'USD':[item(10,'a','2024-02-01')]}}
        }}}
    def test_point_in_time_and_restated(self):
        self.assertEqual(ingest_facts(self.db,self.payload()),6)
        self.assertEqual(ingest_facts(self.db,self.payload()),6)
        self.assertEqual(audit(self.db)['facts'],6)
        normalize(self.db)
        old=snapshot(self.db,123,'2024-03-01')
        new=snapshot(self.db,123,'2024-05-01')
        key=('revenue','2023-01-01','2023-12-31')
        self.assertEqual(old[key]['value'],100)
        self.assertEqual(new[key]['value'],120)
        self.assertAlmostEqual(derived(new)[('2023-01-01','2023-12-31')]['net_margin'],25/120)
        self.assertEqual(derived(new)[('2023-01-01','2023-12-31')]['free_cash_flow'],20)
    def test_no_future_or_nonperiodic(self):
        payload=self.payload()
        payload['facts']['us-gaap']['Revenues']['units']['USD'].append({'end':'2023-12-31','val':999,'accn':'c','filed':'2099-01-01','form':'10-K'})
        payload['facts']['us-gaap']['Revenues']['units']['USD'].append({'end':'2023-12-31','val':888,'accn':'d','filed':'2024-01-01','form':'8-K'})
        ingest_facts(self.db,payload)
        self.assertEqual(audit(self.db)['facts'],6)

if __name__=='__main__': unittest.main()
