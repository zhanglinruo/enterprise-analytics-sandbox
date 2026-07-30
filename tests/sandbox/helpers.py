from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from ainative.sandbox.scenarios import GroundTruth
from ainative.sandbox.service import GenerationResult
from ainative.sandbox.spec import ScenarioSpec
from ainative.sandbox.validation import ValidationReport


def build_correct_answer(result: GenerationResult) -> dict[str, object]:
    """Build a known-correct external answer by querying the generated database."""
    conn = sqlite3.connect(result.database_path)
    try:
        revenue = conn.execute(
            "select sum(revenue_cents) from fact_sales_invoice "
            "where period between '2025-10' and '2025-12'"
        ).fetchone()[0]
        cogs = conn.execute(
            "select sum(quantity * unit_cost_cents) from fact_sales_delivery "
            "where period between '2025-10' and '2025-12'"
        ).fetchone()[0]
        purchase_price = conn.execute(
            "select max(unit_price_cents) from fact_purchase_order "
            "where period between '2025-10' and '2025-12'"
        ).fetchone()[0]
        product_line = conn.execute(
            "select product_line from dim_product "
            "where product_line = 'VALUE' limit 1"
        ).fetchone()[0]
        discount = conn.execute(
            "select max(discount_rate_bps) from fact_sales_order "
            "where period between '2025-10' and '2025-12'"
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "anomalies": [
            {"metric": "revenue", "direction": "up", "magnitude": revenue},
            {
                "metric": "gross_profit",
                "direction": "down",
                "magnitude": revenue - cogs,
            },
        ],
        "causes": [
            {
                "cause": "raw_material_price_increase",
                "confidence": 0.95,
                "evidence": [
                    {
                        "table": "fact_purchase_order",
                        "field": "unit_price_cents",
                        "value": purchase_price,
                    }
                ],
            },
            {
                "cause": "low_margin_product_mix",
                "confidence": 0.92,
                "evidence": [
                    {
                        "table": "dim_product",
                        "field": "product_line",
                        "value": product_line,
                    }
                ],
            },
            {
                "cause": "customer_discount_increase",
                "confidence": 0.90,
                "evidence": [
                    {
                        "table": "fact_sales_order",
                        "field": "discount_rate_bps",
                        "value": discount,
                    }
                ],
            },
        ],
        "unknowns": ["customer_competition_strategy"],
        "recommendations": ["核查采购价格、产品组合和重点客户折扣政策"],
    }


def write_correct_answer(benchmark_dir: Path, destination: Path) -> Path:
    """Load private test state, query its database, and write a correct answer fixture."""
    state = json.loads(
        (benchmark_dir / "private-state.json").read_text(encoding="utf-8")
    )
    spec = ScenarioSpec.create(
        state["scenario_id"], seed=state["effective_seed"]
    )
    truth_payload = state["ground_truth"]
    truth = GroundTruth(
        scenario_id=truth_payload["scenario_id"],
        observations=tuple(truth_payload["observations"]),
        root_causes=tuple(truth_payload["root_causes"]),
        contributions=tuple(truth_payload["contributions"].items()),
        evidence_ids=tuple(truth_payload["evidence_ids"]),
        unknowns=tuple(truth_payload["unknowns"]),
        forbidden_claims=tuple(truth_payload["forbidden_claims"]),
    )
    database_path = benchmark_dir / "enterprise.db"
    result = GenerationResult(
        spec=spec,
        database_path=database_path,
        database_sha256=hashlib.sha256(database_path.read_bytes()).hexdigest(),
        ground_truth=truth,
        validation=ValidationReport(()),
        attempt_count=state["attempt_count"],
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(build_correct_answer(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_correct_answer(args.benchmark, args.output)


if __name__ == "__main__":
    main()
