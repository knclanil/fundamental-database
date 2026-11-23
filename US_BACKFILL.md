# U.S. company-facts backfill

The **US Full-Universe Backfill** workflow covers the first 8,000 CIK-ordered company slots in ten scheduled segments (eight batches of 100 per day). It runs continuously, refreshing each segment every ten days. The existing SEC Incremental Collection workflow remains available for manual targeted batches. A successful scheduled sweep does **not** mean every company has financial facts: some SEC entities have no companyfacts endpoint, and the SEC company master may grow beyond 8,000 entries. Review the master count and extend the segments before claiming full coverage.

## Start the first sweep

Open Actions → US Full-Universe Backfill → Run workflow, choose `sweep_day=0`. Repeat with 1–9 if you want to accelerate the first sweep rather than waiting for the daily schedule. Every segment has eight independently persisted SQLite shards in the `historical-sec-data` GitHub Release.

## Important constraints

- SEC companyfacts is not a complete universe of all historical U.S. public companies; the company ticker file is an active-entity universe, not a delisted-company master.
- Each shard is an independent database, **not** a merged national database. Company counts within shards include the refreshed master; sum only distinct CIKs with facts, not company-master rows.
- GitHub Release assets have limits and are not a guaranteed archival or analytics platform. Monitor storage size and download backups.
- A successful job confirms execution, not 100% financial coverage. Review `collection.log` and `audit.json` for every shard. Missing 404 records are expected; other errors need investigation.
- A single companyfacts request may contain multiple reporting periods and amendments; avoid summing observations as unique statements.
- Run the existing CI workflow before deploying. Set `SEC_USER_AGENT` in repository Actions secrets.
