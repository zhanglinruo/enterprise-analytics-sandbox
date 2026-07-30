# Enterprise Analytics Sandbox — Recommended Roadmap

## Guiding Principle

Do not immediately add many industries, scenarios or platform features. First prove that
an external analysis Agent can use the public package and that the score distinguishes a
useful analysis from a plausible but unsupported one.

## P0 — Local Takeover and Repository Publication

Goal: establish a reliable local development baseline.

1. Extract the handoff ZIP.
2. Open the repository root in local Codex.
3. Read `AGENTS.md` and the handoff documents.
4. Run all 25 tests.
5. Verify `origin`.
6. Authenticate locally and push `main`.
7. Add a simple GitHub Actions workflow for Python tests.

Exit criteria:

- local tests pass;
- GitHub contains the current `main`;
- CI passes on every push.

## P1 — External Agent Validation

Goal: test product value, not add platform breadth.

Run at least three external analysis attempts against the same public ZIP:

1. the current internal AI+BI Agent;
2. a general coding/data Agent;
3. a human financial analyst or AI+BI practitioner.

Capture:

- time to first useful conclusion;
- whether the Agent can understand the data dictionary;
- SQL or evidence errors;
- unsupported causal claims;
- missing business unknowns;
- score and human reviewer score;
- disagreement between deterministic score and human judgment.

Recommended deliverable:

```text
docs/experiments/external-agent-validation-001.md
```

Exit criteria:

- at least one external Agent completes the workflow without developer intervention;
- score weaknesses correspond to observable analysis weaknesses;
- users agree the generated data feels coherent enough for analysis testing.

## P2 — Improve Benchmark Validity

Goal: make the score a trustworthy evaluation instrument.

Recommended work:

- add explicit expected SQL evidence definitions;
- distinguish amount, rate and percentage-point tolerances;
- score causal chains rather than Cause IDs alone;
- strengthen recommendation evaluation with rule-based contradictions;
- compare deterministic score with human ratings;
- add mutation tests for leak prevention;
- add property tests for document amounts and cumulative inventory by stock type;
- record baseline counterfactual metrics explicitly in private state.

Do not expose these definitions in the public package.

## P3 — Productize the Sandbox Workflow

Goal: reduce the friction of generate → analyze → submit → review.

Possible features:

- benchmark catalog;
- one-click generation;
- package download;
- answer upload;
- score detail page;
- evidence explorer;
- human review and score override;
- run comparison across Agents and models.

Keep the generation and scoring services independent from the UI.

## P4 — Add Scenarios Deliberately

Add a second scenario only after P1 produces evidence that the current benchmark is useful.
Good candidates:

1. revenue down while inventory rises;
2. sales growth with worsening receivable days;
3. purchase savings with quality-return increase;
4. budget expense overrun with organization concentration.

Each scenario must define:

- business story;
- operating parameter changes;
- public observables;
- proven causes;
- unknown business context;
- forbidden claims;
- target effect ranges;
- expected evidence;
- score behavior.

## P5 — Synthetic Enterprise Product Direction

If external users value the dataset itself, evolve toward an Enterprise Synthetic Data
Platform:

- industry templates;
- configurable enterprise scale;
- scenario library;
- semantic layer generation;
- benchmark versioning;
- private deployment;
- domain packs for manufacturing, retail, SaaS and services.

Keep two product modes separate:

```text
Benchmark mode: known hidden truth, controlled scoring, reproducible data
Demo/test-data mode: configurable fictional data, no required hidden answer
```

## Deferred Work

Do not prioritize yet:

- arbitrary real-data upload and synthesis;
- full anonymization of personal data;
- unlimited autonomous Agent operation;
- visual workflow builder;
- multi-tenant SaaS administration;
- dozens of Agent runtime adapters;
- complex manufacturing accounting;
- model training.

These are valid future directions but do not help validate the current core assumption.
