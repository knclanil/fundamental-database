"""SEC EDGAR JSON client. Set SEC_USER_AGENT to a descriptive contact string."""
import os
import time
import requests

class SecNotFound(RuntimeError):
    """SEC has no company facts JSON for this CIK."""


BASE = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'
TICKERS = 'https://www.sec.gov/files/company_tickers_exchange.json'

class SecClient:
    def __init__(self, user_agent=None, delay=0.2, session=None):
        self.user_agent = user_agent or os.getenv('SEC_USER_AGENT', '')
        if not self.user_agent or '@' not in self.user_agent:
            raise ValueError('Set SEC_USER_AGENT to organization/name and contact email')
        self.delay = delay
        self.session = session or requests.Session()
        self.last_request = 0.0

    def get(self, url):
        for attempt in range(5):
            elapsed = time.monotonic() - self.last_request
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            try:
                response = self.session.get(url, headers={
                    'User-Agent': self.user_agent, 'Accept-Encoding': 'gzip, deflate',
                    'Accept': 'application/json'}, timeout=45)
                self.last_request = time.monotonic()
                if response.status_code == 404:
                    raise SecNotFound(f'SEC resource not found: {url}')
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 4:
                    retry_after = response.headers.get('Retry-After', '')
                    try:
                        wait = min(60, max(1, float(retry_after)))
                    except ValueError:
                        wait = min(30, 2 ** attempt)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except SecNotFound:
                raise
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt < 4:
                    time.sleep(min(30, 2 ** attempt))
                    continue
                raise RuntimeError(f'SEC request failed ({url}): {exc}') from exc
            except (requests.RequestException, ValueError) as exc:
                raise RuntimeError(f'SEC request failed ({url}): {exc}') from exc
        raise RuntimeError(f'SEC request exhausted retries ({url})')

    def companies(self):
        payload = self.get(TICKERS)
        keys = payload['fields']
        return [dict(zip(keys, row)) for row in payload['data']]

    def facts(self, cik):
        return self.get(BASE.format(cik=int(cik)))
