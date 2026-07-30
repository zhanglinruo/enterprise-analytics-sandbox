# Golden Scenario Analytics Sandbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one reproducible “revenue up, profit down” manufacturing benchmark that generates relational business and accounting data, validates internal consistency, exports a public exam package, accepts a structured Agent answer, and produces a deterministic score report.

**Architecture:** Add an isolated `ainative.sandbox` package beside the existing AI Native Core. A deterministic event simulator is the single source of truth; documents, inventory movements, journal entries, financial views, Ground Truth, exported files, and scores are derived from those events. The first vertical slice is exposed through CLI commands and does not modify the existing web application.

**Tech Stack:** Python 3.12 standard library (`dataclasses`, `decimal`, `random`, `sqlite3`, `csv`, `json`, `zipfile`, `unittest`); no model calls and no new runtime dependency.

## Global Constraints

- Keep `ainative.core` generic; manufacturing, finance, and benchmark logic must live under `ainative.sandbox`.
- Generate exactly one scenario in this plan: `revenue_up_profit_down`.
- Generate 12 monthly periods with a fixed user-supplied integer seed.
- Business events are the only source of truth; never patch final reports to force an anomaly.
- All money calculations use `Decimal` internally and store integer cents in SQLite.
- The public exam package must never contain Ground Truth, golden SQL, cause contributions, or scoring rules.
- Phase 1 accepts structured JSON Agent answers only; Markdown/HTML extraction is a later plan.
- Phase 1 provides CLI workflows only; the four-page web product is a later plan.
- VAT, foreign currency, depreciation, payroll, full MRP, complex BOM, and complex manufacturing overhead are out of scope.
- Do not initialize a Git repository without user approval. The current workspace has no Git metadata; run commit steps only after the user supplies or authorizes a repository.

---

## File Map

| Path | Responsibility |
|---|---|
| `ainative/sandbox/__init__.py` | Public sandbox API |
| `ainative/sandbox/spec.py` | Scenario specification, scale, periods, seed, serialization |
| `ainative/sandbox/schema.py` | SQLite schema for the 15 published tables |
| `ainative/sandbox/master_data.py` | Deterministic organizations, customers, suppliers, products, accounts |
| `ainative/sandbox/events.py` | Monthly sales and procurement event simulation |
| `ainative/sandbox/accounting.py` | Documents, inventory, journal entries, balances, statements |
| `ainative/sandbox/scenarios.py` | “Revenue up, profit down” parameter changes and Ground Truth |
| `ainative/sandbox/validation.py` | Blocking, warning, and scenario-effectiveness checks |
| `ainative/sandbox/packaging.py` | Public SQLite/CSV/schema/semantic/task package |
| `ainative/sandbox/scoring.py` | Structured answer model and deterministic scoring |
| `ainative/sandbox/service.py` | End-to-end generate and score use cases |
| `ainative/cli.py` | `sandbox-generate` and `sandbox-score` commands |
| `config/scenarios/revenue_up_profit_down.json` | Versioned scenario parameters and Cause IDs |
| `tests/sandbox/` | Unit, property-style, golden scenario, packaging, and scoring tests |

---

### Task 1: Scenario Specification and Reproducible Identity

**Files:**
- Create: `ainative/sandbox/__init__.py`
- Create: `ainative/sandbox/spec.py`
- Create: `tests/sandbox/__init__.py`
- Create: `tests/sandbox/test_spec.py`

**Interfaces:**
- Produces: `ScenarioSpec.create(scenario_id: str, seed: int) -> ScenarioSpec`
- Produces: `ScenarioSpec.periods() -> tuple[str, ...]`
- Produces: `ScenarioSpec.to_dict() -> dict[str, object]`
- Produces: `ScenarioSpec.benchmark_id -> str`
- Consumes: no earlier sandbox interfaces

- [ ] **Step 1: Write the failing specification tests**

```python
# tests/sandbox/test_spec.py
import unittest

from ainative.sandbox.spec import ScenarioSpec


class ScenarioSpecTest(unittest.TestCase):
    def test_creates_twelve_months_and_stable_benchmark_id(self):
        first = ScenarioSpec.create("revenue_up_profit_down", seed=20260730)
        second = ScenarioSpec.create("revenue_up_profit_down", seed=20260730)

        self.assertEqual("2025-01", first.periods()[0])
        self.assertEqual("2025-12", first.periods()[-1])
        self.assertEqual(12, len(first.periods()))
        self.assertEqual(first.benchmark_id, second.benchmark_id)

    def test_rejects_unknown_scenario(self):
        with self.assertRaisesRegex(ValueError, "Unsupported scenario"):
            ScenarioSpec.create("unknown", seed=1)

    def test_serialization_contains_version_and_seed(self):
        spec = ScenarioSpec.create("revenue_up_profit_down", seed=9)
        payload = spec.to_dict()
        self.assertEqual("1.0.0", payload["generator_version"])
        self.assertEqual(9, payload["seed"])
```

- [ ] **Step 2: Run the tests and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_spec -v
```

Expected: `ModuleNotFoundError: No module named 'ainative.sandbox'`.

- [ ] **Step 3: Implement the immutable scenario specification**

```python
# ainative/sandbox/spec.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256


SUPPORTED_SCENARIOS = {"revenue_up_profit_down"}


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    seed: int
    start_period: str = "2025-01"
    month_count: int = 12
    company_count: int = 1
    business_unit_count: int = 2
    plant_count: int = 3
    sales_region_count: int = 4
    customer_count: int = 100
    supplier_count: int = 50
    product_count: int = 100
    generator_version: str = "1.0.0"
    scenario_version: str = "1.0.0"

    @classmethod
    def create(cls, scenario_id: str, seed: int) -> "ScenarioSpec":
        if scenario_id not in SUPPORTED_SCENARIOS:
            raise ValueError(f"Unsupported scenario: {scenario_id}")
        if seed < 0:
            raise ValueError("seed must be non-negative")
        return cls(scenario_id=scenario_id, seed=seed)

    @property
    def benchmark_id(self) -> str:
        raw = f"{self.generator_version}:{self.scenario_version}:{self.scenario_id}:{self.seed}"
        return f"bench_{sha256(raw.encode()).hexdigest()[:12]}"

    def periods(self) -> tuple[str, ...]:
        year, month = map(int, self.start_period.split("-"))
        values = []
        for offset in range(self.month_count):
            absolute = year * 12 + month - 1 + offset
            values.append(f"{absolute // 12:04d}-{absolute % 12 + 1:02d}")
        return tuple(values)

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "benchmark_id": self.benchmark_id}
```

Export `ScenarioSpec` from `ainative/sandbox/__init__.py`.

- [ ] **Step 4: Run the tests and verify success**

Run:

```bash
python -m unittest tests.sandbox.test_spec -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit when a repository is available**

```bash
git add ainative/sandbox/__init__.py ainative/sandbox/spec.py tests/sandbox
git commit -m "feat(sandbox): add reproducible scenario specification"
```

---

### Task 2: SQLite Schema and Deterministic Master Data

**Files:**
- Create: `ainative/sandbox/schema.py`
- Create: `ainative/sandbox/master_data.py`
- Create: `tests/sandbox/test_master_data.py`

**Interfaces:**
- Consumes: `ScenarioSpec`
- Produces: `create_database(path: Path) -> sqlite3.Connection`
- Produces: `MasterDataGenerator(spec: ScenarioSpec).populate(conn: sqlite3.Connection) -> None`
- Produces published tables: `dim_organization`, `dim_customer`, `dim_supplier`, `dim_product`, `dim_account`, ten fact tables

- [ ] **Step 1: Write the failing schema and master-data tests**

```python
# tests/sandbox/test_master_data.py
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.master_data import MasterDataGenerator
from ainative.sandbox.schema import PUBLISHED_TABLES, create_database
from ainative.sandbox.spec import ScenarioSpec


class MasterDataTest(unittest.TestCase):
    def test_creates_exactly_fifteen_published_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = create_database(Path(tmp) / "exam.db")
            tables = {
                row[0]
                for row in conn.execute(
                    "select name from sqlite_master where type='table' and name not like '_%'"
                )
            }
            self.assertEqual(15, len(PUBLISHED_TABLES))
            self.assertEqual(set(PUBLISHED_TABLES), tables)

    def test_populates_expected_master_data_and_valid_foreign_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = create_database(Path(tmp) / "exam.db")
            spec = ScenarioSpec.create("revenue_up_profit_down", seed=11)
            MasterDataGenerator(spec).populate(conn)

            self.assertEqual(100, conn.execute("select count(*) from dim_customer").fetchone()[0])
            self.assertEqual(50, conn.execute("select count(*) from dim_supplier").fetchone()[0])
            self.assertEqual(100, conn.execute("select count(*) from dim_product").fetchone()[0])
            self.assertEqual([], conn.execute("pragma foreign_key_check").fetchall())
```

- [ ] **Step 2: Run the tests and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_master_data -v
```

Expected: import failure for `ainative.sandbox.schema`.

- [ ] **Step 3: Define the 15-table schema**

In `schema.py`, define this exact published table tuple:

```python
PUBLISHED_TABLES = (
    "dim_organization",
    "dim_customer",
    "dim_supplier",
    "dim_product",
    "dim_account",
    "fact_sales_order",
    "fact_sales_delivery",
    "fact_sales_invoice",
    "fact_cash_receipt",
    "fact_purchase_order",
    "fact_goods_receipt",
    "fact_supplier_invoice",
    "fact_cash_payment",
    "fact_inventory_movement",
    "fact_journal_entry",
)
```

Use `INTEGER` cents for money. Every fact table must contain `source_event_id`; every downstream document must also contain its preceding document ID. Enable SQLite foreign keys with:

```python
conn = sqlite3.connect(path)
conn.execute("pragma foreign_keys = on")
```

Required fact-table keys:

```text
fact_sales_order(order_line_id, order_id, order_date, period, organization_id,
                 region_id, customer_id, product_id, quantity, unit_price_cents,
                 discount_rate_bps, net_amount_cents, source_event_id)
fact_sales_delivery(delivery_line_id, delivery_id, order_line_id, delivery_date,
                    period, product_id, quantity, unit_cost_cents, source_event_id)
fact_sales_invoice(invoice_line_id, invoice_id, delivery_line_id, invoice_date,
                   period, customer_id, product_id, quantity, revenue_cents,
                   due_date, source_event_id)
fact_cash_receipt(receipt_id, invoice_id, receipt_date, period, customer_id,
                  amount_cents, source_event_id)
fact_purchase_order(po_line_id, po_id, order_date, period, supplier_id,
                    product_id, quantity, unit_price_cents, source_event_id)
fact_goods_receipt(gr_line_id, gr_id, po_line_id, receipt_date, period,
                   supplier_id, product_id, quantity, unit_price_cents,
                   source_event_id)
fact_supplier_invoice(ap_invoice_id, gr_line_id, invoice_date, period,
                      supplier_id, amount_cents, due_date, source_event_id)
fact_cash_payment(payment_id, ap_invoice_id, payment_date, period, supplier_id,
                  amount_cents, source_event_id)
fact_inventory_movement(movement_id, movement_date, period, product_id,
                        movement_type, quantity, unit_cost_cents,
                        source_document_type, source_document_id, source_event_id)
fact_journal_entry(entry_line_id, voucher_id, posting_date, period, account_id,
                   debit_cents, credit_cents, source_document_type,
                   source_document_id, source_event_id)
```

- [ ] **Step 4: Implement stable master-data generation**

Use a local `random.Random(spec.seed)` instance. Generate IDs by sequence, not UUID:

```python
customer_id = f"CUST{index:04d}"
supplier_id = f"SUP{index:04d}"
product_id = f"PROD{index:04d}"
```

Create two product lines:

- `CORE`: 70 products, base gross margin 32%;
- `VALUE`: 30 products, base gross margin 14%.

Create accounts with fixed IDs:

```text
1001 Bank
1122 Accounts Receivable
1405 Raw Material Inventory
1406 Finished Goods Inventory
2202 Accounts Payable
2203 Goods Receipt Accrual
4001 Paid-in Capital
5001 Main Operating Revenue
5401 Cost of Goods Sold
```

Do not insert opening balances in this task. Task 3 emits opening capitalization and opening
inventory events; Task 5 posts them into the published journal and inventory tables.

- [ ] **Step 5: Run schema and master-data tests**

Run:

```bash
python -m unittest tests.sandbox.test_master_data -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit when a repository is available**

```bash
git add ainative/sandbox/schema.py ainative/sandbox/master_data.py tests/sandbox/test_master_data.py
git commit -m "feat(sandbox): add relational schema and master data"
```

---

### Task 3: Business Event Simulation

**Files:**
- Create: `ainative/sandbox/events.py`
- Create: `tests/sandbox/test_events.py`

**Interfaces:**
- Consumes: `ScenarioSpec`
- Consumes master rows from Task 2
- Produces: `BusinessEvent`
- Produces: `OperatingParameters`
- Produces: `normal_parameters(period: str) -> OperatingParameters`
- Produces: `EventSimulator(spec: ScenarioSpec, parameter_resolver: Callable[[str], OperatingParameters]).generate(conn: sqlite3.Connection) -> tuple[BusinessEvent, ...]`
- Produces: sales demand, purchase replenishment, delivery, invoice, receipt, and payment events

- [ ] **Step 1: Write failing event tests**

```python
# tests/sandbox/test_events.py
import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.events import EventSimulator, normal_parameters
from ainative.sandbox.master_data import MasterDataGenerator
from ainative.sandbox.schema import create_database
from ainative.sandbox.spec import ScenarioSpec


class EventSimulatorTest(unittest.TestCase):
    def build(self, seed):
        tmp = tempfile.TemporaryDirectory()
        conn = create_database(Path(tmp.name) / "exam.db")
        spec = ScenarioSpec.create("revenue_up_profit_down", seed=seed)
        MasterDataGenerator(spec).populate(conn)
        return tmp, conn, spec

    def test_same_seed_produces_identical_events(self):
        left_tmp, left_conn, left_spec = self.build(21)
        right_tmp, right_conn, right_spec = self.build(21)
        try:
            left = EventSimulator(left_spec, normal_parameters).generate(left_conn)
            right = EventSimulator(right_spec, normal_parameters).generate(right_conn)
            self.assertEqual(left, right)
        finally:
            left_tmp.cleanup()
            right_tmp.cleanup()

    def test_events_cover_all_periods_and_have_positive_quantities(self):
        tmp, conn, spec = self.build(22)
        try:
            events = EventSimulator(spec, normal_parameters).generate(conn)
            self.assertEqual(set(spec.periods()), {event.period for event in events})
            self.assertTrue(all(event.quantity > 0 for event in events if event.quantity is not None))
        finally:
            tmp.cleanup()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_events -v
```

Expected: import failure for `ainative.sandbox.events`.

- [ ] **Step 3: Define the event model**

```python
@dataclass(frozen=True)
class BusinessEvent:
    event_id: str
    event_type: str
    event_date: str
    period: str
    organization_id: str
    counterparty_id: str | None
    product_id: str | None
    quantity: int | None
    unit_price_cents: int | None
    attributes: tuple[tuple[str, str], ...] = ()
```

Event IDs must be sequential and stable: `EVT00000001`.

Define the immutable parameters passed to every monthly simulation:

```python
@dataclass(frozen=True)
class OperatingParameters:
    period: str
    demand_multiplier: float
    value_product_demand_share: float
    core_material_purchase_price_multiplier: float
    key_customer_discount_increment_bps: int


def normal_parameters(period: str) -> OperatingParameters:
    return OperatingParameters(
        period=period,
        demand_multiplier=1.0,
        value_product_demand_share=0.30,
        core_material_purchase_price_multiplier=1.0,
        key_customer_discount_increment_bps=0,
    )
```

- [ ] **Step 4: Implement the normal operating baseline**

For each month:

- emit opening capitalization and opening inventory events once before the first period;
- generate 600 to 800 sales order lines;
- use monthly seasonality factors `(0.85, 0.88, 0.95, 1.00, 1.04, 1.08, 0.92, 0.94, 1.03, 1.08, 1.20, 1.35)`;
- allocate demand across customers, products, and regions using the seeded RNG;
- replenish products when projected available quantity falls below 1.3 months of demand;
- create delivery 2–10 days after order;
- create sales invoice 0–3 days after delivery;
- schedule customer receipt from the customer credit term plus a seeded -3 to +12 day variation;
- create goods receipt 5–20 days after purchase order;
- create supplier invoice 0–5 days after goods receipt;
- schedule supplier payment from supplier credit term plus a seeded -2 to +5 day variation.
- emit `manufacturing_completion` events that transfer available raw-material cost into
  finished-goods inventory before deliveries.

Do not write public fact tables in this task. Return immutable events so later tasks remain
the only document/accounting projectors.

- [ ] **Step 5: Run event tests**

Run:

```bash
python -m unittest tests.sandbox.test_events -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit when a repository is available**

```bash
git add ainative/sandbox/events.py tests/sandbox/test_events.py
git commit -m "feat(sandbox): simulate deterministic business events"
```

---

### Task 4: Scenario Injection and Ground Truth

**Files:**
- Create: `config/scenarios/revenue_up_profit_down.json`
- Create: `ainative/sandbox/scenarios.py`
- Create: `tests/sandbox/test_scenario.py`

**Interfaces:**
- Consumes: `ScenarioSpec`, `BusinessEvent`
- Produces: `ScenarioDefinition`
- Produces: `ScenarioDefinition.parameters_for_period(period: str, baseline: OperatingParameters) -> OperatingParameters`
- Produces: `GroundTruth.to_dict() -> dict[str, object]`

- [ ] **Step 1: Write failing scenario tests**

```python
# tests/sandbox/test_scenario.py
import unittest

from ainative.sandbox.scenarios import load_scenario
from ainative.sandbox.spec import ScenarioSpec


class ScenarioTest(unittest.TestCase):
    def test_definition_contains_three_versioned_causes(self):
        definition = load_scenario("revenue_up_profit_down")
        self.assertEqual("1.0.0", definition.version)
        self.assertEqual(
            {
                "raw_material_price_increase",
                "low_margin_product_mix",
                "customer_discount_increase",
            },
            {cause.cause_id for cause in definition.causes},
        )
        self.assertAlmostEqual(1.0, sum(cause.contribution for cause in definition.causes))

    def test_ground_truth_separates_proven_causes_and_unknowns(self):
        truth = load_scenario("revenue_up_profit_down").ground_truth()
        self.assertIn("customer_competition_strategy", truth.unknowns)
        self.assertIn("customer_loss", truth.forbidden_claims)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_scenario -v
```

Expected: import failure for `ainative.sandbox.scenarios`.

- [ ] **Step 3: Add the versioned scenario configuration**

```json
{
  "scenario_id": "revenue_up_profit_down",
  "version": "1.0.0",
  "affected_periods": ["2025-10", "2025-11", "2025-12"],
  "target_observations": {
    "revenue_growth_min": 0.15,
    "revenue_growth_max": 0.22,
    "profit_growth_min": -0.18,
    "profit_growth_max": -0.08
  },
  "causes": [
    {
      "cause_id": "raw_material_price_increase",
      "contribution": 0.45,
      "parameter": "core_material_purchase_price",
      "multiplier": 1.18
    },
    {
      "cause_id": "low_margin_product_mix",
      "contribution": 0.35,
      "parameter": "value_product_demand_share",
      "multiplier": 1.55
    },
    {
      "cause_id": "customer_discount_increase",
      "contribution": 0.20,
      "parameter": "key_customer_discount_bps",
      "increment": 450
    }
  ],
  "unknowns": ["customer_competition_strategy"],
  "forbidden_claims": ["customer_loss", "competitor_price_war"],
  "expected_evidence": [
    "purchase_unit_price_by_product",
    "sales_mix_by_product_line",
    "discount_rate_by_customer"
  ]
}
```

- [ ] **Step 4: Implement typed scenario and Ground Truth models**

Use frozen dataclasses:

```python
@dataclass(frozen=True)
class Cause:
    cause_id: str
    contribution: float
    parameter: str
    multiplier: float | None = None
    increment: int | None = None


@dataclass(frozen=True)
class GroundTruth:
    scenario_id: str
    observations: tuple[str, ...]
    root_causes: tuple[str, ...]
    contributions: tuple[tuple[str, float], ...]
    evidence_ids: tuple[str, ...]
    unknowns: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
```

`ScenarioDefinition.parameters_for_period` must return unchanged baseline parameters outside
the affected periods. Inside affected periods it returns a replaced `OperatingParameters`
with the configured demand mix, purchase price, and discount changes. It must not update
events, SQLite output tables, or computed financial results after generation.

- [ ] **Step 5: Run scenario tests**

Run:

```bash
python -m unittest tests.sandbox.test_scenario -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit when a repository is available**

```bash
git add config/scenarios/revenue_up_profit_down.json ainative/sandbox/scenarios.py tests/sandbox/test_scenario.py
git commit -m "feat(sandbox): define revenue-up-profit-down ground truth"
```

---

### Task 5: Document Projection, Inventory, and Double-Entry Accounting

**Files:**
- Create: `ainative/sandbox/accounting.py`
- Create: `tests/sandbox/test_accounting.py`

**Interfaces:**
- Consumes: `tuple[BusinessEvent, ...]`
- Produces: `AccountingProjector.project(conn: sqlite3.Connection, events: tuple[BusinessEvent, ...]) -> None`
- Produces: `FinancialSnapshot`
- Produces: `financial_snapshot(conn: sqlite3.Connection, period: str) -> FinancialSnapshot`

- [ ] **Step 1: Write failing accounting tests**

```python
# tests/sandbox/test_accounting.py
import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.accounting import AccountingProjector, financial_snapshot
from ainative.sandbox.events import EventSimulator, normal_parameters
from ainative.sandbox.master_data import MasterDataGenerator
from ainative.sandbox.schema import create_database
from ainative.sandbox.spec import ScenarioSpec


class AccountingTest(unittest.TestCase):
    def test_every_voucher_balances_and_inventory_reconciles(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = create_database(Path(tmp) / "exam.db")
            spec = ScenarioSpec.create("revenue_up_profit_down", seed=31)
            MasterDataGenerator(spec).populate(conn)
            events = EventSimulator(spec, normal_parameters).generate(conn)
            AccountingProjector().project(conn, events)

            unbalanced = conn.execute(
                """
                select voucher_id
                from fact_journal_entry
                group by voucher_id
                having sum(debit_cents) <> sum(credit_cents)
                """
            ).fetchall()
            negative_inventory = conn.execute(
                """
                select product_id
                from fact_inventory_movement
                group by product_id
                having sum(quantity) < 0
                """
            ).fetchall()
            self.assertEqual([], unbalanced)
            self.assertEqual([], negative_inventory)

    def test_snapshot_satisfies_accounting_equation(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = create_database(Path(tmp) / "exam.db")
            spec = ScenarioSpec.create("revenue_up_profit_down", seed=32)
            MasterDataGenerator(spec).populate(conn)
            events = EventSimulator(spec, normal_parameters).generate(conn)
            AccountingProjector().project(conn, events)
            snapshot = financial_snapshot(conn, "2025-12")

            self.assertEqual(
                snapshot.assets_cents,
                snapshot.liabilities_cents + snapshot.equity_cents,
            )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_accounting -v
```

Expected: import failure for `ainative.sandbox.accounting`.

- [ ] **Step 3: Implement deterministic document projection**

Map event types to the ten fact tables. Use the event ID as the immutable lineage key and
generate sequential document IDs. Enforce:

```text
order_date <= delivery_date <= sales_invoice_date <= cash_receipt_date
purchase_order_date <= goods_receipt_date <= supplier_invoice_date <= cash_payment_date
```

Open with enough starting finished-goods inventory to prevent baseline negative inventory.
Replenishment must occur before projected stockout.

- [ ] **Step 4: Implement journal posting rules**

For each document:

```python
POSTING_RULES = {
    "sales_delivery": (("5401", "debit"), ("1406", "credit")),
    "sales_invoice": (("1122", "debit"), ("5001", "credit")),
    "cash_receipt": (("1001", "debit"), ("1122", "credit")),
    "goods_receipt": (("1405", "debit"), ("2203", "credit")),
    "supplier_invoice": (("2203", "debit"), ("2202", "credit")),
    "cash_payment": (("2202", "debit"), ("1001", "credit")),
}
```

For each `manufacturing_completion` event, transfer purchased raw-material cost into
finished-goods inventory before product delivery:

```text
Debit 1406 Finished Goods Inventory
Credit 1405 Raw Material Inventory
```

Store this transformation as journal and inventory movements linked to its
`manufacturing_completion` source event. Do not create a published production-order table.

- [ ] **Step 5: Implement financial snapshots as queries**

```python
@dataclass(frozen=True)
class FinancialSnapshot:
    period: str
    revenue_cents: int
    cogs_cents: int
    gross_profit_cents: int
    cash_cents: int
    accounts_receivable_cents: int
    inventory_cents: int
    accounts_payable_cents: int
    assets_cents: int
    liabilities_cents: int
    equity_cents: int
```

Calculate balances cumulatively through the requested period from journal lines. Retained
earnings are current cumulative gross profit in this simplified model.

- [ ] **Step 6: Run accounting tests**

Run:

```bash
python -m unittest tests.sandbox.test_accounting -v
```

Expected: 2 tests pass.

- [ ] **Step 7: Commit when a repository is available**

```bash
git add ainative/sandbox/accounting.py tests/sandbox/test_accounting.py
git commit -m "feat(sandbox): project documents and balanced accounting"
```

---

### Task 6: Consistency and Scenario Validation

**Files:**
- Create: `ainative/sandbox/validation.py`
- Create: `tests/sandbox/test_validation.py`

**Interfaces:**
- Consumes: populated SQLite connection, `ScenarioDefinition`
- Produces: `ValidationIssue`
- Produces: `ValidationReport`
- Produces: `SandboxValidator.validate(conn: sqlite3.Connection, scenario: ScenarioDefinition) -> ValidationReport`
- Produces: `ValidationReport.publishable -> bool`

- [ ] **Step 1: Write failing validation tests**

```python
# tests/sandbox/test_validation.py
import sqlite3
import unittest

from ainative.sandbox.validation import SandboxValidator


class ValidationTest(unittest.TestCase):
    def test_unbalanced_voucher_is_blocking(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "create table fact_journal_entry "
            "(voucher_id text, debit_cents integer, credit_cents integer)"
        )
        conn.execute("insert into fact_journal_entry values ('V1', 100, 0)")
        report = SandboxValidator().validate_journals(conn)
        self.assertFalse(report.publishable)
        self.assertEqual("journal_unbalanced", report.issues[0].code)

    def test_valid_report_is_publishable(self):
        report = SandboxValidator.empty_report()
        self.assertTrue(report.publishable)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_validation -v
```

Expected: import failure for `ainative.sandbox.validation`.

- [ ] **Step 3: Implement typed validation output**

```python
class Severity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"
    SCENARIO_FAILURE = "scenario_failure"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: Severity
    message: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def publishable(self) -> bool:
        return not any(
            issue.severity in (Severity.BLOCKING, Severity.SCENARIO_FAILURE)
            for issue in self.issues
        )
```

- [ ] **Step 4: Implement the ten required checks**

Implement named methods:

```text
validate_journals
validate_accounting_equation
validate_inventory
validate_receivables
validate_payables
validate_cash
validate_lineage
validate_foreign_keys
validate_document_dates
validate_scenario_targets
```

`validate_scenario_targets` compares Q4 2025 with Q4 baseline values recorded before
injection. Publish only when:

```text
15% <= revenue growth <= 22%
-18% <= profit growth <= -8%
```

Return a warning, not a blocking failure, when a distribution has more than 70% of its rows
assigned to one customer, supplier, product, or region.

- [ ] **Step 5: Run validation tests**

Run:

```bash
python -m unittest tests.sandbox.test_validation -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Add a property-style seed test**

Add to `tests/sandbox/test_validation.py`:

```python
def test_twenty_seeds_all_generate_publishable_data(self):
    for seed in range(20):
        result = build_golden_scenario(seed=seed)
        self.assertTrue(result.validation.publishable, (seed, result.validation.issues))
```

The `build_golden_scenario` helper is introduced in Task 7. Keep this test skipped with
`@unittest.skip("enabled by Task 7 service")` until Task 7, then remove the decorator.

- [ ] **Step 7: Commit when a repository is available**

```bash
git add ainative/sandbox/validation.py tests/sandbox/test_validation.py
git commit -m "feat(sandbox): validate accounting and scenario integrity"
```

---

### Task 7: Golden Scenario Service with Bounded Retry

**Files:**
- Create: `ainative/sandbox/service.py`
- Create: `tests/sandbox/test_service.py`
- Modify: `tests/sandbox/test_validation.py`

**Interfaces:**
- Consumes all Tasks 1–6
- Produces: `GenerationResult`
- Produces: `build_golden_scenario(seed: int, output_dir: Path | None = None) -> GenerationResult`
- Produces: `GenerationFailed`

- [ ] **Step 1: Write failing end-to-end service tests**

```python
# tests/sandbox/test_service.py
import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.service import build_golden_scenario


class SandboxServiceTest(unittest.TestCase):
    def test_builds_publishable_reproducible_benchmark(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            first = build_golden_scenario(seed=41, output_dir=Path(left))
            second = build_golden_scenario(seed=41, output_dir=Path(right))

            self.assertTrue(first.validation.publishable)
            self.assertEqual(first.spec.benchmark_id, second.spec.benchmark_id)
            self.assertEqual(first.database_sha256, second.database_sha256)
            self.assertEqual(
                {
                    "raw_material_price_increase",
                    "low_margin_product_mix",
                    "customer_discount_increase",
                },
                set(first.ground_truth.root_causes),
            )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_service -v
```

Expected: import failure for `ainative.sandbox.service`.

- [ ] **Step 3: Implement the orchestration result and failure**

```python
@dataclass(frozen=True)
class GenerationResult:
    spec: ScenarioSpec
    database_path: Path
    database_sha256: str
    ground_truth: GroundTruth
    validation: ValidationReport
    attempt_count: int


class GenerationFailed(RuntimeError):
    def __init__(self, seed: int, attempts: tuple[ValidationReport, ...]):
        super().__init__(f"scenario generation failed after {len(attempts)} attempts")
        self.seed = seed
        self.attempts = attempts
```

- [ ] **Step 4: Implement bounded deterministic retry**

`build_golden_scenario` must:

1. try seed `seed`;
2. on non-publishable output try `seed + 1_000_003`;
3. then try `seed + 2_000_006`;
4. raise `GenerationFailed` after three failed validations;
5. expose the effective seed inside the final `ScenarioSpec`;
6. delete only failed attempt databases created inside its own output directory.

For each attempt load the scenario and construct the simulator with:

```python
scenario = load_scenario(spec.scenario_id)
resolver = lambda period: scenario.parameters_for_period(period, normal_parameters(period))
events = EventSimulator(spec, resolver).generate(conn)
```

Use a transaction per generation attempt. Never return or package an unvalidated database.

- [ ] **Step 5: Enable and run the 20-seed property-style test**

Remove the `skip` decorator added in Task 6.

Run:

```bash
python -m unittest tests.sandbox.test_service tests.sandbox.test_validation -v
```

Expected: service test and 20-seed test pass.

- [ ] **Step 6: Commit when a repository is available**

```bash
git add ainative/sandbox/service.py tests/sandbox/test_service.py tests/sandbox/test_validation.py
git commit -m "feat(sandbox): orchestrate validated golden scenario generation"
```

---

### Task 8: Public Exam Package and Leak Prevention

**Files:**
- Create: `ainative/sandbox/packaging.py`
- Create: `tests/sandbox/test_packaging.py`
- Create: `docs/sandbox/data-dictionary-template.md`
- Create: `config/sandbox/metrics.json`

**Interfaces:**
- Consumes: `GenerationResult`
- Produces: `ExamPackageBuilder.build(result: GenerationResult, destination: Path) -> Path`
- Produces ZIP layout: `data/`, `schema/`, `semantic/`, `task/`, `manifest.json`

- [ ] **Step 1: Write failing package tests**

```python
# tests/sandbox/test_packaging.py
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from ainative.sandbox.packaging import ExamPackageBuilder
from ainative.sandbox.service import build_golden_scenario


class PackagingTest(unittest.TestCase):
    def test_package_contains_public_assets_and_no_ground_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_golden_scenario(seed=51, output_dir=root / "work")
            archive = ExamPackageBuilder().build(result, root / "out")
            with zipfile.ZipFile(archive) as package:
                names = set(package.namelist())
                self.assertIn("data/enterprise.db", names)
                self.assertIn("schema/data_dictionary.md", names)
                self.assertIn("semantic/metrics.json", names)
                self.assertIn("task/analysis_question.md", names)
                self.assertIn("manifest.json", names)
                self.assertFalse(any("ground_truth" in name for name in names))
                combined = b"".join(package.read(name) for name in names if not name.endswith(".db"))
                self.assertNotIn(b"raw_material_price_increase", combined)

    def test_manifest_has_lineage_versions_and_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_golden_scenario(seed=52, output_dir=root / "work")
            archive = ExamPackageBuilder().build(result, root / "out")
            with zipfile.ZipFile(archive) as package:
                manifest = json.loads(package.read("manifest.json"))
                self.assertEqual(result.spec.benchmark_id, manifest["benchmark_id"])
                self.assertEqual(result.database_sha256, manifest["database_sha256"])
                self.assertEqual("1.0.0", manifest["generator_version"])
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_packaging -v
```

Expected: import failure for `ainative.sandbox.packaging`.

- [ ] **Step 3: Implement CSV and ZIP export**

For each published table:

1. query rows ordered by primary key;
2. write UTF-8 with BOM CSV using `newline=""`;
3. include the same validated `enterprise.db`;
4. create one Markdown data dictionary listing columns, types, keys, and descriptions;
5. create `relationships.md`;
6. include `metrics.json` with revenue, COGS, gross profit, gross margin, inventory
   turnover, AR days, and order fulfillment rate;
7. include a neutral task prompt that does not reveal the scenario name.

The task prompt must be:

```markdown
# 制造企业经营分析任务

请识别本期最重要的经营异常，量化异常影响，使用数据证据解释主要原因，并明确列出
仅凭现有数据无法确认、需要业务人员补充的信息。所有确定性结论必须注明数据来源。
```

- [ ] **Step 4: Add explicit leak scanning**

Before closing the ZIP, scan all non-database files for:

```python
PRIVATE_TOKENS = (
    "ground_truth",
    "raw_material_price_increase",
    "low_margin_product_mix",
    "customer_discount_increase",
    "forbidden_claims",
    "contribution",
)
```

Also verify the SQLite database contains only the 15 `PUBLISHED_TABLES`. Raise
`PrivateDataLeak` if a private token or table is found.

- [ ] **Step 5: Run packaging tests**

Run:

```bash
python -m unittest tests.sandbox.test_packaging -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit when a repository is available**

```bash
git add ainative/sandbox/packaging.py tests/sandbox/test_packaging.py docs/sandbox config/sandbox
git commit -m "feat(sandbox): export leak-safe public exam package"
```

---

### Task 9: Structured Agent Answer and Deterministic Score Report

**Files:**
- Create: `ainative/sandbox/scoring.py`
- Create: `tests/sandbox/fixtures/hallucinated_answer.json`
- Create: `tests/sandbox/helpers.py`
- Create: `tests/sandbox/test_scoring.py`

**Interfaces:**
- Consumes: `GroundTruth`, validated SQLite database, answer JSON
- Produces: `AgentAnswer.from_dict(payload: dict[str, object]) -> AgentAnswer`
- Produces: `ScoreReport`
- Produces: `DeterministicScorer.score_database(answer: AgentAnswer, result: GenerationResult) -> ScoreReport`

- [ ] **Step 1: Add a test-only correct-answer builder and hallucinated fixture**

`tests/sandbox/helpers.py` must expose:

```python
def build_correct_answer(result: GenerationResult) -> dict[str, object]:
    """Build a known-correct external answer by querying the generated database."""


def write_correct_answer(benchmark_dir: Path, destination: Path) -> Path:
    """Load private test state, query its database, and write a correct answer fixture."""
```

`build_correct_answer` declares the three expected Cause IDs, queries Q4 revenue, profit,
purchase-price growth, product-line mix, and key-customer discounts from SQLite, cites the
actual table/field pairs, and lists `customer_competition_strategy` as unknown. This helper
is test-only and must never be imported by production sandbox code. Add an `argparse`
entrypoint so `python -m tests.sandbox.helpers --benchmark PATH --output FILE` calls
`write_correct_answer`.

`hallucinated_answer.json` must include:

```json
{
  "anomalies": [{"metric": "gross_profit", "direction": "down"}],
  "causes": [
    {
      "cause": "competitor_price_war",
      "confidence": 0.96,
      "evidence": []
    }
  ],
  "unknowns": [],
  "recommendations": ["立即全面降价"]
}
```

- [ ] **Step 2: Write failing scoring tests**

```python
# tests/sandbox/test_scoring.py
import json
import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.scoring import AgentAnswer, DeterministicScorer
from ainative.sandbox.service import build_golden_scenario
from tests.sandbox.helpers import build_correct_answer


FIXTURES = Path(__file__).parent / "fixtures"


class ScoringTest(unittest.TestCase):
    def test_correct_answer_scores_at_least_ninety(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_golden_scenario(seed=61, output_dir=Path(tmp))
            answer = AgentAnswer.from_dict(build_correct_answer(result))
            report = DeterministicScorer().score_database(answer, result)
            self.assertGreaterEqual(report.total_score, 90)
            self.assertEqual(0, len(report.unsupported_claims))

    def test_hallucinated_cause_is_reported_and_capped_below_sixty(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_golden_scenario(seed=61, output_dir=Path(tmp))
            answer = AgentAnswer.from_dict(
                json.loads((FIXTURES / "hallucinated_answer.json").read_text(encoding="utf-8"))
            )
            report = DeterministicScorer().score_database(answer, result)
            self.assertLess(report.total_score, 60)
            self.assertIn("competitor_price_war", report.unsupported_claims)
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_scoring -v
```

Expected: import failure for `ainative.sandbox.scoring`.

- [ ] **Step 4: Implement strict answer parsing**

Define frozen dataclasses for:

```python
MetricClaim(metric: str, direction: str, magnitude: float | None)
EvidenceClaim(table: str, field: str, value: int | float | str)
CauseClaim(cause: str, confidence: float, evidence: tuple[EvidenceClaim, ...])
AgentAnswer(anomalies: tuple[MetricClaim, ...], causes: tuple[CauseClaim, ...],
            unknowns: tuple[str, ...], recommendations: tuple[str, ...])
```

Reject unknown top-level keys, confidence outside `[0, 1]`, invalid directions, missing
cause evidence arrays, and non-finite numeric values.

- [ ] **Step 5: Implement the scoring weights**

```python
WEIGHTS = {
    "anomaly_detection": 20,
    "numbers_and_metrics": 20,
    "root_cause": 25,
    "evidence": 20,
    "judgment_boundary": 10,
    "recommendations": 5,
}
```

Rules:

- award anomaly points for correct metric and direction;
- use tolerances of 0.5 percentage points for rates and 1% relative error for amounts;
- award cause points proportional to matched Ground Truth contribution;
- award evidence points only when table, field, and value can be reproduced from SQLite;
- award boundary points for stated unknowns;
- subtract 10 points per forbidden claim and cap total score at 59 when any forbidden claim
  is asserted as fact;
- Phase 1 gives all 5 recommendation points when recommendations exist and none directly
  conflict with Ground Truth; it does not judge strategic quality.

- [ ] **Step 6: Run scoring tests**

Run:

```bash
python -m unittest tests.sandbox.test_scoring -v
```

Expected: 2 tests pass.

- [ ] **Step 7: Commit when a repository is available**

```bash
git add ainative/sandbox/scoring.py tests/sandbox/fixtures tests/sandbox/helpers.py tests/sandbox/test_scoring.py
git commit -m "feat(sandbox): score structured agent answers"
```

---

### Task 10: CLI Vertical Slice and Handoff Documentation

**Files:**
- Modify: `ainative/cli.py`
- Modify: `ainative/sandbox/__init__.py`
- Modify: `README.md`
- Create: `docs/sandbox/quickstart.md`
- Create: `tests/sandbox/test_cli.py`

**Interfaces:**
- Produces CLI: `python -m ainative.cli sandbox-generate --seed INT --output PATH`
- Produces CLI: `python -m ainative.cli sandbox-score --benchmark PATH --answer PATH`
- Produces JSON score report on stdout and as `score-report.json`

- [ ] **Step 1: Write failing CLI integration tests**

```python
# tests/sandbox/test_cli.py
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SandboxCliTest(unittest.TestCase):
    def test_generate_and_score_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generated = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ainative.cli",
                    "sandbox-generate",
                    "--seed",
                    "61",
                    "--output",
                    str(root / "exam"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            archive = Path(json.loads(generated.stdout)["archive"])
            self.assertTrue(archive.exists())

            from tests.sandbox.helpers import write_correct_answer
            correct_answer = write_correct_answer(root / "exam", root / "correct_answer.json")

            scored = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ainative.cli",
                    "sandbox-score",
                    "--benchmark",
                    str(root / "exam"),
                    "--answer",
                    str(correct_answer),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            report = json.loads(scored.stdout)
            self.assertGreaterEqual(report["total_score"], 90)
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```bash
python -m unittest tests.sandbox.test_cli -v
```

Expected: CLI rejects unknown command `sandbox-generate`.

- [ ] **Step 3: Implement CLI commands**

`sandbox-generate` must:

1. call `build_golden_scenario`;
2. build the public ZIP;
3. write private Ground Truth beside the working benchmark directory, never inside the ZIP;
4. print one JSON object containing `benchmark_id`, `archive`, `validation`, and
   `effective_seed`.

`sandbox-score` must:

1. load the private benchmark state from the working directory;
2. parse the answer JSON;
3. score against the validated database and Ground Truth;
4. write `score-report.json`;
5. print the same report JSON to stdout.

Return exit code 2 for invalid arguments or answer schema, 3 for generation failure, and 4
for private-state mismatch.

- [ ] **Step 4: Document the exact workflow**

Add to `docs/sandbox/quickstart.md`:

```bash
python -m ainative.cli sandbox-generate \
  --seed 61 \
  --output ./data/benchmarks/revenue-profit

# Give the generated ZIP to the Agent under test, then save its answer as answer.json.

python -m ainative.cli sandbox-score \
  --benchmark ./data/benchmarks/revenue-profit \
  --answer ./answer.json
```

Explain the public/private split, supported answer JSON, score dimensions, reproducibility,
and Phase 1 exclusions.

- [ ] **Step 5: Run the complete test suite**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected:

- all existing AI Native Core tests pass;
- all sandbox tests pass;
- at least 20 different seeds produce publishable data;
- test-generated correct answer scores at least 90;
- hallucinated fixture scores below 60.

- [ ] **Step 6: Perform manual acceptance**

Run:

```bash
python -m ainative.cli sandbox-generate --seed 61 --output /tmp/analytics-sandbox-acceptance
unzip -l /tmp/analytics-sandbox-acceptance/*.zip
python -m tests.sandbox.helpers \
  --benchmark /tmp/analytics-sandbox-acceptance \
  --output /tmp/analytics-sandbox-correct-answer.json
python -m ainative.cli sandbox-score \
  --benchmark /tmp/analytics-sandbox-acceptance \
  --answer /tmp/analytics-sandbox-correct-answer.json
```

Verify:

- the ZIP contains SQLite, all 15 CSVs, dictionary, relationships, metrics, task, manifest;
- the ZIP contains no private Cause ID or Ground Truth;
- the score report names matched causes, missing evidence, unsupported claims, and per-dimension
  points;
- running generation again with seed 61 produces the same database checksum.

- [ ] **Step 7: Commit when a repository is available**

```bash
git add ainative/cli.py ainative/sandbox/__init__.py README.md docs/sandbox tests/sandbox/test_cli.py
git commit -m "feat(sandbox): deliver golden scenario CLI workflow"
```

---

## Phase 1 Completion Gate

Do not start the remaining four scenarios, web pages, model-assisted answer extraction, direct
Agent integrations, or human-review workflow until all of the following are true:

- one golden scenario generates reproducibly across at least 20 seeds;
- every published database passes all ten consistency checks;
- Ground Truth cannot leak into the exam package;
- a correct structured answer scores at least 90;
- a forbidden unsupported cause caps the score below 60;
- the existing AI Native Starter tests remain green;
- one external AI+BI practitioner can complete the generate → analyze → submit → score workflow
  using only the quickstart.
