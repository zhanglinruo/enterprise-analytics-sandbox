# Local Codex Instructions

## Start Here

Before changing code, read these files in order:

1. `docs/handoff/PROJECT_HANDOFF.md`
2. `docs/superpowers/specs/2026-07-28-enterprise-analytics-sandbox-design.md`
3. `docs/superpowers/plans/2026-07-30-golden-scenario-sandbox.md`
4. `docs/handoff/TEST_REPORT.md`
5. `docs/handoff/ROADMAP.md`

The implementation plan records the original build sequence. The authoritative current
status is `docs/handoff/PROJECT_HANDOFF.md`.

## Project Goal

Build a deterministic synthetic enterprise environment for testing and benchmarking
AI business-analysis agents. Business events are the source of truth; public documents,
inventory movements, journal entries, financial results and scores must be derived from
those events.

## Required Engineering Rules

- Use test-driven development for behavior changes: failing test, minimal implementation,
  passing test, then refactor.
- Keep generic AI colleague concepts under `ainative.core`.
- Keep manufacturing, accounting, synthetic data and benchmark logic under
  `ainative.sandbox`.
- Use integer cents in SQLite and deterministic IDs; do not use UUIDs in sandbox data.
- Preserve reproducibility for a fixed effective seed.
- Never patch final reports or database rows merely to force the expected anomaly.
- Never place Ground Truth, Cause IDs, scoring rules or forbidden claims in the public ZIP.
- Do not commit generated databases, public ZIP packages, private state or score reports.
- Avoid new runtime dependencies unless the product requirement justifies them.

## Verification

Run the complete suite before claiming completion:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q ainative tests
```

Run a manual vertical-slice check when changing generation, packaging, scoring or CLI:

```bash
python -m ainative.cli sandbox-generate \
  --seed 61 \
  --output /tmp/enterprise-analytics-sandbox

python -m tests.sandbox.helpers \
  --benchmark /tmp/enterprise-analytics-sandbox \
  --output /tmp/enterprise-analytics-answer.json

python -m ainative.cli sandbox-score \
  --benchmark /tmp/enterprise-analytics-sandbox \
  --answer /tmp/enterprise-analytics-answer.json
```

## Git

The repository uses branch `main` and remote:

```text
https://github.com/zhanglinruo/enterprise-analytics-sandbox.git
```

The cloud environment created the local repository and commits but could not authenticate
to GitHub. From an authenticated local environment, verify the remote and run:

```bash
git push -u origin main
```
