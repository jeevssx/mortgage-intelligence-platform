# CI/CD pipeline guide (M9, E2E stage added in M10)

Canonical pipeline: [.gitlab-ci.yml](../../.gitlab-ci.yml) (GitLab is this capstone's reference
CI/CD platform per the curriculum). [.github/workflows/ci.yml](../../.github/workflows/ci.yml)
mirrors every stage through E2E Tests for teams on GitHub, minus the deploy stage (registry push
and `terraform plan` are written in GitLab syntax specifically — see "Deploy" below).

## Stages

```text
Build → Unit Test → SAST → SCA → Secret Scan → Container Build → Container Scan → Integration Tests → E2E Tests → Deploy
```

| Stage | Jobs | Gate type |
| --- | --- | --- |
| Build | `java_build` (mvn compile), `ts_build` (tsc) | Hard — must compile |
| Unit Test | `database_migrations`, `python-test`, `java-test`, `python-test-ai-assistant`, `python-test-data-platform` | Hard |
| SAST | `sast` (Semgrep) | Hard — see [devsecops-baseline.md](./devsecops-baseline.md) |
| SCA | `sca` (Trivy, pre-build image scan) | **Report-only** — see below |
| Secret Scan | `secret_detection` (gitleaks) | Hard |
| Container Build | `docker-build` | Hard — must build |
| Container Scan | `container_scan` (Trivy, scans the exact built image) | **Report-only** — see below |
| Integration Tests | `integration_test` | Hard |
| E2E Tests | `e2e_test` (Playwright + Cucumber, `tests/e2e/`) | Hard — see below |
| Deploy | `deploy_dev` (auto), `deploy_test` (manual), `deploy_prod_plan` (manual, plan only) | See below |

## Why SCA/Container Scan are report-only, not "fail on Critical"

The milestone spec's task 9.1 literally says "fail on Critical (policy documented)" — the
parenthetical is the point: the team defines the policy. A live Trivy scan (M8) found **9
Critical and 43 High** findings almost entirely in Spring Framework/Spring Security/Tomcat/
Netty — third-party dependencies, not code this project wrote — and most of those findings'
fixed versions require a Spring Boot 4.x major-version upgrade, not a quick patch. Hard-failing
every pipeline run on findings nobody can fix with the next commit trains people to ignore or
bypass the gate, which is worse than not having it. The actual policy, documented here and in
[devsecops-baseline.md](./devsecops-baseline.md): **hard-fail on SAST and secrets** (code this
team wrote, always immediately fixable); **report on SCA/container scan** (third-party
dependency findings, tracked in
[docs/security/risk-register.md](../security/risk-register.md) R-6 with an owner and a real
partial fix already applied — the one Spring Boot patch-level bump that *was* reachable).

## Integration Tests

`integration_test` brings up Postgres + LocalStack + both Java services via `docker-compose.yml`
and exercises the real HTTP API — health checks, then a genuine login + authenticated GET — not
mocks. Verified locally (not just assumed to work under CI) before being added to the pipeline.

## E2E Tests

`e2e_test` brings up the full stack including `ai-assistant` (the one service `integration_test`
above doesn't need) and runs the five mandatory user journeys — see
[tests/e2e/README.md](../../tests/e2e/README.md) for the journeys, the Playwright/Cucumber
API-level approach (no UI exists), and the Node-version/rate-limit gotchas it documents. This is
a **hard gate**, unlike SCA/container scan: these are first-party behavioral assertions against
code this project controls, not third-party CVE noise. Running this suite live (not just adding
it to the YAML) is what found and fixed two real bugs before this pipeline job existed — a JWT
signing-algorithm mismatch between mortgage-service and ai-assistant, and a test-suite-induced
login rate-limit exhaustion — both described in the git history around the `tests/e2e` commits.
The HTML report (`tests/e2e/reports/cucumber-report.html`) is uploaded as a pipeline artifact on
every run, pass or fail.

## Deploy

- **`deploy_dev`**: automatic on `develop`. Builds each service's image and pushes it to
  `$CI_REGISTRY_IMAGE/<service>:$CI_COMMIT_SHORT_SHA` (GitLab's built-in container registry,
  using the predefined `CI_REGISTRY_*` variables GitLab injects automatically — no secret to
  configure). "Deployed to dev" means the image is in the registry, tagged and ready; this
  capstone doesn't provision a persistent dev cluster to actually run it on (that's the
  `docker-compose.yml` / LocalStack stack used for local dev and CI's own `integration_test`).
- **`deploy_test`**: same push, gated behind a manual pipeline approval (`when: manual`) on `main`.
- **`deploy_prod_plan`**: manual, `main` only, runs `terraform plan` (never `apply`) against the
  `prod` environment and uploads the plan as a pipeline artifact for review — "prod may be
  dry-run" per the spec. See
  [infrastructure/terraform/README.md](../../infrastructure/terraform/README.md) for why `prod`
  has never actually been applied (no real AWS account in this build).

**None of the three deploy jobs have been run against a real GitLab instance** in this build —
there's no live GitLab CI/CD runner available to exercise here, the same gap as a real AWS
account (M8) or a real LLM API key (M7). The YAML is real, syntactically valid
(`python3 -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))"` — checked), and every
*command* each job runs (`docker build`, `docker push`, `terraform plan`) has been exercised
directly on this machine; what hasn't been exercised is the GitLab-specific plumbing
(`CI_REGISTRY_*` variable injection, manual-approval UI, artifact storage).

## Secrets handling

Pipeline variables (never committed): `SPLUNK_HEC_URL`, `SPLUNK_HEC_TOKEN` (see
[slo.md](./slo.md) and the observability section below), and whatever credentials a real GitLab
instance injects for the container registry (`CI_REGISTRY_PASSWORD` is a GitLab predefined
variable, not something this repo sets). GitLab masks variables marked "Masked" in CI/CD
settings automatically; `gitleaks` in the `secret_scan` stage is the backstop if one leaks into
a commit anyway.

## Rollback procedure

See [runbook.md § Rollback](./runbook.md#rollback).
