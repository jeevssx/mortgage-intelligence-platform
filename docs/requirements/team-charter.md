# Team Charter

## Team

**Team name:** Team Ledger
**Repository:** `mortgage-intelligence-platform`

| Role | Responsibilities | Member |
| --- | --- | --- |
| Developer(s) | Implement stories, write tests, review peers' PRs | Jeevan Shahi (`jeevssx`) |
| Scrum facilitator | Runs stand-ups, sprint planning, and retros; keeps the board current | Jeevan Shahi |
| Documentation owner | Keeps `docs/` and root README accurate and linked | Jeevan Shahi |
| Security liaison | Owns secret scanning, threat model, and security review items in PRs | Jeevan Shahi |

> Roles are combined while the team is one person. When teammates join, update this table in a PR and redistribute roles. Every role still needs a named owner.

## Working agreement

- We work in small, reviewable pull requests (target under 400 changed lines, docs excepted).
- We follow [engineering-standards.md](./engineering-standards.md) for branches, commits, reviews, and data handling.
- We keep the main branch releasable and `develop` integrable at all times.
- We raise blockers the same day, not at the next stand-up.
- We are respectful in reviews: comments address the code, not the author.

## Meeting cadence

| Meeting | When | Length | Purpose |
| --- | --- | --- | --- |
| Stand-up | Class days, start of session | 10 min | Yesterday / today / blockers |
| Sprint planning | First session of each week | 30 min | Pull stories from [sprint-plans.md](./sprint-plans.md) into the sprint |
| Milestone review / demo | Last session of each week | 10 min | Demo script from the milestone doc |
| Retrospective | After each milestone review | 15 min | One thing to keep, one to change |

**Communication channel:** Team chat channel `#capstone-mortgage-intel` for day-to-day; GitHub issues and PR comments for anything that needs a record.

## Definition of done (documentation)

A document is done when it:

1. Has meaningful content for every required section (no "TBD"-only sections).
2. Has been reviewed in a pull request by at least one other person (or the instructor while the team is one person).
3. Is merged to `develop`.
4. Is linked from the root [README](../../README.md).

## Definition of done (code, from M3)

Code is done when it meets the documentation DoD and also: tests pass in CI, new behavior has tests, no secrets are introduced, and the service README is updated.

## Escalation path

1. **Try for 30 minutes**, then ask a teammate (chat or pair).
2. **Still blocked after 2 hours:** raise it in the team channel and note it on the board as blocked.
3. **Blocked for more than one class day,** or the blocker is environmental (sandbox access, licenses): escalate to the instructor.
4. **Security incident** (secret committed, data exposure): notify the security liaison and instructor immediately, rotate the secret, then clean history.
