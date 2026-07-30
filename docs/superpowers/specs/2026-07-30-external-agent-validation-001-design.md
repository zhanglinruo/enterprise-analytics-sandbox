# External Agent Validation 001 — Experiment Design

**Date:** 2026-07-30

**Status:** Proposed

**Phase:** P1 — External Agent Validation

## 1. Objective

Determine whether an external business-analysis Agent can use the public exam package,
without access to private benchmark state or developer guidance, to identify the main
operating anomaly, quantify it, support its causes with reproducible evidence, and state
what the available data cannot prove.

This experiment tests product validity. It does not test new scenarios, a Web interface,
natural-language extraction, or direct Agent runtime integration.

## 2. Primary Questions

1. Can a participant complete the public-package-to-structured-answer workflow without
   developer intervention?
2. Does a weak deterministic score correspond to an observable weakness in the analysis?
3. Does the generated enterprise feel financially and operationally coherent to an
   independent reviewer?
4. Where does deterministic scoring disagree with human judgment?

## 3. Approaches Considered

### A. One fixed package for all participants — selected

Generate one public package from input seed `61` and give the identical archive and
participant instructions to every participant.

- Best comparability across participants.
- Cheapest first experiment.
- Does not measure robustness across different datasets.

### B. A different seed for each participant

- Broadens data coverage.
- Confounds participant capability with benchmark variation.
- Deferred until the fixed-package protocol has been validated.

### C. Automated Agent runtime integration

- Enables repeatable high-volume evaluation.
- Adds integration and orchestration work before product value is established.
- Deferred until at least one manual file-based run succeeds.

## 4. Participants

Run at least one attempt from each group:

1. the current internal AI+BI Agent;
2. a general coding or data-analysis Agent;
3. a human financial analyst or AI+BI practitioner.

Participants must not have read the private state, Ground Truth, scenario source,
scenario tests, scoring implementation, or previous participants' answers.

## 5. Experiment Assets

### Public assets supplied to participants

- the generated `bench_*.zip` archive;
- a participant instruction sheet containing only workflow rules and the public answer
  JSON schema;
- a unique participant ID and run ID.

### Private evaluator assets

- `enterprise.db` working database;
- `private-state.json`;
- deterministic scoring command;
- human-review rubric;
- run timing and observation notes.

The public archive is the only benchmark data asset supplied to participants. The
working database and private state never leave evaluator custody.

## 6. Participant Instructions

Participants must:

1. work only from the supplied public archive;
2. inspect any tables and documents they consider relevant;
3. return one JSON answer matching the documented public schema;
4. cite table, field, and reproducible values for factual causes;
5. list material questions that the public data cannot answer;
6. avoid asking the evaluator for hints about the expected anomaly or causes.

The evaluator may resolve file-access or tool-execution failures but may not explain the
schema, suggest queries, name metrics, identify relevant tables, or reinterpret business
findings during the run. Every intervention must be recorded.

## 7. Run Procedure

### Preparation

1. Generate the benchmark once with input seed `61`.
2. Record benchmark ID, effective seed, archive SHA-256, database SHA-256, generator
   commit, and generation timestamp.
3. Verify the public archive contains no private file, private table, Ground Truth token,
   or Cause ID.
4. Copy the public archive and participant instructions into a handoff directory that
   contains no evaluator-only asset.

### Execution

1. Start the timer when the participant receives the handoff directory.
2. Record time to first useful conclusion and time to final answer.
3. Record tool failures, clarification requests, and evaluator interventions.
4. Save the participant's answer exactly as submitted before any normalization or repair.
5. Validate the answer schema and run deterministic scoring against the original answer.

### Review

1. A reviewer who can access private state assigns a human score using the same six
   dimensions as the deterministic report.
2. The reviewer records factual errors, unsupported claims, evidence failures, missed
   unknowns, and useful conclusions.
3. Compare raw deterministic and human scores by dimension.
4. Record disagreements without changing the participant answer or rerunning the score.

## 8. Cause-ID Validity Boundary

The current deterministic scorer matches root causes by exact Cause ID, while the public
package intentionally does not publish private Cause IDs. A participant may therefore
describe a correct cause using a different identifier and lose deterministic points.

For this experiment:

- do not publish or hint at the expected Cause IDs;
- do not normalize identifiers before deterministic scoring;
- preserve the raw score as the product result;
- let the human reviewer separately recognize semantically correct causes;
- classify any resulting disagreement as a scoring-contract issue, not automatically as
  an analysis failure.

This boundary is an explicit subject of P1 validation and may motivate P2 changes.

## 9. Measurements

Capture for every run:

- participant type, tool/model, and relevant version;
- start time, time to first useful conclusion, and completion time;
- completion without developer intervention;
- data-dictionary comprehension issues;
- SQL, arithmetic, metric-definition, and evidence errors;
- unsupported causal claims;
- material unknowns stated and missed;
- deterministic score by dimension;
- human score by dimension;
- reason for every material score disagreement;
- participant feedback on data coherence and workflow friction.

## 10. Human Review Scale

Use the existing scoring weights:

| Dimension | Points |
|---|---:|
| Anomaly detection | 20 |
| Numbers and metrics | 20 |
| Root cause | 25 |
| Reproducible evidence | 20 |
| Judgment boundary | 10 |
| Recommendations | 5 |

The reviewer must justify deductions with a concrete answer excerpt, query result, or
missing requirement. Human review must not overwrite the deterministic report.

## 11. Success Criteria

P1 Validation 001 succeeds when:

1. at least one external participant completes the workflow without analytical guidance;
2. the participant produces a schema-valid answer or any schema failure is clearly
   attributable to documented workflow friction;
3. observed analytical weaknesses explain low score dimensions, after separately
   accounting for Cause-ID contract disagreements;
4. an independent reviewer considers the dataset sufficiently coherent for Agent testing;
5. the experiment produces specific evidence for either retaining or changing the
   scoring contract in P2.

## 12. Deliverables

- this approved experiment design;
- one verified seed-61 public handoff package;
- `docs/experiments/external-agent-validation-001.md` containing the experiment register,
  per-run observations, scores, disagreements, and conclusion;
- participant answer files kept out of Git unless they are intentionally anonymized and
  reviewed for private or sensitive content.

## 13. Non-Goals and Stop Conditions

Do not add a second scenario, UI, Agent adapter, natural-language extractor, or new
scoring behavior during this experiment. If the public package leaks private state or the
benchmark fails reproducibility checks, stop the experiment and repair the benchmark
before recruiting participants.
