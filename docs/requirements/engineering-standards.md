# Engineering Standards

Project-wide conventions. The program-wide rules (IDs, ports, delinquency rule, error envelope, env var names) come from the capstone handbook's `guides/standards.md` and are summarized where we depend on them. Deviations require an ADR in `docs/adr/`.

---

## Git workflow

### Branches

| Branch | Purpose | Rules |
| --- | --- | --- |
| `main` | Released, demo-ready state | Protected. Updated only by PR from `develop` at milestone end. No force push. |
| `develop` | Integration branch | Protected. Updated only by reviewed PR from a feature branch. No force push. |
| `feature/<ticket-or-short-description>` | One story or task | Branched from `develop`, deleted after merge. Example: `feature/M1-project-structure`, `feature/US-ANL-001-portfolio-summary`. |
| `fix/<short-description>` | Bug fix | Same rules as feature branches. |
| `hotfix/<short-description>` | Urgent fix to `main` | Branched from `main`, merged to `main` and back to `develop`. |

### Commit messages

Format: `type(scope): summary` (Conventional Commits). Summary is imperative, lower case, no trailing period, at most 72 characters.

| Type | Use for |
| --- | --- |
| `feat` | New behavior |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Tests only |
| `refactor` | Code change with no behavior change |
| `chore` | Tooling, config, dependencies |
| `ci` | Pipeline changes |
| `db` | Schema, migrations, seed data |

Examples: `docs(requirements): add personas and scope`, `db(migrations): add core schema`, `feat(analytics): add portfolio summary endpoint`.

### Pull request workflow

1. Create `feature/...` from the latest `develop`.
2. Commit in small, focused commits using the message convention.
3. Push and open a PR to `develop` using the [PR template](../../.github/pull_request_template.md).
4. CI must pass (secret scan, lint, tests).
5. At least **one peer review** approval is required. The author does not approve their own PR.
6. Merge (merge commit or squash), then delete the feature branch.
7. At milestone end, open a PR `develop` → `main`, and tag the release `m<N>` (e.g. `m1`).

No direct commits to `develop` or `main`.

---

## Code review checklist

Reviewers confirm each item, or comment on why it does not apply.

**General**
- [ ] Change matches the linked story / milestone task and nothing more.
- [ ] Names, IDs, and formats follow these standards (`BOR-###`, `MTG-####`, `/api/v1/`, ISO-8601 dates).
- [ ] Docs updated (service README, `docs/`, root README links).

**Security** (expanded in M2 by DevSecOps)
- [ ] No secrets, tokens, private keys, or `.env` files with real values.
- [ ] No real PII; any new data is synthetic.
- [ ] Logs do not include passwords, tokens, full SSNs, or account numbers.
- [ ] Input is validated at the API boundary; SQL uses bound parameters only.
- [ ] Errors use the standard envelope and do not leak stack traces.
- [ ] New dependencies are justified, pinned, and free of known critical CVEs.

**Tests**
- [ ] New behavior has tests; changed behavior has updated tests.
- [ ] Tests pass locally and in CI.
- [ ] Tests use seed demo IDs (`MTG-1001`, `MTG-1002`, `BOR-001`) where relevant.

**Database / migrations**
- [ ] Schema changes are in a new, ordered migration file (never edit an applied migration).
- [ ] Migration applies cleanly on an empty database and on the current schema.
- [ ] Foreign keys, NOT NULL, CHECK constraints, and indexes considered.
- [ ] `docs/architecture/data-dictionary.md` and ERD updated if the model changed.
- [ ] Money columns are `NUMERIC(15,2)`; delinquency logic matches the canonical rule.

**DevSecOps (added M2)**
- [ ] CI is green: secret scan, migration job, and (from M3) tests + `pip-audit`.
- [ ] No new gitleaks allowlist entries without a written justification.
- [ ] Dependabot / dependency-review findings of severity critical are fixed or have an issue linked.
- [ ] New config values are added to the relevant `.env.example` with placeholder values only.
- [ ] DB access in code uses the `mortgage_app` role, never `mortgage_owner` or a superuser.

Controls and branch protection settings: [devsecops-baseline.md](../operations/devsecops-baseline.md).

---

## Documentation rules

- **All capstone docs live under `docs/`.** Service-specific run instructions live in each service's `README.md`.
- Markdown, UTF-8, kebab-case file names, no spaces in paths.
- Diagrams in Mermaid, or PNG/SVG under `docs/architecture/images/`.
- ADRs in `docs/adr/` named `NNNN-short-title.md`.
- OpenAPI specs in `docs/api/{service}-openapi.yaml`.

## Data handling (PII rule)

- **No real borrower data in the repository, ever.** All names, emails, phones, and dates of birth are synthetic.
- Emails use the reserved `example.test` domain; phones use the `555` exchange.
- No SSNs or bank account numbers are stored in seed data. If a later milestone needs them, they are fake, clearly patterned (e.g. `900-xx-xxxx`), and masked in logs and API responses.
- Secrets are supplied through environment variables (see each `.env.example`), never committed.

## Shared conventions (summary of program standards)

| Item | Convention |
| --- | --- |
| IDs | `BOR-001`, `MTG-1001`, `LOAN-2001`; UUID v4 for documents, events, correlation IDs |
| Money | `NUMERIC(15,2)` in DB; JSON number with 2 decimals |
| Dates | ISO-8601 (UTC for timestamps) |
| Correlation | `X-Correlation-Id` header, generated if absent, echoed in response, logged as `correlationId` |
| Ports | mortgage-service 8080, servicing-service 8081, analytics 8000, AI assistant 8001, PostgreSQL 5432 |
| Error body | `{ code, message, correlationId, timestamp }` |
| Delinquency | No successful payment within 30 days after `due_date` → `DELINQUENT`. Rate = `DELINQUENT / (ACTIVE + DELINQUENT)` |

---

## Development environment

### Minimum tool versions

| Tool | Minimum | Check |
| --- | --- | --- |
| Git | 2.40 | `git --version` |
| Java (Temurin) | 17 | `java -version` |
| Maven | 3.9 | `mvn -v` |
| Python | 3.11 | `python --version` |
| Docker Desktop | 24 | `docker --version` |
| PostgreSQL (server + `psql`) | 15 | `psql --version` |
| Node.js (optional tooling) | 20 | `node --version` |
| AWS CLI v2 | 2.15 | `aws --version` |

Team members record their check results in [dev-environment-checklist.md](./dev-environment-checklist.md).

### Git access and identity

- Use SSH keys (`ssh-keygen -t ed25519`) or HTTPS with Git Credential Manager. Private keys never go in the repo.
- Set identity per repository if shared machines forbid global config:

  ```powershell
  git config user.name "Your Name"
  git config user.email "you@example.com"
  ```
- Line endings are normalized by `.gitattributes` (LF in the repo, CRLF for `.ps1`).
