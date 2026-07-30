from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from .events import OperatingParameters


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

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "observations": list(self.observations),
            "root_causes": list(self.root_causes),
            "contributions": dict(self.contributions),
            "evidence_ids": list(self.evidence_ids),
            "unknowns": list(self.unknowns),
            "forbidden_claims": list(self.forbidden_claims),
        }


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    version: str
    affected_periods: tuple[str, ...]
    target_observations: tuple[tuple[str, float], ...]
    demand_multiplier: float
    causes: tuple[Cause, ...]
    unknowns: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    expected_evidence: tuple[str, ...]

    def parameters_for_period(
        self, period: str, baseline: OperatingParameters
    ) -> OperatingParameters:
        if period not in self.affected_periods:
            return baseline

        values = {
            cause.parameter: cause
            for cause in self.causes
        }
        material = values["core_material_purchase_price"]
        mix = values["value_product_demand_share"]
        discount = values["key_customer_discount_bps"]
        return replace(
            baseline,
            period=period,
            demand_multiplier=baseline.demand_multiplier * self.demand_multiplier,
            value_product_demand_share=min(
                1.0,
                baseline.value_product_demand_share * (mix.multiplier or 1.0),
            ),
            core_material_purchase_price_multiplier=(
                baseline.core_material_purchase_price_multiplier
                * (material.multiplier or 1.0)
            ),
            key_customer_discount_increment_bps=(
                baseline.key_customer_discount_increment_bps
                + (discount.increment or 0)
            ),
        )

    def ground_truth(self) -> GroundTruth:
        return GroundTruth(
            scenario_id=self.scenario_id,
            observations=("revenue_up", "gross_profit_down"),
            root_causes=tuple(cause.cause_id for cause in self.causes),
            contributions=tuple(
                (cause.cause_id, cause.contribution) for cause in self.causes
            ),
            evidence_ids=self.expected_evidence,
            unknowns=self.unknowns,
            forbidden_claims=self.forbidden_claims,
        )

    def target(self, name: str) -> float:
        return dict(self.target_observations)[name]


def load_scenario(scenario_id: str) -> ScenarioDefinition:
    config_path = (
        Path(__file__).resolve().parents[2]
        / "config"
        / "scenarios"
        / f"{scenario_id}.json"
    )
    if not config_path.exists():
        raise ValueError(f"Unsupported scenario: {scenario_id}")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    causes = tuple(Cause(**item) for item in payload["causes"])
    return ScenarioDefinition(
        scenario_id=payload["scenario_id"],
        version=payload["version"],
        affected_periods=tuple(payload["affected_periods"]),
        target_observations=tuple(payload["target_observations"].items()),
        demand_multiplier=payload["operating_changes"]["demand_multiplier"],
        causes=causes,
        unknowns=tuple(payload["unknowns"]),
        forbidden_claims=tuple(payload["forbidden_claims"]),
        expected_evidence=tuple(payload["expected_evidence"]),
    )
