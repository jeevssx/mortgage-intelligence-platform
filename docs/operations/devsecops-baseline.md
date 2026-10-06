# DevSecOps Baseline (Milestone 2)

Security controls on the engineering workflow, in place before application code volume grows. Full pipeline (SAST, image scanning, deploy gates) arrives in M9.

## Controls

| Control | Implementation | Where |
| --- | --- | --- |
| Protected branches | `main` and `develop`: PR required, 1 approving review, status checks must pass, no force push, no deletion | GitHub → Settings → Branches (config below) |
| Secret scanning (CI) | gitleaks v8 scans **full git history** on every PR and push; job fails on any finding | `.github/workflows/ci.yml` → `secret-scan`; `.gitlab-ci.yml` → `secret_detection` |
| Secret scanning (platform) | GitHub secret scanning + push protection | GitHub → Settings → Code security |
| Dependency scanning (SCA) | Dependabot weekly PRs for pip and GitHub Actions; `dependency-review-action` blocks PRs adding **critical** CVEs; `pip-audit` in the Python test job (M3) | `.github/dependabot.yml`, `ci.yml` |
| Migration validation | Fresh PostgreSQL 16 in CI: roles → migrations → seed → idempotent re-apply → sample queries as least-privilege role → seed invariants (`MTG-1002` = 45 DPD, etc.) | `ci.yml` → `database` |
| Least-privilege DB access | Services use `mortgage_app` (DML only); DDL only via `mortgage_owner` | `database/schema/000_roles_and_database.sql` |
| Ignore rules | `.env`, keys, Terraform state, build output never tracked | `.gitignore` |
| Review checklist | Security, tests, secrets, migrations | [engineering-standards.md](../requirements/engineering-standards.md#code-review-checklist) |
| PR template | Checklist embedded in every PR | `.github/pull_request_template.md` |

## Branch protection configuration (exported)

Applied with the GitHub API (no tokens recorded here):

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Secret scan (gitleaks)", "Migrations + seed on fresh PostgreSQL", "Analytics service tests"]
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
