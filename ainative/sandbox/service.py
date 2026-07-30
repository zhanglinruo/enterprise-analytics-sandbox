from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .accounting import AccountingProjector
from .events import EventSimulator, normal_parameters
from .master_data import MasterDataGenerator
from .scenarios import GroundTruth, load_scenario
from .schema import create_database
from .spec import ScenarioSpec
from .validation import SandboxValidator, ValidationReport


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
        super().__init__(
            f"scenario generation failed after {len(attempts)} attempts"
        )
        self.seed = seed
        self.attempts = attempts


class PrivateStateMismatch(RuntimeError):
    pass


def build_golden_scenario(
    seed: int, output_dir: Path | None = None
) -> GenerationResult:
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="analytics-sandbox-"))
    output_dir.mkdir(parents=True, exist_ok=True)
    failed_reports: list[ValidationReport] = []
    seed_offsets = (0, 1_000_003, 2_000_006)

    for attempt_count, offset in enumerate(seed_offsets, start=1):
        effective_seed = seed + offset
        spec = ScenarioSpec.create(
            "revenue_up_profit_down", seed=effective_seed
        )
        attempt_path = output_dir / f".enterprise-attempt-{attempt_count}.db"
        if attempt_path.exists():
            attempt_path.unlink()
        conn = create_database(attempt_path)
        try:
            MasterDataGenerator(spec).populate(conn)
            scenario = load_scenario(spec.scenario_id)
            resolver = lambda period: scenario.parameters_for_period(
                period, normal_parameters(period)
            )
            events = EventSimulator(spec, resolver).generate(conn)
            AccountingProjector().project(conn, events)
            validation = SandboxValidator().validate(conn, scenario)
        finally:
            conn.close()

        if not validation.publishable:
            failed_reports.append(validation)
            attempt_path.unlink(missing_ok=True)
            continue

        database_path = output_dir / "enterprise.db"
        attempt_path.replace(database_path)
        database_sha256 = hashlib.sha256(database_path.read_bytes()).hexdigest()
        return GenerationResult(
            spec=spec,
            database_path=database_path,
            database_sha256=database_sha256,
            ground_truth=scenario.ground_truth(),
            validation=validation,
            attempt_count=attempt_count,
        )

    raise GenerationFailed(seed, tuple(failed_reports))


def write_private_state(result: GenerationResult, benchmark_dir: Path) -> Path:
    state_path = benchmark_dir / "private-state.json"
    payload = {
        "schema_version": "1.0.0",
        "benchmark_id": result.spec.benchmark_id,
        "scenario_id": result.spec.scenario_id,
        "effective_seed": result.spec.seed,
        "attempt_count": result.attempt_count,
        "database_sha256": result.database_sha256,
        "ground_truth": result.ground_truth.to_dict(),
    }
    state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return state_path


def load_generation_result(benchmark_dir: Path) -> GenerationResult:
    state_path = benchmark_dir / "private-state.json"
    database_path = benchmark_dir / "enterprise.db"
    if not state_path.exists() or not database_path.exists():
        raise PrivateStateMismatch("Private state or enterprise database is missing")
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    spec = ScenarioSpec.create(
        payload["scenario_id"], seed=payload["effective_seed"]
    )
    checksum = hashlib.sha256(database_path.read_bytes()).hexdigest()
    if checksum != payload["database_sha256"]:
        raise PrivateStateMismatch("Enterprise database checksum mismatch")
    if spec.benchmark_id != payload["benchmark_id"]:
        raise PrivateStateMismatch("Benchmark identity mismatch")
    truth_payload = payload["ground_truth"]
    ground_truth = GroundTruth(
        scenario_id=truth_payload["scenario_id"],
        observations=tuple(truth_payload["observations"]),
        root_causes=tuple(truth_payload["root_causes"]),
        contributions=tuple(truth_payload["contributions"].items()),
        evidence_ids=tuple(truth_payload["evidence_ids"]),
        unknowns=tuple(truth_payload["unknowns"]),
        forbidden_claims=tuple(truth_payload["forbidden_claims"]),
    )
    return GenerationResult(
        spec=spec,
        database_path=database_path,
        database_sha256=checksum,
        ground_truth=ground_truth,
        validation=ValidationReport(()),
        attempt_count=payload["attempt_count"],
    )
