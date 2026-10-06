# Data Flow — Mortgage Document Upload

High-level trace of one path: **API client → API → database → cloud storage**, for an onboarding agent uploading an income verification document for `MTG-1001`. Implemented in M3 (`POST /api/v1/documents/upload`); hardened in M6 and M8.

```mermaid
sequenceDiagram
    autonumber
    participant C as API client (Zone 0)
    participant LB as Load balancer (Zone 1)
    participant AS as mortgage-analytics-service (Zone 2)
    participant PG as PostgreSQL (Zone 3)
    participant S3 as S3 documents bucket
    participant SNS as SNS topic (M5)

    C->>LB: HTTPS POST /api/v1/documents/upload<br/>multipart file + metadata, X-Correlation-Id
    Note over LB: TLS terminates (public cert)
    LB->>AS: HTTPS (re-encrypted) forward
    AS->>AS: Validate JWT/role (M6), validate metadata,<br/>bind correlationId to logs
    AS->>PG: SELECT mortgage by mortgage_external_id (TLS)
    PG-->>AS: mortgage.id
    AS->>S3: PutObject mortgages/MTG-1001/{uuid}-{fileName}<br/>(HTTPS, SSE-KMS)
    S3-->>AS: 200 OK
    AS->>PG: INSERT document (mortgage_id, document_type, s3_key, file_name)
    PG-->>AS: document.id
    AS--)SNS: DocumentUploaded event (optional, M5)
    AS-->>C: 201 {documentId, s3Key, correlationId}
```

## Where TLS terminates

| Hop | Transport |
| --- | --- |
| Client → load balancer | HTTPS; **public TLS terminates at the load balancer** |
| Load balancer → service | HTTPS re-encrypted with internal certificate |
| Service → PostgreSQL | TLS (`sslmode=require` in non-local environments) |
| Service → S3 / SNS | HTTPS through VPC endpoints; bucket policy denies non-TLS requests |

## Where PII is stored

| Data | Location | Protection |
| --- | --- | --- |
| Borrower name, email, phone, date of birth | PostgreSQL `borrower` table (Zone 3) | Encrypted at rest (RDS), least-privilege DB role, never logged |
| Document binaries (paystubs, IDs) | S3 bucket (private) | SSE-KMS, no public access, IAM-scoped access, keys include only business IDs |
| Document metadata (type, file name, S3 key) | PostgreSQL `document` table | Same as above; file names must not contain PII (e.g. `paystub-redacted.pdf`) |
| Logs | CloudWatch | Contain `correlationId` and business IDs only; no names, emails, tokens, or document contents |

## Failure handling

- S3 failure → service returns **502** with the standard error envelope; no `document` row is written.
- DB insert failure after S3 success → object is deleted (best effort) and the error is logged with the correlation ID.
- Unknown `mortgageExternalId` → **404** `MORTGAGE_NOT_FOUND` before anything is written to S3.
