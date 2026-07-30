# Enterprise Analytics Sandbox — Test Report

**Test date:** 2026-07-30  
**Runtime:** Python 3.12  
**Test command:**

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

## Automated Result

```text
Ran 25 tests in 34.352s
OK
```

Compilation verification:

```bash
python -m compileall -q ainative tests
```

Result: successful with no compilation errors.

## Coverage Matrix

| Test area | Verified behavior |
|---|---|
| Scenario specification | Stable ID, 12 periods, unsupported scenario rejection |
| Master data | Exactly 15 public tables, expected entity counts, valid foreign keys |
| Event simulation | Same seed produces identical events, all periods covered |
| Scenario injection | Versioned causes, private unknowns, changes only in affected periods |
| Accounting | Every voucher balances, inventory remains non-negative |
| Financial snapshot | Assets equal liabilities plus equity |
| Validation | Blocking unbalanced vouchers, empty report publishability |
| Seed robustness | 20 input seeds produce publishable benchmarks |
| Service | Reproducible benchmark ID and database checksum |
| Packaging | Required public assets exist and Ground Truth does not leak |
| Scoring | Correct answer scores at least 90 |
| Hallucination handling | Forbidden unsupported cause scores below 60 |
| CLI | Generate → correct answer → score workflow succeeds |
| Existing AI Native Core | Original task, approval, governance and evaluation tests remain green |

## Manual Acceptance

The vertical slice was executed twice with input seed `61`.

Observed result:

```json
{
  "zip_file_count": 21,
  "csv_count": 15,
  "has_database": true,
  "has_private_file": false,
  "score": 100,
  "checksum_reproducible": true,
  "effective_seed": 61
}
```

The acceptance run verified:

- the public archive contains the SQLite database;
- all 15 public tables are exported to CSV;
- no filename indicates private state or Ground Truth;
- the known-correct structured answer scores 100;
- two independent runs with the same seed produce the same database checksum.

## Test Files

```text
tests/test_engine.py
tests/sandbox/test_spec.py
tests/sandbox/test_master_data.py
tests/sandbox/test_events.py
tests/sandbox/test_scenario.py
tests/sandbox/test_accounting.py
tests/sandbox/test_validation.py
tests/sandbox/test_service.py
tests/sandbox/test_packaging.py
tests/sandbox/test_scoring.py
tests/sandbox/test_cli.py
```

## Important Testing Boundary

`tests/sandbox/helpers.py` deliberately constructs a known-correct answer by reading the
private benchmark state. It exists only for automated testing and manual acceptance.
Production code under `ainative/` must never import this helper.
