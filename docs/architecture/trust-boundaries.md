# Trust Boundaries

Boundaries are defined in [deployment-architecture.md](./deployment-architecture.md#trust-boundaries). This page lists the controls at each, grouped by control type. Threats per boundary are analyzed with STRIDE in M6.

| Boundary | Authentication / authorization | Encryption in transit | Network segmentation | Logging / audit |
| --- | --- | --- | --- | --- |
| **TB1** Internet → DMZ | None at edge (public entry); WAF blocks known-bad patterns; rate limiting | TLS 1.2+ with public certificate; HTTP redirected or refused | Only 443 open on load balancer; public subnets contain no app or data hosts | LB and WAF access logs |
| **TB2** DMZ → Application | JWT validated by each service; role checks per endpoint (`UNDERWRITER`, `SERVICING_AGENT`, `RISK_ANALYST`, `ADMIN`, `SUPPORT`) from M6 | TLS re-encryption LB → service | Private subnets; security group admits traffic only from LB security group on service ports | `correlationId` generated or propagated; request logs (no tokens) |
| **TB3** Application → Data | Per-environment DB role `mortgage_app` with DML only (no DDL); migrations run by a separate owner role | TLS to PostgreSQL | Isolated subnets, no internet route; DB security group admits app tier only on 5432 | PostgreSQL connection and error logs; servicing changes recorded in `servicing_history` |
| **TB4** Application → AWS services | IAM role per service with least privilege (e.g. analytics: `s3:PutObject` on `mortgages/*` only) | HTTPS; bucket policy `aws:SecureTransport` deny | VPC endpoints; no NAT path required for S3/SNS/SQS | CloudTrail data events for the documents bucket |
| **Developer → Repository** | GitHub account + 2FA; protected branches; required review | HTTPS / SSH | — | PR history; secret scanning in CI |

## Rules that apply at every boundary

- Never trust input from the zone outside the boundary: validate at the receiving side.
- Never pass credentials in URLs or logs.
- Secrets come from environment variables locally and Secrets Manager in AWS; nothing secret is in Git.
