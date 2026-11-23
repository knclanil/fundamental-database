import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fundamental_database.sec import SecClient, SecNotFound
from fundamental_database.storage import connect
from fundamental_database.cli import main


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code = status
        self.headers = {}
        self.payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return next(self.responses)


class ResilienceTests(unittest.TestCase):
    def test_missing_cik_is_distinct(self):
        client = SecClient('FundamentalDatabase test@example.com', delay=0, session=FakeSession([FakeResponse(404)]))
        with self.assertRaises(SecNotFound):
            client.facts(18748)

    def test_retry_transient_http_error(self):
        session = FakeSession([FakeResponse(503), FakeResponse(200, {'ok': True})])
        client = SecClient('FundamentalDatabase test@example.com', delay=0, session=session)
        with patch('fundamental_database.sec.time.sleep'):
            self.assertEqual(client.get('https://example.com'), {'ok': True})
        self.assertEqual(session.calls, 2)

    def test_collection_skips_missing_cik(self):
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / 'test.sqlite')
            db = connect(path)
            db.execute("INSERT INTO companies(cik,name) VALUES(18748,'Missing')")
            db.commit()
            db.close()
            with patch('fundamental_database.cli.SecClient') as cls:
                cls.return_value.facts.side_effect = SecNotFound('not found')
                main(['--db', path, 'collect', '--limit', '1', '--continue-on-error'])

    def test_export_parquet(self):
        try:
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest('Install analytics extra for Parquet verification')
        from fundamental_database.export import export_parquet
        with tempfile.TemporaryDirectory() as temp:
            db = connect(str(Path(temp) / 'db.sqlite'))
            db.execute("INSERT INTO companies(cik,name) VALUES(123,'Example')")
            db.commit()
            files = export_parquet(db, Path(temp) / 'parquet')
            self.assertTrue(files)
            self.assertEqual(pq.read_table(Path(temp) / 'parquet' / 'companies.parquet').num_rows, 1)
            db.close()


if __name__ == '__main__':
    unittest.main()
