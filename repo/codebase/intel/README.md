# CHẮN threat-intelligence and lookup service

This service implements the `LOOKUP SERVICE` portion of the CHẮN architecture.
It is deliberately separate from the message classifier:

- phone numbers, bank accounts, and URLs become hash-only blocklist entries;
- message/scenario text belongs to the reviewed training service;
- feed membership is evidence of a report, not proof that an unmatched value
  is safe.

```text
PhishTank / licensed feed       Product user report
            │                          │ hash only
            ▼                          ▼
      scheduled sync             quarantine + review
            │                          │ 2 independent reports
            └──────────────┬───────────┘
                           ▼
                 PostgreSQL hash blocklists
                           │
                    2-hex prefix lookup
                           ▼
                 client performs exact match
```

Raw indicators exist only in connector memory while a licensed feed is parsed.
PostgreSQL stores SHA-256 hashes, source-item hashes, timestamps, confidence,
and audit metadata. It never stores raw URLs, phone numbers, bank account
numbers, report evidence, or reporter identities.

## Source policy

| Source | Default | Rights basis | Use |
|---|---:|---|---|
| PhishTank | enabled | API data permits commercial use | hourly verified URL snapshot |
| OpenPhish Community | disabled | written permission required for non-personal use | URL snapshot after permission |
| PhishVN v2 | enabled for manual import | CC BY 4.0 | Vietnamese URL bootstrap |
| Product reports | enabled | explicit consent | phone/account/URL consensus |

References checked on 2026-07-30:

- PhishTank [developer documentation](https://phishtank.org/developer_info.php)
  says the bulk database updates hourly and supports ETag checks; its
  [terms](https://phishtank.org/terms.php) explicitly allow commercial use of
  API `Data`.
- OpenPhish's [terms](https://www.openphish.com/terms.html) limit the public
  service to personal use unless prior written consent is granted. Setting an
  environment flag is an operational acknowledgement, not a substitute for
  that permission.
- [PhishVN v2](https://data.mendeley.com/datasets/b97hxbxtpd/2) is published
  under CC BY 4.0. Preserve its attribution and upstream-source credits in
  product documentation.

Do not add a crawler for CheckScam or another community site without written
permission and a deletion/correction feed.

The complete research and enable/disable decisions are recorded in
[`SOURCES.md`](SOURCES.md).

## Local setup

From the `repo/` project root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'codebase/intel[dev]'

createdb chan
psql chan < codebase/intel/migrations/001_threat_intel.sql

export CHAN_DATABASE_URL='postgresql://localhost/chan'
export CHAN_INTEL_API_KEYS='report-ingest=first-long-random-secret,intel-reviewer=second-long-random-secret'
export CHAN_INTEL_USER_AGENT='chan-threat-intel/ops@example.org'

.venv/bin/chan-intel-api
```

Build the independent service from inside `repo/`:

```bash
docker build -f codebase/intel/Dockerfile -t chan-intel .
```

## Scheduled synchronization

Register a free PhishTank application key for a higher allowance, then run at
most once per hour:

```bash
export CHAN_PHISHTANK_APP_KEY='secret-from-phishtank'
.venv/bin/chan-intel-sync phishtank --expire-reports
```

The command sends `If-None-Match` and `If-Modified-Since`, validates the
documented CSV schema, rejects oversized or malformed feeds, hashes each URL,
and atomically deactivates entries absent from the latest successful full
snapshot. A failed or partial fetch never deactivates the previous snapshot.

Recommended cron:

```cron
17 * * * * cd /srv/chan/repo && .venv/bin/chan-intel-sync phishtank --expire-reports
```

Do not place secrets directly in a crontab in production; inject them from the
platform secret manager.

OpenPhish remains blocked by two independent controls:

1. `CHAN_OPENPHISH_LICENSE_CONFIRMED=true`;
2. `intel_sources.enabled=true` for `openphish`.

After written permission is recorded:

```sql
UPDATE intel_sources SET enabled = true WHERE name = 'openphish';
```

```bash
export CHAN_OPENPHISH_LICENSE_CONFIRMED=true
.venv/bin/chan-intel-sync openphish
```

## Import PhishVN

Download the CC BY 4.0 snapshot from its DOI page, verify its manifest, inspect
the actual column names, and import only the phishing rows:

```bash
.venv/bin/chan-intel-import phishvn /secure/input/dataset_url.csv \
  --url-column url \
  --label-column label \
  --id-column record_id \
  --first-seen-column first_seen \
  --confirm-cc-by-4
```

The source file is not copied into the product repository or database. Adjust
column arguments to match the published version's datasheet.

## Client hash contract

All clients must implement the same versioned, domain-separated hash contract:

```text
account: SHA256("chan:account:v1:" + normalize(account))
phone:   SHA256("chan:phone:v1:"   + normalize(phone))
url:     SHA256("chan:url:v1:"     + normalize_url(url))
```

For URLs, normalization lowercases scheme/IDNA hostname, removes credentials,
default ports and fragments, and preserves path/query. Put parity vectors for
Kotlin and TypeScript in the shared rules package before shipping clients.

Lookup:

```http
GET /v1/lookup/url?prefix=ab
```

Response:

```json
{
  "prefix": "ab",
  "items": [{
    "suffix": "remaining-62-lowercase-hex-characters",
    "report_count": 1,
    "first_seen": "2026-07-01T00:00:00Z",
    "last_seen": "2026-07-30T00:00:00Z",
    "confidence": "verified"
  }],
  "message": "matched_locally_only"
}
```

The client reconstructs `prefix + suffix` and compares locally. An empty
result must render “Chưa có báo cáo”, never “an toàn”.

Version 1 uses two hex characters because the live PhishTank smoke test on
2026-07-30 produced roughly 67,000 records: about 261 records per bucket on
average. Monitor p05/median/p95 bucket sizes by indicator kind. Increase the
versioned prefix length only after the smallest production corpus still
provides an acceptable anonymity set; Web, Android, API and the shared parity
vectors must change together.

## Community indicator reports

The end-user app never calls this internal route directly. The authenticated
product backend normalizes and hashes the indicator, hashes its own stable
pseudonymous reporter ID, stores evidence separately, and sends only hashes:

```http
POST /internal/v1/intel/reports
X-CHAN-Intel-Key: ...
Content-Type: application/json

{
  "items": [{
    "kind": "phone",
    "indicator_hash": "64-lowercase-hex",
    "reporter_hash": "64-lowercase-hex",
    "evidence_hash": "64-lowercase-hex",
    "consented": true
  }]
}
```

Every report starts in quarantine. A separate key identity reviews it:

```http
POST /internal/v1/intel/reports/REPORT_UUID/review
X-CHAN-Intel-Key: ...
Content-Type: application/json

{"decision":"approve","review_reason":"evidence_verified"}
```

The default activation threshold is two approved reports from independent
pseudonymous reporters. One report or one unreviewed feed must not generate a
claim that an entity is certainly fraudulent.

## Deployment boundaries

- Put public lookup behind the main gateway's TLS and per-IP/device rate limit.
- Keep report, review, and source-status routes on private networking.
- Disable body/query logging; this service also disables Uvicorn access logs.
- Use distinct PostgreSQL roles for migration, sync, lookup, report, and review
  in production.
- Alert on source age, schema failures, sudden count changes, and bucket-size
  privacy regressions.
- Keep the previous successful snapshot active when a source is unavailable.
- Run false-positive appeals and source removals as deactivation, not deletion,
  so audit history remains without retaining a raw indicator.
