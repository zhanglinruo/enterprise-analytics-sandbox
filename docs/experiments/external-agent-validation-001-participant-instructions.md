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

```json
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
```

Directions must be `up`, `down`, or `flat`. Confidence must be between 0 and 1.
Use stable snake_case identifiers for metrics and causes. Cite only public tables and
fields, and use values that another analyst can reproduce.

## Independence rules

- You may use local analysis tools, SQL, scripts, or spreadsheets.
- You may ask for help only when the ZIP cannot be opened or a tool cannot access a file.
- The evaluator cannot explain the schema, identify relevant tables, suggest queries,
  name expected metrics, or comment on your findings during the run.
- Submit your first final answer without evaluator editing.
