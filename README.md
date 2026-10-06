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

### Operations

| Document | Description |
| --- | --- |
| [DevSecOps baseline](docs/operations/devsecops-baseline.md) | Branch protection, secret scanning, SCA, CI checks |

### Database

Setup, migrations, seed data, and demo IDs: [database/README.md](database/README.md).

## Milestones

| ID | Milestone | Week | Status |
| --- | --- | --- | --- |
| M1 | Foundation & architecture | 1 | Done |
| M2 | Agile & data foundation | 2 | Done |
| M3 | Python analytics service | 3 | Not started |
| M4 | Java / Spring backend | 4–5 | Not started |
| M5 | Microservices & events | 6 | Not started |
| M6 | Security engineering | 7–8 | Not started |
| M7 | AI / RAG assistant | 9 | Not started |
| M8 | AWS & data platform | 10 | Not started |
| M9 | CI/CD, Terraform, observability | 11 | Not started |
| M10 | Testing & production readiness | 12 | Not started |

## Repository layout

```text
docs/            requirements, architecture, ADRs, security, operations
database/        schema, migrations, seed data, scripts
services/        Java services: mortgage-service, servicing-service
analytics/       Python mortgage-analytics-service
ai/              mortgage-knowledge-assistant
infrastructure/  Terraform
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
3. Never commit secrets or real borrower data. See the [PII rule](docs/requirements/engineering-standards.md#data-handling-pii-rule).
