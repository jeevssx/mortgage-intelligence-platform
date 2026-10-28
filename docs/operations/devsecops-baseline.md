# DevSecOps Baseline (Milestone 2, extended M6)

Security controls on the engineering workflow. SAST, SCA/image scanning, and secret scanning
landed in M6; deploy gates arrive in M9.

## Controls

| Control | Implementation | Where |
| --- | --- | --- |
| Protected branches | `main` and `develop`: PR required, 1 approving review, status checks must pass, no force push, no deletion | GitHub → Settings → Branches (config below) |
| Secret scanning (CI) | gitleaks v8 scans **full git history** on every PR and push; job fails on any finding | `.github/workflows/ci.yml` → `secret-scan`; `.gitlab-ci.yml` → `secret_detection` |
| Secret scanning (platform) | GitHub secret scanning + push protection | GitHub → Settings → Code security |
| SAST (M6) | Semgrep `--config=auto`, fails the build on any `ERROR`-severity finding, against `services/`, `analytics/`, `clients/` | `ci.yml` → `sast`; `.gitlab-ci.yml` → `sast` |
| SCA — Python (M3) | `pip-audit` in the analytics test job | `ci.yml` → `analytics-service` |
| SCA — Java/images (M6) | Trivy image scan (builds each Dockerfile, scans the resulting image) for `mortgage-service`, `servicing-service`, `analytics-service`; **report-only**, see policy below | `ci.yml` → `sca-images`; `.gitlab-ci.yml` → `sca` |
| Dependency PRs | Dependabot weekly PRs for pip, Maven, and GitHub Actions; `dependency-review-action` blocks PRs adding **critical** CVEs on a dependency *version bump* | `.github/dependabot.yml`, `ci.yml` |
| Migration validation | Fresh PostgreSQL 16 in CI: roles → migrations → seed → idempotent re-apply → sample queries as least-privilege role → seed invariants (`MTG-1002` = 45 DPD, etc.) | `ci.yml` → `database` |
| Least-privilege DB access | Services use `mortgage_app` (DML only); DDL only via `mortgage_owner` | `database/schema/000_roles_and_database.sql` |
| Ignore rules | `.env`, keys, Terraform state, build output never tracked | `.gitignore` |
| Review checklist | Security, tests, secrets, migrations | [engineering-standards.md](../requirements/engineering-standards.md#code-review-checklist) |
| PR template | Checklist embedded in every PR | `.github/pull_request_template.md` |

## Pipeline blocking policy (M6)

Not every finding type blocks a merge the same way:

- **Secret scanning and SAST are hard gates.** A secret or a Semgrep `ERROR`-severity finding is
  in code this team wrote and can always fix immediately — there's no reason to let it merge.
- **SCA (dependency/image scanning) is report-only, not a hard gate**, by deliberate design. A
  live Trivy scan during M6 found 9 `CRITICAL` and 43 `HIGH` findings in `mortgage-service`'s
  image, almost entirely in Spring Framework/Spring Security/Tomcat/Netty itself (see
  [vulnerability-report.md V-6](../security/vulnerability-report.md)). One real, fixable issue
  (`CVE-2024-38821` in `spring-security-web`) was patched by bumping
  `spring-boot-starter-parent` 3.3.4 → 3.3.13 in this same milestone. Most of the rest list a
  fixed version in the Spring Framework 7.x / Boot 4.x line — a major-version upgrade, not a
  patch bump, and too large a change to make safely in the same milestone that just built and
  verified the JWT/RBAC security config these frameworks sit under. Hard-failing CI on every
  such finding would make the pipeline permanently red for reasons a quick merge can't fix,
  which trains reviewers to ignore or bypass the gate — worse than not having it. Findings are
  still logged on every build (`--exit-code 0`, not silenced) and tracked with an owner in
  [risk-register.md](../security/risk-register.md) (R-6) instead.

## Branch protection configuration (exported)

Applied with the GitHub API (no tokens recorded here):

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Secret scan (gitleaks)", "Migrations + seed on fresh PostgreSQL", "Analytics service tests", "SAST (semgrep)"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
```

`enforce_admins` is `false` only so the sole maintainer can merge while the team is one person; set it to `true` once a second reviewer joins.

## Local checks before pushing

```powershell
# Secret scan of the working tree and history
gitleaks detect --source . --redact -v

# Python dependency audit (M3+)
pip install pip-audit
pip-audit -r analytics/mortgage-analytics-service/requirements.txt
```

Optional pre-commit hook: add the gitleaks hook (`repo: https://github.com/gitleaks/gitleaks`, `id: gitleaks`) to `.pre-commit-config.yaml`.

## If a secret is committed

1. Treat it as compromised: **rotate it immediately** (rotation matters more than history cleanup).
2. Notify the security liaison and instructor.
3. Remove it from history (`git filter-repo`), force-push with admin approval, and ask collaborators to re-clone.
4. Add a gitleaks allowlist entry only for proven false positives, with a comment explaining why.

## Evidence

- First CI run on the M2 pull request: see the repository's **Actions** tab.
- Branch protection: **Settings → Branches** shows rules for `main` and `develop`.
