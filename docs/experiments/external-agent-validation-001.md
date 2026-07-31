# External Agent Validation 001

## Status

Preparation

## Benchmark provenance

| Field | Value |
|---|---|
| Input seed | 61 |
| Effective seed | 61 |
| Benchmark ID | `bench_2a6511aeb612` |
| Generator commit | `6f35a385711994d741305f5a995fd1dc6ed18fc7` |
| Public archive SHA-256 | `cef9e8c59003a12b54afbdc884b85c3de0af23d94518db3808e54ecec9d6c2cf` |
| Database SHA-256 | `9c33c0e1f0359c58565d270ce0cd719ef8e1558d78686d334958458cf1018016` |
| Generated at | `2026-07-31T00:53:16Z` |

## Run registry

| Run ID | Participant type | Tool/model | Status | Intervention-free | Deterministic score | Human score |
|---|---|---|---|---|---:|---:|
| EAV001-INTERNAL-01 | Internal AI+BI Agent | Recorded at run start | Not started | Not evaluated | — | — |
| EAV001-GENERAL-01 | General coding/data Agent | Recorded at run start | Not started | Not evaluated | — | — |
| EAV001-HUMAN-01 | Human analyst/practitioner | Recorded at run start | Not started | Not evaluated | — | — |

## Run record: EAV001-INTERNAL-01

### Identity and timing

| Field | Value |
|---|---|
| Participant type | Internal AI+BI Agent |
| Tool/model and version | Recorded at run start |
| Execution environment | Recorded at run start |
| Start time | Not started |
| Time to first useful conclusion | Not measured |
| Final submission time | Not started |
| Total elapsed time | Not measured |

### Independence and workflow

| Field | Value |
|---|---|
| Completed without developer intervention | Not evaluated |
| Clarification requests | None recorded |
| Tool or file-access failures | None recorded |
| Evaluator interventions and responses | None recorded |
| Data-dictionary comprehension issues | Not evaluated |
| Raw answer path | Not created |
| Answer schema result | Not evaluated |

### Analysis quality

| Field | Value |
|---|---|
| First useful conclusion | Not recorded |
| SQL errors | Not evaluated |
| Arithmetic errors | Not evaluated |
| Metric-definition errors | Not evaluated |
| Evidence errors | Not evaluated |
| Unsupported causal claims | Not evaluated |
| Material unknowns stated | Not evaluated |
| Material unknowns missed | Not evaluated |
| Dataset coherence feedback | Not recorded |
| Workflow-friction feedback | Not recorded |

### Scores

| Dimension | Deterministic | Human | Disagreement reason |
|---|---:|---:|---|
| Anomaly detection | — | — | Not evaluated |
| Numbers and metrics | — | — | Not evaluated |
| Root cause | — | — | Not evaluated |
| Reproducible evidence | — | — | Not evaluated |
| Judgment boundary | — | — | Not evaluated |
| Recommendations | — | — | Not evaluated |
| Total | — | — | Not evaluated |

### Review evidence

No answer claims, query results, deductions, Cause-ID contract disagreements, or reviewer
notes exist before the run.

## Run record: EAV001-GENERAL-01

### Identity and timing

| Field | Value |
|---|---|
| Participant type | General coding/data Agent |
| Tool/model and version | Recorded at run start |
| Execution environment | Recorded at run start |
| Start time | Not started |
| Time to first useful conclusion | Not measured |
| Final submission time | Not started |
| Total elapsed time | Not measured |

### Independence and workflow

| Field | Value |
|---|---|
| Completed without developer intervention | Not evaluated |
| Clarification requests | None recorded |
| Tool or file-access failures | None recorded |
| Evaluator interventions and responses | None recorded |
| Data-dictionary comprehension issues | Not evaluated |
| Raw answer path | Not created |
| Answer schema result | Not evaluated |

### Analysis quality

| Field | Value |
|---|---|
| First useful conclusion | Not recorded |
| SQL errors | Not evaluated |
| Arithmetic errors | Not evaluated |
| Metric-definition errors | Not evaluated |
| Evidence errors | Not evaluated |
| Unsupported causal claims | Not evaluated |
| Material unknowns stated | Not evaluated |
| Material unknowns missed | Not evaluated |
| Dataset coherence feedback | Not recorded |
| Workflow-friction feedback | Not recorded |

### Scores

| Dimension | Deterministic | Human | Disagreement reason |
|---|---:|---:|---|
| Anomaly detection | — | — | Not evaluated |
| Numbers and metrics | — | — | Not evaluated |
| Root cause | — | — | Not evaluated |
| Reproducible evidence | — | — | Not evaluated |
| Judgment boundary | — | — | Not evaluated |
| Recommendations | — | — | Not evaluated |
| Total | — | — | Not evaluated |

### Review evidence

No answer claims, query results, deductions, Cause-ID contract disagreements, or reviewer
notes exist before the run.

## Run record: EAV001-HUMAN-01

### Identity and timing

| Field | Value |
|---|---|
| Participant type | Human analyst/practitioner |
| Tool/model and version | Recorded at run start |
| Execution environment | Recorded at run start |
| Start time | Not started |
| Time to first useful conclusion | Not measured |
| Final submission time | Not started |
| Total elapsed time | Not measured |

### Independence and workflow

| Field | Value |
|---|---|
| Completed without developer intervention | Not evaluated |
| Clarification requests | None recorded |
| Tool or file-access failures | None recorded |
| Evaluator interventions and responses | None recorded |
| Data-dictionary comprehension issues | Not evaluated |
| Raw answer path | Not created |
| Answer schema result | Not evaluated |

### Analysis quality

| Field | Value |
|---|---|
| First useful conclusion | Not recorded |
| SQL errors | Not evaluated |
| Arithmetic errors | Not evaluated |
| Metric-definition errors | Not evaluated |
| Evidence errors | Not evaluated |
| Unsupported causal claims | Not evaluated |
| Material unknowns stated | Not evaluated |
| Material unknowns missed | Not evaluated |
| Dataset coherence feedback | Not recorded |
| Workflow-friction feedback | Not recorded |

### Scores

| Dimension | Deterministic | Human | Disagreement reason |
|---|---:|---:|---|
| Anomaly detection | — | — | Not evaluated |
| Numbers and metrics | — | — | Not evaluated |
| Root cause | — | — | Not evaluated |
| Reproducible evidence | — | — | Not evaluated |
| Judgment boundary | — | — | Not evaluated |
| Recommendations | — | — | Not evaluated |
| Total | — | — | Not evaluated |

### Review evidence

No answer claims, query results, deductions, Cause-ID contract disagreements, or reviewer
notes exist before the run.

## Human review rubric

| Dimension | Points | Review requirement |
|---|---:|---|
| Anomaly detection | 20 | Identify the material metric and direction using the public period comparison. |
| Numbers and metrics | 20 | Quantify claims with correctly defined, reproducible amounts, rates, or percentage points. |
| Root cause | 25 | Distinguish supported operating causes from correlation or unsupported business stories. |
| Reproducible evidence | 20 | Cite public table, field, and value combinations another reviewer can reproduce. |
| Judgment boundary | 10 | State material questions that cannot be resolved from the public data. |
| Recommendations | 5 | Recommend actions consistent with supported findings and stated uncertainty. |

Every deduction must cite a concrete answer claim, reproducible query result, or missing
requirement. A semantically correct cause with a non-matching identifier is recorded as a
scoring-contract disagreement and does not silently alter the deterministic score.

## Score disagreement log

No deterministic-versus-human disagreements exist before the first completed run.

## Experiment conclusion

Complete only after all three planned attempts or after a documented stop condition.
The conclusion must state whether at least one participant completed without analytical
guidance, whether low score dimensions reflected observable weaknesses, whether the data
was sufficiently coherent for Agent testing, and what evidence supports retaining or
changing the scoring contract in P2.
