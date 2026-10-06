# System Context (C4 Level 1)

The Mortgage Intelligence Platform as a single system, the people who use it, and the external systems it depends on. Internal components are in [application-architecture.md](./application-architecture.md).

```mermaid
flowchart TB
    subgraph People
        UW([Underwriter])
        SA([Servicing Agent])
        RA([Risk Analyst])
        AD([Administrator])
        SEC([Security Analyst])
        SUP([Support Engineer])
    end

    MIP[["Mortgage Intelligence Platform<br/><i>Manages borrowers, mortgages, payments,<br/>servicing, delinquency, analytics, documents,<br/>and policy Q&A</i>"]]

    IDP[(Identity Provider<br/><i>placeholder; JWT issuer in M6</i>)]
    DOCS[(Document Storage<br/><i>AWS S3</i>)]
    MSG[(Messaging<br/><i>AWS SNS/SQS, M5</i>)]
    OBS[(Observability<br/><i>logs, metrics, alerts, M9</i>)]
    LLM[(LLM / Embedding Provider<br/><i>AI assistant, M7</i>)]

    UW -->|review loans, approve/decline, ask policy questions| MIP
    SA -->|view servicing history, post payments| MIP
    RA -->|portfolio and delinquency analytics| MIP
    AD -->|manage users, roles, configuration| MIP
    SEC -->|review access, audit logs| MIP
    SUP -->|troubleshoot with correlation IDs| MIP

    MIP -->|authenticate users, validate tokens| IDP
    MIP -->|store and retrieve loan documents| DOCS
    MIP -->|publish and consume lifecycle events| MSG
    MIP -->|ship logs and metrics| OBS
    MIP -->|embeddings and grounded completions| LLM
```

## Actors

| Actor | Interaction |
| --- | --- |
| Underwriter | Reviews loan terms and records underwriting decisions; asks the AI assistant policy questions. |
| Servicing Agent | Views mortgage status, payment history, servicing history; posts payments. |
| Risk Analyst | Reads portfolio summary, delinquency, borrower risk, and payment trends. |
| Administrator | Manages user accounts and roles; configures environments. |
| Security Analyst | Reviews access and audit logs; supports incidents. |
| Support Engineer | Uses health endpoints, logs, and dashboards to resolve failures. |

See [personas.md](../requirements/personas.md) for goals and pain points.

## External systems

| System | Purpose | Status |
| --- | --- | --- |
| Identity provider | Issues and validates user identity/tokens | Placeholder; service-issued JWT in M6 |
| Document storage (S3) | Holds document binaries; platform keeps metadata | M3 (upload), M8 (data platform) |
| Messaging (SNS/SQS) | Lifecycle events between services | M5 |
| Observability | Centralized logs, metrics, alerting | M9 |
| LLM / embeddings provider | Powers the AI assistant | M7 |

No real Fannie Mae, credit bureau, or payment network integrations are in scope (see [project-scope.md](../requirements/project-scope.md#out-of-scope)).
