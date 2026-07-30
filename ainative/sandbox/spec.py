from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256


SUPPORTED_SCENARIOS = frozenset({"revenue_up_profit_down"})


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
        identity = (
            f"{self.generator_version}:{self.scenario_version}:"
            f"{self.scenario_id}:{self.seed}"
        )
        return f"bench_{sha256(identity.encode()).hexdigest()[:12]}"

    def periods(self) -> tuple[str, ...]:
        year, month = (int(part) for part in self.start_period.split("-"))
        periods: list[str] = []
        for offset in range(self.month_count):
            absolute_month = year * 12 + month - 1 + offset
            period_year, zero_based_month = divmod(absolute_month, 12)
            periods.append(f"{period_year:04d}-{zero_based_month + 1:02d}")
        return tuple(periods)

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "benchmark_id": self.benchmark_id}
