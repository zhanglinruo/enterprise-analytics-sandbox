# External Agent Validation 001 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one verified seed-61 blind-test handoff, a reusable participant instruction sheet, and an experiment register ready to capture three comparable external analysis runs.

**Architecture:** Generate the benchmark once inside the ignored `data/benchmarks/` tree, retain the working database and private state in an evaluator-only directory, and copy only the public ZIP plus public instructions into a separate participant handoff directory. Commit only protocol documentation; never commit generated databases, archives, answers, private state, or score reports.

**Tech Stack:** Python 3.11+, `ainative.cli`, SQLite, ZIP, JSON, Markdown, PowerShell, GitHub Actions.

## Global Constraints

- Use input seed `61` for every Validation 001 participant.
- Give every participant the identical public archive and instruction sheet.
- Never expose `private-state.json`, Ground Truth, Cause IDs, scoring rules, scenario source, scenario tests, or prior answers.
- Preserve the raw participant answer before validation, normalization, scoring, or human review.
- Do not normalize Cause IDs before deterministic scoring.
- Commit documentation only; `data/benchmarks/` remains ignored.
- Do not add a scenario, UI, Agent adapter, answer extractor, dependency, or scoring behavior.

---

## File Structure

- Create `docs/experiments/external-agent-validation-001-participant-instructions.md`: public instructions supplied unchanged to each participant.
- Create `docs/experiments/external-agent-validation-001.md`: evaluator-owned experiment register and per-run record.
- Generate `data/benchmarks/external-agent-validation-001/evaluator/`: private working benchmark; ignored by Git.
- Generate `data/benchmarks/external-agent-validation-001/participant-handoff/`: public ZIP and copied instruction sheet; ignored by Git.
- Generate `data/benchmarks/external-agent-validation-001/runs/<run-id>/`: raw answers, score reports, timings, and evaluator notes; ignored by Git.

### Task 1: Public Participant Instructions

**Files:**
- Create: `docs/experiments/external-agent-validation-001-participant-instructions.md`

**Interfaces:**
- Consumes: public ZIP layout and answer schema from `docs/sandbox/quickstart.md`
- Produces: one immutable instruction sheet copied into every participant handoff

- [ ] **Step 1: Create the instruction sheet**

Use this exact structure:

```markdown
# Enterprise Analytics Blind Test 001 — Participant Instructions

## Your task

Analyze the supplied fictional manufacturing-enterprise package. Identify the most
important operating anomaly, quantify it, explain supported causes with reproducible
evidence, state what the available data cannot establish, and recommend next actions.

## Allowed information

Use only files contained in the supplied public ZIP. Do not search the project source,
scoring implementation, prior answers, or private benchmark files.

## Submission

Return one UTF-8 JSON file with exactly these top-level keys:

{
  "anomalies": [
    {"metric": "metric_name", "direction": "up", "magnitude": 0}
  ],
  "causes": [
    {
      "cause": "your_stable_cause_identifier",
      "confidence": 0.0,
      "evidence": [
        {"table": "public_table", "field": "public_field", "value": 0}
      ]
    }
  ],
  "unknowns": ["material question not answerable from the supplied data"],
  "recommendations": ["specific next action"]
}

Directions must be `up`, `down`, or `flat`. Confidence must be between 0 and 1.
Use stable snake_case identifiers for metrics and causes. Cite only public tables and
fields, and use values that another analyst can reproduce.

## Independence rules

- You may use local analysis tools, SQL, scripts, or spreadsheets.
- You may ask for help only when the ZIP cannot be opened or a tool cannot access a file.
- The evaluator cannot explain the schema, identify relevant tables, suggest queries,
  name expected metrics, or comment on your findings during the run.
- Submit your first final answer without evaluator editing.
```

- [ ] **Step 2: Check that the instructions contain no private identifiers**

Run:

```powershell
Select-String `
  -Path docs\experiments\external-agent-validation-001-participant-instructions.md `
  -Pattern 'raw_material_price_increase|low_margin_product_mix|customer_discount_increase|ground_truth|forbidden_claims' `
  -CaseSensitive:$false
```

Expected: no matches.

- [ ] **Step 3: Check Markdown and Git whitespace**

Run:

```powershell
git diff --check
```

Expected: exit code `0`.

- [ ] **Step 4: Commit the public instructions**

```powershell
git add docs/experiments/external-agent-validation-001-participant-instructions.md
git diff --cached
git commit -m "docs: add blind-test participant instructions"
```

### Task 2: Evaluator Experiment Register

**Files:**
- Create: `docs/experiments/external-agent-validation-001.md`

**Interfaces:**
- Consumes: approved design in `docs/superpowers/specs/2026-07-30-external-agent-validation-001-design.md`
- Produces: benchmark provenance, run registry, review rubric, disagreement log, and experiment conclusion

- [ ] **Step 1: Create the experiment register**

Include:

```markdown
# External Agent Validation 001

## Status

Preparation

## Benchmark provenance

| Field | Value |
|---|---|
| Input seed | 61 |
| Effective seed | Recorded after generation |
| Benchmark ID | Recorded after generation |
| Generator commit | Recorded after generation |
| Public archive SHA-256 | Recorded after generation |
| Database SHA-256 | Recorded after generation |
| Generated at | Recorded after generation |

## Run registry

| Run ID | Participant type | Tool/model | Status | Intervention-free | Deterministic score | Human score |
|---|---|---|---|---|---:|---:|
| EAV001-INTERNAL-01 | Internal AI+BI Agent | Recorded at run start | Not started | Not evaluated | — | — |
| EAV001-GENERAL-01 | General coding/data Agent | Recorded at run start | Not started | Not evaluated | — | — |
| EAV001-HUMAN-01 | Human analyst/practitioner | Recorded at run start | Not started | Not evaluated | — | — |

## Per-run record

For each run record timestamps, participant environment, interventions, first useful
conclusion, raw answer path, schema result, deterministic dimensions, human dimensions,
evidence errors, unsupported claims, missed unknowns, coherence feedback, and score
disagreements.

## Human review rubric

Use the existing 20/20/25/20/10/5 dimensions. Every deduction must cite a concrete
answer claim, reproducible query result, or missing requirement. Semantically correct
causes with non-matching identifiers are recorded as scoring-contract disagreements.

## Conclusion

Complete only after all three planned attempts or an experiment stop condition.
```

- [ ] **Step 2: Confirm the register contains all design measurements**

Compare it line by line with sections 7–12 of the approved design. Add explicit fields
for every measurement; do not replace missing fields with generic prose.

- [ ] **Step 3: Check for unresolved markers and whitespace**

Run:

```powershell
Select-String `
  -Path docs\experiments\external-agent-validation-001.md `
  -Pattern 'T.B.D|T.O.D.O|F.I.X.M.E|P.L.A.C.E.H.O.L.D.E.R' `
  -CaseSensitive:$false
git diff --check
```

Expected: no unresolved-marker matches and exit code `0`.

- [ ] **Step 4: Commit the evaluator register**

```powershell
git add docs/experiments/external-agent-validation-001.md
git diff --cached
git commit -m "docs: add external validation experiment register"
```

### Task 3: Generate and Verify the Fixed Benchmark

**Files:**
- Generate: `data/benchmarks/external-agent-validation-001/evaluator/`
- Modify: `docs/experiments/external-agent-validation-001.md`

**Interfaces:**
- Consumes: `python -m ainative.cli sandbox-generate --seed 61 --output PATH`
- Produces: validated database, private evaluator state, public ZIP, and recorded provenance

- [ ] **Step 1: Record the exact generator commit**

Run:

```powershell
git rev-parse HEAD
git status --short
```

Expected: one commit hash and no uncommitted source changes.

- [ ] **Step 2: Generate the evaluator benchmark**

Run:

```powershell
python -m ainative.cli sandbox-generate `
  --seed 61 `
  --output data/benchmarks/external-agent-validation-001/evaluator
```

Expected: JSON with `validation.publishable` equal to `true`, plus benchmark ID, archive
path, and effective seed.

- [ ] **Step 3: Calculate provenance hashes**

Run:

```powershell
Get-FileHash `
  data/benchmarks/external-agent-validation-001/evaluator/enterprise.db `
  -Algorithm SHA256
Get-ChildItem `
  data/benchmarks/external-agent-validation-001/evaluator/bench_*.zip |
  Get-FileHash -Algorithm SHA256
```

Expected: one database SHA-256 and one archive SHA-256.

- [ ] **Step 4: Inspect the public archive**

Run:

```powershell
python -c "import pathlib,zipfile; p=next(pathlib.Path('data/benchmarks/external-agent-validation-001/evaluator').glob('bench_*.zip')); z=zipfile.ZipFile(p); print('\n'.join(sorted(z.namelist())))"
```

Expected: `data/enterprise.db`, 15 CSV files, schema documents, metrics, task, and manifest;
no private state or Ground Truth file.

- [ ] **Step 5: Re-run the leak and reproducibility tests**

Run:

```powershell
python -m unittest tests.sandbox.test_packaging tests.sandbox.test_service -v
```

Expected: all selected tests pass.

- [ ] **Step 6: Record the real provenance**

Replace every `Recorded after generation` value in the experiment register with the
actual effective seed, benchmark ID, generator commit, hashes, and ISO-8601 timestamp.

- [ ] **Step 7: Commit provenance only**

```powershell
git status --short
git add docs/experiments/external-agent-validation-001.md
git diff --cached
git commit -m "docs: record validation benchmark provenance"
```

Expected: only the Markdown register is committed; `data/benchmarks/` remains ignored.

### Task 4: Build and Audit the Participant Handoff

**Files:**
- Generate: `data/benchmarks/external-agent-validation-001/participant-handoff/`

**Interfaces:**
- Consumes: verified public ZIP and committed participant instructions
- Produces: evaluator-audited directory containing exactly two public files

- [ ] **Step 1: Create the handoff directory**

Run:

```powershell
$handoff = 'data/benchmarks/external-agent-validation-001/participant-handoff'
New-Item -ItemType Directory -Force -Path $handoff
Copy-Item `
  data/benchmarks/external-agent-validation-001/evaluator/bench_*.zip `
  -Destination $handoff
Copy-Item `
  docs/experiments/external-agent-validation-001-participant-instructions.md `
  -Destination $handoff
```

- [ ] **Step 2: Assert the handoff contains exactly two files**

Run:

```powershell
Get-ChildItem `
  data/benchmarks/external-agent-validation-001/participant-handoff `
  -File |
  Select-Object Name,Length
```

Expected: one `bench_*.zip` and one participant instruction Markdown file.

- [ ] **Step 3: Scan the handoff for forbidden filenames and text**

Run:

```powershell
Get-ChildItem `
  data/benchmarks/external-agent-validation-001/participant-handoff `
  -Recurse -File |
  Where-Object {
    $_.Name -match 'private|ground.?truth|score.?report|answer'
  }
Select-String `
  -Path data/benchmarks/external-agent-validation-001/participant-handoff/*.md `
  -Pattern 'raw_material_price_increase|low_margin_product_mix|customer_discount_increase|ground_truth|forbidden_claims' `
  -CaseSensitive:$false
```

Expected: no matches.

- [ ] **Step 4: Confirm generated assets are ignored**

Run:

```powershell
git status --short --ignored data/benchmarks/external-agent-validation-001
```

Expected: the generated tree is ignored and no generated asset is staged.

### Task 5: Execute and Review the First Blind Run

**Files:**
- Generate: `data/benchmarks/external-agent-validation-001/runs/EAV001-INTERNAL-01/`
- Modify: `docs/experiments/external-agent-validation-001.md`

**Interfaces:**
- Consumes: participant handoff, raw participant JSON, evaluator private state
- Produces: immutable raw answer, deterministic score report, human review, and recorded disagreement analysis

- [ ] **Step 1: Record participant metadata and start time**

Create the run directory and record the tool, model/version, execution environment, and
ISO-8601 start time before transferring the handoff.

- [ ] **Step 2: Run the participant without analytical intervention**

Give only the two handoff files to the participant. Record every clarification request,
tool failure, and evaluator response verbatim.

- [ ] **Step 3: Preserve the first final answer**

Save the participant submission unchanged as:

```text
data/benchmarks/external-agent-validation-001/runs/EAV001-INTERNAL-01/raw-answer.json
```

Do not correct JSON, rename metrics or causes, or add evidence.

- [ ] **Step 4: Score the raw answer**

Run:

```powershell
python -m ainative.cli sandbox-score `
  --benchmark data/benchmarks/external-agent-validation-001/evaluator `
  --answer data/benchmarks/external-agent-validation-001/runs/EAV001-INTERNAL-01/raw-answer.json
```

Expected: either a deterministic report or a documented schema error. Copy any generated
`score-report.json` into the run directory without altering it.

- [ ] **Step 5: Complete independent human review**

Score anomaly detection, numbers, root cause, evidence, judgment boundary, and
recommendations independently. Record every deduction and every semantic-cause versus
Cause-ID disagreement. State whether the dataset is sufficiently coherent for Agent
testing and explain every material deterministic-versus-human score disagreement.

- [ ] **Step 6: Update and commit the experiment register**

Record timing, intervention status, deterministic and human scores, errors, feedback,
and disagreements in `docs/experiments/external-agent-validation-001.md`.

```powershell
git add docs/experiments/external-agent-validation-001.md
git diff --cached
git commit -m "docs: record first external validation run"
```

Do not commit raw answers or score reports until they have been intentionally anonymized
and reviewed for private or sensitive content.

## Final Verification

- [ ] Run the complete suite:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q ainative tests
```

- [ ] Confirm Git contains documentation only:

```powershell
git status --short
git log --oneline --decorate -8
```

- [ ] Confirm the public handoff contains exactly the verified ZIP and instructions.
- [ ] Confirm the evaluator directory retains `private-state.json` and is never shared.
- [ ] Push documentation commits after local verification and confirm GitHub CI succeeds.
