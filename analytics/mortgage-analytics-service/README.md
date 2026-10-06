# mortgage-analytics-service

Python service (FastAPI + Pandas) that normalizes borrower, mortgage, and payment data, computes portfolio analytics from the M2 PostgreSQL schema, and uploads loan documents to S3. **Port 8000.** OpenAPI: [`docs/api/analytics-openapi.yaml`](../../docs/api/analytics-openapi.yaml) (or `/docs` while running).

```text
src/
├── api/            main.py (app factory), middleware.py (correlation ID, error envelope),
│                   dependencies.py, routes/ (health, analytics, documents)
├── analytics/      normalization.py, portfolio.py (Pandas metrics)
├── services/       analytics_service.py, document_service.py, aws_clients.py
├── repositories/   mortgage_repository.py (SQLAlchemy, PostgreSQL)
├── models/         schemas.py (Pydantic request/response)
├── utils/          logging_config.py (JSON logs), errors.py
└── config.py       env-based settings
tests/              unit, API, S3 (moto), DB integration
```

## Run locally

Prerequisites: Python 3.11+ (tested on 3.11 in CI and 3.13 locally), and the M2 database set up per [database/README.md](../../database/README.md).

```powershell
cd analytics/mortgage-analytics-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env     # then set POSTGRES_PASSWORD (mortgage_app) in .env
uvicorn src.api.main:app --reload --port 8000
```

On startup the service checks the database and **refuses to start** with a `CRITICAL` log line (`Database unreachable at startup`) if PostgreSQL is unreachable. Set `DB_CHECK_ON_STARTUP=false` to skip this check.

## Configuration

All settings come from environment variables (`.env` is loaded if present). See [`.env.example`](./.env.example).

| Variable | Default | Notes |
| --- | --- | --- |
| `SERVICE_NAME` | `mortgage-analytics-service` | Appears in every log line |
| `LOG_LEVEL` | `INFO` | |
| `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` | `localhost` / `5432` / `mortgage_intel` | |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `mortgage_app` / — | Runtime role (DML only). Password is passed to the driver separately, never placed in the URL or logs |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `5` / `5` | SQLAlchemy pool; `pool_pre_ping` enabled |
| `DB_CONNECT_TIMEOUT_SECONDS` | `5` | |
| `DB_CHECK_ON_STARTUP` | `true` | Fail fast if DB unreachable |
| `AWS_REGION` / `AWS_PROFILE` | `us-east-1` / — | Credentials come from the profile or IAM role, **never** from code or `.env` keys |
| `S3_BUCKET_DOCUMENTS` | `capstone-mortgage-docs-dev` | |
| `AWS_ENDPOINT_URL` | — | Set to `http://localhost:4566` for LocalStack |
| `SNS_TOPIC_MORTGAGE_EVENTS` | — | If set, publishes `DocumentUploaded` (M5 prep) |
| `MAX_UPLOAD_BYTES` | `10485760` | 10 MB |

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness: `{"status":"UP","service":"mortgage-analytics-service"}` |
| GET | `/api/v1/analytics/portfolio-summary` | Counts by status, serviced balance, delinquency rate |
| GET | `/api/v1/analytics/delinquency` | Delinquent mortgages with days past due and severity, worst first |
| GET | `/api/v1/analytics/borrowers/{BOR-###}/risk-summary` | One borrower's exposure and risk level |
| GET | `/api/v1/analytics/borrowers/risk-summary` | Risk export for all borrowers (excludes rows flagged by normalization) |
| GET | `/api/v1/analytics/payment-trends?from=YYYY-MM-DD&to=YYYY-MM-DD` | Monthly posted amount and on-time rate (default: last 365 days) |
| POST | `/api/v1/analytics/normalize` | Validate raw records against the normalization rules (400 on any invalid row) |
| POST | `/api/v1/documents/upload` | Upload to S3 + `document` row. `multipart/form-data` (preferred) or JSON with `contentBase64` |

### Examples (seed data)

```powershell
curl -s -H "X-Correlation-Id: demo-m3-001" http://localhost:8000/api/v1/analytics/portfolio-summary
# {"totalMortgages":12,"activeMortgages":6,"delinquentMortgages":3,"pendingMortgages":1,"closedMortgages":2,
#  "outstandingBalanceTotal":2707750.0,"delinquentBalanceTotal":799250.0,"delinquencyRate":0.3333,"asOf":"..."}

curl -s http://localhost:8000/api/v1/analytics/delinquency
# MTG-1005 (85 DPD, HIGH), MTG-1002 (45 DPD, MODERATE), MTG-1008 (40 DPD, MODERATE)

curl -s http://localhost:8000/api/v1/analytics/borrowers/BOR-001/risk-summary
curl -s "http://localhost:8000/api/v1/analytics/payment-trends?from=2025-01-01&to=2026-12-31"

# Document upload (multipart)
curl -s -X POST http://localhost:8000/api/v1/documents/upload `
  -F mortgageExternalId=MTG-1001 -F documentType=INCOME_VERIFICATION `
  -F "file=@paystub-redacted.pdf;type=application/pdf"
# {"documentId":"...","s3Key":"mortgages/MTG-1001/<uuid>-paystub-redacted.pdf","correlationId":"...",...}
```

Cross-check against SQL:

```sql
SELECT COUNT(*) FROM mortgage WHERE status = 'DELINQUENT';                                   -- 3
SELECT SUM(outstanding_balance) FROM mortgage WHERE status IN ('ACTIVE','DELINQUENT');       -- 2707750.00
```

### Errors

Every error uses the standard envelope, and responses always carry `X-Correlation-Id`:

```json
{"code":"BORROWER_NOT_FOUND","message":"Borrower BOR-999 was not found","correlationId":"…","timestamp":"2026-03-15T14:30:00Z"}
```

| Status | Codes |
| --- | --- |
| 400 | `VALIDATION_ERROR` (bad params, invalid records, disallowed file type, too large); includes `details` |
| 404 | `BORROWER_NOT_FOUND`, `MORTGAGE_NOT_FOUND`, `NOT_FOUND` |
| 500 | `INTERNAL_ERROR` (no stack trace in body), `DATA_INTEGRITY_ERROR`, `DOCUMENT_METADATA_FAILED` |
| 502 | `S3_UPLOAD_FAILED` |

## Metric formulas

| Metric | Formula |
| --- | --- |
| Total mortgages | `count(*)` over all statuses |
| Outstanding balance | `sum(outstanding_balance)` where status in (`ACTIVE`, `DELINQUENT`). This is the serviced portfolio: `PENDING` loans are unfunded and `CLOSED` ones are paid off or declined |
| Delinquent loans | status = `DELINQUENT`, joined to the `delinquency` snapshot, sorted by `days_past_due` desc |
| **Delinquency rate** | `count(DELINQUENT) / count(ACTIVE + DELINQUENT)`, rounded to 4 decimals; 0 if no serviced loans (canonical rule from the engineering standards) |
| Borrower risk summary | Group by `borrower_external_id`: mortgage count (all), serviced balance, delinquent count and balance, max days past due. **Risk level:** `HIGH` if any delinquent loan ≥ 60 DPD, `MEDIUM` if any delinquent loan, else `LOW` |
| Payment trends | `POSTED` payments grouped monthly by `paid_date` (`pd.Grouper(freq="MS")`): `postedAmount = sum(amount)`, `paymentCount`, `onTimeRate = mean(paid_date <= due_date + 15 days)`. `FAILED`/`REVERSED` excluded; months with no postings omitted |

## Normalization rules

Applied to every DataFrame loaded from the database, and to client data sent to `POST /analytics/normalize`. Whitespace is trimmed, IDs and enums are upper-cased, emails lower-cased, money rounded to 2 decimals, and dates parsed. All errors in a batch are collected and reported together.

| Field | Rule | On failure |
| --- | --- | --- |
| `status` (mortgage) | in `PENDING, ACTIVE, DELINQUENT, CLOSED, FORECLOSURE` | error |
| `status` (payment) | in `SCHEDULED, POSTED, FAILED, REVERSED` | error |
| `outstanding_balance` | numeric, ≥ 0 | error |
| `original_amount`, payment `amount` | numeric, > 0 | error |
| `paid_date` | required when status is `POSTED` | error |
| `due_date` | required, valid date | error |
| IDs | `BOR-###`, `MTG-####`, unique within the batch | error |
| `email` | missing → row flagged `email_missing`, **warning** logged with `correlationId`, borrower excluded from the risk export | warning |

Errors in client-supplied records return **400** `VALIDATION_ERROR` with per-row `details`. Errors in data read from our own database return **500** `DATA_INTEGRITY_ERROR`, since that is a server-side problem.

## Logging

One JSON object per line on stdout, with `timestamp`, `level`, `service`, `correlationId`, `logger`, `message`, plus context fields (`mortgageId`, `path`, `status`, `durationMs`, …). The `X-Correlation-Id` request header is reused if it is safe (≤128 chars, `[A-Za-z0-9._:-]`); otherwise a UUID v4 is generated. It is echoed in the response header, included in error bodies, stored as S3 object metadata, and carried in `DocumentUploaded` events. Passwords, tokens, and borrower PII are never logged.

```json
{"timestamp":"2026-10-06T12:18:08.282Z","level":"INFO","service":"mortgage-analytics-service","correlationId":"demo-m3-001","logger":"src.api.access","message":"Request completed","method":"GET","path":"/api/v1/analytics/portfolio-summary","status":200,"durationMs":12.1}
```

## Document upload and AWS

Flow: validate (mortgage ID format, document type, file extension `.pdf/.png/.jpg/.jpeg/.tif/.tiff`, size) → look up the mortgage (404 if unknown) → `PutObject` to `s3://{S3_BUCKET_DOCUMENTS}/mortgages/{MTG-####}/{uuid}-{fileName}` with SSE (AES256) → insert `document` row → optionally publish `DocumentUploaded` to SNS.

- **Resilience:** boto3 `Config(retries={"max_attempts": 3, "mode": "standard"}, connect_timeout=5, read_timeout=10)`. On S3 failure the service returns **502** and writes no row. If the DB insert fails after the upload, the S3 object is deleted (best effort). SNS failures are logged and never fail the upload.
- **File names** are reduced to their base name and unsafe characters are replaced (`../../x.pdf` → `x.pdf`).
- **Credentials:** use an AWS profile (`aws configure --profile capstone-dev`) or an IAM role. Never put keys in `.env` or code.

### AWS sandbox setup

```powershell
aws s3api create-bucket --bucket capstone-mortgage-docs-dev --region us-east-1 --profile capstone-dev
aws s3api put-public-access-block --bucket capstone-mortgage-docs-dev --profile capstone-dev `
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-tagging --bucket capstone-mortgage-docs-dev --profile capstone-dev `
  --tagging 'TagSet=[{Key=Project,Value=mortgage-intelligence},{Key=Environment,Value=dev}]'
```

Minimum IAM for this service: `s3:PutObject` and `s3:DeleteObject` on `arn:aws:s3:::capstone-mortgage-docs-dev/mortgages/*`, plus `sns:Publish` on the lifecycle topic if events are enabled.

### Without AWS (LocalStack)

```powershell
docker run -d -p 4566:4566 localstack/localstack
$env:AWS_ACCESS_KEY_ID="test"; $env:AWS_SECRET_ACCESS_KEY="test"
aws --endpoint-url http://localhost:4566 s3 mb s3://capstone-mortgage-docs-dev
# .env: AWS_ENDPOINT_URL=http://localhost:4566 and leave AWS_PROFILE empty
```

Tests use **moto**, so no AWS or LocalStack is needed to run them.

## Tests

```powershell
pytest -v                                    # unit + API + S3 (moto); no DB needed
pytest --cov=src --cov-report=term-missing   # coverage

# Integration: cross-checks API results against SQL on the seeded database
$env:INTEGRATION_DB="1"; $env:POSTGRES_PASSWORD="<mortgage_app password>"
pytest -m integration -v
```

| File | Covers |
| --- | --- |
| `test_normalization.py` | Bad status, negative balance, POSTED without paid date, bad/duplicate IDs, missing email warning |
| `test_analytics.py` | Metrics on CSV fixtures with a known delinquency rate (0.2), borrower risk, payment trends |
| `test_api.py` | All routes, error envelope, correlation ID echo/generation/sanitization, JSON logs, 500 without stack trace |
| `test_s3.py` | Upload via multipart and JSON (moto), 404/400/502, DB-failure rollback, SNS `DocumentUploaded`, retry config |
| `test_integration_db.py` | API vs SQL aggregates on the seed, real document insert, fail-fast startup |

Current result: **79 passed, 98% line coverage** (`src/analytics` and `src/services` at 98–100%).

Dependency audit: `pip install pip-audit && pip-audit -r requirements.txt`.

Regenerate the OpenAPI spec after API changes: `python -m scripts.export_openapi`.
