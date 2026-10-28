# Mortgage Intelligence Platform

A Fannie Mae–style **secondary mortgage intelligence platform**, built as a 12-week enterprise capstone. It manages the mortgage lifecycle after origination (borrowers, mortgages, underwriting outcomes, servicing, payments, and delinquency) and adds portfolio analytics, secure document storage, and an AI policy assistant. All data is synthetic.

**Repository:** https://github.com/jeevssx/mortgage-intelligence-platform

## Documentation

### Requirements

| Document | Description |
| --- | --- |
| [Project scope](docs/requirements/project-scope.md) | Problem, objectives, in/out of scope, assumptions, NFRs |
| [Personas](docs/requirements/personas.md) | Six platform personas (plus borrower) and their features |
| [Business flow](docs/requirements/business-flow.md) | Mortgage lifecycle from onboarding to analytics |
| [Stakeholder map](docs/requirements/stakeholder-map.md) | Interest, influence, and touchpoints |
| [Backlog epics](docs/requirements/backlog-epics.md) | The 11 program epics |
| [Team charter](docs/requirements/team-charter.md) | Roles, cadence, definition of done, escalation |
| [Engineering standards](docs/requirements/engineering-standards.md) | Git workflow, commit and PR conventions, review checklist, PII rule, tool versions |
| [Dev environment checklist](docs/requirements/dev-environment-checklist.md) | Tool validation per teammate |
| [User stories](docs/requirements/user-stories.md) | 31 stories with Given/When/Then acceptance criteria |
| [Sprint plans](docs/requirements/sprint-plans.md) | Sprint 1 and Sprint 2 |

### Architecture

| Document | Description |
| --- | --- |
| [System context](docs/architecture/system-context.md) | C4 level 1: users and external systems |
| [Application architecture](docs/architecture/application-architecture.md) | Services, data stores, planned interactions |
| [Deployment architecture](docs/architecture/deployment-architecture.md) | Environments, topology, security zones, trust boundaries |
| [Data flow](docs/architecture/data-flow.md) | Document upload path, TLS termination, PII locations |
| [Trust boundaries](docs/architecture/trust-boundaries.md) | Controls at each boundary |
| [ERD](docs/architecture/erd.md) | Entity relationship diagram and cardinality |
| [Data dictionary](docs/architecture/data-dictionary.md) | Columns, keys, constraints, indexes, roles |
| [Query notes](docs/architecture/query-notes.md) | EXPLAIN output and index rationale |
| [Service ownership matrix](docs/architecture/service-ownership-matrix.md) | Tables/APIs/events owned per service |
| [Event catalog](docs/architecture/event-catalog.md) | Lifecycle events, producers/consumers, schemas |
| [AWS IAM matrix](docs/architecture/aws-iam-matrix.md) | Least-privilege roles for the analytics, API, and Lambda components |

### Architecture decisions

| Document | Description |
| --- | --- |
| [ADR-001](docs/adr/ADR-001-service-data-ownership.md) | Data ownership split between mortgage-service and servicing-service |
| [ADR-002](docs/adr/ADR-002-microservice-decomposition.md) | Microservice decomposition and event backbone |
| [ADR-003](docs/adr/ADR-003-kinesis-vs-sqs-only.md) | Why M8 didn't add a Kinesis stream |

### Security (M6)

| Document | Description |
| --- | --- |
| [Security controls](docs/security/security-controls.md) | Auth, RBAC matrix, data classification, encryption, OWASP controls |
| [Threat model](docs/security/threat-model.md) | STRIDE analysis against the M1 architecture and M5 event backbone |
| [Risk register](docs/security/risk-register.md) | Tracked risks with likelihood/impact/owner |
| [Vulnerability report](docs/security/vulnerability-report.md) | M6 pentest/SCA findings and remediation status |
| [Remediation backlog](docs/security/remediation-backlog.md) | Prioritized fixes, linked to commits |

### Operations

| Document | Description |
| --- | --- |
| [DevSecOps baseline](docs/operations/devsecops-baseline.md) | Branch protection, secret scanning, SAST, SCA, CI checks |
| [Operations runbook](docs/operations/runbook.md) | Secrets rotation and general operational procedures |
| [Messaging runbook](docs/operations/messaging-runbook.md) | SNS/SQS/DLQ operations, LocalStack bootstrap, DLQ drill |
| [Data pipeline runbook](docs/operations/data-pipeline-runbook.md) | PostgreSQL → S3 → curated pipeline, reconciliation, schema drift |

### AI (M7)

| Document | Description |
| --- | --- |
| [Prompt library](docs/ai/prompt-library.md) | Templates for underwriting, delinquency, security, FAQ, and incident prompts |
| [AI governance](docs/ai/governance.md) | Human-in-the-loop rules, PII redaction, hallucination controls |

### Services

| Service | Port | Status | Docs |
| --- | --- | --- | --- |
| mortgage-analytics-service (Python, FastAPI) | 8000 | M3, done | [README](analytics/mortgage-analytics-service/README.md) · [OpenAPI](docs/api/analytics-openapi.yaml) |
| mortgage-service (Java, Spring Boot) | 8080 | M4, done | [README](services/mortgage-service/README.md) |
| servicing-service (Java, Spring Boot) | 8081 | M4, done | [README](services/servicing-service/README.md) |
| mortgage-knowledge-assistant (Python, FastAPI) | 8001 | M7, done | [README](ai/mortgage-knowledge-assistant/README.md) |

### Database

Setup, migrations, seed data, and demo IDs: [database/README.md](database/README.md).

## Milestones

| ID | Milestone | Week | Status |
| --- | --- | --- | --- |
| M1 | Foundation & architecture | 1 | Done |
| M2 | Agile & data foundation | 2 | Done |
| M3 | Python analytics service | 3 | Done |
| M4 | Java / Spring backend | 4–5 | Done |
| M5 | Microservices & events | 6 | Done |
| M6 | Security engineering | 7–8 | Done |
| M7 | AI / RAG assistant | 9 | Done |
| M8 | AWS & data platform | 10 | Done |
| M9 | CI/CD, Terraform, observability | 11 | Not started |
| M10 | Testing & production readiness | 12 | Not started |

## Repository layout

```text
docs/            requirements, architecture, ADRs, security, operations
database/        schema, migrations, seed data, scripts
services/        Java services: mortgage-service, servicing-service
analytics/       Python mortgage-analytics-service
clients/         TypeScript mortgage-api-consumer (M6 secure API consumer demo)
ai/              mortgage-knowledge-assistant
infrastructure/  AWS IAM/Lambda, data pipeline scripts (M8), LocalStack bootstrap, Terraform (M9)
docker/          container definitions
monitoring/      dashboards and alerts
tests/           api, integration, security, e2e suites
```

## Team

| Member | GitHub | Roles |
| --- | --- | --- |
| Jeevan Shahi | [@jeevssx](https://github.com/jeevssx) | Developer, scrum facilitator, doc owner, security liaison |

## Getting started

1. Check your tools against the [minimum versions](docs/requirements/engineering-standards.md#minimum-tool-versions) and add your row to the [dev environment checklist](docs/requirements/dev-environment-checklist.md).
2. Read the [Git workflow](docs/requirements/engineering-standards.md#git-workflow): branch from `develop` as `feature/<ticket>`, use `type(scope): summary` commits, and open a PR to `develop`.
3. Set up PostgreSQL and load the seed data: [database/README.md](database/README.md#setup-powershell).
4. Run the analytics service:

   ```powershell
   cd analytics/mortgage-analytics-service
   python -m venv .venv; .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env   # set POSTGRES_PASSWORD
   uvicorn src.api.main:app --reload --port 8000
   curl http://localhost:8000/health
   ```
5. Run the Java services (Maven 3.9+, Java 17+). Set the **same** `JWT_SECRET` for both (M6
   auth) or accept the insecure dev-only default (logs a warning, local use only):

   ```bash
   cd services/mortgage-service
   JWT_SECRET=<32+ byte random value> POSTGRES_PASSWORD=<your-local-password> mvn spring-boot:run   # port 8080
   cd ../servicing-service
   JWT_SECRET=<same value as above> POSTGRES_PASSWORD=<your-local-password> mvn spring-boot:run   # port 8081
   ```

   Try the secure TypeScript consumer: [clients/mortgage-api-consumer/README.md](clients/mortgage-api-consumer/README.md).
6. Run the AI assistant (Python 3.11+, no API key required — see
   [ai/mortgage-knowledge-assistant/README.md](ai/mortgage-knowledge-assistant/README.md)):

   ```bash
   cd ai/mortgage-knowledge-assistant
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python -m src.ingestion.ingest
   uvicorn src.api.main:app --reload --port 8001
   curl -X POST http://localhost:8001/api/v1/assistant/ask -H "Content-Type: application/json" \
     -d '{"question": "What happens when a payment is 30 days late?"}'
   ```
7. Or run the full stack containerized, including LocalStack for SNS/SQS (M5) and S3/DynamoDB/
   Lambda (M8 — the `localstack-init` container also deploys and wires the document-processor
   Lambda automatically):

   ```bash
   docker compose up --build -d
   docker compose ps                       # all six services "healthy"
   curl http://localhost:8080/actuator/health
   curl http://localhost:8081/actuator/health
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   ```

   See [docs/operations/messaging-runbook.md](docs/operations/messaging-runbook.md) to publish a
   test event or force a DLQ delivery, and
   [docs/operations/data-pipeline-runbook.md](docs/operations/data-pipeline-runbook.md) to run
   the PostgreSQL → S3 → curated pipeline.
8. Never commit secrets or real borrower data. See the [PII rule](docs/requirements/engineering-standards.md#data-handling-pii-rule).
